import logging
from typing import Any, Dict, List, Optional

from github import Auth, Github, GithubException
from github.Repository import Repository

from app.core.config import settings

logger = logging.getLogger(__name__)

IGNORED_DIRS = {".git", ".github", "venv", "node_modules", "__pycache__"}
MAX_TREE_DEPTH = 3


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

    def _safe_repo(self, owner: str, repo: str) -> Optional[Repository]:
        """Return a repository object or log and return None on failure."""
        try:
            return self.client.get_repo(f"{owner}/{repo}")
        except GithubException as exc:
            logger.warning("Failed to fetch repository %s/%s: %s", owner, repo, exc)
            return None

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
        logger.warning("[DEBUG] GITHUB -> get_readme(%s/%s)", owner, repo)
        repo_obj = self._safe_repo(owner, repo)
        if repo_obj is None:
            return ""

        try:
            readme = repo_obj.get_readme()
            return readme.decoded_content.decode("utf-8", errors="replace")
        except GithubException as exc:
            logger.warning("Failed to fetch README for %s/%s: %s", owner, repo, exc)
            return ""

    def get_contributing(self, owner: str, repo: str) -> str:
        """Return the CONTRIBUTING file content if available."""
        logger.warning("[DEBUG] GITHUB -> get_contributing(%s/%s)", owner, repo)
        repo_obj = self._safe_repo(owner, repo)
        if repo_obj is None:
            return ""

        try:
            contributing = repo_obj.get_contents("CONTRIBUTING.md")
            if hasattr(contributing, "decoded_content"):
                return contributing.decoded_content.decode("utf-8", errors="replace")
            return ""
        except GithubException as exc:
            logger.warning("Failed to fetch CONTRIBUTING for %s/%s: %s", owner, repo, exc)
            return ""

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
        logger.warning("[DEBUG] GITHUB -> get_repo_metadata(%s/%s)", owner, repo)
        repo_obj = self._safe_repo(owner, repo)
        if repo_obj is None:
            return {
                "name": repo,
                "description": "",
                "stars": 0,
                "forks": 0,
                "language": "",
                "topics": [],
            }

        return {
            "name": repo_obj.name,
            "description": repo_obj.description or "",
            "stars": repo_obj.stargazers_count,
            "forks": repo_obj.forks_count,
            "language": repo_obj.language or "",
            "topics": list(repo_obj.get_topics()) if hasattr(repo_obj, "get_topics") else [],
        }

    def get_good_first_issues(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Return up to 20 open beginner-friendly issues using GitHub Search API."""
        logger.warning("[DEBUG] GITHUB -> get_good_first_issues(%s/%s)", owner, repo)
        try:
            good_first_labels = ["good first issue", "help wanted", "beginner", "documentation"]
            results: List[Dict[str, Any]] = []
            seen_issue_numbers: set[int] = set()

            for label in good_first_labels:
                query = f'repo:{owner}/{repo} label:"{label}" state:open is:issue'
                logger.info("Searching label: %s", label)
                logger.info("Query: %s", query)

                issues = []
                try:
                    search_results = self.client.search_issues(query=query, sort="created", order="desc")
                    for idx, issue in enumerate(search_results):
                        if idx >= 10:
                            break
                        issues.append(issue)
                except Exception as exc:
                    logger.warning("Issue search failed for query %s: %s", query, exc)
                    issues = []

                count = 0
                for issue in issues:
                    if issue.pull_request is not None or issue.number in seen_issue_numbers:
                        continue

                    count += 1
                    seen_issue_numbers.add(issue.number)
                    labels = [label_obj.name for label_obj in getattr(issue, "labels", [])]
                    results.append(
                        {
                            "number": issue.number,
                            "title": issue.title,
                            "body": (issue.body or "")[:500],
                            "url": issue.html_url,
                            "labels": sorted({name.lower() for name in labels}),
                            "created_at": issue.created_at.isoformat() if issue.created_at else None,
                        }
                    )

                    if len(results) >= 20:
                        break

                logger.info("Found %s issues for label %s", count, label)
                if len(results) >= 20:
                    break

            results.sort(key=lambda item: item.get("created_at") or "", reverse=True)
            logger.info("Returning %s unique issues", len(results))
            return results[:20]
        except GithubException as exc:
            logger.warning("Failed to fetch good first issues for %s/%s: %s", owner, repo, exc)
            return []

    def get_repository_tree(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Return a repository directory tree using a single GitHub Tree API call."""
        logger.warning("[DEBUG] GITHUB -> get_repository_tree(%s/%s)", owner, repo)
        repo_obj = self._safe_repo(owner, repo)
        if repo_obj is None:
            return []

        try:
            branch = repo_obj.default_branch
            tree = repo_obj.get_git_tree(branch, recursive=True)
            
            return [{"path": element.path, "type": element.type} for element in tree.tree]
        except GithubException as exc:
            logger.warning("Failed to fetch repository tree for %s/%s: %s", owner, repo, exc)
            return []

    def get_issue_comments(self, owner: str, repo: str, issue_number: int) -> List[Dict[str, Any]]:
        """Return a structured list of comments for a specific issue."""
        logger.warning("[DEBUG] GITHUB -> get_issue_comments(%s/%s)", owner, repo)
        repo_obj = self._safe_repo(owner, repo)
        if repo_obj is None:
            return []

        try:
            issue = repo_obj.get_issue(issue_number)
            comments = issue.get_comments()

            results: List[Dict[str, Any]] = []
            for idx, comment in enumerate(comments):
                if idx >= 10:  # Limit comments to avoid excessive token usage
                    break
                results.append(
                    {
                        "author": comment.user.login if comment.user else "Ghost",
                        "body": (comment.body or "")[:1000],  # Truncate to limit tokens
                        "created_at": comment.created_at.isoformat() if comment.created_at else None,
                    }
                )
            return results
        except GithubException as exc:
            logger.warning("Failed to fetch comments for issue #%s in %s/%s: %s", issue_number, owner, repo, exc)
            return []
