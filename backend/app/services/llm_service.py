import ast
import json
import logging
import re
import threading
import time
from typing import Any, Dict

from groq import Groq, GroqError

from app.core.config import settings
from app.services.token_manager import TokenBudgetManager
from app.utils.performance_utils import estimate_tokens

logger = logging.getLogger(__name__)


class LLMGenerationError(RuntimeError):
    """Raised when the LLM cannot produce valid JSON output."""


class LLMService:
    """Thin wrapper around the Groq SDK for JSON generation."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the service with a Groq API key."""
        key = api_key or getattr(settings, "GROQ_API_KEY", None)
        if not key:
            raise ValueError("GROQ_API_KEY is required to initialize LLMService.")

        self.client = Groq(api_key=key)
        self.model = settings.MODEL_NAME
        self.temperature = 0.2
        self.token_manager = TokenBudgetManager()
        self._lock = threading.Lock()
        self._invocations = []

    def clean_model_response(self, text: str) -> str:
        """Clean raw model output before JSON parsing."""
        cleaned = text.strip()

        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        cleaned = re.sub(r"(?is)<reasoning>.*?</reasoning>", "", cleaned)
        cleaned = re.sub(r"(?is)here is the json:\s*", "", cleaned)

        first_brace = cleaned.find('{')
        last_brace = cleaned.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            cleaned = cleaned[first_brace:last_brace + 1]

        return cleaned.strip()

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract and parse JSON from model output with robust fallbacks."""
        raw_text = text or ""
        logger.debug("Raw model output: %s", raw_text)

        cleaned = self.clean_model_response(raw_text)
        logger.debug("Cleaned model output: %s", cleaned)

        try:
            parsed = json.loads(cleaned)
            logger.debug("Parsed JSON output: %s", parsed)
            if isinstance(parsed, dict):
                return parsed
            raise ValueError("Model response did not evaluate to a JSON object.")
        except json.JSONDecodeError as json_exc:
            logger.warning("JSON parsing failed for output: %s", raw_text, exc_info=True)
            try:
                parsed = ast.literal_eval(cleaned)
                logger.debug("Fallback literal_eval output: %s", parsed)
                if isinstance(parsed, dict):
                    return parsed
                raise ValueError("Literal evaluation did not produce a dictionary.")
            except (ValueError, SyntaxError, TypeError) as fallback_exc:
                logger.error(
                    "Both JSON parsing and literal_eval failed. Raw output: %s | Cleaned output: %s",
                    raw_text,
                    cleaned,
                    exc_info=True,
                )
                raise ValueError(
                    f"Model response was not valid JSON. Raw output: {raw_text}"
                ) from fallback_exc

    def _is_retryable_error(self, exc: Exception) -> tuple[bool, str, str]:
        """
        Classify an exception from an LLM call.
        Returns: (is_retryable: bool, reason: str, category: str)
        """
        exc_str = str(exc).lower()

        # 1. Non-retryable authentication & authorization errors
        if any(term in exc_str for term in ["invalid api key", "authentication", "permission_denied", "401", "403"]):
            return False, "Authentication/Authorization error", "NON_RETRYABLE_AUTH"

        # 2. Non-retryable prompt/parameter errors
        if isinstance(exc, ValueError) and ("prompt must be" in exc_str or "required" in exc_str):
            return False, "Invalid prompt parameter", "NON_RETRYABLE_PARAM"

        # 3. Rate Limit (429)
        if "rate_limit" in exc_str or "429" in exc_str or "rate limit" in exc_str:
            return True, "Rate limit exceeded (429)", "TRANSIENT_RATE_LIMIT"

        # 4. JSON validation / max tokens truncation
        if any(term in exc_str for term in [
            "json_validate_failed",
            "failed to generate json",
            "failed to validate json",
            "max completion tokens reached",
            "max_tokens",
            "truncated",
            "json_object",
            "not valid json",
            "did not evaluate to a json object",
            "did not produce a dictionary"
        ]) or isinstance(exc, (json.JSONDecodeError, SyntaxError)):
            if "max completion tokens" in exc_str or "max_tokens" in exc_str:
                return True, "Max completion tokens reached", "TRANSIENT_MAX_TOKENS"
            return True, "JSON validation/parse failure", "TRANSIENT_JSON_VALIDATION"

        # 5. Connection / Timeout / Server errors (500, 502, 503, 504, socket errors)
        if any(term in exc_str for term in [
            "timeout",
            "connection",
            "connect",
            "network",
            "500", "502", "503", "504",
            "internal server error",
            "bad gateway",
            "service unavailable"
        ]) or isinstance(exc, (TimeoutError, ConnectionError, OSError)):
            return True, "Network/Server transient error", "TRANSIENT_SERVER_ERROR"

        # Default fallback for GroqError or JSON errors: treat as retryable generation failure
        if isinstance(exc, (GroqError, json.JSONDecodeError, ValueError, TypeError)):
            return True, f"Transient LLM error ({type(exc).__name__})", "TRANSIENT_OTHER"

        return False, f"Unhandled non-retryable error ({type(exc).__name__})", "NON_RETRYABLE_OTHER"

    def generate_json(self, prompt: str, service_name: str = "General") -> Dict[str, Any]:
        """Generate structured JSON from a prompt using Groq with automatic retry resilience."""
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt must be a non-empty string.")

        system_prompt = (
            "You are a strict JSON generator. Reply with valid JSON only, "
            "without markdown fences, explanations, or commentary."
        )
        user_prompt = f"{prompt}\nReturn valid JSON only."

        last_error: Exception | None = None

        start_invocation = time.perf_counter()
        attempts = 0
        retry_happened = False
        json_parse_failed = False
        validation_failed = False
        final_status = "Failure"
        recorded = False
        last_reason = "None"
        last_category = "NONE"

        # Backoff intervals for non-429 retries (in seconds): Attempt 1 -> 0.5s -> Attempt 2 -> 1.0s -> Attempt 3
        backoffs = [0.5, 1.0]

        try:
            for attempt in range(1, 4):
                attempts = attempt
                if attempt > 1:
                    retry_happened = True

                # Adaptive recovery prompt on retries for JSON validation/token truncation errors
                current_system_prompt = system_prompt
                if attempt > 1 and last_category in ("TRANSIENT_JSON_VALIDATION", "TRANSIENT_MAX_TOKENS"):
                    current_system_prompt = (
                        "You are a strict, ultra-concise JSON generator. "
                        "Reply ONLY with valid, compact JSON, without markdown fences or explanations."
                    )

                try:
                    start_req = time.perf_counter()
                    response = self.client.chat.completions.create(
                        model=self.model,
                        temperature=self.temperature,
                        messages=[
                            {"role": "system", "content": current_system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        response_format={"type": "json_object"},
                    )
                    req_dur = time.perf_counter() - start_req
                    content = response.choices[0].message.content or ""
                    if service_name == "Roadmap":
                        print(f"ROADMAP RAW RESPONSE: {content}", flush=True)
                        logger.info("ROADMAP RAW RESPONSE: %s", content)

                    start_ext = time.perf_counter()
                    try:
                        parsed = self._extract_json(content)
                    except Exception:
                        json_parse_failed = True
                        raise

                    ext_dur = time.perf_counter() - start_ext
                    logger.info("LLM JSON generation succeeded on attempt %s (service: %s)", attempt, service_name)
                    logger.info("[LLM PERF INTERNAL]\nService: %s\nModel Response: %.2fs\nJSON Extraction: %.2fs", service_name, req_dur, ext_dur)

                    prompt_chars = len(prompt)
                    resp_chars = len(content)
                    prompt_tokens = estimate_tokens(prompt)
                    resp_tokens = estimate_tokens(content)

                    logger.info("[TOKEN PERF]\nService: %s\n\nPrompt Chars: %d\nPrompt Tokens: %d\n\nResponse Chars: %d\nResponse Tokens: %d\n", service_name, prompt_chars, prompt_tokens, resp_chars, resp_tokens)

                    self.token_manager.record_usage(service_name, prompt, content)

                    final_status = "Success"
                    duration = time.perf_counter() - start_invocation
                    self._record_invocation(
                        service_name=service_name,
                        duration=duration,
                        attempts=attempts,
                        retry_happened=retry_happened,
                        json_parse_failed=json_parse_failed,
                        validation_failed=validation_failed,
                        final_status=final_status,
                        retry_reason=last_reason,
                        failure_category=last_category,
                    )
                    recorded = True
                    return parsed

                except Exception as exc:
                    last_error = exc
                    is_retryable, reason, category = self._is_retryable_error(exc)
                    last_reason = reason
                    last_category = category

                    if category == "TRANSIENT_JSON_VALIDATION":
                        validation_failed = True

                    logger.warning(
                        "LLM JSON generation attempt %d/3 for %s failed [%s]: %s",
                        attempt,
                        service_name,
                        category,
                        exc,
                    )

                    # Non-retryable error -> Raise immediately without wasting retries
                    if not is_retryable:
                        logger.error("Non-retryable LLM error encountered for %s: %s", service_name, exc)
                        raise

                    # If this was the final attempt (attempt == 3), do not sleep; loop ends
                    if attempt >= 3:
                        break

                    # Determine backoff duration
                    exc_str = str(exc).lower()
                    if category == "TRANSIENT_RATE_LIMIT":
                        match = re.search(r"try again in (\d+\.?\d*)s", exc_str)
                        wait_time = float(match.group(1)) + 1.0 if match else 15.0
                        logger.warning("Rate limit (429) hit for %s on attempt %d. Waiting %.2fs before retry...", service_name, attempt, wait_time)
                        time.sleep(wait_time)
                    else:
                        sleep_dur = backoffs[attempt - 1]
                        logger.info("Retrying %s (attempt %d/3) after %.2fs backoff due to %s...", service_name, attempt + 1, sleep_dur, reason)
                        time.sleep(sleep_dur)

            raise LLMGenerationError(
                f"Failed to generate valid JSON for {service_name} after 3 attempts. Last error: {last_error}"
            ) from last_error

        except Exception:
            if not recorded:
                duration = time.perf_counter() - start_invocation
                self._record_invocation(
                    service_name=service_name,
                    duration=duration,
                    attempts=attempts,
                    retry_happened=retry_happened,
                    json_parse_failed=json_parse_failed,
                    validation_failed=validation_failed,
                    final_status=final_status,
                    retry_reason=last_reason,
                    failure_category=last_category,
                )
            raise

    def _record_invocation(
        self,
        service_name: str,
        duration: float,
        attempts: int,
        retry_happened: bool,
        json_parse_failed: bool,
        validation_failed: bool,
        final_status: str,
        retry_reason: str = "None",
        failure_category: str = "NONE",
    ) -> None:
        with self._lock:
            self._invocations.append({
                "service_name": service_name,
                "duration": duration,
                "attempts": attempts,
                "retry_happened": retry_happened,
                "json_parse_failed": json_parse_failed,
                "validation_failed": validation_failed,
                "final_status": final_status,
                "retry_reason": retry_reason,
                "failure_category": failure_category,
                "recovery_success": retry_happened and final_status == "Success",
                "final_latency": duration,
            })

    def print_reliability_summary(self) -> None:
        """Print LLM Reliability Summary to console."""
        with self._lock:
            invocations = list(self._invocations)

        calls = len(invocations)
        if calls == 0:
            print("==============================")
            print("LLM RELIABILITY SUMMARY")
            print("==============================")
            print()
            print("No LLM calls made during this request.")
            print()
            print("==============================")
            return

        successful = sum(1 for inv in invocations if inv["final_status"] == "Success")
        failures = sum(1 for inv in invocations if inv["final_status"] == "Failure")
        retried = sum(1 for inv in invocations if inv["retry_happened"])
        recoveries = sum(1 for inv in invocations if inv.get("recovery_success", False))
        retry_attempts = sum(inv["attempts"] - 1 for inv in invocations)
        parse_failures = sum(1 for inv in invocations if inv["json_parse_failed"])
        validation_failures = sum(1 for inv in invocations if inv["validation_failed"])

        durations = [inv["duration"] for inv in invocations]
        avg_call_time = sum(durations) / calls if durations else 0.0
        longest_call = max(durations) if durations else 0.0
        shortest_call = min(durations) if durations else 0.0

        success_rate = (successful / calls) * 100 if calls > 0 else 0.0
        retry_rate = (retried / calls) * 100 if calls > 0 else 0.0

        print("==============================")
        print("LLM RELIABILITY SUMMARY")
        print("==============================")
        print()
        print(f"Calls: {calls}")
        print()
        print(f"Successful: {successful}")
        print()
        print(f"Retried: {retried}")
        print()
        print(f"Automatic Recoveries: {recoveries}")
        print()
        print(f"Retry Attempts: {retry_attempts}")
        print()
        print(f"Failures: {failures}")
        print()
        print(f"Parse Failures: {parse_failures}")
        print()
        print(f"Validation Failures: {validation_failures}")
        print()
        print(f"Average Call Time: {avg_call_time:.2f}s")
        print()
        print(f"Longest Call: {longest_call:.2f}s")
        print()
        print(f"Shortest Call: {shortest_call:.2f}s")
        print()
        print(f"Success Rate: {success_rate:.1f}%")
        print()
        print(f"Retry Rate: {retry_rate:.1f}%")
        print()
        print("==============================")
