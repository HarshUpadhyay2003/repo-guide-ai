import json
import logging
import time
from typing import Any, Dict, List

from app.schema.issue_guidance import IssueGuidanceInput, IssueGuidanceOutput
from app.services.llm_service import LLMGenerationError, LLMService
from app.utils.file_ranking import score_file, get_candidate_files
from constants import ENABLE_PERF_DIAGNOSTICS
from app.utils.performance_utils import estimate_tokens

logger = logging.getLogger(__name__)

COMPRESSED_GUIDANCE_PROMPT = """
Analyze this GitHub issue and suggest exploration hints for a beginner contributor.

Repository Context: {repo_name} - {repo_desc}

Repository Map:
{repository_map}

Candidate Directories:
{candidate_dirs}

Candidate Files:
{candidate_files}

Issue Title: {title}
Labels: {labels}

Issue Body (Truncated):
{body}

Comments:
{comments}

Instructions for generating each JSON field:
1. "analysis":
   - "beginner_explanation": Explain the issue simply for a beginner.
   - "skills_required": List of required skills (e.g. Python, React).
   - "affected_area": Module or layout area affected.
   - "difficulty": Must be "Beginner", "Intermediate", or "Advanced".
   - "confidence_score": Confidence score from 0 to 100.
2. "exploration_hints":
   - "affected_area": Module or layout area affected.
   - "likely_directories": Most likely directories (CRITICAL: Must be selected from Candidate Directories).
   - "possible_files": Possible files to explore (CRITICAL: Must be selected from Candidate Files. Never invent or guess file names).
   - "reasoning": Explain why these are relevant.
   - "confidence": Confidence score from 0 to 100.

Return ONLY valid JSON matching the exact schema below.

EXPECTED JSON SCHEMA:
{{
  "analysis": {{
    "beginner_explanation": "String",
    "skills_required": ["String", "String"],
    "affected_area": "String",
    "difficulty": "Beginner | Intermediate | Advanced",
    "confidence_score": Integer
  }},
  "exploration_hints": {{
    "affected_area": "String",
    "likely_directories": ["String", "String"],
    "possible_files": ["String", "String"],
    "reasoning": "String",
    "confidence": Integer
  }}
}}
"""

