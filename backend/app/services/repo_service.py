import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from app.prompts.repo_summary import REPO_SUMMARY_PROMPT
from app.services.repository_summary_service import RepositorySummaryService
from app.services.github_service import GitHubService
from app.services.issue_service import IssueService
from app.services.llm_service import LLMGenerationError, LLMService
from app.services.exploration_hints_service import ExplorationHintsService
from app.services.issue_guidance_service import IssueGuidanceService
from app.services.roadmap_service import RoadmapService
from app.services.repository_map_service import RepositoryMapService
from app.utils.github_parser import parse_github_url
from constants import MAX_ANALYSIS_ISSUES, ENABLE_PARALLEL_ANALYSIS, ENABLE_PERF_DIAGNOSTICS, ENABLE_DEEP_PROFILING

logger = logging.getLogger(__name__)


class RepoService:
    """Coordinate repository analysis using GitHub and LLM services."""

    def __init__(self) -> None:
        self.github_service = GitHubService()
        self.llm_service = LLMService()
        self.repository_map_service = RepositoryMapService(self.github_service)
        self.issue_service = IssueService(self.llm_service)
        self.exploration_hints_service = ExplorationHintsService(self.llm_service)
        self.issue_guidance_service = IssueGuidanceService(self.llm_service)
        self.roadmap_service = RoadmapService(self.llm_service)
        self.repository_summary_service = RepositorySummaryService(self.llm_service)

    def _analyze_issue_entry(self, owner: str, repo: str, issue: Dict[str, Any], summary: Dict[str, Any], repository_map: Dict[str, Any], all_files: List[str], all_dirs: List[str]) -> Dict[str, Any]:
        """Analyze one issue entry and degrade gracefully on failure."""
        issue_number = issue.get("number")
        comments = []
        
        comment_start = time.perf_counter()
        if issue_number:
            try:
                comments = self.github_service.get_issue_comments(owner, repo, issue_number)
            except Exception as exc:
                logger.warning("Failed to fetch comments for issue #%s: %s", issue_number, exc)
        comment_dur = time.perf_counter() - comment_start
        if hasattr(self, "comment_fetch_times") and isinstance(self.comment_fetch_times, list):
            self.comment_fetch_times.append(comment_dur)

        analysis = None
        exploration_hints = None
        issue_payload = {
            "number": issue_number,
            "title": issue.get("title", ""),
            "body": issue.get("body", ""),
            "labels": issue.get("labels", []),
        }

        # Track combined issue guidance time
        start_guidance = time.perf_counter()
        try:
            guidance = self.issue_guidance_service.generate_guidance(
                {
                    "issue": issue_payload,
                    "repo_summary": summary,
                    "repository_map": repository_map,
                    "comments": comments,
                    "all_files": all_files,
                    "all_dirs": all_dirs,
                }
            )
            analysis = guidance.get("analysis")
            exploration_hints = guidance.get("exploration_hints")
        except Exception as exc:
            logger.warning("Issue guidance generation failed for #%s: %s", issue.get("number", "?"), exc)
        duration_guidance = time.perf_counter() - start_guidance

        if hasattr(self, "metrics") and isinstance(self.metrics, dict):
            if issue_number in self.metrics.get("issues", {}):
                self.metrics["issues"][issue_number]["comment_fetch"] = comment_dur

        return {
            "raw_issue": issue,
            "analysis": analysis,
            "exploration_hints": exploration_hints,
            "timing_guidance": duration_guidance,
        }

    def analyze_repository(self, url: str, mode: str = "FAST_MVP") -> Dict[str, Any]:
        """Analyze a GitHub repository and return structured guidance."""
        request_start = time.perf_counter()
        logger.info("Starting repository analysis for URL: %s", url)

        # Initialize metrics context dictionary
        self.metrics = {
            "metadata_fetch": 0.0,
            "readme_fetch": 0.0,
            "contributing_fetch": 0.0,
            "metadata_total": 0.0,
            "tree_download": 0.0,
            "map_generation": 0.0,
            "map_total": 0.0,
            "discovery_search": 0.0,
            "discovery_merge": 0.0,
            "discovery_dedup": 0.0,
            "discovery_ranking": 0.0,
            "discovery_selection": 0.0,
            "issue_discovery_total": 0.0,
            "total_comment_collection": 0.0,
            "issues": {},  # key is issue number
            "roadmap_ranking": 0.0,
            "roadmap_assembly": 0.0,
            "roadmap_validation": 0.0,
            "roadmap_total": 0.0,
            "response_assembly": 0.0,
            "pydantic_validation": 0.0,
            "json_serialization": 0.0,
            "total": 0.0
        }
        
        # Propagate metrics context to sub-services
        self.github_service.metrics = self.metrics
        self.issue_guidance_service.metrics = self.metrics
        self.roadmap_service.metrics = self.metrics
        self.repository_summary_service.metrics = self.metrics
        
        # Reset JSON reliability metrics for this run
        self.llm_service.reliability_metrics = {
            "attempts": {}
        }

        # Thread-safe comment fetch times list
        self.comment_fetch_times = []

        try:
            parsed = parse_github_url(url)
            owner = parsed["owner"]
            repo = parsed["repo"]

            # Stage 1: Metadata & Required Files Fetch (Concurrent)
            def fetch_metadata():
                t0 = time.perf_counter()
                res = self.github_service.get_repo_metadata(owner, repo)
                return res, time.perf_counter() - t0
                
            def fetch_readme():
                t0 = time.perf_counter()
                res = (self.github_service.get_readme(owner, repo) or "")[:10000]
                return res, time.perf_counter() - t0
                
            def fetch_contributing():
                t0 = time.perf_counter()
                res = (self.github_service.get_contributing(owner, repo) or "")[:5000]
                return res, time.perf_counter() - t0
                
            meta_total_start = time.perf_counter()
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_meta = executor.submit(fetch_metadata)
                future_readme = executor.submit(fetch_readme)
                future_contrib = executor.submit(fetch_contributing)
                
                metadata, metadata_dur = future_meta.result()
                readme, readme_dur = future_readme.result()
                contributing, contrib_dur = future_contrib.result()
            metadata_total_dur = time.perf_counter() - meta_total_start

            self.metrics["metadata_fetch"] = metadata_dur
            self.metrics["readme_fetch"] = readme_dur
            self.metrics["contributing_fetch"] = contrib_dur
            self.metrics["metadata_total"] = metadata_total_dur

            # Stage 2: Repository Summary
            summary_start = time.perf_counter()
            summary_prompt = REPO_SUMMARY_PROMPT.format(
                readme=readme or "",
                contributing=contributing or "",
                metadata=metadata,
            )
            summary = self.repository_summary_service.generate_summary(metadata, readme or "", contributing or "", summary_prompt)
            print(f"[PERF] Repository Summary: {time.perf_counter() - summary_start:.2f}s")
            print()

            # Stage 3: Repository Map Generation
            map_total_start = time.perf_counter()
            repository_map = {}
            all_files = []
            all_dirs = []
            tree_dur = 0.0
            map_gen_dur = 0.0
            try:
                tree_start = time.perf_counter()
                tree = self.github_service.get_repository_tree(owner, repo)
                tree_dur = time.perf_counter() - tree_start
                
                map_gen_start = time.perf_counter()
                for item in tree:
                    path = item.get("path", "")
                    if item.get("type") == "tree":
                        all_dirs.append(path)
                    else:
                        all_files.append(path)
                repository_map = self.repository_map_service.generate_map(owner=owner, repo=repo, tree=tree)
                map_gen_dur = time.perf_counter() - map_gen_start
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
            map_total_dur = time.perf_counter() - map_total_start
            print(f"[PERF] Repository Map: {map_total_dur:.2f}s")
            print()

            self.metrics["tree_download"] = tree_dur
            self.metrics["map_generation"] = map_gen_dur
            self.metrics["map_total"] = map_total_dur

            # Stage 4: Issue Discovery
            discovery_start = time.perf_counter()
            raw_issues = self.github_service.get_good_first_issues(owner, repo)
            discovery_total_dur = time.perf_counter() - discovery_start
            print(f"[PERF] Issue Discovery: {discovery_total_dur:.2f}s")
            print()
            self.metrics["issue_discovery_total"] = discovery_total_dur
            
            if mode == "FAST_MVP":
                top_issues = raw_issues[:2]
            else:
                top_issues = raw_issues[:MAX_ANALYSIS_ISSUES]
                
            issues_with_analysis: List[Dict[str, Any]] = []
            guidance_start = time.perf_counter()
            if top_issues:
                if ENABLE_PARALLEL_ANALYSIS:
                    with ThreadPoolExecutor(max_workers=min(5, len(top_issues))) as executor:
                        futures = [executor.submit(self._analyze_issue_entry, owner, repo, issue, summary, repository_map, all_files, all_dirs) for issue in top_issues]
                        for future in as_completed(futures):
                            issues_with_analysis.append(future.result())
                else:
                    # Sequential execution to prevent 429 TPM exhaustion limits
                    for issue in top_issues:
                        issues_with_analysis.append(self._analyze_issue_entry(owner, repo, issue, summary, repository_map, all_files, all_dirs))
            
            # Graceful Failure: Skip failed issues, log warnings, and compile successfully analyzed issues
            successful_issues = []
            for item in issues_with_analysis:
                if item.get("analysis") is not None and item.get("exploration_hints") is not None:
                    successful_issues.append(item)
                else:
                    issue_num = item.get("raw_issue", {}).get("number")
                    logger.warning("[WARNING] Guidance generation failed for Issue #%s", issue_num)
                    print(f"[WARNING] Guidance generation failed for Issue #{issue_num}")
            issues_with_analysis = successful_issues

            print(f"[PERF] Issue Guidance: {time.perf_counter() - guidance_start:.2f}s")
            print()

            # --- Part 6: GUIDANCE PROFILING SUMMARY ---
            guidance_runs = self.metrics.get("guidance_runs", [])
            issues_analyzed = len(guidance_runs)
            
            if issues_analyzed > 0:
                prompt_tokens_list = [r["prompt_tokens"] for r in guidance_runs]
                guidance_times_list = [r["guidance_time"] for r in guidance_runs]
                
                total_prompt_tokens = sum(prompt_tokens_list)
                avg_prompt_tokens = total_prompt_tokens / issues_analyzed
                largest_prompt_tokens = max(prompt_tokens_list)
                smallest_prompt_tokens = min(prompt_tokens_list)
                
                total_guidance_time = sum(guidance_times_list)
                avg_guidance_time = total_guidance_time / issues_analyzed
                longest_guidance_call = max(guidance_times_list)
                shortest_guidance_call = min(guidance_times_list)
            else:
                total_prompt_tokens = 0
                avg_prompt_tokens = 0.0
                largest_prompt_tokens = 0
                smallest_prompt_tokens = 0
                total_guidance_time = 0.0
                avg_guidance_time = 0.0
                longest_guidance_call = 0.0
                shortest_guidance_call = 0.0

            print("==============================")
            print("GUIDANCE PROFILING SUMMARY")
            print("==============================")
            print()
            print(f"Repository: {repo}")
            print()
            print(f"Issues Analyzed: {issues_analyzed}")
            print()
            print(f"Average Prompt Tokens: {avg_prompt_tokens:.0f}")
            print()
            print(f"Average Guidance Time: {avg_guidance_time:.2f}s")
            print()
            print(f"Longest Guidance Call: {longest_guidance_call:.2f}s")
            print()
            print(f"Shortest Guidance Call: {shortest_guidance_call:.2f}s")
            print("==============================")
            print()

            total_comment_collection_dur = sum(self.comment_fetch_times)
            self.metrics["total_comment_collection"] = total_comment_collection_dur

            # Stage 5: Contributor Roadmap
            roadmap_start = time.perf_counter()
            if not issues_with_analysis:
                print("[INFO] No beginner-friendly issues found. Skipping roadmap generation.")
                roadmap = {}
            else:
                try:
                    roadmap = self.roadmap_service.analyze_roadmap(
                        {
                            "repo_summary": summary,
                            "repository_map": repository_map,
                            "issues": issues_with_analysis,
                            "all_files": all_files,
                            "all_dirs": all_dirs,
                        }
                    )
                except Exception as exc:
                    logger.warning("Roadmap generation failed for %s/%s: %s", owner, repo, exc)
                    roadmap = {}
            print(f"[PERF] Contributor Roadmap: {time.perf_counter() - roadmap_start:.2f}s")
            print()

            # Stage G - Response Assembly
            assembly_start = time.perf_counter()
            response_dict = {
                "metadata": metadata,
                "summary": summary,
                "repository_map": repository_map,
                "issues": issues_with_analysis,
                "roadmap": roadmap,
            }
            assembly_dur = time.perf_counter() - assembly_start
            self.metrics["response_assembly"] = assembly_dur

            # Serialization profiling (Part 6)
            ser_start = time.perf_counter()
            response_json_str = json.dumps(response_dict)
            serialization_dur = time.perf_counter() - ser_start

            if ENABLE_DEEP_PROFILING:
                print()
                print("[SERIALIZATION PROFILE]")
                print()
                print(f"Metadata Size: {len(json.dumps(metadata))}")
                print(f"Summary Size: {len(json.dumps(summary))}")
                print(f"Repository Map Size: {len(json.dumps(repository_map))}")
                print(f"Issues Size: {len(json.dumps(issues_with_analysis))}")
                print(f"Roadmap Size: {len(json.dumps(roadmap))}")
                print()
                print(f"Response JSON Size: {len(response_json_str)}")
                print(f"Serialization Time: {serialization_dur:.4f}s")
                print()

            total_request_dur = time.perf_counter() - request_start
            
            # Print Cache Summary (Stage 8.2A)
            from app.core.cache.dependencies import get_cache_manager
            cache_mgr = get_cache_manager()
            stats = cache_mgr.get_stats()
            
            print("==============================")
            print("CACHE SUMMARY")
            print("==============================")
            print()
            print(f"Backend: {stats['backend_name'].capitalize()}")
            print()
            print(f"Hits: {stats['hits']}")
            print(f"Misses: {stats['misses']}")
            print(f"Writes: {stats['writes']}")
            print()
            print(f"Current Entries: {stats['current_entries']}")
            print()
            print(f"Expired Entries: {stats['expired_entries']}")
            print()
            print(f"Lookup Time: {stats['lookup_time_ms']:.1f}ms")
            print(f"Write Time: {stats['write_time_ms']:.1f}ms")
            print()
            print("==============================")
            print()

            # Print LLM Reliability Summary
            self.llm_service.print_reliability_summary()
            print()

            print(f"[PERF] TOTAL /repo/analyze: {total_request_dur:.2f}s")
            self.metrics["total"] = total_request_dur

            # Global Request Breakdown (Part 7)
            if ENABLE_DEEP_PROFILING:
                summary_llm_generation = self.metrics.get("summary_llm_generation", 0.0)
                summary_total_stage = self.metrics.get("summary_total", 0.0)
                
                # Guidance LLM times
                guidance_llm_total = 0.0
                issues_metrics = self.metrics.get("issues", {})
                for im in issues_metrics.values():
                    guidance_llm_total += im.get("llm_request", 0.0)

                llm_total_time = summary_llm_generation + guidance_llm_total
                
                # Network times
                net_metadata = self.metrics.get("metadata_total", 0.0)
                net_tree = self.metrics.get("tree_download_time", 0.0)
                net_search = self.metrics.get("discovery_search", 0.0)
                net_selection = self.metrics.get("discovery_selection", 0.0)
                net_comments = self.metrics.get("total_comment_collection", 0.0)
                
                network_total_time = net_metadata + net_tree + net_search + net_selection + net_comments
                cpu_total_time = max(0.0, total_request_dur - llm_total_time - network_total_time)

                print("====================================================")
                print("REQUEST PERFORMANCE REPORT")
                print("====================================================")
                print()
                print(f"Repository: {repo}")
                print(f"Owner: {owner}")
                print()
                print("Metadata:")
                print(f"{metadata_total_dur:.2f}s")
                print()
                print("Repository Summary:")
                print(f"{summary_total_stage:.2f}s")
                print()
                print("Repository Map:")
                print(f"{map_total_dur:.2f}s")
                print()
                print("Issue Discovery:")
                print(f"{discovery_total_dur:.2f}s")
                print()
                print("Issue Guidance:")
                print(f"{(time.perf_counter() - guidance_start):.2f}s")
                print()
                print("Roadmap:")
                print(f"{(time.perf_counter() - roadmap_start):.2f}s")
                print()
                print("Serialization:")
                print(f"{serialization_dur:.2f}s")
                print()
                print("TOTAL:")
                print(f"{total_request_dur:.2f}s")
                print()
                print("----------------------------------------------------")
                print("LLM TOTAL TIME:")
                print(f"{llm_total_time:.2f}s")
                print()
                print("NETWORK TOTAL TIME:")
                print(f"{network_total_time:.2f}s")
                print()
                print("LOCAL CPU TOTAL TIME:")
                print(f"{cpu_total_time:.2f}s")
                print("----------------------------------------------------")
                print()



            return response_dict
        except (ValueError, LLMGenerationError, Exception) as exc:
            logger.exception("Repository analysis failed for %s: %s", url, exc)
            raise RuntimeError("Failed to analyze repository.") from exc
