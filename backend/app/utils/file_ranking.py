import re
from functools import lru_cache
from typing import List, Tuple, Dict, Any

@lru_cache(maxsize=16384)
def get_path_category(file_path: str) -> str:
    path_lower = file_path.lower()
    
    # 1. Config/workflow
    if (
        ".github/" in path_lower 
        or "workflows/" in path_lower 
        or "/config/" in path_lower 
        or "/configs/" in path_lower 
        or path_lower.startswith("config/") 
        or path_lower.startswith("configs/")
        or "ci/" in path_lower
        or path_lower.endswith(('.yml', '.yaml', '.json', '.toml', '.ini', '.cfg', '.config', '.lock'))
    ):
        return "config"
        
    # 2. Tests
    if "test" in path_lower or "spec" in path_lower:
        return "tests"
        
    # 3. Docs
    if "doc" in path_lower or "example" in path_lower or "sample" in path_lower or path_lower.endswith(('.md', '.rst', '.txt')):
        return "docs"
        
    # 4. Scripts
    if "script" in path_lower or "tools/" in path_lower or "bin/" in path_lower or path_lower.startswith("tools/") or path_lower.startswith("bin/"):
        return "scripts"
        
    # 5. Frontend source
    if (
        "frontend/" in path_lower 
        or "web/" in path_lower 
        or "ui/" in path_lower 
        or "client/" in path_lower 
        or "static/" in path_lower
        or path_lower.endswith(('.ts', '.tsx', '.jsx', '.css', '.scss', '.html'))
    ):
        return "frontend"
        
    # 6. Backend source
    if (
        "backend/" in path_lower 
        or "server/" in path_lower 
        or "api/" in path_lower 
        or "app/" in path_lower
        or path_lower.endswith(('.py', '.go', '.java', '.js'))
    ):
        return "backend"
        
    return "other"

@lru_cache(maxsize=128)
def _extract_keywords_cached(text: str) -> Tuple[str, ...]:
    if not text:
        return ()
    # Tokenize by splitting on any character that is not alphanumeric
    words = re.findall(r'[a-zA-Z0-9]+', text.lower())
    stop_words = {
        "the", "and", "for", "with", "this", "that", "from", "are", "was", "were", 
        "but", "not", "its", "out", "has", "our", "your", "their", "they", "them", 
        "will", "would", "should", "could", "about", "above", "after", "again", "against"
    }
    keywords = []
    for w in words:
        if len(w) >= 3 and w not in stop_words:
            keywords.append(w)
            # Remove 'ing' suffix
            if w.endswith('ing') and len(w) > 5:
                keywords.append(w[:-3])
            # Remove 's' suffix
            if w.endswith('s') and len(w) > 4:
                keywords.append(w[:-1])
    return tuple(sorted(list(set(keywords))))

def extract_keywords(text: str) -> List[str]:
    return list(_extract_keywords_cached(text))

@lru_cache(maxsize=16384)
def _score_file_cached(
    file_path: str,
    issue_title: str,
    affected_area: str,
    issue_labels_tuple: Tuple[str, ...]
) -> Tuple[int, Tuple[str, ...]]:
    reasons = []
    score = 0
    
    path_lower = file_path.lower()
    category = get_path_category(file_path)
    
    # Check if workflow issue
    issue_text = f"{issue_title or ''} {affected_area or ''} {' '.join(issue_labels_tuple or [])}".lower()
    workflow_keywords = ["workflow", "github actions", "pipeline", "ci", "yaml"]
    is_workflow_issue = any(wk in issue_text for wk in workflow_keywords)
    
    # 1. Category scoring
    if category == "backend":
        score += 100
        reasons.append("Backend source: +100")
    elif category == "frontend":
        score += 100
        reasons.append("Frontend source: +100")
    elif category == "tests":
        score += 50
        reasons.append("Tests: +50")
    elif category == "docs":
        score += 20
        reasons.append("Docs: +20")
    elif category == "scripts":
        score += 10
        reasons.append("Scripts: +10")
    elif category == "config":
        if is_workflow_issue:
            score += 100
            reasons.append("Workflow exception (Config): +100")
        else:
            score -= 50
            reasons.append("Config/workflow: -50")
            
    # 2. Extension scoring
    ext_boost = (".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java")
    ext_penalty = (".yml", ".yaml", ".json")
    
    if path_lower.endswith(ext_boost):
        score += 25
        reasons.append("Extension scoring: +25")
    elif path_lower.endswith(ext_penalty):
        if category == "config" and is_workflow_issue:
            score += 25
            reasons.append("Workflow exception (Extension): +25")
        else:
            score -= 25
            reasons.append("Extension scoring: -25")
            
    # 3. Keyword scoring
    allow_keyword_boost = True
    if category == "config" and not is_workflow_issue:
        allow_keyword_boost = False
        
    if allow_keyword_boost:
        title_kws = extract_keywords(issue_title)
        area_kws = extract_keywords(affected_area)
        keywords = list(set(title_kws + area_kws))
        
        matched_keywords = []
        for kw in keywords:
            if kw in path_lower:
                score += 50
                matched_keywords.append(kw)
        if matched_keywords:
            reasons.append(f"Keyword scoring ({', '.join(sorted(matched_keywords))}): +{len(matched_keywords) * 50}")
            
    return score, tuple(reasons)