class IssueGuidanceService:
    """Analyze GitHub issues and generate exploration hints in a single LLM request."""

    def __init__(self, llm_service: LLMService | None = None) -> None:
        self.llm_service = llm_service or LLMService()

    def normalize_guidance_response(self, data: Dict[str, Any], fallback_affected_area: str = "Unknown Area") -> Dict[str, Any]:
        """Repairs common schema deviations before Pydantic validation."""
        # Normalize the "analysis" sub-object
        analysis = data.get("analysis", {})
        if not isinstance(analysis, dict):
            analysis = {}
            data["analysis"] = analysis
            
        if "beginner_explanation" not in analysis:
            if "explanation" in analysis:
                analysis["beginner_explanation"] = analysis.pop("explanation")
            elif "beginner_friendly_explanation" in analysis:
                analysis["beginner_explanation"] = analysis.pop("beginner_friendly_explanation")
            else:
                analysis["beginner_explanation"] = "No explanation provided."

        if "affected_area" in analysis and isinstance(analysis["affected_area"], list):
            analysis["affected_area"] = " ".join(str(x) for x in analysis["affected_area"])
        elif "affected_area" not in analysis:
            analysis["affected_area"] = fallback_affected_area

        if "confidence_score" in analysis and isinstance(analysis["confidence_score"], str):
            score_str = analysis["confidence_score"].strip().lower()
            if score_str == "low":
                analysis["confidence_score"] = 40
            elif score_str == "medium":
                analysis["confidence_score"] = 70
            elif score_str == "high":
                analysis["confidence_score"] = 90
            else:
                analysis["confidence_score"] = 50
        elif "confidence_score" not in analysis:
            analysis["confidence_score"] = 50

        if "skills_required" not in analysis:
            analysis["skills_required"] = []
        if "difficulty" not in analysis:
            analysis["difficulty"] = "Beginner"

        # Normalize the "exploration_hints" sub-object
        hints = data.get("exploration_hints", {})
        if not isinstance(hints, dict):
            hints = {}
            data["exploration_hints"] = hints

        if "affected_area" not in hints:
            hints["affected_area"] = fallback_affected_area

        if "confidence" not in hints:
            if "confidence_score" in hints:
                hints["confidence"] = hints.pop("confidence_score")
            elif "confidenceLevel" in hints:
                hints["confidence"] = hints.pop("confidenceLevel")
            else:
                hints["confidence"] = 50

        if isinstance(hints.get("confidence"), str):
            score_str = hints["confidence"].strip().lower()
            if score_str == "low":
                hints["confidence"] = 40
            elif score_str == "medium":
                hints["confidence"] = 70
            elif score_str == "high":
                hints["confidence"] = 90
            else:
                try:
                    hints["confidence"] = int(score_str)
                except ValueError:
                    hints["confidence"] = 50
        elif "confidence" not in hints:
            hints["confidence"] = 50

        if "likely_directories" not in hints or hints["likely_directories"] is None:
            hints["likely_directories"] = []
        elif isinstance(hints["likely_directories"], str):
            hints["likely_directories"] = [hints["likely_directories"]]
            
        if "possible_files" not in hints or hints["possible_files"] is None:
            hints["possible_files"] = []
        elif isinstance(hints["possible_files"], str):
            hints["possible_files"] = [hints["possible_files"]]

        if "reasoning" not in hints:
            hints["reasoning"] = "No reasoning provided."

        return data

    def generate_guidance(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze issue and generate exploration hints in a single LLM request."""
        logger.info("Starting issue guidance generation with payload: %s", payload)

        try:
            start_total = time.perf_counter()
            
            validated_payload = IssueGuidanceInput.model_validate(payload)
            issue = validated_payload.issue
            repo_summary = validated_payload.repo_summary
            repository_map = validated_payload.repository_map
            comments = validated_payload.comments
            all_files = validated_payload.all_files
            all_dirs = validated_payload.all_dirs

            metadata = repo_summary.get("metadata", {})
            repo_name = metadata.get("name", "Unknown Repo")
            repo_desc = metadata.get("description", "No description")

            # Remove empty map categories to save tokens
            compact_map = {k: v for k, v in repository_map.items() if v}

            # Compile candidate_dirs and candidate_files (capped at 200)
            candidate_dirs = []
            if isinstance(repository_map, dict):
                for paths in repository_map.values():
                    if isinstance(paths, list):
                        candidate_dirs.extend(paths)
            candidate_dirs = sorted(list(set(candidate_dirs)))

            # Use optimized C-speed candidate files filtering
            candidate_files = get_candidate_files(all_files, repository_map)

            # Score each candidate file using relevance-based ranking
            issue_title = issue.get("title", "")
            issue_labels = issue.get("labels", [])
            
            # Use combined title/labels for file scoring.
            scored_candidates = []
            for f in candidate_files:
                score, reasons = score_file(f, issue_title, "", issue_labels)
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

            # Apply [:25] after sorting by relevance
            candidate_files = [x[1] for x in scored_candidates[:25]]

            prompt_start = time.perf_counter()
            prompt = COMPRESSED_GUIDANCE_PROMPT.format(
                repo_name=repo_name,
                repo_desc=repo_desc,
                repository_map=json.dumps(compact_map, ensure_ascii=False)[:1000],
                candidate_dirs=json.dumps(candidate_dirs, ensure_ascii=False),
                candidate_files=json.dumps(candidate_files, ensure_ascii=False),
                title=issue_title,
                body=issue.get("body", "")[:1000],
                labels=", ".join(issue_labels),
                comments=json.dumps(comments, ensure_ascii=False)[:500] if comments else "None",
            )
            prompt_dur = time.perf_counter() - prompt_start
            logger.info("[PERF] Issue Guidance Prompt Build Time: %.2fs", prompt_dur)
            logger.info("[TOKENS] Issue Guidance Prompt Chars: %d", len(prompt))

            # Audit diagnostics print
            approx_tokens = estimate_tokens(prompt)
            issue_number = issue.get("number", "")
            print(f"[LLM PROMPT]\n\nIssue: #{issue_number}\nPrompt Tokens: {approx_tokens}\n")

            logger.info("Sending issue guidance prompt to LLM")
            llm_start = time.perf_counter()
            response = self.llm_service.generate_json(prompt, service_name="Issue Guidance")
            llm_dur = time.perf_counter() - llm_start
            logger.info("[PERF] Issue Guidance LLM Call Time: %.2fs", llm_dur)
            logger.info("[TOKENS] Issue Guidance Response Chars: %d", len(str(response)))

            val_start = time.perf_counter()
            response = self.normalize_guidance_response(response, fallback_affected_area="Unknown Area")
            
            # --- POST-FILTERING TO PREVENT HALLUCINATIONS ---
            full_dirs_set = set(all_dirs)
            full_files_set = set(all_files)
            if full_dirs_set or full_files_set:
                exploration_hints = response.get("exploration_hints", {})
                if isinstance(exploration_hints, dict):
                    exploration_hints["likely_directories"] = [
                        d for d in exploration_hints.get("likely_directories", []) if d in full_dirs_set
                    ]
                    exploration_hints["possible_files"] = [
                        f for f in exploration_hints.get("possible_files", []) if f in full_files_set
                    ]

            guidance = IssueGuidanceOutput.model_validate(response)
            val_dur = time.perf_counter() - val_start
            logger.info("[PERF] Issue Guidance Validation Time: %.2fs", val_dur)

            total_dur = time.perf_counter() - start_total
            logger.info("[PERF] Issue Guidance Total Time: %.2fs", total_dur)
            if total_dur > 5.0: logger.warning("[SLOW] Issue Guidance took %.2fs", total_dur)

            # Record profiling metrics for Stage 7.2
            if hasattr(self, "metrics") and isinstance(self.metrics, dict):
                if "guidance_runs" not in self.metrics:
                    self.metrics["guidance_runs"] = []
                self.metrics["guidance_runs"].append({
                    "prompt_tokens": approx_tokens,
                    "guidance_time": total_dur,
                    "response_tokens": estimate_tokens(json.dumps(response)) if response else 0,
                    "issue_number": issue.get("number") if isinstance(issue, dict) else getattr(issue, "number", 0)
                })

            logger.info("Issue guidance generation completed successfully")
            return guidance.model_dump()

        except Exception as exc:
            logger.exception("Issue guidance generation failed (Validation/Execution): %s", exc)
            raise RuntimeError(f"Failed to generate issue guidance: {exc}") from exc
