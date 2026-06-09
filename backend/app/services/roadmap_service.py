import json
import logging
from typing import Any, Dict, List

from app.prompts.contributor_roadmap import CONTRIBUTOR_ROADMAP_PROMPT
from app.schema.roadmap import RoadmapInput, RoadmapOutput
from app.services.llm_service import LLMGenerationError, LLMService

logger = logging.getLogger(__name__)


class RoadmapService:
    """Generate a beginner-friendly contributor roadmap."""

    def __init__(self, llm_service: LLMService | None = None) -> None:
        self.llm_service = llm_service or LLMService()

    def analyze_roadmap(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a personalized contribution roadmap from repo context and issues."""
        logger.info("Starting roadmap generation with payload: %s", payload)

        try:
            validated_payload = RoadmapInput.model_validate(payload)
            repo_summary = validated_payload.repo_summary
            tree_analysis = validated_payload.tree_analysis
            issues = validated_payload.issues

            prompt = CONTRIBUTOR_ROADMAP_PROMPT.format(
                repo_summary=json.dumps(repo_summary, ensure_ascii=False)[:4000],
                tree_analysis=json.dumps(tree_analysis, ensure_ascii=False)[:4000],
                issues=json.dumps(issues, ensure_ascii=False)[:4000],
            )

            logger.info("Sending roadmap prompt to LLM")
            response = self.llm_service.generate_json(prompt)
            roadmap = RoadmapOutput.model_validate(response)

            logger.info("Roadmap generation completed successfully")
            return roadmap.model_dump()
        except (ValueError, TypeError, KeyError, LLMGenerationError, Exception) as exc:
            logger.exception("Roadmap generation failed: %s", exc)
            raise RuntimeError("Failed to generate contributor roadmap.") from exc
