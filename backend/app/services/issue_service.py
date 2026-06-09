import json
import logging
from typing import Any, Dict

from app.prompts.issue_analysis import ISSUE_ANALYSIS_PROMPT
from app.schema.issue_analysis import IssueAnalysisOutput, IssueInput
from app.services.llm_service import LLMGenerationError, LLMService

logger = logging.getLogger(__name__)


class IssueService:
    """Generate beginner-friendly explanations for GitHub issues."""

    def __init__(self, llm_service: LLMService | None = None) -> None:
        self.llm_service = llm_service or LLMService()

    def analyze_issue(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a GitHub issue and return structured beginner guidance."""
        logger.info("Starting issue analysis for payload: %s", payload)

        try:
            validated_payload = IssueInput.model_validate(payload)
            issue = validated_payload.issue
            repo_summary = validated_payload.repo_summary

            prompt = ISSUE_ANALYSIS_PROMPT.format(
                title=issue.get("title", ""),
                body=issue.get("body", ""),
                labels=", ".join(issue.get("labels", []) or []),
                repo_summary=json.dumps(repo_summary, ensure_ascii=False),
            )

            logger.info("Sending issue analysis prompt to LLM")
            response = self.llm_service.generate_json(prompt)
            analysis = IssueAnalysisOutput.model_validate(response)

            logger.info("Issue analysis completed successfully")
            return analysis.model_dump()
        except (ValueError, TypeError, KeyError, LLMGenerationError, Exception) as exc:
            logger.exception("Issue analysis failed: %s", exc)
            raise RuntimeError("Failed to analyze issue.") from exc
