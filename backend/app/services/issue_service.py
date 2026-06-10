import json
import logging
import time
from typing import Any, Dict

from app.schema.issue_analysis import IssueAnalysisOutput, IssueInput
from app.services.llm_service import LLMGenerationError, LLMService

logger = logging.getLogger(__name__)

COMPRESSED_ISSUE_PROMPT = """
Analyze this GitHub issue for a beginner contributor.

Repository Context: {repo_name} - {repo_desc}
Issue Title: {title}
Labels: {labels}

Issue Body (Truncated):
{body}

Comments:
{comments}

Provide a beginner-friendly explanation, skills required, affected area, difficulty, and confidence score. Return ONLY valid JSON matching the exact schema below.

EXPECTED JSON SCHEMA:
{{
  "beginner_explanation": "String explaining the issue simply.",
  "skills_required": ["List", "of", "strings", "for", "required", "skills"],
  "affected_area": "String describing the affected module or file.",
  "difficulty": "Beginner | Intermediate | Advanced",
  "confidence_score": Integer from 0 to 100
}}

EXAMPLE OUTPUT:
{{
  "beginner_explanation": "This issue requires fixing a typo in the main header.",
  "skills_required": ["HTML", "CSS"],
  "affected_area": "Frontend UI",
  "difficulty": "Beginner",
  "confidence_score": 95
}}
"""

class IssueService:
    """Generate beginner-friendly explanations for GitHub issues."""

    def __init__(self, llm_service: LLMService | None = None) -> None:
        self.llm_service = llm_service or LLMService()

    def normalize_issue_analysis_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Repairs common schema deviations before Pydantic validation."""
        if "beginner_explanation" not in data:
            if "explanation" in data:
                data["beginner_explanation"] = data.pop("explanation")
            elif "beginner_friendly_explanation" in data:
                data["beginner_explanation"] = data.pop("beginner_friendly_explanation")

        if "affected_area" in data and isinstance(data["affected_area"], list):
            data["affected_area"] = " ".join(str(x) for x in data["affected_area"])

        if "confidence_score" in data and isinstance(data["confidence_score"], str):
            score_str = data["confidence_score"].strip().lower()
            if score_str == "low":
                data["confidence_score"] = 40
            elif score_str == "medium":
                data["confidence_score"] = 70
            elif score_str == "high":
                data["confidence_score"] = 90

        return data

    def analyze_issue(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a GitHub issue and return structured beginner guidance."""
        logger.info("Starting issue analysis for payload: %s", payload)

        try:
            start_total = time.perf_counter()
            
            validated_payload = IssueInput.model_validate(payload)
            issue = validated_payload.issue
            repo_summary = validated_payload.repo_summary
            comments = validated_payload.comments

            # Extract minimal repo context to save tokens
            metadata = repo_summary.get("metadata", {})
            repo_name = metadata.get("name", "Unknown Repo")
            repo_desc = metadata.get("description", "No description")

            prompt_start = time.perf_counter()
            prompt = COMPRESSED_ISSUE_PROMPT.format(
                repo_name=repo_name,
                repo_desc=repo_desc,
                title=issue.get("title", ""),
                body=issue.get("body", "")[:1000],  # Truncate issue body intelligently
                labels=", ".join(issue.get("labels", []) or []),
                comments=json.dumps(comments, ensure_ascii=False)[:500] if comments else "None",
            )
            prompt_dur = time.perf_counter() - prompt_start
            logger.info("[PERF] Issue Analysis Prompt Build Time: %.2fs", prompt_dur)
            logger.info("[TOKENS] Issue Analysis Prompt Chars: %d", len(prompt))

            logger.info("Sending issue analysis prompt to LLM")
            llm_start = time.perf_counter()
            response = self.llm_service.generate_json(prompt, service_name="Issue Analysis")
            llm_dur = time.perf_counter() - llm_start
            logger.info("[PERF] Issue Analysis LLM Call Time: %.2fs", llm_dur)
            logger.info("[TOKENS] Issue Analysis Response Chars: %d", len(str(response)))
            
            val_start = time.perf_counter()
            response = self.normalize_issue_analysis_response(response)
            analysis = IssueAnalysisOutput.model_validate(response)
            val_dur = time.perf_counter() - val_start
            logger.info("[PERF] Issue Analysis Validation Time: %.2fs", val_dur)
            
            total_dur = time.perf_counter() - start_total
            logger.info("[PERF] Issue Analysis Total Analysis Time: %.2fs", total_dur)
            if total_dur > 5.0: logger.warning("[SLOW] Issue Analysis took %.2fs", total_dur)

            logger.info("Issue analysis completed successfully")
            return analysis.model_dump()
        except (ValueError, TypeError, KeyError, LLMGenerationError, Exception) as exc:
            logger.exception("Issue analysis failed: %s", exc)
            raise RuntimeError("Failed to analyze issue.") from exc
