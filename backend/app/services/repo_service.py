import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from app.prompts.repo_summary import REPO_SUMMARY_PROMPT
from app.services.github_service import GitHubService
from app.services.issue_service import IssueService
from app.services.llm_service import LLMGenerationError, LLMService
from app.services.exploration_hints_service import ExplorationHintsService
from app.services.roadmap_service import RoadmapService
from app.services.repository_map_service import RepositoryMapService
from app.utils.github_parser import parse_github_url
from constants import MAX_ANALYSIS_ISSUES, ENABLE_PARALLEL_ANALYSIS

logger = logging.getLogger(__name__)


class RepoService:
    """Coordinate repository analysis using GitHub and LLM services."""

    def __init__(self) -> None:
        self.github_service = GitHubService()
        self.llm_service = LLMService()
        self.repository_map_service = RepositoryMapService(self.github_service)
        self.issue_service = IssueService(self.llm_service)
        self.exploration_hints_service = ExplorationHintsService(self.llm_service)
        self.roadmap_service = RoadmapService(self.llm_service)

    def _analyze_issue_entry(self, owner: str, repo: str, issue: Dict[str, Any], summary: Dict[str, Any], repository_map: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze one issue entry and degrade gracefully on failure."""
        issue_number = issue.get("number")
        comments = []
        
        if issue_number:
            try:
                comments = self.github_service.get_issue_comments(owner, repo, issue_number)
            except Exception as exc:
                logger.warning("Failed to fetch comments for issue #%s: %s", issue_number, exc)

        analysis = None
        exploration_hints = None
        issue_payload = {
            "title": issue.get("title", ""),
            "body": issue.get("body", ""),
            "labels": issue.get("labels", []),
        }

        try:
            logger.warning("[DEBUG] ANALYZING ISSUE -> repo=%s issue=%s", repo, issue.get("number"))
            analysis = self.issue_service.analyze_issue(
                {
                    "issue": issue_payload,
                    "repo_summary": summary,
                    "repository_map": repository_map,
                    "comments": comments,
                }
            )
        except Exception as exc:
            logger.warning("Issue analysis failed for #%s: %s", issue.get("number", "?"), exc)

        if analysis:
            try:
                logger.warning("[DEBUG] HINTS INPUT -> repo=%s affected_area=%s", repo, analysis.get("affected_area"))
                exploration_hints = self.exploration_hints_service.generate_hints(
                    {
                        "repository_map": repository_map,
                        "issue_analysis": analysis,
                        "issue": issue_payload,
                        "comments": comments,
                    }
                )
            except Exception as exc:
                logger.warning("Exploration hints generation failed for #%s: %s", issue.get("number", "?"), exc)

        return {
            "raw_issue": issue,
            "analysis": analysis,
            "exploration_hints": exploration_hints,
        }

    def analyze_repository(self, url: str, mode: str = "FAST_MVP") -> Dict[str, Any]:
        """Analyze a GitHub repository and return structured guidance."""
        started_at = time.perf_counter()
        logger.info("Starting repository analysis for URL: %s", url)

        try:
            parsed = parse_github_url(url)
            owner = parsed["owner"]
            repo = parsed["repo"]
            logger.warning("[DEBUG] PARSER -> URL=%s OWNER=%s REPO=%s", url, owner, repo)

            start = time.perf_counter()
            metadata = self.github_service.get_repo_metadata(owner, repo)
            duration = time.perf_counter() - start
            logger.info("[PERF] Metadata Fetch: %.2fs", duration)
            logger.warning("[DEBUG] METADATA RETURNED -> name=%s stars=%s", metadata.get("name"), metadata.get("stars"))
            if duration > 5.0:
                logger.warning("[SLOW] Metadata Fetch took %.2fs", duration)

            start = time.perf_counter()
            readme = self.github_service.get_readme(owner, repo)
            readme = (readme or "")[:10000]
            duration = time.perf_counter() - start
            logger.info("[PERF] README Fetch: %.2fs", duration)
            if duration > 5.0:
                logger.warning("[SLOW] README Fetch took %.2fs", duration)

            start = time.perf_counter()
            contributing = self.github_service.get_contributing(owner, repo)
            contributing = (contributing or "")[:5000]
            duration = time.perf_counter() - start
            logger.info("[PERF] CONTRIBUTING Fetch: %.2fs", duration)
            if duration > 5.0:
                logger.warning("[SLOW] CONTRIBUTING Fetch took %.2fs", duration)

            logger.warning("[DEBUG] SUMMARY INPUT -> repo=%s description=%s", metadata.get("name"), metadata.get("description"))
            summary_prompt = REPO_SUMMARY_PROMPT.format(
                readme=readme or "",
                contributing=contributing or "",
                metadata=metadata,
            )
            start = time.perf_counter()
            summary = self.llm_service.generate_json(summary_prompt, service_name="Repository Summary")
            duration = time.perf_counter() - start
            logger.info("[PERF] Repository Summary Generation: %.2fs", duration)
            if duration > 5.0:
                logger.warning("[SLOW] Repository Summary Generation took %.2fs", duration)

            start = time.perf_counter()
            logger.warning("[DEBUG] MAP INPUT -> owner=%s repo=%s", owner, repo)
            repository_map = {}
            try:
                repository_map = self.repository_map_service.generate_map(owner=owner, repo=repo)
            except Exception as exc:
                logger.warning("Repository map generation failed for %s/%s: %s", owner, repo, exc)
                repository_map = {
                    "frontend": [],
                    "backend": [],
                    "tests": [],
                    "docs": [],
                    "config": [],
                    "scripts": [],
                    "other": []
                }
            duration = time.perf_counter() - start
            logger.info("[PERF] Repository Map Generation: %.2fs", duration)
            if duration > 5.0:
                logger.warning("[SLOW] Repository Map Generation took %.2fs", duration)
            logger.warning("[DEBUG] MAP GENERATED -> frontend=%d backend=%d", len(repository_map.get("frontend", [])), len(repository_map.get("backend", [])))

            start = time.perf_counter()
            raw_issues = self.github_service.get_good_first_issues(owner, repo)
            duration = time.perf_counter() - start
            logger.info("[PERF] Issue Discovery: %.2fs", duration)
            if duration > 5.0:
                logger.warning("[SLOW] Issue Discovery took %.2fs", duration)
            logger.warning("[DEBUG] ISSUES FOUND -> repo=%s count=%d", repo, len(raw_issues))
            for issue in raw_issues[:3]:
                logger.warning("[DEBUG] ISSUE -> #%s %s", issue.get("number"), issue.get("title"))
            
            if mode == "FAST_MVP":
                top_issues = raw_issues[:2]
            else:
                top_issues = raw_issues[:MAX_ANALYSIS_ISSUES]
                
            issues_with_analysis: List[Dict[str, Any]] = []
            if top_issues:
                if ENABLE_PARALLEL_ANALYSIS:
                    with ThreadPoolExecutor(max_workers=min(5, len(top_issues))) as executor:
                        futures = [executor.submit(self._analyze_issue_entry, owner, repo, issue, summary, repository_map) for issue in top_issues]
                        for future in as_completed(futures):
                            issues_with_analysis.append(future.result())
                else:
                    # Sequential execution to prevent 429 TPM exhaustion limits
                    for issue in top_issues:
                        issues_with_analysis.append(self._analyze_issue_entry(owner, repo, issue, summary, repository_map))
                        
            roadmap = {}
            
            if mode == "FAST_MVP":
                roadmap = {"best_issue_to_start": None, "why_this_issue": "Roadmap disabled in FAST_MVP mode", "recommended_learning_order": [], "files_to_read_first": [], "contribution_plan": [], "success_tips": []}
            else:
                try:
                    roadmap = self.roadmap_service.analyze_roadmap(
                        {
                            "repo_summary": summary,
                            "repository_map": repository_map,
                            "issues": [item["raw_issue"] for item in issues_with_analysis],
                        }
                    )
                except Exception as exc:
                    logger.warning("Roadmap generation failed for %s/%s: %s", owner, repo, exc)
                    roadmap = {"best_issue_to_start": None, "why_this_issue": "Roadmap unavailable", "recommended_learning_order": [], "files_to_read_first": [], "contribution_plan": [], "success_tips": []}

            # Log final budget tracking details
            logger.info("Final Total Analysis Token Estimation: %d", self.llm_service.token_manager.total_estimated_tokens)

            total_duration = time.perf_counter() - started_at
            logger.info("[PERF] Full Analysis Total Time: %.2fs", total_duration)

            logger.warning("[DEBUG] FINAL RESPONSE -> metadata=%s issues=%d", metadata.get("name"), len(issues_with_analysis))
            return {
                "metadata": metadata,
                "summary": summary,
                "repository_map": repository_map,
                "issues": issues_with_analysis,
                "roadmap": roadmap,
            }
        except (ValueError, LLMGenerationError, Exception) as exc:
            logger.exception("Repository analysis failed for %s: %s", url, exc)
            raise RuntimeError("Failed to analyze repository.") from exc
