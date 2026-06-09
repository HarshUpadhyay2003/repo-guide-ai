import json
import logging
from typing import Any, Dict, List

from app.prompts.tree_analysis import TREE_ANALYSIS_PROMPT
from app.schema.tree_analysis import TreeAnalysisOutput, TreeInput
from app.services.github_service import GitHubService
from app.services.llm_service import LLMGenerationError, LLMService

logger = logging.getLogger(__name__)

IGNORED_FOLDERS = {
    ".git",
    ".github",
    ".vscode",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    "target",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}


class TreeService:
    """Explain repository folders to beginners using LLM analysis."""

    def __init__(self, github_service: GitHubService | None = None, llm_service: LLMService | None = None) -> None:
        self.github_service = github_service or GitHubService()
        self.llm_service = llm_service or LLMService()

    def _compact_tree(self, tree: Dict[str, Any]) -> Dict[str, Any]:
        """Keep only important top-level folders and trim content for prompt size."""
        compact: Dict[str, Any] = {}
        for name, children in tree.items():
            if name in IGNORED_FOLDERS or name.startswith("."):
                continue
            compact[name] = list(children)[:5] if isinstance(children, list) else []
        return dict(sorted(compact.items()))

    def analyze_tree(self, payload: Dict[str, Any], owner: str | None = None, repo: str | None = None) -> Dict[str, Any]:
        """Analyze repository folders and return beginner-friendly guidance."""
        logger.info("Starting tree analysis with payload: %s", payload)

        try:
            if owner and repo:
                tree = self.github_service.get_repository_tree(owner, repo)
            else:
                tree = payload.get("tree", {})

            validated_payload = TreeInput.model_validate({
                "tree": self._compact_tree(tree if isinstance(tree, dict) else {}),
                "repo_summary": payload.get("repo_summary", {}),
            })

            prompt = TREE_ANALYSIS_PROMPT.format(
                repo_summary=json.dumps(validated_payload.repo_summary, ensure_ascii=False),
                tree=json.dumps(validated_payload.tree, ensure_ascii=False)[:4000],
            )

            logger.info("Sending tree analysis prompt to LLM")
            response = self.llm_service.generate_json(prompt)
            analysis = TreeAnalysisOutput.model_validate(response)

            logger.info("Tree analysis completed successfully")
            return analysis.model_dump()
        except (ValueError, TypeError, KeyError, LLMGenerationError, Exception) as exc:
            logger.exception("Tree analysis failed: %s", exc)
            raise RuntimeError("Failed to analyze repository tree.") from exc
