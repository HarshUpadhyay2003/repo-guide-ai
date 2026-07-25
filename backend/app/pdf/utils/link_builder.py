from typing import Any, Dict

def parse_repo_info(metadata: Dict[str, Any]) -> tuple:
    """
    Extract owner and repo name from metadata dictionary.
    Supports direct extraction, nested metadata, and parsing from html_url or url.
    """
    if not metadata:
        return "UnknownOwner", "UnknownRepo"
        
    owner = metadata.get("owner")
    repo = metadata.get("name") or metadata.get("repo")
    
    # Try parsing from html_url or url if owner or repo is missing
    html_url = metadata.get("html_url") or metadata.get("url")
    if html_url and (not owner or not repo):
        # e.g., https://github.com/owner/repo or https://github.com/owner/repo/issues/123
        parts = html_url.rstrip("/").split("/")
        if "github.com" in parts:
            gh_idx = parts.index("github.com")
            if len(parts) > gh_idx + 2:
                if not owner:
                    owner = parts[gh_idx + 1]
                if not repo:
                    repo = parts[gh_idx + 2]
                
    return owner or "UnknownOwner", repo or "UnknownRepo"

def get_default_branch(metadata: Dict[str, Any]) -> str:
    """Retrieve default branch from metadata, falling back to 'main'."""
    if not metadata:
        return "main"
    return metadata.get("default_branch") or "main"

def build_repository_url(metadata: Dict[str, Any]) -> str:
    """Build the repository home URL on GitHub."""
    owner, repo = parse_repo_info(metadata)
    if owner != "UnknownOwner" and repo != "UnknownRepo":
        return f"https://github.com/{owner}/{repo}"
        
    html_url = metadata.get("html_url") or metadata.get("url") if metadata else None
    if html_url and "/issues/" not in html_url:
        return html_url
        
    return f"https://github.com/{owner}/{repo}"

def build_issue_url(issue_or_metadata: Dict[str, Any], issue_number: Any = None) -> str:
    """
    Build or return the canonical GitHub URL for a specific issue.
    
    Priority:
    1. If issue_or_metadata contains a direct issue URL ('html_url' or 'url' containing '/issues/'), return it directly.
    2. Otherwise, construct https://github.com/{owner}/{repo}/issues/{issue_number} using verified owner/repo metadata.
    """
    if not issue_or_metadata:
        issue_or_metadata = {}

    # 1. Direct canonical issue URL from GitHub API
    direct_url = issue_or_metadata.get("html_url") or issue_or_metadata.get("url")
    if direct_url and "/issues/" in direct_url:
        return direct_url

    # 2. Extract issue number if not explicitly provided
    num = issue_number or issue_or_metadata.get("number") or issue_or_metadata.get("issue_number")

    # 3. Extract owner & repo
    owner, repo = parse_repo_info(issue_or_metadata)

    if owner != "UnknownOwner" and repo != "UnknownRepo" and num:
        return f"https://github.com/{owner}/{repo}/issues/{num}"

    # 4. Fallback using repository URL
    repo_url = build_repository_url(issue_or_metadata)
    if num:
        return f"{repo_url}/issues/{num}"
    return repo_url

def build_readme_url(metadata: Dict[str, Any]) -> str:
    """Build the README.md file URL using the repository's default branch."""
    repo_url = build_repository_url(metadata)
    default_branch = get_default_branch(metadata)
    return f"{repo_url}/blob/{default_branch}/README.md"

def build_contributing_url(metadata: Dict[str, Any]) -> str:
    """Build the CONTRIBUTING.md file URL using the repository's default branch."""
    repo_url = build_repository_url(metadata)
    default_branch = get_default_branch(metadata)
    return f"{repo_url}/blob/{default_branch}/CONTRIBUTING.md"
