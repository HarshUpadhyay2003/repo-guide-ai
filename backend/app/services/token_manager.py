import logging
from typing import Dict

logger = logging.getLogger(__name__)

class TokenBudgetManager:
    def __init__(self) -> None:
        self.usage: Dict[str, Dict[str, int]] = {}
        self.total_estimated_tokens: int = 0

    def estimate_tokens(self, text: str) -> int:
        """Rough estimation: 1 token ~= 4 characters."""
        return len(str(text)) // 4

    def record_usage(self, service_name: str, prompt: str, response: str = "") -> None:
        prompt_tokens = self.estimate_tokens(prompt)
        completion_tokens = self.estimate_tokens(response)
        total = prompt_tokens + completion_tokens

        if service_name not in self.usage:
            self.usage[service_name] = {"prompt": 0, "completion": 0, "total": 0}

        self.usage[service_name]["prompt"] += prompt_tokens
        self.usage[service_name]["completion"] += completion_tokens
        self.usage[service_name]["total"] += total
        self.total_estimated_tokens += total

        logger.info(
            "Token Budget [%s]: %d tokens used.", service_name, total
        )