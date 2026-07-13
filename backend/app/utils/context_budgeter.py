import os
import re
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple

logger = logging.getLogger(__name__)

# Constants
PROMPT_TOKEN_BUDGET = 1500
MIN_OVERRIDE_MARGIN = 30

# Priority levels
PRIORITY_1_CLASSIFICATION_CORE = 1
PRIORITY_2_CRITICAL_EVIDENCE = 2
PRIORITY_3_EXPLICIT_PATHS = 3
PRIORITY_4_TOP_CANDIDATES = 4
PRIORITY_5_STRONG_EVIDENCE = 5
PRIORITY_6_ISSUE_CORE = 6
PRIORITY_7_RELEVANT_COMMENTS = 7
PRIORITY_8_REPOSITORY_CONTEXT = 8
PRIORITY_9_OPTIONAL_CONTEXT = 9

# Evidence authority weights
EVIDENCE_AUTHORITY_WEIGHTS = {
    "MAINTAINER_DIAGNOSIS": 100.0,
    "ROOT_CAUSE_STATEMENT": 90.0,
    "ERROR_SIGNATURE": 80.0,
    "EXPLICIT_PATH": 70.0,
    "REPRODUCTION_DETAIL": 60.0,
    "IMPLEMENTATION_STATEMENT": 50.0,
    "ACTUAL_BEHAVIOR": 40.0,
    "EXPECTED_BEHAVIOR": 30.0,
    "NAMED_CLASS": 20.0,
    "NAMED_FUNCTION": 15.0,
    "NAMED_MODULE": 10.0,
    "TECHNICAL_DEPENDENCY": 5.0,
    "GENERIC_DISCUSSION": 2.0,
    "CONTRIBUTOR_NOISE": 1.0,
    "BOT_NOISE": 1.0
}

COMPRESSED_GUIDANCE_PROMPT_TEMPLATE = """Analyze this GitHub issue and suggest exploration hints for a beginner contributor.

Repository Context: {repo_name} - {repo_desc}

{repo_summary}
{repository_map}
{readme}
{contributing}
Issue Title: {title}
Labels: {labels}

{body}
{comments}
{instructions}

Return ONLY valid JSON matching the exact schema below.

EXPECTED JSON SCHEMA:
{json_schema}"""


@dataclass
class BudgetedContextSection:
    name: str
    priority: int
    mandatory: bool
    content: str
    estimated_tokens: int
    included: bool = False
    truncation_reason: Optional[str] = None


@dataclass
class BudgetedPromptContext:
    resolved_classification: str
    protected_evidence: str
    explicit_paths: str
    candidate_files: str
    issue_context: str
    repository_context: str
    optional_context: str

    included_sections: List[str]
    removed_sections: List[str]

    estimated_tokens: int
    budget_limit: int

    protected_evidence_count: int
    candidate_file_count: int
    explicit_path_count: int

    budget_status: str
    selected_attempt: int
    selected_mode: str
    static_template_tokens: int
    dynamic_context_tokens: int
    
    # Additional required telemetry
    candidate_files_available_count: int
    candidate_files_included_count: int
    candidate_files_included: List[str]
    critical_evidence_included_count: int
    strong_evidence_included_count: int
    explicit_paths_included_count: int
    issue_segments_included_count: int
    comment_segments_included_count: int
    protected_core_integrity_status: str
    integrity_failures: List[str]
    emergency_core_used: bool
    additional_llm_calls_from_context_budgeting: int = 0
    context_budgeting_ms: float = 0.0
    capture_status: str = "CAPTURED"
    critical_evidence_available_count: int = 0
    strong_evidence_available_count: int = 0
    explicit_paths_available_count: int = 0
    all_attempt_prompts: Dict[int, str] = field(default_factory=dict)


def _matches_keyword(text: str, kw: str) -> bool:
    """Helper to match keywords strictly on word boundaries for pure alphabetic strings, or substring otherwise."""
    if not re.search(r'[^a-zA-Z0-9]', kw):
        return bool(re.search(r'\b' + re.escape(kw) + r'\b', text))
    else:
        return kw in text


def estimate_tokens(text: str) -> int:
    """Rough estimation: 1 token ~= 4 characters."""
    return len(str(text)) // 4


def estimate_static_template_tokens(
    repo_name: str,
    repo_desc: str,
    issue_title: str,
    issue_labels_str: str,
    instructions_text: str,
    json_schema_text: str
) -> int:
    empty_prompt = COMPRESSED_GUIDANCE_PROMPT_TEMPLATE.format(
        repo_name=repo_name,
        repo_desc=repo_desc,
        repo_summary="",
        repository_map="",
        readme="",
        contributing="",
        title=issue_title,
        labels=issue_labels_str,
        body="",
        comments="",
        instructions=instructions_text,
        json_schema=json_schema_text
    )
    return estimate_tokens(empty_prompt)


