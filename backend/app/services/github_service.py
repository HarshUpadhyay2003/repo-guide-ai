import datetime
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional

from github import Auth, Github, GithubException
from github.Repository import Repository

from app.core.config import settings
from constants import ENABLE_DEEP_PROFILING

# Cache imports
from app.core.cache.dependencies import get_cache_manager
from app.core.cache.keys import (
    get_repo_metadata_key,
    get_repo_readme_key,
    get_repo_contributing_key,
    get_repo_tree_key,
    get_repo_issue_search_key,
    get_issue_comments_key,
)
from app.core.cache.config import (
    CACHE_TTL_REPO_METADATA,
    CACHE_TTL_REPO_README,
    CACHE_TTL_REPO_CONTRIBUTING,
    CACHE_TTL_REPO_TREE,
    CACHE_TTL_ISSUE_SEARCH,
    CACHE_TTL_ISSUE_COMMENTS,
)

logger = logging.getLogger(__name__)

IGNORED_DIRS = {".git", ".github", "venv", "node_modules", "__pycache__"}
MAX_TREE_DEPTH = 3


class DoNotCacheError(Exception):
    """Raised inside fetch functions to signal that the result should be returned but not stored in the cache."""
    def __init__(self, value: Any) -> None:
        super().__init__()
        self.value = value


class CachedIssueDTO:
    """Lightweight DTO mimicking PyGithub Issue object to avoid fetching from GitHub when cached."""
    def __init__(self, data: Dict[str, Any], github_service: Any, owner: str, repo: str) -> None:
        self.number = data["number"]
        self.title = data["title"]
        self.body = data["body"]
        self.html_url = data["url"]
        self.labels = [type("Label", (object,), {"name": name})() for name in data["labels"]]
        self.comments = data.get("comments", 0)
        self._service = github_service
        self._owner = owner
        self._repo = repo
        self.created_at = (
            datetime.datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None
        )

    def get_comments(self) -> Any:
        repo_obj = self._service._safe_repo(self._owner, self._repo)
        if repo_obj is None:
            return []
        real_issue = repo_obj.get_issue(self.number)
        return real_issue.get_comments()


@lru_cache(maxsize=32)
def _get_repo_cached(client: Github, owner: str, repo: str) -> Repository:
    return client.get_repo(f"{owner}/{repo}")


