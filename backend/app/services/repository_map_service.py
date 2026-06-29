import json
import logging
import re
import time
from typing import Any, Dict, List, Tuple

from app.schema.repository_map import RepositoryMap
from app.services.github_service import GitHubService
from constants import ENABLE_PERF_DIAGNOSTICS, MAX_DIRECTORY_ENTRIES, ENABLE_DEEP_PROFILING

# Cache imports
from app.core.cache.dependencies import get_cache_manager
from app.core.cache.manager import CacheManager
from app.core.cache.keys import get_repo_map_key
from app.core.cache.config import CACHE_TTL_REPO_MAP

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

# Directories permitted at depth-3 if they match these exactly
HIGH_PRIORITY_NAMES = {
    "docs", "documentation", "examples", "example", "samples", "sample",
    "test", "tests", "testing", "__tests__", "spec", "specs", "e2e", "integration",
    "scripts", "tools", "bin",
    "config", "configs", ".github", "github", "workflows", "ci",
    "deployment", "infra", "infrastructure"
}

# Exact matching keywords for splitting check
RULES_EXACT = {
    "tests": {
        "test", "tests", "testing", "spec", "specs", "e2e", 
        "integration", "unittest", "unittests", "pytest", "jest"
    },
    "docs": {
        "docs", "doc", "documentation", "wiki", "examples", "example", 
        "samples", "sample", "tutorial", "tutorials", "guide", "guides"
    },
    "config": {
        "config", "configs", "configuration", "configurations", 
        "github", "workflows", "ci", "deployment", "deploy", 
        "infra", "infrastructure", "docker", "kubernetes", "k8s", 
        "helm", "terraform", "tf", "ansible", "settings", "setup"
    },
    "scripts": {
        "scripts", "script", "tools", "tool", "bin", "cli", 
        "utilities", "utility", "utils", "util", "tasks", "task"
    },
    "frontend": {
        "frontend", "web", "ui", "client", "app", "components", "component", 
        "styles", "style", "pages", "page", "views", "view", "static", 
        "public", "assets", "react", "next", "vue", "angular", "ts", "js"
    },
    "backend": {
        "backend", "server", "api", "services", "service", "libs", "lib", 
        "models", "model", "controllers", "controller", "routers", "router", 
        "handlers", "handler", "queries", "query", "commands", "command", 
        "db", "database", "migrations", "migration"
    }
}

# Specific path patterns matching parent-child fragments (whole-path substring matches)
PATH_PATTERN_BONUSES = {
    "frontend": ["src/components", "src/styles", "src/pages", "src/views", "frontend/", "/frontend", "web/", "/web", "client/", "/client"],
    "backend": ["app/api", "src/api", "server/api", "backend/", "/backend", "server/", "/server", "api/", "/api"],
    "tests": ["/tests", "tests/", "/test", "test/", "/spec", "spec/", "/testing", "testing/"],
    "docs": ["/docs", "docs/", "/documentation", "documentation/", "/examples", "examples/"],
    "config": [".github/", "/.github", "workflows/", "/workflows", "config/", "/config", "configs/", "/configs"],
    "scripts": ["scripts/", "/scripts", "tools/", "/tools", "bin/", "/bin"]
}

# Fallback substring rules for the entire path string
FALLBACK_SUBSTRINGS = {
    "tests": ["test", "spec", "testing", "specs", "e2e"],
    "docs": ["docs", "documentation", "examples", "example", "samples", "sample"],
    "config": [".github", "workflows", "config", "configs", "infrastructure", "deployment"]
}


