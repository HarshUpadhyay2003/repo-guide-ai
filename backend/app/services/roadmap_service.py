import datetime
import json
import logging
import time
from typing import Any, Dict, List

from app.schema.roadmap import RoadmapInput, RoadmapOutput
from app.services.llm_service import LLMService
from constants import ENABLE_PERF_DIAGNOSTICS
from app.utils.file_ranking import score_file, get_candidate_files

logger = logging.getLogger(__name__)


def get_issue_age_days(created_at_str: str | None) -> int:
    if not created_at_str:
        return 30  # Default fallback if missing
    try:
        clean_str = created_at_str
        if clean_str.endswith("Z"):
            clean_str = clean_str[:-1] + "+00:00"
        dt = datetime.datetime.fromisoformat(clean_str)
        if dt.tzinfo is not None:
            now = datetime.datetime.now(datetime.timezone.utc)
        else:
            now = datetime.datetime.now()
        delta = now - dt
        return max(0, delta.days)
    except Exception as e:
        logger.warning("Failed to parse issue created_at string %s: %s", created_at_str, e)
        return 30


def calculate_issue_score(issue: Dict[str, Any]) -> float:
    # 1. Difficulty (Max 40)
    difficulty = issue.get("difficulty", "Unknown")
    if difficulty == "Beginner":
        s_diff = 40.0
    elif difficulty == "Intermediate":
        s_diff = 20.0
    elif difficulty == "Advanced":
        s_diff = 5.0
    else:
        s_diff = 0.0

    # 2. Confidence (Max 20)
    confidence = issue.get("confidence_score", 50)
    try:
        confidence_val = float(confidence)
    except (ValueError, TypeError):
        confidence_val = 50.0
    s_conf = confidence_val * 0.2

    # 3. Presence of "good first issue" (Max 15)
    labels = [str(l).lower() for l in issue.get("labels", [])]
    s_gfi = 15.0 if "good first issue" in labels else 0.0

    # 4. Other Beginner Labels (Max 15)
    beginner_labels = {"help wanted", "beginner", "documentation", "docs", "easy", "starter"}
    matching_labels = [l for l in labels if l in beginner_labels and l != "good first issue"]
    s_label = min(15.0, len(matching_labels) * 5.0)

    # 5. Issue Age Score (Max 10)
    created_at = issue.get("created_at")
    age_days = get_issue_age_days(created_at)
    if age_days <= 7:
        s_age = 10.0
    elif age_days <= 30:
        s_age = 7.0
    elif age_days <= 90:
        s_age = 4.0
    else:
        s_age = 0.0

    return s_diff + s_conf + s_gfi + s_label + s_age


