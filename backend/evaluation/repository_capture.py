import logging
import requests
from typing import Any, Dict, List, Optional
from app.utils.github_parser import parse_github_url
from evaluation.benchmark_models import RepositoryMetadata

logger = logging.getLogger(__name__)

class RepositoryCapture:
    """Helper to capture GitHub repository metadata and size statistics."""

    def __init__(self, token: str) -> None:
        self.token = token
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    def fetch_repo_metadata(self, url: str, tree: List[Dict[str, Any]], readme_text: str, contributing_text: str) -> RepositoryMetadata:
        """Fetch general repository metadata from GitHub and compute size stats from the tree."""
        parsed = parse_github_url(url)
        owner = parsed["owner"]
        repo = parsed["repo"]

        meta = RepositoryMetadata(name=repo, url=url)

        # 1. Fetch metadata from GitHub API
        try:
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            res = requests.get(api_url, headers=self.headers, timeout=15)
            res.raise_for_status()
            data = res.json()

            meta.stars = data.get("stargazers_count", 0)
            meta.forks = data.get("forks_count", 0)
            meta.language = data.get("language", "") or ""
            meta.topics = data.get("topics", [])
            meta.size_kb = data.get("size", 0)
        except Exception as e:
            logger.warning("Failed to fetch repository details for %s/%s: %s", owner, repo, e)

        # 2. Count files and directories from the repository tree
        total_files = 0
        total_dirs = 0
        for item in tree:
            if item.get("type") == "tree":
                total_dirs += 1
            else:
                total_files += 1

        meta.total_files = total_files
        meta.total_directories = total_dirs
        meta.readme_size_bytes = len(readme_text.encode('utf-8')) if readme_text else 0
        meta.contributing_present = bool(contributing_text and len(contributing_text) > 0)

        return meta
