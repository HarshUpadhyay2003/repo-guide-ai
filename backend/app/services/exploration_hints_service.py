import json
import logging
import time
from typing import Any, Dict

from app.schema.exploration_hints import ExplorationHintsInput, ExplorationHintsOutput
from app.services.llm_service import LLMGenerationError, LLMService

logger = logging.getLogger(__name__)

COMPRESSED_HINTS_PROMPT = """
Based on the following repository map and previously analyzed issue context, suggest exploration hints for a beginner contributor.

Repository Map:
{repository_map}

Issue Affected Area: {affected_area}
Issue Difficulty: {difficulty}

Identify the likely directories, possible files, reasoning, and confidence score. Return ONLY valid JSON matching the exact schema below.

EXPECTED JSON SCHEMA:
{{
  "affected_area": "String describing the affected module or file.",
  "likely_directories": ["List", "of", "relevant", "directories"],
  "possible_files": ["List", "of", "relevant", "files"],
  "reasoning": "String explaining why these files/directories are relevant.",
  "confidence": Integer from 0 to 100
}}

EXAMPLE OUTPUT:
{{
  "affected_area": "Frontend UI",
  "likely_directories": ["frontend/src/components", "frontend/src/styles"],
  "possible_files": ["Header.tsx", "Header.css"],
  "reasoning": "The issue involves fixing a typo in the main header component, which is located in these files.",
  "confidence": 90
}}
"""

class ExplorationHintsService:
    """Suggest likely repository areas for beginners to explore."""

    def __init__(self, llm_service: LLMService | None = None) -> None:
        self.llm_service = llm_service or LLMService()
        
    def normalize_exploration_hints_response(self, data: Dict[str, Any], fallback_affected_area: str = "Unknown Area") -> Dict[str, Any]:
        """Repairs common schema deviations before Pydantic validation."""
        if "affected_area" not in data:
            if "area" in data:
                data["affected_area"] = data.pop("area")
            else:
                data["affected_area"] = fallback_affected_area

        if "confidence" not in data:
            if "confidence_score" in data:
                data["confidence"] = data.pop("confidence_score")
            elif "confidenceLevel" in data:
                data["confidence"] = data.pop("confidenceLevel")
            else:
                data["confidence"] = 50

        if isinstance(data.get("confidence"), str):
            score_str = data["confidence"].strip().lower()
            if score_str == "low":
                data["confidence"] = 40
            elif score_str == "medium":
                data["confidence"] = 70
            elif score_str == "high":
                data["confidence"] = 90
            else:
                try:
                    data["confidence"] = int(score_str)
                except ValueError:
                    data["confidence"] = 50

        if "likely_directories" not in data or data["likely_directories"] is None:
            data["likely_directories"] = []
        elif isinstance(data["likely_directories"], str):
            data["likely_directories"] = [data["likely_directories"]]
            
        if "possible_files" not in data or data["possible_files"] is None:
            data["possible_files"] = []
        elif isinstance(data["possible_files"], str):
            data["possible_files"] = [data["possible_files"]]

        return data

    def generate_hints(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze inputs and return structured exploration hints."""
        logger.info("Starting exploration hints generation with payload: %s", payload)

        try:
            start_total = time.perf_counter()
            
            validated_payload = ExplorationHintsInput.model_validate(payload)
            repository_map = validated_payload.repository_map
            issue_analysis = validated_payload.issue_analysis

            affected_area = issue_analysis.get("affected_area", "Unknown Area")
            difficulty = issue_analysis.get("difficulty", "Unknown Difficulty")

            # Remove empty map categories to save tokens
            compact_map = {k: v for k, v in repository_map.items() if v}

            prompt_start = time.perf_counter()
            prompt = COMPRESSED_HINTS_PROMPT.format(
                repository_map=json.dumps(compact_map, ensure_ascii=False)[:1000],
                affected_area=affected_area,
                difficulty=difficulty,
            )
            prompt_dur = time.perf_counter() - prompt_start
            logger.info("[PERF] Exploration Hints Prompt Build Time: %.2fs", prompt_dur)
            logger.info("[TOKENS] Exploration Hints Prompt Chars: %d", len(prompt))

            logger.debug("Exploration Hints generated prompt: %s", prompt)
            logger.info("Sending exploration hints prompt to LLM")
            
            llm_start = time.perf_counter()
            response = self.llm_service.generate_json(prompt, service_name="Exploration Hints")
            llm_dur = time.perf_counter() - llm_start
            logger.info("[PERF] Exploration Hints LLM Call Time: %.2fs", llm_dur)
            logger.info("[TOKENS] Exploration Hints Response Chars: %d", len(str(response)))
            logger.debug("Exploration Hints raw response: %s", response)
            
            val_start = time.perf_counter()
            response = self.normalize_exploration_hints_response(response, fallback_affected_area=affected_area)
            logger.debug("Exploration Hints normalized response: %s", response)
            
            hints = ExplorationHintsOutput.model_validate(response)
            val_dur = time.perf_counter() - val_start
            logger.info("[PERF] Exploration Hints Validation Time: %.2fs", val_dur)

            total_dur = time.perf_counter() - start_total
            logger.info("[PERF] Exploration Hints Total Exploration Hints Time: %.2fs", total_dur)
            if total_dur > 5.0: logger.warning("[SLOW] Exploration Hints took %.2fs", total_dur)

            logger.info("Exploration hints generation completed successfully")
            return hints.model_dump()
            
        except Exception as exc:
            logger.exception("Exploration hints generation failed (Validation/Execution): %s", exc)
            raise RuntimeError(f"Failed to generate exploration hints: {exc}") from exc