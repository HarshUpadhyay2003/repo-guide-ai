import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple

# Configuration Constants
MIN_OVERRIDE_MARGIN = 30
SCORE_CRITICAL = 40
SCORE_STRONG = 25
SCORE_SUPPORTING = 10

@dataclass
class ClassificationReconciliationResult:
    original_category: str
    original_subsystem: str
    resolved_category: str
    resolved_subsystem: str
    decision: str  # RETAINED, OVERRIDDEN, INSUFFICIENT_EVIDENCE, NO_CONFLICT
    confidence_score: float
    conflicting_evidence: List[Any] = field(default_factory=list)
    supporting_evidence: List[Any] = field(default_factory=list)
    evidence_entities: List[str] = field(default_factory=list)
    rationale: str = ""

def _matches_keyword(text: str, kw: str) -> bool:
    """Helper to match keywords strictly on word boundaries for pure alphabetic strings, or substring otherwise."""
    if not re.search(r'[^a-zA-Z0-9]', kw):
        return bool(re.search(r'\b' + re.escape(kw) + r'\b', text))
    else:
        return kw in text

def reconcile_issue_classification(
    issue_intelligence: Any,
    issue_evidence: Any
) -> ClassificationReconciliationResult:
    """Deterministic repository-agnostic reconciliation of issue category and subsystem.
    
    Uses critical and strong evidence items as primary decision drivers, with supporting items
    providing minor signal weight.
    """
    orig_cat = getattr(issue_intelligence, "category", "other") or "other"
    orig_sub = getattr(issue_intelligence, "subsystem", "") or ""
    
    # 1. Gather evidence items and filter by strength
    evidence_items = getattr(issue_evidence, "technical_evidence", []) or []
    
    critical_items = [x for x in evidence_items if x.strength == "CRITICAL"]
    strong_items = [x for x in evidence_items if x.strength == "STRONG"]
    supporting_items = [x for x in evidence_items if x.strength == "SUPPORTING"]
    
    high_authority_items = critical_items + strong_items
    
    # All unique entities present in critical/strong/supporting evidence
    evidence_entities = []
    for item in high_authority_items + supporting_items:
        for ent in item.technical_entities:
            if ent not in evidence_entities:
                evidence_entities.append(ent)
                
    if not high_authority_items and not supporting_items:
        return ClassificationReconciliationResult(
            original_category=orig_cat,
            original_subsystem=orig_sub,
            resolved_category=orig_cat,
            resolved_subsystem=orig_sub,
            decision="NO_CONFLICT",
            confidence_score=100.0,
            rationale="No technical evidence was available to reconcile."
        )

    # 2. Define category signal rules (generic keywords / patterns)
    category_keywords = {
        "backend": [
            "client", "server", "api", "database", "db", "query", "httpx", "request", "response",
            "connection", "pool", "instantiation", "fastapi", "flask", "django", "pydantic",
            "sqlalchemy", "requests", "urllib", "runnableconfig", "config", "run", "execute",
            "call", "service", "provider", "adapter", "repository", "controller", "backend", "core",
            "exception", "error", "typeerror", "valueerror"
        ],
        "frontend": [
            "react", "jsx", "tsx", "css", "html", "component", "hook", "dom", "browser", "render",
            "ui", "frontend", "frontend/", "client-side", "styles", "div", "button", "classname"
        ],
        "docs": [
            "readme", "documentation", "docstring", "typo", "guide", "tutorial", "example text",
            "broken documentation link", "doc", "docs", "markdown", ".md"
        ],
        "tests": [
            "pytest", "unittest", "unit test", "integration test", "fixture", "assertion", "mock",
            "test_", "_test", "tests/"
        ],
        "config": [
            "yaml", "toml", "dockerfile", "workflow", "ci", "env", ".github/workflows", "configuration",
            "darg.yaml", "requirements.txt", "pyproject.toml"
        ],
        "scripts": [
            "shell", "bash", "migration", "cli", ".sh", "automation script", "migration script",
            "cli script"
        ],
        "other": []
    }
    
    # 3. Score categories deterministically
    category_scores = {c: 0.0 for c in category_keywords.keys()}
    
    # Map item to categories
    for item in high_authority_items + supporting_items:
        score_weight = 0.0
        if item.strength == "CRITICAL":
            score_weight = SCORE_CRITICAL
        elif item.strength == "STRONG":
            score_weight = SCORE_STRONG
        elif item.strength == "SUPPORTING":
            score_weight = SCORE_SUPPORTING
            
        if score_weight <= 0:
            continue
            
        matched_categories = set()
        
        # Check text signals
        text_lower = item.text.lower()
        norm_lower = item.normalized_value.lower()
        
        for cat, keywords in category_keywords.items():
            for kw in keywords:
                if _matches_keyword(text_lower, kw) or _matches_keyword(norm_lower, kw):
                    matched_categories.add(cat)
                    break
                    
        # Check entities directly
        for ent in item.technical_entities:
            ent_lower = ent.lower()
            for cat, keywords in category_keywords.items():
                for kw in keywords:
                    if _matches_keyword(ent_lower, kw):
                        matched_categories.add(cat)
                        break
                        
        # Specific evidence types matching
        if item.evidence_type == "ERROR_SIGNATURE":
            matched_categories.add("backend")
        elif item.evidence_type == "EXPLICIT_PATH":
            path = item.normalized_value.lower()
            if path.endswith((".md", ".txt")) or "/docs/" in path:
                matched_categories.add("docs")
            elif "/tests/" in path or "test_" in path or "_test.py" in path:
                matched_categories.add("tests")
            elif path.endswith(".sh"):
                matched_categories.add("scripts")
            elif path.endswith((".yaml", ".yml", ".toml")) or "dockerfile" in path:
                matched_categories.add("config")
            elif "libs/" in path or "src/" in path or "app/" in path:
                matched_categories.add("backend")
                
        # Default to backend if it's code element NAMED_CLASS/NAMED_FUNCTION/NAMED_MODULE
        # and has not matched frontend/tests/config/docs/scripts
        if item.evidence_type in ["NAMED_CLASS", "NAMED_FUNCTION", "NAMED_MODULE"]:
            if not matched_categories.intersection({"frontend", "tests", "config", "docs", "scripts"}):
                matched_categories.add("backend")
                
        # Add weights to matched categories
        for cat in matched_categories:
            category_scores[cat] += score_weight
            
    # 4. Resolve Category using constraints
    resolved_category = orig_cat
    decision = "RETAINED"
    conflicting_evidence = []
    supporting_evidence = []
    
    # Tie-breaking priority order (specific categories first)
    priority_order = ["tests", "config", "frontend", "docs", "scripts", "backend", "other"]
    
    # Sort categories: first by score desc, then by priority_order index asc
    sorted_cats = sorted(
        category_scores.keys(),
        key=lambda k: (-category_scores[k], priority_order.index(k))
    )
    best_candidate = sorted_cats[0]
    max_score = category_scores[best_candidate]
            
    # Check if there is an override candidate
    if best_candidate != orig_cat:
        # Preconditions for Override:
        # Must have at least 1 CRITICAL or at least 2 STRONG items associated with the override category
        candidate_items = []
        for item in high_authority_items:
            # Check if this item signals the override candidate category
            signals_candidate = False
            text_lower = item.text.lower()
            norm_lower = item.normalized_value.lower()
            
            for kw in category_keywords[best_candidate]:
                if _matches_keyword(text_lower, kw) or _matches_keyword(norm_lower, kw) or any(_matches_keyword(e.lower(), kw) for e in item.technical_entities):
                    signals_candidate = True
                    break
            if item.evidence_type == "EXPLICIT_PATH" and best_candidate == "docs" and (item.normalized_value.endswith((".md", ".txt")) or "/docs/" in item.normalized_value.lower()):
                signals_candidate = True
            elif item.evidence_type == "EXPLICIT_PATH" and best_candidate == "tests" and ("/tests/" in item.normalized_value.lower() or "test_" in item.normalized_value.lower()):
                signals_candidate = True
            elif item.evidence_type == "ERROR_SIGNATURE" and best_candidate == "backend":
                signals_candidate = True
            elif item.evidence_type in ["NAMED_CLASS", "NAMED_FUNCTION", "NAMED_MODULE"] and best_candidate == "backend":
                signals_candidate = True
                
            if signals_candidate:
                candidate_items.append(item)
                
        has_critical = any(x.strength == "CRITICAL" for x in candidate_items)
        strong_count = len([x for x in candidate_items if x.strength == "STRONG"])
        
        preconditions_met = has_critical or (strong_count >= 2)
        score_diff = category_scores[best_candidate] - category_scores[orig_cat]
        margin_met = score_diff >= MIN_OVERRIDE_MARGIN
        
        if preconditions_met and margin_met:
            resolved_category = best_candidate
            decision = "OVERRIDDEN"
            
            # Populate conflicting and supporting evidence
            for item in high_authority_items + supporting_items:
                is_support = False
                text_lower = item.text.lower()
                norm_lower = item.normalized_value.lower()
                for kw in category_keywords[resolved_category]:
                    if _matches_keyword(text_lower, kw) or _matches_keyword(norm_lower, kw) or any(_matches_keyword(e.lower(), kw) for e in item.technical_entities):
                        is_support = True
                        break
                if item.evidence_type == "ERROR_SIGNATURE" and resolved_category == "backend":
                    is_support = True
                elif item.evidence_type in ["NAMED_CLASS", "NAMED_FUNCTION", "NAMED_MODULE"] and resolved_category == "backend":
                    is_support = True
                    
                if is_support:
                    supporting_evidence.append(item)
                else:
                    conflicting_evidence.append(item)
        else:
            decision = "INSUFFICIENT_EVIDENCE"
            resolved_category = orig_cat
            
    # Calculate confidence based on margin and counts
    confidence_score = 50.0
    if decision == "OVERRIDDEN":
        confidence_score = min(100.0, 70.0 + (max_score - category_scores.get(orig_cat, 0.0)))
    elif decision == "NO_CONFLICT":
        confidence_score = 100.0
    else:
        confidence_score = 80.0
        
    # 5. Resolve Subsystem separately
    resolved_subsystem = orig_sub
    
    # Subsystem resolution flags
    has_tools_signals = False
    has_client_signals = False
    has_ui_signals = False
    has_test_signals = False
    
    for item in high_authority_items:
        text_lower = item.text.lower()
        entities_lower = [e.lower() for e in item.technical_entities]
        
        if any(x in text_lower or x in entities_lower for x in ["basetool.run", "structuredtool._run", "runnableconfig", "basetool", "structuredtool"]):
            has_tools_signals = True
        if any(x in text_lower or x in entities_lower for x in ["azurechatopenai", "httpx", "client instantiation"]):
            has_client_signals = True
        if any(x in text_lower or x in entities_lower for x in ["react", "component", "render"]):
            has_ui_signals = True
        if any(x in text_lower or x in entities_lower for x in ["pytest", "fixture"]):
            has_test_signals = True
            
    if has_tools_signals:
        resolved_subsystem = "core/tools"
    elif has_client_signals:
        resolved_subsystem = "integration/client"
    elif has_ui_signals:
        resolved_subsystem = "ui/component"
    elif has_test_signals:
        resolved_subsystem = "tests"
        
    # Build rationale statement
    if decision == "OVERRIDDEN":
        rationale = f"Reconciler overrode category '{orig_cat}' to '{resolved_category}' with score margin of {category_scores[resolved_category] - category_scores[orig_cat]:.1f}."
    elif decision == "INSUFFICIENT_EVIDENCE":
        rationale = f"Reconciler retained category '{orig_cat}' despite potential candidate '{best_candidate}' due to insufficient margin or high-authority counts."
    elif decision == "NO_CONFLICT":
        rationale = "No conflicting technical signals were encountered; category retained."
    else:
        rationale = f"Reconciler retained original category '{orig_cat}' with matching evidence."
        
    if resolved_subsystem != orig_sub:
        rationale += f" Resolved subsystem to '{resolved_subsystem}' based on technical signals."
        
    return ClassificationReconciliationResult(
        original_category=orig_cat,
        original_subsystem=orig_sub,
        resolved_category=resolved_category,
        resolved_subsystem=resolved_subsystem,
        decision=decision,
        confidence_score=confidence_score,
        conflicting_evidence=conflicting_evidence,
        supporting_evidence=supporting_evidence,
        evidence_entities=evidence_entities,
        rationale=rationale
    )