def calculate_selection_weight(item: Any, resolved_subsystem: str, candidate_paths: List[str]) -> float:
    # 1. Strength weight
    strength_map = {
        "CRITICAL": 100.0,
        "STRONG": 60.0,
        "SUPPORTING": 30.0,
        "WEAK": 10.0,
        "IGNORE": 0.0
    }
    strength_weight = strength_map.get(item.strength, 0.0)
    
    # 2. Evidence authority weight
    authority_weight = EVIDENCE_AUTHORITY_WEIGHTS.get(item.evidence_type, 0.0)
    
    # 3. Explicit path bonus
    explicit_path_bonus = 0.0
    if item.evidence_type == "EXPLICIT_PATH":
        explicit_path_bonus = 20.0
        
    # 4. Candidate overlap bonus
    candidate_overlap_bonus = 0.0
    for path in candidate_paths:
        norm_val = (item.normalized_value or "").lower()
        if norm_val and (norm_val in path.lower() or path.lower() in norm_val):
            candidate_overlap_bonus = 30.0
            break
            
    # 5. Resolved subsystem overlap bonus
    subsystem_overlap_bonus = 0.0
    if resolved_subsystem:
        text_lower = (item.text or "").lower()
        sub_lower = resolved_subsystem.lower()
        for word in sub_lower.replace("/", " ").split():
            if len(word) > 3 and word in text_lower:
                subsystem_overlap_bonus = 20.0
                break
                
    # 6. Provenance/repetition bonus
    repetition_bonus = 0.0
    if hasattr(item, "technical_entities") and item.technical_entities:
        repetition_bonus = min(15.0, len(item.technical_entities) * 2.0)
        
    return strength_weight + authority_weight + explicit_path_bonus + candidate_overlap_bonus + subsystem_overlap_bonus + repetition_bonus


def find_grounded_candidate(explicit_path: str, candidates: List[Dict[str, Any]]) -> Optional[str]:
    ep_clean = explicit_path.replace("\\", "/").lower().strip("/")
    for c in candidates:
        c_path = c["path"].replace("\\", "/").lower()
        if c_path.endswith(ep_clean) or c_path.endswith("/" + ep_clean):
            return c["path"]
        if ep_clean == c_path:
            return c["path"]
        reason = c.get("explanation", "").lower()
        if ep_clean in reason or "explicit path" in reason or "suffix match" in reason:
            if ep_clean in c_path:
                return c["path"]
    return None


def compact_ranking_reasons(explanation: str, max_reasons: int = 2) -> List[str]:
    if not explanation:
        return ["No specific reason provided."]
    parts = re.split(r'[;\.\n]+', explanation)
    cleaned_parts = []
    for p in parts:
        p_clean = p.strip()
        if p_clean and len(p_clean) > 4:
            if "matched file" in p_clean.lower() and len(p_clean) < 30:
                cleaned_parts.append((1, p_clean))
            else:
                cleaned_parts.append((0, p_clean))
                
    cleaned_parts.sort(key=lambda x: x[0])
    reasons = [x[1] for x in cleaned_parts[:max_reasons]]
    if not reasons:
        return [explanation]
    return reasons


def extract_budgeted_issue_body(body: str, key_entities: List[str], max_chars: int) -> str:
    if not body:
        return ""
    if len(body) <= max_chars:
        return body
        
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [p.strip() for p in body.split("\n") if p.strip()]
        
    scored_paragraphs = []
    for idx, p in enumerate(paragraphs):
        score = 0
        p_lower = p.lower()
        for ent in key_entities:
            if ent.lower() in p_lower:
                score += 10
        if any(x in p_lower for x in ["exception", "error", "fail", "broken", "traceback"]):
            score += 5
        if any(x in p_lower for x in ["because", "due to", "root cause", "fix", "resolve"]):
            score += 3
        score -= idx * 0.1
        scored_paragraphs.append((score, idx, p))
        
    scored_paragraphs.sort(key=lambda x: (-x[0], x[1]))
    
    selected = []
    current_len = 0
    to_include = []
    for score, idx, p in scored_paragraphs:
        if current_len + len(p) <= max_chars or not to_include:
            to_include.append((idx, p))
            current_len += len(p)
            if current_len >= max_chars:
                break
                
    to_include.sort(key=lambda x: x[0])
    result_text = "\n\n".join(x[1] for x in to_include)
    
    if len(body) > len(result_text):
        result_text += "\n[Body excerpted for priority context]"
    return result_text


