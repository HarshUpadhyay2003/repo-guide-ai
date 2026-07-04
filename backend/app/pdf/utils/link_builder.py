from typing import Any, Dict

def parse_repo_info(metadata: Dict[str, Any]) -> tuple:
    """
    Extract owner and repo name from metadata dictionary.
    Supports both direct extraction and parsing from html_url.
    """
    if not metadata:
        return "UnknownOwner", "UnknownRepo"
        
    owner = metadata.get("owner")
    repo = metadata.get("name") or metadata.get("repo")
    
    # Try parsing from html_url if owner or repo is missing
    html_url = metadata.get("html_url")
    if html_url and (not owner or not repo):
        # e.g., https://github.com/owner/repo
        parts = html_url.rstrip("/").split("/")
        if len(parts) >= 5:
            if not owner:
                owner = parts[-2]
            if not repo:
                repo = parts[-1]
                
    return owner or "UnknownOwner", repo or "UnknownRepo"

def get_default_branch(metadata: Dict[str, Any]) -> str:
    """Retrieve default branch from metadata, falling back to 'main'."""
    if not metadata:
        return "main"
    return metadata.get("default_branch") or "main"

def build_repository_url(metadata: Dict[str, Any]) -> str:
    """Build the repository home URL on GitHub."""
    if metadata and metadata.get("html_url"):
        return metadata.get("html_url")
    owner, repo = parse_repo_info(metadata)
    return f"https://github.com/{owner}/{repo}"

def build_issue_url(metadata: Dict[str, Any], issue_number: Any) -> str:
    """Build the GitHub URL for a specific issue."""
    repo_url = build_repository_url(metadata)
    return f"{repo_url}/issues/{issue_number}"

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
