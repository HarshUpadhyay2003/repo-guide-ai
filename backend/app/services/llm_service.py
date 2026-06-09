import ast
import json
import logging
import re
from typing import Any, Dict

from groq import Groq, GroqError

from app.core.config import settings

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

    def clean_model_response(self, text: str) -> str:
        """Clean raw model output before JSON parsing."""
        cleaned = text.strip()

        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        cleaned = re.sub(r"(?is)<reasoning>.*?</reasoning>", "", cleaned)
        cleaned = re.sub(r"(?is)here is the json:\s*", "", cleaned)
        cleaned = re.sub(r"(?is)^.*?\{", "{", cleaned, count=1)
        cleaned = re.sub(r"\}.*$", "}", cleaned, count=1)

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

    def generate_json(self, prompt: str) -> Dict[str, Any]:
        """Generate structured JSON from a prompt using Groq."""
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt must be a non-empty string.")

        system_prompt = (
            "You are a strict JSON generator. Reply with valid JSON only, "
            "without markdown fences, explanations, or commentary."
        )
        user_prompt = f"{prompt}\nReturn valid JSON only."

        last_error: Exception | None = None

        for attempt in range(1, 4):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content or ""
                parsed = self._extract_json(content)
                logger.info("LLM JSON generation succeeded on attempt %s: %s", attempt, parsed)
                return parsed
            except (GroqError, ValueError, TypeError, json.JSONDecodeError) as exc:
                last_error = exc
                logger.warning(
                    "LLM JSON generation attempt %s failed: %s",
                    attempt,
                    exc,
                )

        raise LLMGenerationError(
            "Failed to generate valid JSON after 3 attempts."
        ) from last_error
