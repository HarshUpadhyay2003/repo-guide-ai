import json
import logging
from typing import Any, Dict, List

from app.prompts.repository_map import REPOSITORY_MAP_PROMPT
from app.schema.repository_map import RepositoryMap
from app.services.github_service import GitHubService
from app.services.llm_service import LLMGenerationError, LLMService

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

    def __init__(self, github_service: GitHubService | None = None, llm_service: LLMService | None = None) -> None:
        self.github_service = github_service or GitHubService()
        self.llm_service = llm_service or LLMService()

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

    def generate_map(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch repository structure and return categorized directories."""
        logger.info("Starting repository map generation for %s/%s", owner, repo)

        try:
            tree = self.github_service.get_repository_tree(owner, repo)
            directories = self._extract_important_directories(tree)

            if not directories:
                logger.warning("No valid directories found to map.")
                return RepositoryMap().model_dump()

            prompt = REPOSITORY_MAP_PROMPT.format(
                directories=json.dumps(directories, ensure_ascii=False)[:4000]
            )

            logger.info("Sending repository map prompt to LLM")
            response = self.llm_service.generate_json(prompt)
            repo_map = RepositoryMap.model_validate(response)

            logger.info("Repository map generation completed successfully")
            return repo_map.model_dump()
            
        except (ValueError, TypeError, KeyError, LLMGenerationError, Exception) as exc:
            logger.exception("Repository map generation failed: %s", exc)
            raise RuntimeError("Failed to generate repository map.") from exc