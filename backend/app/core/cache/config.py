from typing import Final

# Centralized TTL configurations (in seconds) for RepoGuideAI cache infrastructure.
# These define the maximum cache age for various domains of repository data.
CACHE_TTL_REPO_METADATA: Final[int] =  3600# 1 hour
CACHE_TTL_REPO_SUMMARY: Final[int] = 86400        # 24 hours
CACHE_TTL_REPO_MAP: Final[int] = 86400            # 24 hours
CACHE_TTL_ISSUE_GUIDANCE: Final[int] = 86400      # 24 hours
CACHE_TTL_ROADMAP: Final[int] = 86400             # 24 hours
CACHE_TTL_FULL_ANALYSIS: Final[int] = 86400       # 24 hours

# GitHub API Response Caching TTLs (Stage 8.2)
CACHE_TTL_REPO_README: Final[int] = 86400         # 24 hours
CACHE_TTL_REPO_CONTRIBUTING: Final[int] = 86400   # 24 hours
CACHE_TTL_REPO_TREE: Final[int] = 86400           # 24 hours
CACHE_TTL_ISSUE_SEARCH: Final[int] = 900          # 15 minutes
CACHE_TTL_ISSUE_COMMENTS: Final[int] = 900        # 15 minutes

