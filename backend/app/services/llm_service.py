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

    def generate_json(self, prompt: str, service_name: str = "General") -> Dict[str, Any]:
        """Generate structured JSON from a prompt using Groq."""
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

        try:
            for attempt in range(1, 4):
                attempts = attempt
                if attempt > 1:
                    retry_happened = True

                try:
                    start_req = time.perf_counter()
                    response = self.client.chat.completions.create(
                        model=self.model,
                        temperature=self.temperature,
                        messages=[
                            {"role": "system", "content": system_prompt},
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
                    logger.info("LLM JSON generation succeeded on attempt %s: %s", attempt, parsed)
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
                        final_status=final_status
                    )
                    recorded = True
                    return parsed
                except (GroqError, ValueError, TypeError, json.JSONDecodeError) as exc:
                    last_error = exc

                    exc_str = str(exc).lower()
                    if "json_validate_failed" in exc_str or "failed to validate json" in exc_str:
                        validation_failed = True

                    if "rate_limit_exceeded" in exc_str or "429" in exc_str:
                        match = re.search(r"try again in (\d+\.?\d*)s", exc_str)
                        wait_time = float(match.group(1)) + 1.0 if match else 15.0
                        logger.warning("Rate limit (429) hit for %s on attempt %d. Waiting %.2fs before retry...", service_name, attempt, wait_time)
                        time.sleep(wait_time)
                        continue

                    logger.warning(
                        "LLM JSON generation attempt %s failed: %s",
                        attempt,
                        exc,
                    )

            raise LLMGenerationError(
                "Failed to generate valid JSON after 3 attempts."
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
                    final_status=final_status
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
        final_status: str
    ) -> None:
        with self._lock:
            self._invocations.append({
                "service_name": service_name,
                "duration": duration,
                "attempts": attempts,
                "retry_happened": retry_happened,
                "json_parse_failed": json_parse_failed,
                "validation_failed": validation_failed,
                "final_status": final_status
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