def select_budgeted_comments(
    comments: List[Dict[str, Any]],
    evidence_items: List[Any],
    max_comments: int
) -> str:
    if not comments:
        return "None"
        
    scored_comments = []
    for idx, c in enumerate(comments):
        c_body = c.get("body", "") or c.get("text", "") or ""
        c_body_lower = c_body.lower()
        
        is_bot = "bot" in c.get("user", {}).get("login", "").lower() or "github-actions" in c_body_lower
        is_noise = any(pattern in c_body_lower for pattern in ["assigned to", "i'm working on", "assign me", "lgtm", "thanks", "thank you"])
        
        if is_bot or is_noise:
            score = -100.0
        else:
            score = 0.0
            
        for item in evidence_items:
            if hasattr(item, "source") and str(item.source).startswith(f"COMMENT (Index: {idx})"):
                strength_bonus = {"CRITICAL": 50.0, "STRONG": 25.0, "SUPPORTING": 10.0}.get(item.strength, 0.0)
                score += strength_bonus
            if hasattr(item, "text") and item.text and item.text.lower() in c_body_lower:
                score += 10.0
                
        score -= idx * 0.1
        scored_comments.append((score, idx, c))
        
    scored_comments.sort(key=lambda x: -x[0])
    
    selected_comments = []
    for score, idx, c in scored_comments[:max_comments]:
        if score < -50.0 and len(selected_comments) > 0:
            break
        c_body = c.get("body", "") or c.get("text", "") or ""
        author = c.get("user", {}).get("login", "unknown")
        if len(c_body) > 400:
            c_body = c_body[:400] + "\n[Comment truncated]"
        selected_comments.append(f"Comment by @{author}:\n{c_body}")
        
    if not selected_comments:
        return "None"
    return "\n\n".join(selected_comments)


def validate_protected_core_integrity(
    prompt: str,
    issue_intel: Any,
    issue_evidence: Any,
    candidate_evidence: Any,
    attempt: int
) -> Tuple[bool, List[str]]:
    failures = []
    
    resolved_category = getattr(issue_intel, "category", "")
    resolved_subsystem = getattr(issue_intel, "subsystem", "")
    
    if not resolved_category or resolved_category not in prompt:
        failures.append(f"Missing resolved category '{resolved_category}'")
    if resolved_subsystem and resolved_subsystem not in prompt:
        failures.append(f"Missing resolved subsystem '{resolved_subsystem}'")
            
    critical_items = [x for x in getattr(issue_evidence, "technical_evidence", []) if x.strength == "CRITICAL"]
    if critical_items:
        has_crit = False
        for item in critical_items:
            if (item.normalized_value and item.normalized_value in prompt) or \
               (item.text and item.text in prompt) or \
               any(e in prompt for e in item.technical_entities):
                has_crit = True
                break
        if not has_crit:
            failures.append("None of the CRITICAL evidence items are represented")
            
    explicit_paths = getattr(issue_evidence, "explicit_paths", []) or []
    if explicit_paths:
        has_ep = False
        for ep in explicit_paths:
            if ep in prompt:
                has_ep = True
                break
        if not has_ep:
            failures.append("None of the explicit paths are represented")
            
    candidates = getattr(candidate_evidence, "candidates", []) or []
    avail_count = len(candidates)
    
    inc_count = 0
    for c in candidates:
        if c["path"] in prompt:
            inc_count += 1
            
    if avail_count > 0:
        if inc_count < 1:
            failures.append("Available candidate files > 0 but none are included in the prompt")
        elif attempt == 4 and avail_count >= 2 and inc_count < 2:
            prompt_tokens = estimate_tokens(prompt)
            if prompt_tokens < 1300:
                failures.append(f"Protected Core Mode has space ({prompt_tokens} tokens) but only included {inc_count} of 2 preferred candidates")
            
    return len(failures) == 0, failures