class RepositoryMapService:
    """Analyze repository tree and categorize directories."""

    def __init__(
        self,
        github_service: GitHubService | None = None,
        cache_manager: CacheManager | None = None
    ) -> None:
        self.github_service = github_service or GitHubService()
        self.cache_manager = cache_manager or get_cache_manager()

    def _extract_important_directories(self, tree: List[Dict[str, Any]]) -> List[str]:
        """Extract top-level and important second/third-level directories."""
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
            elif len(parts) == 3:
                # Allow depth = 3 only if a path component exactly matches high-priority folder names
                if any(part in HIGH_PRIORITY_NAMES for part in parts):
                    directories.add(path)
                
        return sorted(list(directories))

    def _classify_paths(self, paths: List[str]) -> Tuple[Dict[str, List[str]], List[Dict[str, Any]]]:
        categorized: Dict[str, List[str]] = {
            "frontend": [], "backend": [], "tests": [],
            "docs": [], "config": [], "scripts": [], "other": []
        }
        diagnostics = []
        
        for path in paths:
            path_lower = path.lower()
            parts = [p.lower() for p in path.split("/")]
            
            scores = {cat: 0 for cat in ["frontend", "backend", "tests", "docs", "config", "scripts"]}
            reasons = {cat: [] for cat in ["frontend", "backend", "tests", "docs", "config", "scripts"]}
            
            # 1. Path pattern bonuses
            for cat, patterns in PATH_PATTERN_BONUSES.items():
                for pat in patterns:
                    if pat in path_lower:
                        scores[cat] += 15
                        reasons[cat].append(f"matched path pattern {pat}")
                        
            # 2. Exact component word match
            for part in parts:
                sub_parts = re.split(r'[-_.]', part)
                for sub_part in sub_parts:
                    for cat, keywords in RULES_EXACT.items():
                        if sub_part in keywords:
                            scores[cat] += 10
                            reasons[cat].append(f"matched exact component keyword '{sub_part}'")
                            
            # 3. Fallback substring matches
            for cat, substrings in FALLBACK_SUBSTRINGS.items():
                for sub in substrings:
                    if sub in path_lower:
                        scores[cat] += 20
                        reasons[cat].append(f"fallback substring matched '{sub}'")
            
            # Tie-breaker priority order
            categories = ["tests", "docs", "config", "scripts", "frontend", "backend"]
            best_category = "other"
            max_score = 0
            for cat in categories:
                score = scores[cat]
                if score > max_score:
                    max_score = score
                    best_category = cat
                    
            if max_score > 0:
                reason_list = reasons[best_category]
            else:
                best_category = "other"
                reason_list = ["no scoring rules matched"]
                
            categorized[best_category].append(path)
            
            if ENABLE_PERF_DIAGNOSTICS:
                diagnostics.append({
                    "path": path,
                    "category": best_category,
                    "score": max_score,
                    "reason": reason_list
                })
                
        return categorized, diagnostics

    def _limit_entries(self, repo_map: Dict[str, List[str]]) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {
            "frontend": [], "backend": [], "tests": [],
            "docs": [], "config": [], "scripts": [], "other": []
        }
        
        for category, items in repo_map.items():
            result[category] = items[:MAX_DIRECTORY_ENTRIES]
                    
        return result

    def generate_map(self, owner: str, repo: str, tree: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
        """Fetch repository structure and return categorized directories."""
        logger.info("Starting repository map generation for %s/%s", owner, repo)
        start_map = time.perf_counter()
        
        # 1. Cache Read Attempt
        key = None
        cached_map = None
        try:
            key = get_repo_map_key(owner, repo)
            cached_map = self.cache_manager.get(key)
        except Exception as exc:
            if isinstance(exc, (TypeError, ValueError)):
                raise
            logger.warning("[CACHE] Cache check failed for key %s: %s", key or "unknown", exc)

        if cached_map is not None:
            print("[CACHE][Repository Map] HIT")
            
            # Save metrics to self.metrics if available
            if hasattr(self, "metrics") and isinstance(self.metrics, dict):
                self.metrics["tree_map_gen_dur"] = time.perf_counter() - start_map
                
            return cached_map
        else:
            print("[CACHE][Repository Map] MISS")
        
        tree_download_time = 0.0

        try:
            if tree is None:
                tree_start = time.perf_counter()
                tree = self.github_service.get_repository_tree(owner, repo)
                tree_download_time = time.perf_counter() - tree_start
            
            # Count files and directories
            total_entries = len(tree)
            files_count = sum(1 for x in tree if x.get("type") != "tree")
            dirs_count = sum(1 for x in tree if x.get("type") == "tree")

            extract_start = time.perf_counter()
            directories = self._extract_important_directories(tree)
            extract_dur = time.perf_counter() - extract_start

            if not directories:
                logger.warning("No valid directories found to map.")
                empty_map = RepositoryMap().model_dump()
                
                # Cache empty map as well
                if key:
                    try:
                        self.cache_manager.set(key, empty_map, CACHE_TTL_REPO_MAP)
                        print("[CACHE WRITE][Repository Map]")
                    except Exception as exc:
                        if isinstance(exc, (TypeError, ValueError)):
                            raise
                        logger.warning("[CACHE] Cache write failed for key %s: %s", key, exc)
                return empty_map

            classify_start = time.perf_counter()
            repo_map, diagnostics = self._classify_paths(directories)
            classify_dur = time.perf_counter() - classify_start
            
            limited_map = self._limit_entries(repo_map)
            map_gen_dur = time.perf_counter() - start_map

            # Print Repository Tree Profile (Part 5)
            if ENABLE_DEEP_PROFILING:
                print()
                print("[TREE PROFILE]")
                print()
                print(f"Total Tree Entries: {total_entries}")
                print()
                print(f"Files: {files_count}")
                print(f"Directories: {dirs_count}")
                print()
                print(f"Tree Download Time: {tree_download_time:.4f}s")
                print()
                print(f"Directory Extraction Time: {extract_dur:.4f}s")
                print()
                print(f"Classification Time: {classify_dur:.4f}s")
                print(f"Map Generation Time: {map_gen_dur:.4f}s")
                print()

            # Save metrics to self.metrics if available
            if hasattr(self, "metrics") and isinstance(self.metrics, dict):
                self.metrics["tree_total_entries"] = total_entries
                self.metrics["tree_files"] = files_count
                self.metrics["tree_dirs"] = dirs_count
                self.metrics["tree_download_time"] = tree_download_time
                self.metrics["tree_extract_dur"] = extract_dur
                self.metrics["tree_classify_dur"] = classify_dur
                self.metrics["tree_map_gen_dur"] = map_gen_dur

            # Log summary
            logger.info(
                "Repository Map Summary:\n"
                "Frontend: %d\n"
                "Backend: %d\n"
                "Tests: %d\n"
                "Docs: %d\n"
                "Config: %d\n"
                "Scripts: %d\n"
                "Other: %d",
                len(limited_map.get("frontend", [])),
                len(limited_map.get("backend", [])),
                len(limited_map.get("tests", [])),
                len(limited_map.get("docs", [])),
                len(limited_map.get("config", [])),
                len(limited_map.get("scripts", [])),
                len(limited_map.get("other", [])),
            )

            # Log detailed diagnostics if enabled
            if ENABLE_PERF_DIAGNOSTICS:
                logger.info("Classification Diagnostics:\n%s", json.dumps(diagnostics, indent=2))

            result_map = RepositoryMap(**limited_map).model_dump()

            # Cache Write Attempt
            if key:
                try:
                    self.cache_manager.set(key, result_map, CACHE_TTL_REPO_MAP)
                    print("[CACHE WRITE][Repository Map]")
                except Exception as exc:
                    if isinstance(exc, (TypeError, ValueError)):
                        raise
                    logger.warning("[CACHE] Cache write failed for key %s: %s", key, exc)

            logger.info("Repository map generation completed successfully")
            return result_map
            
        except (ValueError, TypeError, KeyError, Exception) as exc:
            logger.exception("Repository map generation failed: %s", exc)
            raise RuntimeError("Failed to generate repository map.") from exc