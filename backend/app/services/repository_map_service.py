import logging
from typing import Any, Dict, List

from app.schema.repository_map import RepositoryMap
from app.services.github_service import GitHubService
from constants import MAX_DIRECTORY_ENTRIES

logger = logging.getLogger(__name__)

IGNORED_DIRS = {
    ".git",
    "node_modules",
    "venv",
    "env",
    "__pycache__",
    "dist",
    "build",
    "target",
    ".pytest_cache",
    ".mypy_cache",
}

class RepositoryMapService:
    """Analyze repository tree and categorize directories."""

    def __init__(self, github_service: GitHubService | None = None) -> None:
        self.github_service = github_service or GitHubService()

    def _extract_important_directories(self, tree: List[Dict[str, Any]]) -> List[str]:
        """Extract top-level and important second-level directories."""
        directories = set()
        
        for item in tree:
            if item.get("type") != "tree":
                continue
                
            path = item.get("path", "")
            parts = path.split("/")
            
            # Ignore hidden folders at root except .github
            if parts[0].startswith(".") and parts[0] != ".github":
                continue
                
            # Ignore common dependency/build folders
            if any(ignored in parts for ignored in IGNORED_DIRS):
                continue
            
            # Add top-level and second-level directories
            if len(parts) <= 2:
                directories.add(path)
                
        return sorted(list(directories))

    def _classify_paths(self, paths: List[str]) -> Dict[str, List[str]]:
        categorized: Dict[str, List[str]] = {
            "frontend": [], "backend": [], "tests": [],
            "docs": [], "config": [], "scripts": [], "other": []
        }
        
        rules = {
            "frontend": ["frontend", "web", "ui", "client", "app", "src/components", "src/styles"],
            "backend": ["backend", "server", "api", "services", "libs", "models", "app/api"],
            "tests": ["tests", "test", "e2e", "integration-tests", "spec"],
            "docs": ["docs", "documentation", "wiki"],
            "config": [".github", "config", "configs", ".circleci"],
            "scripts": ["scripts", "tools", "bin"]
        }

        for path in paths:
            matched = False
            for category, keywords in rules.items():
                if any(kw in path for kw in keywords):
                    categorized[category].append(path)
                    matched = True
                    break
            
            if not matched:
                categorized["other"].append(path)
                
        return categorized

    def _limit_entries(self, repo_map: Dict[str, List[str]]) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {
            "frontend": [], "backend": [], "tests": [],
            "docs": [], "config": [], "scripts": [], "other": []
        }
        
        count = 0
        for category, items in repo_map.items():
            for item in items:
                if count < MAX_DIRECTORY_ENTRIES:
                    result[category].append(item)
                    count += 1
                else:
                    break
                    
        return result

    def generate_map(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch repository structure and return categorized directories."""
        logger.info("Starting repository map generation for %s/%s", owner, repo)

        try:
            tree = self.github_service.get_repository_tree(owner, repo)
            directories = self._extract_important_directories(tree)

            if not directories:
                logger.warning("No valid directories found to map.")
                return RepositoryMap().model_dump()

            repo_map = self._classify_paths(directories)
            limited_map = self._limit_entries(repo_map)

            logger.info("Repository map generation completed successfully")
            return RepositoryMap(**limited_map).model_dump()
            
        except (ValueError, TypeError, KeyError, Exception) as exc:
            logger.exception("Repository map generation failed: %s", exc)
            raise RuntimeError("Failed to generate repository map.") from exc