def build_emergency_core(
    repo_name: str,
    repo_desc: str,
    issue_intel: Any,
    issue_evidence: Any,
    candidate_evidence: Any,
    instructions_text: str,
    json_schema_text: str,
    budget_limit: int = 1500
) -> Tuple[str, int]:
    resolved_category = getattr(issue_intel, "category", "other")
    resolved_subsystem = getattr(issue_intel, "subsystem", "")
    issue_title = getattr(issue_intel, "keywords", ["Issue"])[0] if getattr(issue_intel, "keywords", None) else "Issue"
    
    classification_text = (
        f"ISSUE UNDERSTANDING:\n"
        f"Category: {resolved_category}\n"
        f"Likely Subsystem: {resolved_subsystem}\n"
    )
    
    candidates = getattr(candidate_evidence, "candidates", []) or []
    top_cand_path = candidates[0]["path"] if candidates else ""
    candidate_text = ""
    if top_cand_path:
        candidate_text = f"Candidate Files:\n- File: '{top_cand_path}' (Score: {candidates[0]['score']})\n"
        
    empty_prompt = COMPRESSED_GUIDANCE_PROMPT_TEMPLATE.format(
        repo_name=repo_name,
        repo_desc=repo_desc,
        repo_summary="",
        repository_map="",
        readme="",
        contributing="",
        title=issue_title,
        labels="",
        body=classification_text,
        comments="",
        instructions=instructions_text,
        json_schema=json_schema_text
    )
    
    overhead = estimate_tokens(empty_prompt)
    remaining_tokens = budget_limit - overhead - estimate_tokens(candidate_text)
    
    critical_items = [x for x in getattr(issue_evidence, "technical_evidence", []) if x.strength == "CRITICAL"]
    cand_paths = [c["path"] for c in candidates]
    critical_items.sort(key=lambda x: -calculate_selection_weight(x, resolved_subsystem, cand_paths))
    
    evidence_section = ""
    if critical_items:
        top_crit = critical_items[0]
        type_str = top_crit.evidence_type
        norm_str = top_crit.normalized_value or ""
        ent_str = ", ".join(top_crit.technical_entities)
        txt_excerpt = top_crit.text
        if len(txt_excerpt) > 150:
            txt_excerpt = txt_excerpt[:150] + "..."
            
        compact_txt = f"[{type_str} | CRITICAL]\nValue: {norm_str}\nEntities: {ent_str}\nExcerpt: {txt_excerpt}\n"
        evidence_section = f"PROTECTED TECHNICAL EVIDENCE:\n{compact_txt}\n"
        
    explicit_path_section = ""
    grounded_paths = []
    for ep in getattr(issue_evidence, "explicit_paths", []) or []:
        matched = find_grounded_candidate(ep, candidates)
        if matched:
            grounded_paths.append((ep, matched))
            
    if grounded_paths:
        top_ep, top_gr = grounded_paths[0]
        explicit_path_section = f"EXPLICIT PATH EVIDENCE:\n- Issue Path: {top_ep} -> Grounded to: {top_gr}\n"
        
    second_candidate_text = ""
    if len(candidates) > 1 and top_cand_path:
        second_cand = candidates[1]
        second_candidate_text = f"- File: '{second_cand['path']}' (Score: {second_cand['score']})\n"
        
    body_parts = [classification_text]
    map_parts = [candidate_text]
    
    current_added_tokens = 0
    
    if evidence_section:
        ev_tokens = estimate_tokens(evidence_section)
        if current_added_tokens + ev_tokens < remaining_tokens:
            body_parts.append(evidence_section)
            current_added_tokens += ev_tokens
            
    if explicit_path_section:
        ep_tokens = estimate_tokens(explicit_path_section)
        if current_added_tokens + ep_tokens < remaining_tokens:
            body_parts.append(explicit_path_section)
            current_added_tokens += ep_tokens
            
    if second_candidate_text:
        sec_tokens = estimate_tokens(second_candidate_text)
        if current_added_tokens + sec_tokens < remaining_tokens:
            map_parts.append(second_candidate_text)
            current_added_tokens += sec_tokens
            
    final_body = "\n".join(body_parts)
    final_map = "\n".join(map_parts)
    
    prompt = COMPRESSED_GUIDANCE_PROMPT_TEMPLATE.format(
        repo_name=repo_name,
        repo_desc=repo_desc,
        repo_summary="",
        repository_map=final_map,
        readme="",
        contributing="",
        title=issue_title,
        labels="",
        body=final_body,
        comments="",
        instructions=instructions_text,
        json_schema=json_schema_text
    )
    
    return prompt, estimate_tokens(prompt)


def compress_markdown(text: str, keep_keywords: list, remove_keywords: list) -> str:
    """Helper from existing code to compress markdown semantically."""
    if not text:
        return ""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    
    def code_replacer(match):
        code_content = match.group(2)
        if len(code_content.splitlines()) > 5 or len(code_content) > 200:
            return "```\n[Code block omitted for brevity]\n```"
        return match.group(0)
    
    text = re.sub(r"```(python|javascript|typescript|bash|sh|json|yaml|yml|html|css)?\n(.*?)\n```", code_replacer, text, flags=re.DOTALL | re.IGNORECASE)
    
    lines = text.splitlines()
    sections = []
    current_header = "Intro"
    current_content = []
    for line in lines:
        if line.strip().startswith(("#", "##", "###", "####")):
            if current_content:
                sections.append((current_header, "\n".join(current_content)))
            current_header = line.strip()
            current_content = []
        else:
            current_content.append(line)
    if current_content:
        sections.append((current_header, "\n".join(current_content)))
        
    filtered = []
    for header, content in sections:
        h_lower = header.lower()
        if any(kw in h_lower for kw in remove_keywords):
            continue
        if keep_keywords:
            if "intro" in h_lower or header == "Intro" or any(kw in h_lower for kw in keep_keywords):
                filtered.append(f"{header}\n{content}")
        else:
            filtered.append(f"{header}\n{content}")
            
    return "\n\n".join(filtered)


