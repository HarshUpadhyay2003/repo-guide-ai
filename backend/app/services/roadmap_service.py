import json
import logging
import time
from typing import Any, Dict, List

from app.schema.roadmap import RoadmapInput, RoadmapOutput
from app.services.llm_service import LLMGenerationError, LLMService

logger = logging.getLogger(__name__)

COMPRESSED_ROADMAP_PROMPT = """
Generate a personalized contributor roadmap for a beginner.

Repository Context: {repo_name} - {repo_desc}

Repository Map:
{repository_map}

Available Issues:
{issues}

Provide the best issue to start with, why, a recommended learning order, files to read first, a contribution plan, and success tips. Return ONLY valid JSON matching the schema.
"""

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
            issues = validated_payload.issues

            # Safely fetch map and compact it
            raw_map = payload.get("repository_map", getattr(validated_payload, "tree_analysis", {}))
            compact_map = {k: v for k, v in raw_map.items() if v} if isinstance(raw_map, dict) else {}
            
            metadata = repo_summary.get("metadata", {})
            
            # Strip massive issue bodies; we only need titles to build a roadmap
            compact_issues = [{"number": i.get("number"), "title": i.get("title"), "labels": i.get("labels")} for i in issues]

            prompt_start = time.perf_counter()
            prompt = COMPRESSED_ROADMAP_PROMPT.format(
                repo_name=metadata.get("name", "Unknown Repo"),
                repo_desc=metadata.get("description", "No description")[:200],
                repository_map=json.dumps(compact_map, ensure_ascii=False)[:1000],
                issues=json.dumps(compact_issues, ensure_ascii=False)[:1000],
            )

            logger.info("Sending roadmap prompt to LLM")
            response = self.llm_service.generate_json(prompt, service_name="Roadmap")
            roadmap = RoadmapOutput.model_validate(response)

            logger.info("Roadmap generation completed successfully")
            return roadmap.model_dump()
        except (ValueError, TypeError, KeyError, LLMGenerationError, Exception) as exc:
            logger.exception("Roadmap generation failed: %s", exc)
            raise RuntimeError("Failed to generate contributor roadmap.") from exc
