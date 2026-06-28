import json
import logging
import time
from typing import Any, Dict, List

from app.schema.exploration_hints import ExplorationHintsInput, ExplorationHintsOutput
from app.services.llm_service import LLMGenerationError, LLMService
from constants import ENABLE_PERF_DIAGNOSTICS
from app.utils.file_ranking import score_file, get_candidate_files

logger = logging.getLogger(__name__)

COMPRESSED_HINTS_PROMPT = """
Based on the following repository map, available candidate files/directories, and analyzed issue context, suggest exploration hints for a beginner contributor.

Repository Map:
{repository_map}

Candidate Directories:
{candidate_dirs}

Candidate Files:
{candidate_files}

Issue Affected Area: {affected_area}
Issue Difficulty: {difficulty}

Instructions for generating each JSON field:
1. "affected_area": Describe the affected module or layout area.
2. "likely_directories": Identify the most likely directories.
   - CRITICAL: Only choose directories that are present in Candidate Directories.
3. "possible_files": Identify the possible files to explore.
   - CRITICAL: Never invent or guess file names.
   - Only recommend files that are present in Candidate Files.
   - If no relevant files are found in Candidate Files, return an empty list: [].
4. "reasoning": Explain why these are relevant.
5. "confidence": Confidence score from 0 to 100.

Requirements:
- Return ONLY valid JSON.
- Return ALL fields. Never omit any fields.
- If any information is unknown, use empty arrays [] or empty strings "".

Return ONLY valid JSON matching the exact schema below.

EXPECTED JSON SCHEMA:
{{
  "affected_area": "String",
  "likely_directories": ["String", "String"],
  "possible_files": ["String", "String"],
  "reasoning": "String",
  "confidence": Integer
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
            all_files = validated_payload.all_files
            all_dirs = validated_payload.all_dirs

            affected_area = issue_analysis.get("affected_area", "Unknown Area")
            difficulty = issue_analysis.get("difficulty", "Unknown Difficulty")

            # Remove empty map categories to save tokens
            compact_map = {k: v for k, v in repository_map.items() if v}

            # Compile candidate_dirs and candidate_files (capped at 200)
            candidate_dirs = []
            if isinstance(repository_map, dict):
                for paths in repository_map.values():
                    if isinstance(paths, list):
                        candidate_dirs.extend(paths)
            candidate_dirs = sorted(list(set(candidate_dirs)))

            candidate_files = get_candidate_files(all_files, repository_map)

            # Score each candidate file
            issue = validated_payload.issue
            issue_title = issue.get("title", "")
            issue_labels = issue.get("labels", [])
            
            scored_candidates = []
            for f in candidate_files:
                score, reasons = score_file(f, issue_title, affected_area, issue_labels)
                scored_candidates.append((score, f, reasons))

            # Sort by: score DESC, path ASC (tie-break)
            scored_candidates.sort(key=lambda x: (-x[0], x[1]))

            if ENABLE_PERF_DIAGNOSTICS:
                total_candidates = len(candidate_files)
                files_sent = min(25, total_candidates)
                removed_count = max(0, total_candidates - 25)
                print(
                    f"[PERF DIAGNOSTICS]\n"
                    f"Candidate Files Considered: {total_candidates}\n"
                    f"Candidate Files Sent: {files_sent}\n"
                    f"Files Removed By Slice: {removed_count}"
                )
            candidate_files = [x[1] for x in scored_candidates[:25]]

            prompt_start = time.perf_counter()
            prompt = COMPRESSED_HINTS_PROMPT.format(
                repository_map=json.dumps(compact_map, ensure_ascii=False)[:1000],
                affected_area=affected_area,
                difficulty=difficulty,
                candidate_dirs=json.dumps(candidate_dirs, ensure_ascii=False),
                candidate_files=json.dumps(candidate_files, ensure_ascii=False),
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
            
            # --- POST-FILTERING TO PREVENT HALLUCINATIONS ---
            full_dirs_set = set(all_dirs)
            full_files_set = set(all_files)
            if full_dirs_set or full_files_set:
                response["likely_directories"] = [
                    d for d in response.get("likely_directories", []) if d in full_dirs_set
                ]
                response["possible_files"] = [
                    f for f in response.get("possible_files", []) if f in full_files_set
                ]
            
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