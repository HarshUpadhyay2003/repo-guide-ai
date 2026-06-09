import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from app.prompts.repo_summary import REPO_SUMMARY_PROMPT
from app.services.github_service import GitHubService
from app.services.issue_service import IssueService
from app.services.llm_service import LLMGenerationError, LLMService
from app.services.roadmap_service import RoadmapService
from app.services.repository_map_service import RepositoryMapService
from app.utils.github_parser import parse_github_url

logger = logging.getLogger(__name__)


class RepoService:
    """Coordinate repository analysis using GitHub and LLM services."""

    def __init__(self) -> None:
        self.github_service = GitHubService()
        self.llm_service = LLMService()
        self.repository_map_service = RepositoryMapService(self.github_service, self.llm_service)
        self.issue_service = IssueService(self.llm_service)
        self.roadmap_service = RoadmapService(self.llm_service)

    def _analyze_issue_entry(self, issue: Dict[str, Any], summary: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze one issue entry and degrade gracefully on failure."""
        try:
            return {
                "raw": issue,
                "analysis": self.issue_service.analyze_issue(
                    {
                        "issue": {
                            "title": issue.get("title", ""),
                            "body": issue.get("body", ""),
                            "labels": issue.get("labels", []),
                        },
                        "repo_summary": summary,
                    }
                ),
            }
        except Exception as exc:
            logger.warning("Issue analysis failed for #%s: %s", issue.get("number", "?"), exc)
            return {"raw": issue, "analysis": None}

    def analyze_repository(self, url: str) -> Dict[str, Any]:
        """Analyze a GitHub repository and return structured guidance."""
        started_at = time.perf_counter()
        logger.info("Starting repository analysis for URL: %s", url)

        try:
            parse_start = time.perf_counter()
            logger.info("Starting URL parsing for %s", url)
            parsed = parse_github_url(url)
            logger.info("Completed URL parsing in %.3fs: %s", time.perf_counter() - parse_start, parsed)
            owner = parsed["owner"]
            repo = parsed["repo"]

            metadata_start = time.perf_counter()
            logger.info("Starting metadata fetch for %s/%s", owner, repo)
            metadata = self.github_service.get_repo_metadata(owner, repo)
            logger.info("Completed metadata fetch in %.3fs for %s/%s", time.perf_counter() - metadata_start, owner, repo)

            readme_start = time.perf_counter()
            logger.info("Starting README fetch for %s/%s", owner, repo)
            readme = self.github_service.get_readme(owner, repo)
            readme = (readme or "")[:10000]
            logger.info("Completed README fetch in %.3fs for %s/%s (characters=%d)", time.perf_counter() - readme_start, owner, repo, len(readme or ""))

            contributing_start = time.perf_counter()
            logger.info("Starting CONTRIBUTING fetch for %s/%s", owner, repo)
            contributing = self.github_service.get_contributing(owner, repo)
            contributing = (contributing or "")[:5000]
            logger.info("Completed CONTRIBUTING fetch in %.3fs for %s/%s (characters=%d)", time.perf_counter() - contributing_start, owner, repo, len(contributing or ""))

            summary_prompt = REPO_SUMMARY_PROMPT.format(
                readme=readme or "",
                contributing=contributing or "",
                metadata=metadata,
            )
            logger.info("Starting summary generation for %s/%s", owner, repo)
            summary_start = time.perf_counter()
            summary = self.llm_service.generate_json(summary_prompt)
            logger.info("Completed summary generation in %.3fs for %s/%s", time.perf_counter() - summary_start, owner, repo)

            tree_start = time.perf_counter()
            logger.info("Starting repository map generation for %s/%s", owner, repo)
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
            logger.info("Completed repository map generation in %.3fs for %s/%s", time.perf_counter() - tree_start, owner, repo)

            issues_start = time.perf_counter()
            logger.info("Starting issue fetch for %s/%s", owner, repo)
            raw_issues = self.github_service.get_good_first_issues(owner, repo)
            top_issues = raw_issues[:5]
            logger.info("Completed issue fetch in %.3fs for %s/%s (count=%d)", time.perf_counter() - issues_start, owner, repo, len(raw_issues))

            issue_analysis_start = time.perf_counter()
            logger.info("Starting issue analysis for %s/%s", owner, repo)
            issues_with_analysis: List[Dict[str, Any]] = []
            if top_issues:
                with ThreadPoolExecutor(max_workers=min(5, len(top_issues))) as executor:
                    futures = [executor.submit(self._analyze_issue_entry, issue, summary) for issue in top_issues]
                    for future in as_completed(futures):
                        issues_with_analysis.append(future.result())
            logger.info("Completed issue analysis in %.3fs for %s/%s", time.perf_counter() - issue_analysis_start, owner, repo)

            roadmap_start = time.perf_counter()
            logger.info("Starting roadmap generation for %s/%s", owner, repo)
            roadmap = {}
            try:
                roadmap = self.roadmap_service.analyze_roadmap(
                    {
                        "repo_summary": summary,
                        "repository_map": repository_map,
                        "issues": [item["raw"] for item in issues_with_analysis],
                    }
                )
            except Exception as exc:
                logger.warning("Roadmap generation failed for %s/%s: %s", owner, repo, exc)
                roadmap = {"best_issue_to_start": None, "why_this_issue": "Roadmap unavailable", "recommended_learning_order": [], "files_to_read_first": [], "contribution_plan": [], "success_tips": []}
            logger.info("Completed roadmap generation in %.3fs for %s/%s", time.perf_counter() - roadmap_start, owner, repo)

            logger.info("Returning final analysis response for %s/%s in %.3fs", owner, repo, time.perf_counter() - started_at)

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