class RoadmapService:
    """Generate a beginner-friendly contributor roadmap deterministically."""

    def __init__(self, llm_service: LLMService | None = None) -> None:
        # Keep parameter signature for backward compatibility, though not used
        self.llm_service = llm_service or LLMService()

    def analyze_roadmap(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a personalized contribution roadmap from repo context and issues deterministically."""
        logger.info("Starting deterministic roadmap generation with payload: %s", payload)

        try:
            roadmap_total_start = time.perf_counter()
            
            validated_payload = RoadmapInput.model_validate(payload)
            repo_summary = validated_payload.repo_summary
            issues = validated_payload.issues
            if not issues:
                print("[INFO] No beginner-friendly issues found. Skipping roadmap generation.")
                return {}
            raw_map = validated_payload.repository_map
            all_files = validated_payload.all_files
            all_dirs = validated_payload.all_dirs

            ranking_start = time.perf_counter()
            # Compact the list of issues and compute scores
            compact_issues = []
            for item in issues:
                raw = item.get("raw_issue", {}) or {}
                analysis = item.get("analysis", {}) or {}
                hints = item.get("exploration_hints", {}) or {}
                
                issue_entry = {
                    "number": raw.get("number"),
                    "title": raw.get("title"),
                    "labels": raw.get("labels", []),
                    "created_at": raw.get("created_at"),
                    "difficulty": analysis.get("difficulty", "Unknown"),
                    "confidence_score": analysis.get("confidence_score", 50),
                    "skills_required": analysis.get("skills_required", []),
                    "affected_area": analysis.get("affected_area", "Unknown"),
                    "likely_directories": hints.get("likely_directories", []),
                    "possible_files": hints.get("possible_files", []),
                    "beginner_explanation": analysis.get("beginner_explanation", "No explanation provided.")
                }
                issue_entry["score"] = calculate_issue_score(issue_entry)
                compact_issues.append(issue_entry)

            # Sort candidate issues by: score DESC, issue number ASC (tie-breaker)
            compact_issues.sort(key=lambda x: (-x["score"], x["number"] or 0))
            ranking_dur = time.perf_counter() - ranking_start

            assembly_start = time.perf_counter()

            # Select best issue to start
            if compact_issues:
                selected_issue = compact_issues[0]
                best_issue_info = {
                    "issue_number": selected_issue["number"] or 1,
                    "title": selected_issue["title"] or "Recommended Issue"
                }
            else:
                # Fallback if no issues
                selected_issue = {
                    "number": 1,
                    "title": "General Repository Setup",
                    "labels": [],
                    "created_at": None,
                    "difficulty": "Beginner",
                    "confidence_score": 100,
                    "skills_required": [],
                    "affected_area": "Repository Root",
                    "likely_directories": [],
                    "possible_files": [],
                    "beginner_explanation": "Get started by setting up the repository and exploring the project structure."
                }
                best_issue_info = {
                    "issue_number": 1,
                    "title": "General Repository Setup"
                }

            # Extract fields for output generation
            issue_title = selected_issue["title"]
            difficulty = selected_issue["difficulty"]
            affected_area = selected_issue["affected_area"]
            skills_required = selected_issue["skills_required"]
            beginner_explanation = selected_issue["beginner_explanation"]
            likely_dirs = selected_issue["likely_directories"]
            possible_files = selected_issue["possible_files"]

            # Filter likely directories and possible files to prevent hallucinations
            full_dirs_set = set(all_dirs)
            full_files_set = set(all_files)
            
            # Extract valid map paths
            valid_map_paths = set()
            if isinstance(raw_map, dict):
                for cat, paths in raw_map.items():
                    if isinstance(paths, list):
                        for p in paths:
                            valid_map_paths.add(p)

            # Standardized filter for files to read first
            # Prioritize possible files, then likely directories
            raw_files_to_read = list(possible_files) + list(likely_dirs)
            
            # Perform exact existence filtering
            files_to_read_first = []
            for path in raw_files_to_read:
                if (path in full_files_set or 
                    path in full_dirs_set or 
                    path in valid_map_paths or 
                    (not full_files_set and not full_dirs_set)):  # Allow local tests with empty sets
                    if path not in files_to_read_first:
                        files_to_read_first.append(path)
            
            # Limit to top 5 files to read first to keep it concise
            files_to_read_first = files_to_read_first[:5]

            # Construct why_this_issue
            skills_str = ", ".join(skills_required) if skills_required else "general development concepts"
            why_this_issue = (
                f"We recommend starting with this issue because it is classified as '{difficulty}' difficulty and focuses on the "
                f"'{affected_area}' area of the repository. Addressing it will help you gain familiarity with "
                f"{skills_str}. {beginner_explanation}"
            )

            # Construct recommended_learning_order
            recommended_learning_order = []
            if likely_dirs:
                recommended_learning_order.append(
                    f"Understand the repository structure, focusing on the key directories: {', '.join(likely_dirs[:2])}"
                )
            else:
                recommended_learning_order.append("Familiarize yourself with the repository folder structure and README.")

            if skills_required:
                recommended_learning_order.append(
                    f"Learn or review the core technologies required for this issue: {', '.join(skills_required)}"
                )
            else:
                recommended_learning_order.append("Review basic contribution standards and workflow setup.")

            recommended_learning_order.append(f"Explore the affected codebase area: '{affected_area}'")

            # Construct contribution_plan
            contribution_plan = [
                "Clone the repository and set up the local development environment.",
                f"Locate the '{affected_area}' module and examine key files: {', '.join(files_to_read_first[:3]) or 'relevant area'}."
            ]
            if issue_title:
                contribution_plan.append(f"Try to reproduce the issue described: '{issue_title}'.")
            contribution_plan.extend([
                f"Implement the changes using {', '.join(skills_required) if skills_required else 'appropriate practices'}.",
                "Write tests to verify your implementation and ensure all existing tests pass.",
                "Open a Pull Request and detail your changes in the PR description."
            ])

            # Construct success_tips
            success_tips = [
                "Start small: focus only on the files recommended for this issue.",
                "Write tests: adding tests increases the chance of your PR being merged.",
                "Ask for feedback: engage with the community or maintainers early if you get stuck."
            ]
            
            # Add language-specific premium tips
            languages_lower = [s.lower() for s in skills_required]
            if any(l in languages_lower for l in ["python", "django", "flask", "fastapi"]):
                success_tips.append("Ensure your code follows PEP 8 styling conventions and has proper type hinting.")
            if any(l in languages_lower for l in ["javascript", "typescript", "react", "nextjs", "node"]):
                success_tips.append("Run the project's linter (e.g., ESLint or Prettier) before submitting your PR.")

            # Build final response structure
            response = {
                "best_issue_to_start": best_issue_info,
                "why_this_issue": why_this_issue,
                "recommended_learning_order": recommended_learning_order,
                "files_to_read_first": files_to_read_first,
                "contribution_plan": contribution_plan,
                "success_tips": success_tips
            }
            assembly_dur = time.perf_counter() - assembly_start

            # Validate against Pydantic schema to ensure absolute compatibility
            validation_start = time.perf_counter()
            roadmap = RoadmapOutput.model_validate(response)
            validation_dur = time.perf_counter() - validation_start
            
            roadmap_total_dur = time.perf_counter() - roadmap_total_start
            
            # Log metrics to console

            # Save to self.metrics if available
            if hasattr(self, "metrics") and isinstance(self.metrics, dict):
                self.metrics["roadmap_ranking"] = ranking_dur
                self.metrics["roadmap_assembly"] = assembly_dur
                self.metrics["roadmap_validation"] = validation_dur
                self.metrics["roadmap_total"] = roadmap_total_dur

            return roadmap.model_dump()

        except Exception as exc:
            logger.exception("Deterministic roadmap generation failed: %s", exc)
            raise RuntimeError("Failed to generate contributor roadmap.") from exc
