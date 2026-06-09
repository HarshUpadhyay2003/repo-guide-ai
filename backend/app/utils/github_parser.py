import re
from typing import Dict

_GITHUB_URL_PATTERN = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)/?$"
)


def parse_github_url(url: str) -> Dict[str, str]:
    """Parse a GitHub repository URL into owner and repo names.

    Args:
        url: A GitHub repository URL such as https://github.com/owner/repo/.

    Returns:
        A dictionary with the keys "owner" and "repo".

    Raises:
        ValueError: If the URL is not a valid GitHub repository URL.
    """
    if not isinstance(url, str) or not url.strip():
        raise ValueError("GitHub URL must be a non-empty string.")

    match = _GITHUB_URL_PATTERN.fullmatch(url.strip())
    if not match:
        raise ValueError(
            "Invalid GitHub repository URL. Expected https://github.com/owner/repo"
        )

    return {
        "owner": match.group("owner"),
        "repo": match.group("repo"),
    }
