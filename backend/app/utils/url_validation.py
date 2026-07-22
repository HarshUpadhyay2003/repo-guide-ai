import ipaddress
import re
from urllib.parse import urlparse


GITHUB_HOSTS = {"github.com", "www.github.com"}
VALID_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+$")


def validate_github_url(url: str) -> tuple[str, str]:
    """Validate a GitHub repository URL using structured parsing.
    
    Requirements:
    - Must be a non-empty string
    - Must use HTTPS scheme
    - Must target host github.com or www.github.com
    - Must specify valid owner and repository path (/owner/repo)
    - Rejects localhost, IP literals, private networks, and non-GitHub hosts
    
    Returns:
        tuple[str, str]: Normalized (owner, repo) pair.
        
    Raises:
        ValueError: If validation fails.
    """
    if not isinstance(url, str) or not url.strip():
        raise ValueError("URL must be a non-empty string.")

    cleaned_url = url.strip()

    try:
        parsed = urlparse(cleaned_url)
    except Exception as exc:
        raise ValueError(f"Invalid URL structure: {url}") from exc

    # 1. Require HTTPS scheme strictly
    scheme = (parsed.scheme or "").lower()
    if scheme != "https":
        raise ValueError(f"Invalid URL scheme '{scheme}'. Only 'https' is permitted.")

    # 2. Extract host and port
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError("URL host cannot be empty.")

    # Reject IP literals (IPv4 and IPv6)
    try:
        ipaddress.ip_address(hostname)
        raise ValueError(f"IP literals are not permitted: '{hostname}'.")
    except ValueError as ip_exc:
        # Expected: hostname is a domain string, not an IP address
        if "are not permitted" in str(ip_exc):
            raise

    # Reject localhost or non-GitHub hosts
    if hostname == "localhost" or hostname.endswith(".local") or hostname.endswith(".internal"):
        raise ValueError(f"Host '{hostname}' is not a permitted public host.")

    if hostname not in GITHUB_HOSTS:
        raise ValueError(f"Invalid host '{hostname}'. Only 'github.com' is permitted.")

    # 3. Validate path structure: /owner/repo or /owner/repo.git
    path_segments = [seg for seg in parsed.path.strip("/").split("/") if seg]
    if len(path_segments) < 2:
        raise ValueError(
            f"Invalid GitHub repository path '{parsed.path}'. "
            "URL must follow the format 'https://github.com/owner/repository'."
        )

    owner = path_segments[0]
    repo = path_segments[1]

    # Remove trailing .git if present
    if repo.endswith(".git"):
        repo = repo[:-4]

    if not owner or not repo:
        raise ValueError("Owner and repository name cannot be empty.")

    if not VALID_NAME_PATTERN.match(owner):
        raise ValueError(f"Invalid GitHub repository owner: '{owner}'.")

    if not VALID_NAME_PATTERN.match(repo):
        raise ValueError(f"Invalid GitHub repository name: '{repo}'.")

    return owner.lower(), repo.lower()
