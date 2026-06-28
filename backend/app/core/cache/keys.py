from typing import Final, Union

# RATIONALE FOR CACHE VERSIONING:
# Versioning prevents cache pollution and compatibility issues when data schemas or layouts evolve.
# Changing CACHE_VERSION dynamically invalidates the entire cache namespace across all backends
# without needing backend-specific flush/clear operations.
CACHE_VERSION: Final[str] = "v1"

def _normalize(owner: str, repo: str) -> tuple[str, str]:
    """Helper to strip and lowercase owner and repo name to avoid duplicate cache entries due to case mismatch."""
    return owner.strip().lower(), repo.strip().lower()

def get_repo_metadata_key(owner: str, repo: str) -> str:
    """Generate a deterministic, human-readable cache key for repository metadata."""
    o, r = _normalize(owner, repo)
    return f"cache:{CACHE_VERSION}:repo:{o}/{r}:metadata"

def get_repo_summary_key(owner: str, repo: str) -> str:
    """Generate a deterministic, human-readable cache key for repository summary."""
    o, r = _normalize(owner, repo)
    return f"cache:{CACHE_VERSION}:repo:{o}/{r}:summary"

def get_repo_map_key(owner: str, repo: str) -> str:
    """Generate a deterministic, human-readable cache key for repository map."""
    o, r = _normalize(owner, repo)
    return f"cache:{CACHE_VERSION}:repo:{o}/{r}:map"

def get_issue_guidance_key(owner: str, repo: str, issue_number: Union[int, str]) -> str:
    """Generate a deterministic, human-readable cache key for issue guidance."""
    o, r = _normalize(owner, repo)
    issue_num_str = str(issue_number).strip()
    return f"cache:{CACHE_VERSION}:repo:{o}/{r}:issue:{issue_num_str}:guidance"

def get_roadmap_key(owner: str, repo: str) -> str:
    """Generate a deterministic, human-readable cache key for contributor roadmap."""
    o, r = _normalize(owner, repo)
    return f"cache:{CACHE_VERSION}:repo:{o}/{r}:roadmap"

def get_full_analysis_key(owner: str, repo: str) -> str:
    """Generate a deterministic, human-readable cache key for full repository analysis."""
    o, r = _normalize(owner, repo)
    return f"cache:{CACHE_VERSION}:repo:{o}/{r}:full_analysis"

def get_repo_readme_key(owner: str, repo: str) -> str:
    """Generate a deterministic, human-readable cache key for repository README."""
    o, r = _normalize(owner, repo)
    return f"cache:{CACHE_VERSION}:repo:{o}/{r}:readme"

def get_repo_contributing_key(owner: str, repo: str) -> str:
    """Generate a deterministic, human-readable cache key for repository CONTRIBUTING."""
    o, r = _normalize(owner, repo)
    return f"cache:{CACHE_VERSION}:repo:{o}/{r}:contributing"

def get_repo_tree_key(owner: str, repo: str) -> str:
    """Generate a deterministic, human-readable cache key for repository tree structure."""
    o, r = _normalize(owner, repo)
    return f"cache:{CACHE_VERSION}:repo:{o}/{r}:tree"

def get_repo_issue_search_key(owner: str, repo: str) -> str:
    """Generate a deterministic, human-readable cache key for good first issues search results."""
    o, r = _normalize(owner, repo)
    return f"cache:{CACHE_VERSION}:repo:{o}/{r}:issue_search"

def get_issue_comments_key(owner: str, repo: str, issue_number: Union[int, str]) -> str:
    """Generate a deterministic, human-readable cache key for issue comments."""
    o, r = _normalize(owner, repo)
    issue_num_str = str(issue_number).strip()
    return f"cache:{CACHE_VERSION}:repo:{o}/{r}:issue:{issue_num_str}:comments"