def score_file(
    file_path: str,
    issue_title: str,
    affected_area: str,
    issue_labels: List[str]
) -> Tuple[int, List[str]]:
    labels_tuple = tuple(issue_labels) if issue_labels else ()
    score, reasons_tuple = _score_file_cached(file_path, issue_title, affected_area, labels_tuple)
    return score, list(reasons_tuple)

# Bounded cache for candidate files
_candidate_files_cache = {}

def get_candidate_files(all_files: List[str], repository_map: Dict[str, Any]) -> List[str]:
    # Extract candidate directories
    candidate_dirs = []
    if isinstance(repository_map, dict):
        for paths in repository_map.values():
            if isinstance(paths, list):
                candidate_dirs.extend(paths)
    candidate_dirs = sorted(list(set(candidate_dirs)))
    
    # Deterministic cache key based on the candidate directories and repo files footprint
    repo_footprint = (len(all_files), all_files[0] if all_files else "")
    cache_key = (tuple(candidate_dirs), repo_footprint)
    
    if cache_key in _candidate_files_cache:
        return _candidate_files_cache[cache_key]
        
    tuple_prefixes = tuple(folder + "/" for folder in candidate_dirs)
    candidate_files = [f for f in all_files if f.startswith(tuple_prefixes)]
    
    # Bounded size eviction to prevent leaks
    if len(_candidate_files_cache) >= 32:
        _candidate_files_cache.clear()
        
    _candidate_files_cache[cache_key] = candidate_files
    return candidate_files


def infer_issue_category(
    issue_title: str,
    affected_area: str,
    issue_labels: List[str]
) -> str | None:
    context = f"{issue_title or ''} {affected_area or ''} {' '.join(issue_labels or [])}".lower()
    
    frontend_kws = {
        "frontend", "web", "ui", "client", "layout", "css", "html", "react", "vue", "ts", "tsx", "js", "jsx",
        "style", "button", "render", "page", "component", "components", "assets", "styles", "modal", "dialog",
        "tab", "menu", "navbar", "dom", "browser", "dropdown", "spacing", "alignment", "flexbox", "grid"
    }
    backend_kws = {
        "backend", "server", "api", "db", "database", "sql", "postgres", "query", "model", "models", "python",
        "django", "flask", "fastapi", "go", "golang", "java", "orm", "migration", "migrations", "endpoint",
        "route", "auth", "login", "redis", "cache", "cron", "worker", "celery", "task", "tasks"
    }
    tests_kws = {
        "test", "tests", "spec", "testing", "pytest", "unittest", "mock", "stub", "assert", "coverage"
    }
    docs_kws = {
        "doc", "docs", "documentation", "readme", "markdown", "rst", "wiki", "changelog", "tutorial", "guide"
    }
    config_kws = {
        "config", "configs", "configuration", "settings", "env", "github actions", "ci", "cd", "workflow",
        "pipelines", "docker", "compose", "yaml", "yml", "toml", "ini", "package.json", "requirements.txt"
    }
    scripts_kws = {
        "script", "scripts", "tools", "bin", "cli", "bash", "sh", "utility", "utilities", "helper", "helpers"
    }

    words = re.findall(r'[a-zA-Z0-9]+', context)
    
    scores = {
        "frontend": sum(1 for w in words if w in frontend_kws),
        "backend": sum(1 for w in words if w in backend_kws),
        "tests": sum(1 for w in words if w in tests_kws),
        "docs": sum(1 for w in words if w in docs_kws),
        "config": sum(1 for w in words if w in config_kws),
        "scripts": sum(1 for w in words if w in scripts_kws)
    }

    max_score = max(scores.values())
    if max_score == 0:
        return None

    best_cats = [cat for cat, score in scores.items() if score == max_score]
    if len(best_cats) == 1:
        return best_cats[0]
        
    return None


def prefilter_candidates(
    candidate_files: List[str],
    issue_title: str,
    affected_area: str,
    issue_labels: List[str]
) -> List[str]:
    # Extract keywords
    title_kws = extract_keywords(issue_title)
    area_kws = extract_keywords(affected_area) if affected_area else []
    labels_kws = [l.lower() for l in issue_labels] if issue_labels else []
    keywords = set(title_kws + area_kws + labels_kws)
    
    # Extension detection
    workflow_kws = {"workflow", "github actions", "pipeline", "ci", "yaml", "yml"}
    doc_kws = {"docs", "documentation", "readme", "markdown"}
    
    if any(wk in keywords for wk in workflow_kws):
        allowed_exts = (".yml", ".yaml", ".toml", ".json", ".ini")
    elif any(dk in keywords for dk in doc_kws):
        allowed_exts = (".md", ".rst", ".txt")
    else:
        allowed_exts = (".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".css", ".scss", ".html")

    tier1 = []
    tier2 = []
    tier3 = []
    
    for f in candidate_files:
        path_lower = f.lower()
        has_kw = any(kw in path_lower for kw in keywords)
        has_ext = path_lower.endswith(allowed_exts)
        
        if has_kw and has_ext:
            tier1.append(f)
        elif has_kw:
            tier2.append(f)
        elif has_ext:
            tier3.append(f)
            
    # Dynamic Backfill Strategy
    if len(tier1) >= 100:
        pool = tier1[:300]
    else:
        pool = (tier1 + tier2)[:200]
        if len(pool) < 200:
            pool = (pool + tier3)[:200]
            
    if len(pool) < 50:
        return candidate_files
        
    return pool
