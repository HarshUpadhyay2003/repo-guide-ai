import re
import os
import logging
from typing import Any, Dict, List, Optional, Tuple
import requests

from evaluation.benchmark_models import GitHubGroundTruth

logger = logging.getLogger(__name__)

class GitHubIssueCapture:
    """Helper to query the GitHub REST API and collect Ground Truth data for issues and linked pull requests."""

    def __init__(self, token: str) -> None:
        self.token = token
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Helper to send a GET request and return the JSON response."""
        response = requests.get(url, headers=self.headers, params=params, timeout=15)
        response.raise_for_status()
        return response.json()

    def fetch_issue_ground_truth(self, owner: str, repo: str, issue_number: int) -> GitHubGroundTruth:
        """Determine if a merged PR exists for the issue, and extract changes as ground truth."""
        api_base = f"https://api.github.com/repos/{owner}/{repo}"
        gt = GitHubGroundTruth(issue_number=issue_number)

        try:
            # 1. Fetch issue metadata
            issue_data = self._get(f"{api_base}/issues/{issue_number}")
            gt.state = issue_data.get("state", "open")

            if gt.state == "open":
                gt.ground_truth_status = "unavailable_open_issue"
                gt.status_text = "No merged PR available (Issue is open)"
                return gt

            # 2. Try to find the closing PR or commit
            pr_number, closing_commit = self._find_closing_pr_from_timeline(owner, repo, issue_number)
            
            # Fallback search if timeline did not yield a PR
            if not pr_number:
                pr_number = self._find_closing_pr_via_search(owner, repo, issue_number)

            if not pr_number:
                if closing_commit:
                    gt.closing_commit = closing_commit
                    gt.ground_truth_status = "unavailable_no_linked_pr"
                    gt.status_text = f"Closed by commit {closing_commit} (No merged PR found)"
                else:
                    gt.ground_truth_status = "unavailable_no_linked_pr"
                    gt.status_text = "No merged PR available"
                return gt

            # 3. Fetch PR Details
            pr_url = f"{api_base}/pulls/{pr_number}"
            pr_data = self._get(pr_url)

            # Ensure the PR is actually merged
            if not pr_data.get("merged", False):
                gt.ground_truth_status = "unavailable_pr_not_merged"
                gt.status_text = f"Linked PR #{pr_number} found but is NOT merged (PR state: {pr_data.get('state')})"
                return gt

            gt.merged_pr_number = pr_number
            gt.merged_pr_url = pr_data.get("html_url")
            gt.pr_title = pr_data.get("title")
            gt.pr_description = pr_data.get("body", "")
            gt.closing_commit = pr_data.get("merge_commit_sha")

            # 4. Fetch PR Commits
            commits_data = self._get(f"{pr_url}/commits")
            gt.commits = [c.get("commit", {}).get("message", "") for c in commits_data]

            # 5. Fetch PR Files
            files_data = self._get(f"{pr_url}/files", params={"per_page": 100})
            file_paths = [f.get("filename", "") for f in files_data if f.get("filename")]
            gt.files_changed = file_paths

            # Extract unique directories containing changed files
            dirs = set()
            for f in file_paths:
                dirname = os.path.dirname(f)
                if dirname:
                    dirs.add(dirname)
            gt.directories_changed = sorted(list(dirs))

            # 6. Deduce languages from file extensions
            languages = set()
            lang_map = {
                r"\.py$": "Python",
                r"\.tsx?$": "TypeScript",
                r"\.jsx?$": "JavaScript",
                r"\.go$": "Go",
                r"\.rs$": "Rust",
                r"\.sh$": "Shell",
                r"\.ya?ml$": "YAML",
                r"\.json$": "JSON",
                r"\.md$": "Markdown",
                r"\.sql$": "SQL",
                r"\.css$": "CSS",
                r"\.html$": "HTML",
                r"(^|/)Dockerfile$": "Docker"
            }
            for f in file_paths:
                for regex, lang in lang_map.items():
                    if re.search(regex, f, re.IGNORECASE):
                        languages.add(lang)
                        break
            gt.changed_languages = sorted(list(languages))
            gt.ground_truth_status = "available"
            gt.status_text = "Success"

        except Exception as e:
            logger.warning("Failed to fetch GitHub ground truth for issue #%d: %s", issue_number, e)
            gt.ground_truth_status = "capture_failed"
            gt.status_text = f"Error: {e}"

        return gt

    def _find_closing_pr_from_timeline(self, owner: str, repo: str, issue_number: int) -> Tuple[Optional[int], Optional[str]]:
        """Scan issue timeline to locate the pull request or commit that closed it."""
        try:
            timeline_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/timeline"
            events = self._get(timeline_url, params={"per_page": 100})
            
            pr_number = None
            closing_commit = None

            for event in events:
                event_name = event.get("event")
                
                # Check closed event
                if event_name == "closed":
                    commit_sha = event.get("commit_id")
                    if commit_sha:
                        closing_commit = commit_sha
                    
                    # Sometimes the closing event directly points to a pull request source
                    source = event.get("source", {})
                    if source.get("type") == "issue" and "pull_request" in source.get("issue", {}):
                        pr_num = source.get("issue", {}).get("number")
                        if pr_num:
                            pr_number = pr_num
                
                # Check connected/cross-referenced events
                elif event_name in ("connected", "cross-referenced"):
                    source = event.get("source", {})
                    if source.get("type") == "issue" and "pull_request" in source.get("issue", {}):
                        pr_num = source.get("issue", {}).get("number")
                        if pr_num:
                            pr_number = pr_num

            return pr_number, closing_commit
        except Exception as e:
            logger.debug("Timeline fetch failed or had issues for #%d: %s", issue_number, e)
            return None, None

    def _find_closing_pr_via_search(self, owner: str, repo: str, issue_number: int) -> Optional[int]:
        """Query GitHub search API for merged PRs referencing the issue number."""
        try:
            query = f"is:pr is:merged repo:{owner}/{repo} {issue_number}"
            search_url = "https://api.github.com/search/issues"
            res = self._get(search_url, params={"q": query})
            
            items = res.get("items", [])
            for item in items:
                pr_num = item.get("number")
                if pr_num and pr_num != issue_number:
                    # Double check if it contains a pull_request link
                    if "pull_request" in item:
                        return pr_num
            return None
        except Exception as e:
            logger.debug("Search API failed to find PR for issue #%d: %s", issue_number, e)
            return None