def budget_and_assemble_prompt(
    repo_name: str,
    repo_desc: str,
    repo_context: Any,
    candidate_evidence: Any,
    issue_intel: Any,
    issue_evidence: Any,
    readme_raw: str,
    contributing_raw: str,
    issue_body: str,
    issue_labels_str: str,
    comments: List[Dict[str, Any]],
    instructions_text: str,
    json_schema_text: str,
    budget_limit: int = 1500
) -> Tuple[str, BudgetedPromptContext]:
    start_time = os.times().elapsed if hasattr(os, "times") else 0.0
    
    issue_title = getattr(issue_intel, "keywords", ["Issue"])[0] if getattr(issue_intel, "keywords", None) else "Issue"
    
    # Calculate static template overhead
    static_template_tokens = estimate_static_template_tokens(
        repo_name=repo_name,
        repo_desc=repo_desc,
        issue_title=issue_title,
        issue_labels_str=issue_labels_str,
        instructions_text=instructions_text,
        json_schema_text=json_schema_text
    )
    
    dynamic_context_budget = budget_limit - static_template_tokens
    
    # Candidates preparation
    candidates = getattr(candidate_evidence, "candidates", []) or []
    cand_paths = [c["path"] for c in candidates]
    candidate_files_available_count = len(candidates)
    
    # Evidence preparation and ranking
    all_evidence = getattr(issue_evidence, "technical_evidence", []) or []
    resolved_subsystem = getattr(issue_intel, "subsystem", "")
    all_evidence_sorted = sorted(all_evidence, key=lambda x: -calculate_selection_weight(x, resolved_subsystem, cand_paths))
    
    critical_evidence = [x for x in all_evidence_sorted if x.strength == "CRITICAL"]
    strong_evidence = [x for x in all_evidence_sorted if x.strength == "STRONG"]
    
    # Grounded path tracking
    explicit_paths = getattr(issue_evidence, "explicit_paths", []) or []
    grounded_relations = []
    ungrounded_paths = []
    for ep in explicit_paths:
        match = find_grounded_candidate(ep, candidates)
        if match:
            grounded_relations.append((ep, match))
        else:
            ungrounded_paths.append(ep)
            
    # Keywords list for issue body excerpt matching
    key_entities = list(getattr(issue_intel, "keywords", []))
    for item in all_evidence:
        key_entities.extend(item.technical_entities)
    key_entities = list(set(key_entities))
    
    # Attempt loop parameters mapping
    attempt_modes = {
        1: {
            "name": "FULL PRIORITIZED CONTEXT",
            "max_candidates": 5,
            "max_reasons": 3,
            "max_body_chars": 1200,
            "max_comments": 3,
            "include_readme": True,
            "compress_readme": False,
            "include_contributing": True,
            "compress_contributing": False,
            "include_repo_summary": True,
            "compact_repo_summary": False,
            "include_optional": True,
            "max_strong_evidence": 999
        },
        2: {
            "name": "COMPACT PRIORITIZED CONTEXT",
            "max_candidates": 3,
            "max_reasons": 2,
            "max_body_chars": 600,
            "max_comments": 1,
            "include_readme": True,
            "compress_readme": False,
            "include_contributing": True,
            "compress_contributing": False,
            "include_repo_summary": True,
            "compact_repo_summary": True,
            "include_optional": False,
            "max_strong_evidence": 5
        },
        3: {
            "name": "EVIDENCE-FOCUSED CONTEXT",
            "max_candidates": 3,
            "max_reasons": 1,
            "max_body_chars": 300,
            "max_comments": 0,
            "include_readme": True,
            "compress_readme": True,
            "include_contributing": True,
            "compress_contributing": True,
            "include_repo_summary": False,
            "compact_repo_summary": False,
            "include_optional": False,
            "max_strong_evidence": 3
        },
        4: {
            "name": "PROTECTED CORE MODE",
            "max_candidates": 2,
            "max_reasons": 1,
            "max_body_chars": 0,
            "max_comments": 0,
            "include_readme": False,
            "compress_readme": False,
            "include_contributing": False,
            "compress_contributing": False,
            "include_repo_summary": False,
            "compact_repo_summary": False,
            "include_optional": False,
            "max_strong_evidence": 3
        }
    }
    
    selected_prompt = ""
    selected_captured = None
    built_prompts = {}
    
    for attempt in [1, 2, 3, 4]:
        mode_conf = attempt_modes[attempt]
        
        # Build Candidate Files block
        sel_cands = candidates[:mode_conf["max_candidates"]]
        candidate_lines = []
        for c in sel_cands:
            reasons = compact_ranking_reasons(c.get("explanation", ""), mode_conf["max_reasons"])
            reason_text = " ".join(f"- {r}" for r in reasons)
            candidate_lines.append(f"- File: '{c['path']}' (Score: {c['score']}) Reason: {reason_text}")
            
        candidate_files_block = ""
        if candidate_lines:
            candidate_dirs = sorted(list(set(os.path.dirname(f) for f in [c["path"] for c in sel_cands] if os.path.dirname(f))))
            candidate_files_block = (
                f"TOP CANDIDATE FILES:\n"
                f"Candidate Directories:\n{json.dumps(candidate_dirs, ensure_ascii=False)}\n\n"
                f"Candidate Files & Evidence:\n" + "\n".join(candidate_lines) + "\n"
            )
            
        # Build Protected Evidence block
        sel_crit = critical_evidence
        sel_strong = strong_evidence[:mode_conf["max_strong_evidence"]]
        
        evidence_lines = []
        for item in sel_crit:
            evidence_lines.append(f"[{item.evidence_type} | CRITICAL] {item.text} (Entities: {', '.join(item.technical_entities)})")
        for item in sel_strong:
            evidence_lines.append(f"[{item.evidence_type} | STRONG] {item.text} (Entities: {', '.join(item.technical_entities)})")
            
        protected_evidence_block = ""
        if evidence_lines:
            protected_evidence_block = "PROTECTED TECHNICAL EVIDENCE:\n" + "\n".join(evidence_lines) + "\n"
            
        # Explicit paths block
        explicit_path_lines = []
        for raw_path, grounded in grounded_relations:
            explicit_path_lines.append(f"- Issue Path: {raw_path} -> Grounded to: {grounded}")
        for raw_path in ungrounded_paths:
            explicit_path_lines.append(f"- Ungrounded Issue Path Reference: {raw_path}")
            
        explicit_paths_block = ""
        if explicit_path_lines:
            explicit_paths_block = "EXPLICIT PATH EVIDENCE:\n" + "\n".join(explicit_path_lines) + "\n"
            
        # Build Repository Summary
        summary_lines = []
        if mode_conf["include_repo_summary"]:
            if mode_conf["compact_repo_summary"]:
                summary_lines.append(f"Repository Purpose:\n{getattr(repo_context, 'relevant_summary', '') or getattr(repo_context, 'repository_purpose', '')}")
                summary_lines.append(f"Relevant Technologies: {', '.join(getattr(repo_context, 'relevant_technologies', []))}")
            else:
                summary_lines.append(f"Repository Purpose:\n{getattr(repo_context, 'relevant_summary', '') or getattr(repo_context, 'repository_purpose', '')}")
                summary_lines.append(f"Relevant Technologies: {', '.join(getattr(repo_context, 'relevant_technologies', []))}")
                summary_lines.append(f"Architectural Concepts: {getattr(repo_context, 'architectural_notes', '')}")
                if getattr(repo_context, "relevant_structures", ""):
                    summary_lines.append(f"Internal Directory Roles & Structure:\n{repo_context.relevant_structures}")
                    
        repo_summary_block = ""
        if summary_lines:
            repo_summary_block = "REPOSITORY CONTEXT:\n" + "\n\n".join(summary_lines) + "\n"
        
        # Build README
        readme_block = ""
        if mode_conf["include_readme"]:
            if mode_conf["compress_readme"]:
                excerpt = compress_markdown(
                    readme_raw,
                    keep_keywords=["setup", "install", "getting started", "quick start", "contrib", "build", "run"],
                    remove_keywords=["example", "demo", "tutorial", "license", "changelog", "history", "roadmap", "status", "badge", "sponsors", "sponsorship"]
                )
            else:
                excerpt = readme_raw[:2000]
            readme_block = f"Relevant README Context:\n{excerpt}\n" if excerpt else ""
            
        # Build CONTRIBUTING
        contributing_block = ""
        if mode_conf["include_contributing"]:
            if mode_conf["compress_contributing"]:
                excerpt = compress_markdown(
                    contributing_raw,
                    keep_keywords=["workflow", "pull request", "pr", "test", "lint", "style", "standard", "guide"],
                    remove_keywords=["history", "notes", "example", "tutorial", "sponsorship", "thanks"]
                )
            else:
                excerpt = contributing_raw[:1000]
            contributing_block = f"Relevant CONTRIBUTING Context:\n{excerpt}\n" if excerpt else ""
            
        # Build Optional Context
        optional_block = ""
        if mode_conf["include_optional"]:
            opt_lines = []
            if getattr(repo_context, "beginner_summary", ""):
                opt_lines.append(f"Beginner Summary: {repo_context.beginner_summary}")
            if getattr(repo_context, "relevant_concepts", []):
                opt_lines.append(f"Concepts: {', '.join(repo_context.relevant_concepts)}")
            optional_block = "\n".join(opt_lines) if opt_lines else ""
            
        # Build Issue Body containing standard metadata and priority evidence sections
        body_text = (
            f"ISSUE CLASSIFICATION:\n"
            f"Resolved Category: {getattr(issue_intel, 'category', 'other')}\n"
            f"Resolved Subsystem: {getattr(issue_intel, 'subsystem', '')}\n"
            f"Intent: {getattr(issue_intel, 'intent', 'bug')}\n"
            f"Difficulty: {getattr(issue_intel, 'difficulty', 'Intermediate')}\n\n"
        )
        
        if protected_evidence_block:
            body_text += f"{protected_evidence_block}\n"
            
        if explicit_paths_block:
            body_text += f"{explicit_paths_block}\n"
            
        body_text += "ISSUE CONTEXT:\n"
        body_text += f"Detected Keywords: {', '.join(getattr(issue_intel, 'keywords', []))}\n"
        hints_text = "\n".join(f"- {h}" for h in getattr(issue_intel, "implementation_hints", [])) if getattr(issue_intel, "implementation_hints", None) else "None"
        body_text += f"Implementation Hints:\n{hints_text}\n\n"
        
        if mode_conf["max_body_chars"] > 0:
            excerpt_body = extract_budgeted_issue_body(issue_body, key_entities, mode_conf["max_body_chars"])
            body_text += f"ISSUE DESCRIPTION:\n{excerpt_body}\n"
        else:
            body_text += "ISSUE DESCRIPTION:\n[Excerpt omitted for Protected Core]\n"
            
        # Build Comments
        comments_block = ""
        selected_comments_len = 0
        if mode_conf["max_comments"] > 0:
            comments_block = select_budgeted_comments(comments, all_evidence, mode_conf["max_comments"])
            if comments_block and comments_block != "None":
                selected_comments_len = len(comments_block.split("\n\n"))
                comments_block = f"RELEVANT COMMENTS:\n{comments_block}\n"
                
        # Final formatting
        prompt = COMPRESSED_GUIDANCE_PROMPT_TEMPLATE.format(
            repo_name=repo_name,
            repo_desc=repo_desc,
            repo_summary=repo_summary_block,
            repository_map=candidate_files_block,
            readme=readme_block,
            contributing=contributing_block,
            title=issue_title,
            labels=issue_labels_str,
            body=body_text,
            comments=comments_block,
            instructions=instructions_text,
            json_schema=json_schema_text
        )
        built_prompts[attempt] = prompt
        
        prompt_tokens = estimate_tokens(prompt)
        
        # Calculate metric lists
        inc_cats = []
        rem_cats = []
        if repo_summary_block: inc_cats.append("repo_summary")
        else: rem_cats.append("repo_summary")
        if candidate_files_block: inc_cats.append("candidate_files")
        else: rem_cats.append("candidate_files")
        if readme_block: inc_cats.append("readme")
        else: rem_cats.append("readme")
        if contributing_block: inc_cats.append("contributing")
        else: rem_cats.append("contributing")
        if comments_block: inc_cats.append("comments")
        else: rem_cats.append("comments")
        if optional_block: inc_cats.append("optional_context")
        else: rem_cats.append("optional_context")
        
        # Validate integrity
        is_valid, integrity_failures = validate_protected_core_integrity(
            prompt=prompt,
            issue_intel=issue_intel,
            issue_evidence=issue_evidence,
            candidate_evidence=candidate_evidence,
            attempt=attempt
        )
        
        if is_valid and prompt_tokens <= budget_limit:
            selected_prompt = prompt
            end_time = os.times().elapsed if hasattr(os, "times") else 0.0
            
            selected_captured = BudgetedPromptContext(
                resolved_classification=f"{getattr(issue_intel, 'category', 'other')} / {getattr(issue_intel, 'subsystem', '')}",
                protected_evidence=protected_evidence_block,
                explicit_paths=explicit_paths_block,
                candidate_files=candidate_files_block,
                issue_context=body_text,
                repository_context=repo_summary_block,
                optional_context=optional_block,
                included_sections=inc_cats,
                removed_sections=rem_cats,
                estimated_tokens=prompt_tokens,
                budget_limit=budget_limit,
                protected_evidence_count=len(critical_evidence) + len(strong_evidence),
                candidate_file_count=len(sel_cands),
                explicit_path_count=len(explicit_paths),
                budget_status="SUCCESS",
                selected_attempt=attempt,
                selected_mode=mode_conf["name"],
                static_template_tokens=static_template_tokens,
                dynamic_context_tokens=prompt_tokens - static_template_tokens,
                candidate_files_available_count=candidate_files_available_count,
                candidate_files_included_count=len([c for c in sel_cands if c["path"] in prompt]),
                candidate_files_included=[c["path"] for c in sel_cands if c["path"] in prompt],
                critical_evidence_included_count=len([x for x in critical_evidence if (x.normalized_value and x.normalized_value in prompt) or (x.text and x.text in prompt) or any(e in prompt for e in x.technical_entities)]),
                strong_evidence_included_count=len([x for x in strong_evidence if (x.normalized_value and x.normalized_value in prompt) or (x.text and x.text in prompt) or any(e in prompt for e in x.technical_entities)]),
                explicit_paths_included_count=len([ep for ep in explicit_paths if ep in prompt]),
                issue_segments_included_count=1 if mode_conf["max_body_chars"] > 0 else 0,
                comment_segments_included_count=selected_comments_len,
                protected_core_integrity_status="PASSED",
                integrity_failures=[],
                emergency_core_used=False,
                context_budgeting_ms=(end_time - start_time) * 1000.0,
                critical_evidence_available_count=len(critical_evidence),
                strong_evidence_available_count=len(strong_evidence),
                explicit_paths_available_count=len(explicit_paths),
                all_attempt_prompts=built_prompts
            )
            return selected_prompt, selected_captured
            
        else:
            logger.info("Attempt %d (%s) failed validation or exceeded budget (tokens: %d, valid: %s, failures: %s)", attempt, mode_conf["name"], prompt_tokens, is_valid, integrity_failures)
            
    # If we fall through all four attempts, build emergency core
    logger.warning("All budgeting attempts failed. Building Emergency Core.")
    emerg_prompt, emerg_tokens = build_emergency_core(
        repo_name=repo_name,
        repo_desc=repo_desc,
        issue_intel=issue_intel,
        issue_evidence=issue_evidence,
        candidate_evidence=candidate_evidence,
        instructions_text=instructions_text,
        json_schema_text=json_schema_text,
        budget_limit=budget_limit
    )
    
    end_time = os.times().elapsed if hasattr(os, "times") else 0.0
    
    # Integrity check for emergency core
    emerg_valid, emerg_failures = validate_protected_core_integrity(
        prompt=emerg_prompt,
        issue_intel=issue_intel,
        issue_evidence=issue_evidence,
        candidate_evidence=candidate_evidence,
        attempt=5
    )
    
    built_prompts[5] = emerg_prompt
    
    # Collect telemetry for emergency core
    selected_captured = BudgetedPromptContext(
        resolved_classification=f"{getattr(issue_intel, 'category', 'other')} / {getattr(issue_intel, 'subsystem', '')}",
        protected_evidence="[Emergency Protected Evidence]",
        explicit_paths="[Emergency Explicit Paths]",
        candidate_files="[Emergency Candidate Files]",
        issue_context="[Emergency Issue Context]",
        repository_context="",
        optional_context="",
        included_sections=["classification", "critical_evidence", "candidate_files"],
        removed_sections=["repo_summary", "readme", "contributing", "comments", "optional_context"],
        estimated_tokens=emerg_tokens,
        budget_limit=budget_limit,
        protected_evidence_count=len(critical_evidence),
        candidate_file_count=1 if candidates else 0,
        explicit_path_count=len(explicit_paths),
        budget_status="EMERGENCY" if emerg_tokens <= budget_limit else "BUDGETING_FAILED",
        selected_attempt=5,
        selected_mode="EMERGENCY CORE",
        static_template_tokens=static_template_tokens,
        dynamic_context_tokens=emerg_tokens - static_template_tokens,
        candidate_files_available_count=candidate_files_available_count,
        candidate_files_included_count=1 if (candidates and candidates[0]["path"] in emerg_prompt) else 0,
        candidate_files_included=[candidates[0]["path"]] if (candidates and candidates[0]["path"] in emerg_prompt) else [],
        critical_evidence_included_count=1 if (critical_evidence and (critical_evidence[0].text in emerg_prompt or any(e in emerg_prompt for e in critical_evidence[0].technical_entities))) else 0,
        strong_evidence_included_count=0,
        explicit_paths_included_count=1 if grounded_relations else 0,
        issue_segments_included_count=0,
        comment_segments_included_count=0,
        protected_core_integrity_status="PASSED" if emerg_valid else "FAILED",
        integrity_failures=emerg_failures,
        emergency_core_used=True,
        context_budgeting_ms=(end_time - start_time) * 1000.0,
        critical_evidence_available_count=len(critical_evidence),
        strong_evidence_available_count=len(strong_evidence),
        explicit_paths_available_count=len(explicit_paths),
        all_attempt_prompts=built_prompts
    )
    
    if emerg_tokens <= budget_limit:
        return emerg_prompt, selected_captured
    else:
        # Emergency core also exceeded 1500 tokens! Raise exception to trigger pipeline fallback
        raise ValueError(f"Emergency prompt size {emerg_tokens} still exceeds budget limit {budget_limit}.")
