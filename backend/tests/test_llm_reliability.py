import pytest
from unittest.mock import MagicMock, patch
from app.services.llm_service import LLMService, LLMGenerationError
from groq import GroqError, AuthenticationError

def test_llm_retry_on_transient_json_error():
    """Verify that LLMService automatically retries transient JSON validation errors and recovers on attempt 2."""
    with patch("app.services.llm_service.Groq") as mock_groq_class:
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        # Mock attempt 1 failure (transient json_validate_failed), attempt 2 success
        response_fail = MagicMock()
        response_fail.choices = [MagicMock()]
        response_fail.choices[0].message.content = "Invalid JSON response"

        response_success = MagicMock()
        response_success.choices = [MagicMock()]
        response_success.choices[0].message.content = '{"status": "ok", "message": "recovered"}'

        mock_client.chat.completions.create.side_effect = [
            GroqError("json_validate_failed: Failed to generate JSON"),
            response_success
        ]

        llm_service = LLMService(api_key="test_key")
        result = llm_service.generate_json("Test prompt", service_name="TestService")

        assert result == {"status": "ok", "message": "recovered"}
        assert mock_client.chat.completions.create.call_count == 2
        
        # Verify telemetry
        invocations = llm_service._invocations
        assert len(invocations) == 1
        assert invocations[0]["attempts"] == 2
        assert invocations[0]["retry_happened"] is True
        assert invocations[0]["recovery_success"] is True
        assert invocations[0]["failure_category"] == "TRANSIENT_JSON_VALIDATION"

def test_llm_no_retry_on_auth_error():
    """Verify that non-retryable errors (e.g. authentication 401) fail immediately without retrying."""
    with patch("app.services.llm_service.Groq") as mock_groq_class:
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        mock_client.chat.completions.create.side_effect = GroqError("Invalid API key provided (401)")

        llm_service = LLMService(api_key="test_key")
        with pytest.raises(GroqError):
            llm_service.generate_json("Test prompt", service_name="TestAuth")

        # Must fail fast on 1st attempt
        assert mock_client.chat.completions.create.call_count == 1

def test_llm_exhaust_retries_raises_llm_error():
    """Verify that exhausting all 3 attempts raises LLMGenerationError."""
    with patch("app.services.llm_service.Groq") as mock_groq_class:
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        mock_client.chat.completions.create.side_effect = GroqError("max completion tokens reached")

        llm_service = LLMService(api_key="test_key")
        with pytest.raises(LLMGenerationError):
            llm_service.generate_json("Test prompt", service_name="TestExhaust")

        assert mock_client.chat.completions.create.call_count == 3
        invocations = llm_service._invocations
        assert invocations[0]["attempts"] == 3
        assert invocations[0]["final_status"] == "Failure"