class GitHubService:
    """Small wrapper around PyGithub for repository inspection."""

    def __init__(self, token: Optional[str] = None) -> None:
        """Initialize the service with a GitHub token.

        Args:
            token: Optional token override. Defaults to the configured value.
        """
        self.token = token or getattr(settings, "GITHUB_TOKEN", None)
        if not self.token:
            raise ValueError("GITHUB_TOKEN is required to initialize GitHubService.")

        auth = Auth.Token(self.token)
        self.client = Github(auth=auth)
        self._issue_cache = {}
        # Inject the process-wide CacheManager singleton
        self.cache_manager = get_cache_manager()

    def _safe_repo(self, owner: str, repo: str) -> Optional[Repository]:
        """Return a repository object or log and return None on failure."""
        try:
            return _get_repo_cached(self.client, owner, repo)
        except GithubException as exc:
            logger.warning("Failed to fetch repository %s/%s: %s", owner, repo, exc)
            return None

    def _get_or_cache(
        self,
        key: str,
        ttl: Optional[int],
        display_name: str,
        fetch_function: Callable[[], Any],
        serializer: Optional[Callable[[Any], Any]] = None,
    ) -> Any:
        """Helper to get a value from cache or fetch and store it on miss.

        Gracefully handles cache exceptions and performs standardized logging.
        """
        try:
            is_hit = self.cache_manager.exists(key)
        except Exception as exc:
            if isinstance(exc, (TypeError, ValueError)):
                raise
            logger.warning("[CACHE] Cache check failed for key %s: %s", key, exc)
            is_hit = False

        if is_hit:
            print(f"[CACHE][{display_name}] HIT")
        else:
            print(f"[CACHE][{display_name}] MISS")

        try:
            class InterceptedDoNotCache(Exception):
                def __init__(self, value: Any) -> None:
                    self.value = value

            def compute_wrapper() -> Any:
                try:
                    return fetch_function()
                except DoNotCacheError as dnc:
                    raise InterceptedDoNotCache(dnc.value)

            try:
                result = self.cache_manager.cache_or_compute(
                    key=key,
                    ttl=ttl,
                    compute_function=compute_wrapper,
                    serializer=serializer
                )
                if not is_hit:
                    print(f"[CACHE WRITE][{display_name}]")
                return result
            except InterceptedDoNotCache as idnc:
                return idnc.value

        except Exception as exc:
            if isinstance(exc, (TypeError, ValueError)):
                raise
            logger.warning("[CACHE] Cache operations failed for key %s: %s", key, exc)
            try:
                return fetch_function()
            except DoNotCacheError as dnc:
                return dnc.value

    def get_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        """Return a normalized repository summary."""
        repo_obj = self._safe_repo(owner, repo)
        if repo_obj is None:
            return {"owner": owner, "repo": repo, "found": False}

        return {
            "owner": repo_obj.owner.login,
            "repo": repo_obj.name,
            "full_name": repo_obj.full_name,
            "private": repo_obj.private,
            "description": repo_obj.description or "",
            "url": repo_obj.html_url,
            "found": True,
        }

    def get_readme(self, owner: str, repo: str) -> str:
        """Return the repository README content as text."""
        key = get_repo_readme_key(owner, repo)

        def fetch() -> str:
            logger.warning("[DEBUG] GITHUB -> get_readme(%s/%s)", owner, repo)
            repo_obj = self._safe_repo(owner, repo)
            if repo_obj is None:
                raise DoNotCacheError("")
            try:
                readme = repo_obj.get_readme()
                return readme.decoded_content.decode("utf-8", errors="replace")
            except GithubException as exc:
                if exc.status == 404:
                    return ""
                logger.warning("Failed to fetch README for %s/%s: %s", owner, repo, exc)
                raise DoNotCacheError("")

        return self._get_or_cache(key, CACHE_TTL_REPO_README, "README", fetch)

    def get_contributing(self, owner: str, repo: str) -> str:
        """Return the CONTRIBUTING file content if available."""
        key = get_repo_contributing_key(owner, repo)

        def fetch() -> str:
            logger.warning("[DEBUG] GITHUB -> get_contributing(%s/%s)", owner, repo)
            repo_obj = self._safe_repo(owner, repo)
            if repo_obj is None:
                raise DoNotCacheError("")
            try:
                contributing = repo_obj.get_contents("CONTRIBUTING.md")
                if hasattr(contributing, "decoded_content"):
                    return contributing.decoded_content.decode("utf-8", errors="replace")
                return ""
            except GithubException as exc:
                if exc.status == 404:
                    return ""
                logger.warning("Failed to fetch CONTRIBUTING for %s/%s: %s", owner, repo, exc)
                raise DoNotCacheError("")

        return self._get_or_cache(key, CACHE_TTL_REPO_CONTRIBUTING, "CONTRIBUTING", fetch)

    def get_languages(self, owner: str, repo: str) -> Dict[str, int]:
        """Return repository language usage as a dictionary."""
        repo_obj = self._safe_repo(owner, repo)
        if repo_obj is None:
            return {}

        try:
            return dict(repo_obj.get_languages())
        except GithubException as exc:
            logger.warning("Failed to fetch languages for %s/%s: %s", owner, repo, exc)
            return {}

    def get_repo_metadata(self, owner: str, repo: str) -> Dict[str, Any]:
        """Return standardized repository metadata."""
        key = get_repo_metadata_key(owner, repo)

        def fetch() -> Dict[str, Any]:
            logger.warning("[DEBUG] GITHUB -> get_repo_metadata(%s/%s)", owner, repo)
            repo_obj = self._safe_repo(owner, repo)
            if repo_obj is None:
                raise DoNotCacheError({
                    "name": repo,
                    "description": "",
                    "stars": 0,
                    "forks": 0,
                    "language": "",
                    "topics": [],
                })

            return {
                "name": repo_obj.name,
                "description": repo_obj.description or "",
                "stars": repo_obj.stargazers_count,
                "forks": repo_obj.forks_count,
                "language": repo_obj.language or "",
                "topics": list(repo_obj.get_topics()) if hasattr(repo_obj, "get_topics") else [],
            }

        return self._get_or_cache(key, CACHE_TTL_REPO_METADATA, "Metadata", fetch)

    def _search_label_issues(self, owner: str, repo: str, label: str) -> List[Any]:
        """Wrapper method for issue search by label to support future caching hooks."""
        query = f'repo:{owner}/{repo} label:"{label}" state:open is:issue'
        search_results = self.client.search_issues(query=query, sort="created", order="desc")
        issues_list = []
        for idx, issue in enumerate(search_results):
            if idx >= 10:
                break
            issues_list.append(issue)
        return issues_list

    def _fetch_issue_comments(self, issue_obj: Any) -> List[Dict[str, Any]]:
        """Wrapper method for issue comments fetch to support future caching hooks."""
        # Phase 4 — Skip Zero-Comment Requests
        if getattr(issue_obj, "comments", 0) == 0:
            return []
            
        comments = issue_obj.get_comments()
        results: List[Dict[str, Any]] = []
        for idx, comment in enumerate(comments):
            if idx >= 10:
                break
            results.append(
                {
                    "author": comment.user.login if comment.user else "Ghost",
                    "body": (comment.body or "")[:1000],
                    "created_at": comment.created_at.isoformat() if comment.created_at else None,
                }
            )
        return results
    def get_good_first_issues(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Return up to 20 open beginner-friendly issues using GitHub Search API."""
        key = get_repo_issue_search_key(owner, repo)

        def fetch() -> List[Dict[str, Any]]:
            self._issue_cache.clear()
            logger.warning("[DEBUG] GITHUB -> get_good_first_issues(%s/%s)", owner, repo)
            good_first_labels = ["good first issue", "help wanted", "beginner", "documentation"]
            
            timings = {}
            results_by_label = {}
            
            def search_worker(label: str):
                start_time = time.perf_counter()
                try:
                    issues = self._search_label_issues(owner, repo, label)
                    results_by_label[label] = issues
                except Exception as exc:
                    logger.warning("Failed label search '%s' for %s/%s: %s", label, owner, repo, exc)
                    results_by_label[label] = []
                dur = time.perf_counter() - start_time
                timings[label] = dur

            search_total_start = time.perf_counter()
            with ThreadPoolExecutor(max_workers=min(4, len(good_first_labels))) as executor:
                executor.map(search_worker, good_first_labels)
            search_total_dur = time.perf_counter() - search_total_start

            merge_start = time.perf_counter()
            merged_issues = []
            seen_numbers = set()
            
            for label in good_first_labels:
                for issue in results_by_label.get(label, []):
                    if issue.number not in seen_numbers:
                        seen_numbers.add(issue.number)
                        merged_issues.append(issue)
                        self._issue_cache[(owner, repo, issue.number)] = issue

            merge_dur = time.perf_counter() - merge_start
            dedup_start = time.perf_counter()
            dedup_dur = time.perf_counter() - dedup_start

            rank_start = time.perf_counter()
            merged_issues.sort(key=lambda item: item.created_at or datetime.datetime.min, reverse=True)
            rank_dur = time.perf_counter() - rank_start

            selection_start = time.perf_counter()
            final_issues = []
            
            for x in merged_issues:
                if len(final_issues) >= 20:
                    break
                
                raw_data = getattr(x, "_rawData", None)
                has_pr = isinstance(raw_data, dict) and "pull_request" in raw_data
                
                if not has_pr:
                    final_issues.append(x)
            
            selection_dur = time.perf_counter() - selection_start

            if hasattr(self, "metrics") and isinstance(self.metrics, dict):
                self.metrics["discovery_search"] = search_total_dur
                self.metrics["discovery_merge"] = merge_dur
                self.metrics["discovery_dedup"] = dedup_dur
                self.metrics["discovery_ranking"] = rank_dur
                self.metrics["discovery_selection"] = selection_dur
                for label in good_first_labels:
                    self.metrics[f"label_search_{label}"] = timings.get(label, 0.0)

            results = []
            for issue in final_issues:
                labels = [label_obj.name for label_obj in getattr(issue, "labels", [])]
                results.append(
                    {
                        "number": issue.number,
                        "title": issue.title,
                        "body": (issue.body or "")[:500],
                        "url": issue.html_url,
                        "labels": sorted({name.lower() for name in labels}),
                        "created_at": issue.created_at.isoformat() if issue.created_at else None,
                        "comments": getattr(issue, "comments", 0),
                    }
                )

            logger.info("Returning %s unique issues from GitHub", len(results))
            return results

        try:
            results = self._get_or_cache(key, CACHE_TTL_ISSUE_SEARCH, "Issue Search", fetch)
        except Exception as exc:
            logger.warning("Issue search caching failed: %s", exc)
            results = fetch()

        self._issue_cache.clear()
        for issue_data in results:
            dto = CachedIssueDTO(issue_data, self, owner, repo)
            self._issue_cache[(owner, repo, dto.number)] = dto

        return results

    def get_repository_tree(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Return a repository directory tree using a single GitHub Tree API call."""
        key = get_repo_tree_key(owner, repo)

        def fetch() -> Dict[str, Any]:
            logger.warning("[DEBUG] GITHUB -> get_repository_tree(%s/%s)", owner, repo)
            repo_obj = self._safe_repo(owner, repo)
            if repo_obj is None:
                raise DoNotCacheError({"generated_at": "", "tree": []})
            try:
                branch = repo_obj.default_branch
                tree = repo_obj.get_git_tree(branch, recursive=True)
                tree_list = [{"path": element.path, "type": element.type} for element in tree.tree]
                return {
                    "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "tree": tree_list
                }
            except GithubException as exc:
                logger.warning("Failed to fetch repository tree for %s/%s: %s", owner, repo, exc)
                raise DoNotCacheError({"generated_at": "", "tree": []})

        result = self._get_or_cache(key, CACHE_TTL_REPO_TREE, "Tree", fetch)
        if isinstance(result, dict) and "tree" in result:
            return result["tree"]
        return result

    def get_issue_comments(self, owner: str, repo: str, issue_number: int) -> List[Dict[str, Any]]:
        """Return a structured list of comments for a specific issue."""
        key = get_issue_comments_key(owner, repo, issue_number)
        display_name = f"Comments #{issue_number}"

        def fetch() -> List[Dict[str, Any]]:
            logger.warning("[DEBUG] GITHUB -> get_issue_comments(%s/%s)", owner, repo)
            
            issue_obj = self._issue_cache.get((owner, repo, issue_number))
            if issue_obj is None:
                repo_obj = self._safe_repo(owner, repo)
                if repo_obj is None:
                    raise DoNotCacheError([])
                try:
                    issue_obj = repo_obj.get_issue(issue_number)
                except Exception as exc:
                    logger.warning("Failed to fetch issue #%s in %s/%s: %s", issue_number, owner, repo, exc)
                    raise DoNotCacheError([])

            comments_count = getattr(issue_obj, "comments", 0)
            if comments_count == 0:
                return []

            try:
                comments = issue_obj.get_comments()
                results: List[Dict[str, Any]] = []
                for idx, comment in enumerate(comments):
                    if idx >= 10:
                        break
                    results.append(
                        {
                            "author": comment.user.login if comment.user else "Ghost",
                            "body": (comment.body or "")[:1000],
                            "created_at": comment.created_at.isoformat() if comment.created_at else None,
                        }
                    )
                return results
            except Exception as exc:
                logger.warning("Failed to fetch comments for issue #%s in %s/%s: %s", issue_number, owner, repo, exc)
                raise DoNotCacheError([])

        start_time = time.perf_counter()
        try:
            res = self._get_or_cache(key, CACHE_TTL_ISSUE_COMMENTS, display_name, fetch)
        except Exception as exc:
            logger.warning("Comments caching failed: %s", exc)
            res = fetch()
        dur = time.perf_counter() - start_time

        if ENABLE_DEEP_PROFILING:
            print()
            print("[COMMENT PROFILE]")
            print()
            print(f"Issue Number: {issue_number}")
            print()
            print(f"Comment Fetch/Cache Get Time: {dur:.4f}s")
            print()
            print(f"Comments Returned: {len(res)}")
            print()

        return res
