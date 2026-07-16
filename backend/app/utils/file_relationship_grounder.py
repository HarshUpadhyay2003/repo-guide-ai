import os
import re
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set

from app.utils.technical_entity_utils import (
    normalize_raw_path,
    tokenize_string,
    GENERIC_TECHNICAL_TOKENS
)

@dataclass
class ExplicitPathResolution:
    evidence_ref: str
    original_value: str
    normalized_value: str
    resolution_status: str              # GROUNDED, AMBIGUOUS, UNGROUNDED
    match_type: Optional[str]           # EXACT, SUFFIX, BASENAME, None
    grounded_paths: List[str]           # List of matching canonical files in repo
    ambiguity_count: int
    rationale: str

@dataclass
class CandidateFileRelationship:
    path: str
    candidate_rank: int
    candidate_score: float
    relationship_score: float
    relationship_strength: str          # DIRECT, STRONG, MODERATE, WEAK
    investigation_priority: str         # PRIMARY, SECONDARY, SUPPORTING, LOW_CONFIDENCE
    relationship_types: List[str]
    matched_evidence_refs: List[str]
    matched_evidence_types: List[str]
    matched_evidence_strengths: List[str]
    matched_entities: List[str]
    matched_explicit_paths: List[str]
    subsystem_alignment: bool
    category_alignment: bool
    repository_map_alignment: bool
    direct_evidence_score: float
    entity_evidence_score: float
    structural_alignment_score: float
    ranking_support_score: float
    candidate_ranking_reasons: List[str] = field(default_factory=list)
    rationale: str = ""

@dataclass
class CandidateRelationshipEdge:
    source_path: str
    target_path: str
    relationship_types: List[str]
    shared_entities: List[str]
    shared_evidence_count: int
    shared_parent_path: Optional[str]
    relationship_score: float
    rationale: str


@dataclass
class FileRelationshipGroundingResult:
    status: str                         # SUCCESS, FALLBACK
    explicit_path_resolutions: List[ExplicitPathResolution]
    candidate_relationships: List[CandidateFileRelationship]
    file_relationship_edges: List[CandidateRelationshipEdge]
    investigation_order: List[str]
    total_candidates: int
    direct_relationship_count: int
    strong_relationship_count: int
    moderate_relationship_count: int
    weak_relationship_count: int
    primary_count: int
    secondary_count: int
    supporting_count: int
    low_confidence_count: int
    explicit_paths_available: int
    explicit_paths_grounded: int
    explicit_paths_ambiguous: int
    explicit_paths_ungrounded: int
    grounding_latency_ms: float
    additional_llm_calls: int = 0

# Configuration Constants
DIRECT_SIGNAL_WEIGHTS = {
    "EXPLICIT_PATH_MATCH": 60.0,
    "PATH_SUFFIX_MATCH": 45.0,
    "FILE_BASENAME_MATCH": 20.0,
}

ENTITY_SIGNAL_WEIGHTS = {
    "TECHNICAL_ENTITY_PATH_MATCH": 22.0,
    "MODULE_PATH_MATCH": 18.0,
}

STRUCTURAL_SIGNAL_WEIGHTS = {
    "SUBSYSTEM_ALIGNMENT": 10.0,
    "CATEGORY_ALIGNMENT": 6.0,
    "REPOSITORY_MAP_ALIGNMENT": 8.0,
}

SUPPORT_SIGNAL_WEIGHTS = {
    "RANKING_SUPPORT": 5.0,
}

EVIDENCE_AUTHORITY = {
    "CRITICAL": 1.00,
    "STRONG": 0.80,
    "SUPPORTING": 0.50,
    "WEAK": 0.20,
    "IGNORE": 0.00,
}

CONTRIBUTION_CAPS = {
    "DIRECT_PATH_CAP": 60.0,
    "ENTITY_CAP": 35.0,
    "STRUCTURAL_CAP": 24.0,
    "SUPPORT_CAP": 5.0,
}

RELATIONSHIP_STRENGTH_THRESHOLDS = {
    "DIRECT": 50.0,
    "STRONG": 35.0,
    "MODERATE": 20.0,
}

INVESTIGATION_PRIORITY_THRESHOLDS = {
    "PRIMARY": 55.0,
    "SECONDARY": 40.0,
    "SUPPORTING": 25.0,
}

EDGE_WEIGHTS = {
    "SHARED_CRITICAL_EVIDENCE": 30.0,
    "SHARED_STRONG_EVIDENCE": 20.0,
    "SHARED_SUPPORTING_EVIDENCE": 10.0,
    "SHARED_ENTITY": 12.0,
    "MEANINGFUL_SHARED_PARENT": 8.0,
    "REPOSITORY_MAP_AREA": 6.0,
}

AMBIGUITY_PENALTY = 15.0
GENERIC_FILENAME_PENALTY = 20.0

GENERIC_FILENAMES = {
    "config.py", "utils.py", "base.py", "index.ts", "main.py", 
    "__init__.py", "helpers.py", "setup.py", "constants.py"
}

def extract_path_tokens(text: str) -> List[str]:
    if not text:
        return []
    
    # If the text is a single word (no whitespace), just return the cleaned word
    words = text.split()
    if len(words) == 1:
        cleaned = text.strip('`\'"()[]{}*#,;:?')
        if cleaned:
            return [cleaned]
            
    # Otherwise, extract quoted substrings (enclosed in backticks, single quotes, double quotes)
    quoted_tokens = re.findall(r'[`\'"]([^\s`\'"]+)[`\'"]', text)
    
    extracted = list(quoted_tokens)
    for word in words:
        # Strip common trailing/leading punctuation
        cleaned = word.strip('`\'"()[]{}*#,;:?')
        if cleaned.endswith('.') and not cleaned.endswith('..'):
            cleaned = cleaned.rstrip('.')
        if not cleaned:
            continue
        if cleaned.lower().startswith(('http://', 'https://')):
            continue
            
        has_slash = '/' in cleaned or '\\' in cleaned
        has_ext = False
        if '.' in cleaned and not cleaned.endswith('.'):
            ext = cleaned.split('.')[-1]
            if len(ext) >= 2 and len(ext) <= 6 and ext.isalnum():
                if cleaned.lower() not in ["e.g", "i.e", "vs", "etc"] and not re.match(r'^v?[0-9.]+$', cleaned):
                    has_ext = True
                    
        if has_slash or has_ext:
            extracted.append(cleaned)
            
    # Normalize and deduplicate while preserving order
    seen = set()
    result = []
    for token in extracted:
        norm = normalize_raw_path(token)
        if norm and norm not in seen:
            seen.add(norm)
            result.append(token)
    return result

def get_suffix_match_length(path_parts: List[str], repo_parts: List[str]) -> int:
    match_len = 0
    for p_part, r_part in zip(reversed(path_parts), reversed(repo_parts)):
        if p_part.lower().casefold() == r_part.lower().casefold():
            match_len += 1
        else:
            break
    return match_len

def classify_entity_specificity(entity: str, repo_token_freq: Dict[str, int], total_files: int) -> str:
    entity_clean = entity.strip()
    if not entity_clean:
        return "LOW"
        
    qualified = [q for q in entity_clean.split('.') if q]
    lexical_tokens = tokenize_string(entity_clean)
    if not lexical_tokens:
        return "LOW"
        
    # Check for generic tokens
    non_generic_tokens = [t for t in lexical_tokens if t not in GENERIC_TECHNICAL_TOKENS]
    if not non_generic_tokens:
        return "LOW"
        
    # Relative frequency in repo
    high_freq_tokens = []
    if total_files >= 5:
        for t in non_generic_tokens:
            freq = repo_token_freq.get(t, 0)
            rel_freq = freq / total_files
            if (rel_freq >= 0.3 and freq >= 3) or freq > 15:
                high_freq_tokens.append(t)
                
    specific_tokens = [t for t in non_generic_tokens if t not in high_freq_tokens]
    if not specific_tokens:
        # If all non-generic tokens are actually very high frequency, it's LOW
        return "LOW"
        
    is_compound = len(lexical_tokens) >= 2 or len(qualified) >= 2
    if is_compound:
        return "HIGH"
    else:
        return "MEDIUM"

def check_entity_path_alignment(
    entity: str,
    path: str,
    spec: str,
    repo_token_freq: Dict[str, int],
    total_files: int,
    subsystem_alignment: bool,
    category_alignment: bool,
    repository_map_alignment: bool,
    is_grounded: bool
) -> Tuple[bool, bool]: # (is_matched, is_low)
    if spec == "LOW":
        # Check if any lexical token matches the path (excluding extension)
        lex_toks = tokenize_string(entity)
        path_parts = path.lower().casefold().split("/")
        path_body = "/".join(path_parts[:-1]) + "/" + path_parts[-1].split(".")[0]
        if any(t in path_body for t in lex_toks):
            return False, True
        return False, False
        
    lex_toks = tokenize_string(entity)
    if not lex_toks:
        return False, False
        
    path_parts = path.lower().casefold().split("/")
    path_body = "/".join(path_parts[:-1]) + "/" + path_parts[-1].split(".")[0]
    
    # Check match of individual tokens
    matched_toks = [t for t in lex_toks if t in path_body]
    if not matched_toks:
        return False, False
        
    # Get specific tokens
    non_generic = [t for t in lex_toks if t not in GENERIC_TECHNICAL_TOKENS]
    high_freq = []
    if total_files >= 5:
        for t in non_generic:
            freq = repo_token_freq.get(t, 0)
            rel_freq = freq / total_files
            if (rel_freq >= 0.3 and freq >= 3) or freq > 15:
                high_freq.append(t)
    specific = [t for t in non_generic if t not in high_freq]
    
    # If the entity is classified as HIGH/MEDIUM, but has no specific tokens at all,
    # it shouldn't produce a match (treated as low specificity)
    if not specific:
        return False, True
        
    if spec == "HIGH":
        # Must contain at least one specific token in the matched tokens
        if any(t in specific for t in matched_toks):
            return True, False
        return False, False
        
    elif spec == "MEDIUM":
        # Must contain at least one specific token in the matched tokens
        if not any(t in specific for t in matched_toks):
            return False, False
            
        # Corroboration signals:
        # 1. At least 2 matched tokens (compound match)
        if len(matched_toks) >= 2:
            return True, False
        # 2. Structural/context corroborations
        if subsystem_alignment or category_alignment or repository_map_alignment or is_grounded:
            return True, False
            
        return False, False
        
    return False, False


def ground_file_relationships(
    all_files: List[str],
    repository_map: Dict[str, Any],
    candidate_evidence: Any,
    issue_intelligence: Any,
    issue_evidence: Any,
) -> FileRelationshipGroundingResult:
    start_time = time.perf_counter()
    
    resolved_subsystem = (getattr(issue_intelligence, "subsystem", "") or "").lower().casefold()
    resolved_category = (getattr(issue_intelligence, "category", "") or "").lower().casefold()
    
    # Build token frequency map of the repository
    repo_token_freq = {}
    for f in all_files:
        file_tokens = set(tokenize_string(f))
        for t in file_tokens:
            repo_token_freq[t] = repo_token_freq.get(t, 0) + 1
            
    # 1. Prepare Path Maps
    # canonical path -> lowercased comparison path
    comparison_paths: Dict[str, str] = {}
    for f in all_files:
        comparison_paths[f] = f.lower().casefold()
        
    # 2. Sequential Evidence Map
    evidence_map: Dict[str, Any] = {}
    evidence_items = getattr(issue_evidence, "technical_evidence", []) or []
    for idx, item in enumerate(evidence_items):
        ref = f"ev_{idx:03d}"
        evidence_map[ref] = item

    # 3. Explicit Path Resolution
    explicit_path_resolutions: List[ExplicitPathResolution] = []
    
    # Track grounding per candidate path
    path_grounding_refs: Dict[str, List[str]] = {} # canonical_path -> list of evidence_refs
    path_grounding_types: Dict[str, List[str]] = {}
    path_grounding_raws: Dict[str, List[str]] = {}
    
    # We resolve each explicit path from sequential evidence items of type EXPLICIT_PATH
    for ref, item in evidence_map.items():
        if item.evidence_type != "EXPLICIT_PATH":
            continue
            
        original_value = item.text
        path_tokens = extract_path_tokens(original_value)
        if not path_tokens:
            # Add an ungrounded resolution so telemetry is complete
            explicit_path_resolutions.append(ExplicitPathResolution(
                evidence_ref=ref,
                original_value=original_value,
                normalized_value=original_value,
                resolution_status="UNGROUNDED",
                match_type=None,
                grounded_paths=[],
                ambiguity_count=0,
                rationale="No valid path tokens could be extracted from evidence text."
            ))
            continue
            
        for token in path_tokens:
            norm_val = normalize_raw_path(token)
            if not norm_val:
                continue
                
            norm_val_lower = norm_val.lower().casefold()
            basename = norm_val.split("/")[-1]
            basename_lower = basename.lower().casefold()
            
            grounded_canonicals = []
            resolution_status = "UNGROUNDED"
            match_type = None
            rationale = ""
            
            # Phase A: Exact Match
            exact_matches = [f for f, cp in comparison_paths.items() if cp == norm_val_lower]
            if exact_matches:
                grounded_canonicals = exact_matches
                match_type = "EXACT"
            else:
                # Phase B: Suffix Match (Component-based longest unique suffix)
                norm_parts = norm_val.split("/")
                suffix_matches = []
                max_match_len = 0
                for f in all_files:
                    f_parts = f.split("/")
                    m_len = get_suffix_match_length(norm_parts, f_parts)
                    if m_len >= 2:
                        if m_len > max_match_len:
                            max_match_len = m_len
                            suffix_matches = [f]
                        elif m_len == max_match_len:
                            suffix_matches.append(f)
                            
                if suffix_matches and max_match_len >= 2:
                    if len(suffix_matches) == 1:
                        grounded_canonicals = suffix_matches
                        match_type = "SUFFIX"
                    else:
                        grounded_canonicals = suffix_matches
                        match_type = "SUFFIX" # Ambiguous
                        
                # Phase C: Basename Match
                if not grounded_canonicals and "." in basename:
                    base_matches = [f for f in all_files if f.split("/")[-1].lower().casefold() == basename_lower]
                    if base_matches:
                        corroborated_matches = []
                        high_evidence_entities = []
                        for ref_key, ev_item in evidence_map.items():
                            if ev_item.strength in ["CRITICAL", "STRONG", "SUPPORTING"]:
                                high_evidence_entities.extend(ev_item.technical_entities)
                        high_evidence_entities = list(set(high_evidence_entities))
                        
                        for match in base_matches:
                            match_lower = match.lower().casefold()
                            is_corroborated = False
                            
                            if resolved_subsystem and resolved_subsystem in match_lower:
                                is_corroborated = True
                            if resolved_category and resolved_category in match_lower:
                                is_corroborated = True
                            if resolved_category and resolved_category in repository_map:
                                cat_dirs = repository_map.get(resolved_category, [])
                                if any(match_lower.startswith(d.lower().casefold()) for d in cat_dirs):
                                    is_corroborated = True
                            for entity in high_evidence_entities:
                                spec = classify_entity_specificity(entity, repo_token_freq, len(all_files))
                                is_matched, _ = check_entity_path_alignment(
                                    entity, match, spec, repo_token_freq, len(all_files),
                                    resolved_subsystem in match_lower,
                                    resolved_category in match_lower,
                                    False,
                                    False
                                )
                                if is_matched:
                                    is_corroborated = True
                                    
                            if is_corroborated:
                                corroborated_matches.append(match)
                                
                        if len(corroborated_matches) == 1:
                            grounded_canonicals = corroborated_matches
                            match_type = "BASENAME"
                        elif len(base_matches) == 1:
                            grounded_canonicals = base_matches
                            match_type = "BASENAME"
                        else:
                            grounded_canonicals = base_matches
                            match_type = "BASENAME"
                            
            # Determine status and ambiguity
            if len(grounded_canonicals) == 1:
                resolution_status = "GROUNDED"
                rationale = f"Successfully resolved explicit path reference to unique file '{grounded_canonicals[0]}' via {match_type} match."
                canon = grounded_canonicals[0]
                path_grounding_refs.setdefault(canon, []).append(ref)
                path_grounding_types.setdefault(canon, []).append("PATH_SUFFIX_MATCH" if match_type == "SUFFIX" else (match_type + "_MATCH"))
                path_grounding_raws.setdefault(canon, []).append(original_value)
            elif len(grounded_canonicals) > 1:
                resolution_status = "AMBIGUOUS"
                rationale = f"Ambiguous reference: matched {len(grounded_canonicals)} files in repository."
            else:
                resolution_status = "UNGROUNDED"
                rationale = "Reference path does not match any file in the repository tree."
                
            explicit_path_resolutions.append(ExplicitPathResolution(
                evidence_ref=ref,
                original_value=original_value,
                normalized_value=norm_val,
                resolution_status=resolution_status,
                match_type=match_type,
                grounded_paths=grounded_canonicals,
                ambiguity_count=len(grounded_canonicals) if resolution_status == "AMBIGUOUS" else 0,
                rationale=rationale
            ))

    # 4. Score Candidate Relationships
    candidate_relationships: List[CandidateFileRelationship] = []
    candidates_list = getattr(candidate_evidence, "candidates", []) or []
    
    for idx, c in enumerate(candidates_list):
        path = c["path"]
        path_lower = path.lower().casefold()
        basename = path.split("/")[-1]
        basename_lower = basename.lower().casefold()
        
        direct_evidence_score = 0.0
        entity_evidence_score = 0.0
        structural_alignment_score = 0.0
        ranking_support_score = 0.0
        
        relationship_types = []
        matched_evidence_refs = []
        matched_evidence_types = []
        matched_evidence_strengths = []
        matched_entities = []
        matched_explicit_paths = []
        
        # Check Direct Explicit Path Matches
        if path in path_grounding_refs:
            matched_refs = path_grounding_refs[path]
            matched_explicit_paths.extend(path_grounding_raws[path])
            
            highest_direct_signal = 0.0
            for r in matched_refs:
                ev_item = evidence_map[r]
                authority = EVIDENCE_AUTHORITY.get(ev_item.strength, 0.0)
                
                res_obj = next((res for res in explicit_path_resolutions if res.evidence_ref == r and path in res.grounded_paths), None)
                if res_obj and res_obj.match_type:
                    sig_name = "PATH_SUFFIX_MATCH" if res_obj.match_type == "REPOSITORY_SUFFIX" else (res_obj.match_type + "_MATCH")
                    sig_weight = DIRECT_SIGNAL_WEIGHTS.get(sig_name, 20.0)
                    relationship_types.append(sig_name)
                    
                    signal_value = sig_weight * authority
                    if signal_value > highest_direct_signal:
                        highest_direct_signal = signal_value
                
                matched_evidence_refs.append(r)
                matched_evidence_types.append(ev_item.evidence_type)
                matched_evidence_strengths.append(ev_item.strength)
                
            direct_evidence_score = min(CONTRIBUTION_CAPS["DIRECT_PATH_CAP"], highest_direct_signal)

        # Check Entity Matches (from all evidence items, not just explicit paths)
        entity_signals = []
        low_entities_matched_count = 0
        is_grounded = (path in path_grounding_refs)
        
        # Determine subsystem and category alignment beforehand to pass to helper
        subsystem_alignment = False
        if resolved_subsystem and resolved_subsystem in path_lower:
            subsystem_alignment = True
        category_alignment = False
        cat = c.get("category", "")
        if cat and resolved_category and cat.lower().casefold() == resolved_category:
            category_alignment = True
        repository_map_alignment = False
        if resolved_category and resolved_category in repository_map:
            cat_dirs = repository_map.get(resolved_category, [])
            if any(path_lower.startswith(d.lower().casefold()) for d in cat_dirs):
                repository_map_alignment = True
                
        for r, ev_item in evidence_map.items():
            authority = EVIDENCE_AUTHORITY.get(ev_item.strength, 0.0)
            if authority <= 0.0:
                continue
                
            # A. Dotted module matches
            if ev_item.evidence_type == "NAMED_MODULE":
                module_val = (ev_item.normalized_value or "").lower().casefold()
                module_components = [m for m in module_val.split(".") if len(m) >= 4]
                if module_components and any(mc in path_lower for mc in module_components):
                    mod_spec = classify_entity_specificity(module_val, repo_token_freq, len(all_files))
                    if mod_spec != "LOW":
                        sig_value = ENTITY_SIGNAL_WEIGHTS["MODULE_PATH_MATCH"] * authority
                        entity_signals.append(sig_value)
                        relationship_types.append("MODULE_PATH_MATCH")
                        matched_evidence_refs.append(r)
                        matched_evidence_types.append(ev_item.evidence_type)
                        matched_evidence_strengths.append(ev_item.strength)
                    else:
                        low_entities_matched_count += 1
                        
            # B. Class/Function token matches
            for entity in ev_item.technical_entities:
                spec = classify_entity_specificity(entity, repo_token_freq, len(all_files))
                is_matched, is_low = check_entity_path_alignment(
                    entity, path, spec, repo_token_freq, len(all_files),
                    subsystem_alignment, category_alignment, repository_map_alignment, is_grounded
                )
                
                if is_matched:
                    sig_value = ENTITY_SIGNAL_WEIGHTS["TECHNICAL_ENTITY_PATH_MATCH"] * authority
                    entity_signals.append(sig_value)
                    relationship_types.append("TECHNICAL_ENTITY_PATH_MATCH")
                    matched_entities.append(entity)
                    matched_evidence_refs.append(r)
                    matched_evidence_types.append(ev_item.evidence_type)
                    matched_evidence_strengths.append(ev_item.strength)
                elif is_low:
                    low_entities_matched_count += 1
                    
        # Calculate entity score
        base_entity_score = sum(entity_signals)
        low_corroboration_bonus = 0.0
        if (base_entity_score > 0.0 or direct_evidence_score > 0.0) and low_entities_matched_count > 0:
            low_corroboration_bonus = min(2.0, low_entities_matched_count * 0.5)
            
        entity_evidence_score = min(CONTRIBUTION_CAPS["ENTITY_CAP"], base_entity_score + low_corroboration_bonus)

        # Check Structural Alignments
        if subsystem_alignment:
            structural_alignment_score += STRUCTURAL_SIGNAL_WEIGHTS["SUBSYSTEM_ALIGNMENT"]
            relationship_types.append("SUBSYSTEM_ALIGNMENT")
        if category_alignment:
            structural_alignment_score += STRUCTURAL_SIGNAL_WEIGHTS["CATEGORY_ALIGNMENT"]
            relationship_types.append("CATEGORY_ALIGNMENT")
        if repository_map_alignment:
            structural_alignment_score += STRUCTURAL_SIGNAL_WEIGHTS["REPOSITORY_MAP_ALIGNMENT"]
            relationship_types.append("REPOSITORY_MAP_ALIGNMENT")
            
        structural_alignment_score = min(CONTRIBUTION_CAPS["STRUCTURAL_CAP"], structural_alignment_score)
        
        # Ranking Support Score
        if c.get("score", 0.0) >= 50.0:
            ranking_support_score = SUPPORT_SIGNAL_WEIGHTS["RANKING_SUPPORT"]
            relationship_types.append("RANKING_SUPPORT")
            
        # Aggregate Score calculation
        relationship_score = direct_evidence_score + entity_evidence_score + structural_alignment_score + ranking_support_score
        
        # Apply penalties
        penalties = 0.0
        # Basename penalty: if generic basename and lacks direct path match
        if basename_lower in GENERIC_FILENAMES:
            # If supported only by entity or structural matching, apply penalty
            if not direct_evidence_score > 0:
                penalties += GENERIC_FILENAME_PENALTY
                
        # Ambiguity penalty: if the matched path resolution was marked ambiguous in suffix/basename before deduplication
        has_ambiguity = False
        for res in explicit_path_resolutions:
            if res.resolution_status == "AMBIGUOUS" and path in res.grounded_paths:
                has_ambiguity = True
                
        if has_ambiguity:
            penalties += AMBIGUITY_PENALTY
            
        relationship_score = max(0.0, min(100.0, relationship_score - penalties))
        
        # Clean lists to be unique and preserve order
        relationship_types = sorted(list(set(relationship_types)))
        matched_evidence_refs = sorted(list(set(matched_evidence_refs)))
        matched_evidence_types = sorted(list(set(matched_evidence_types)))
        matched_evidence_strengths = sorted(list(set(matched_evidence_strengths)))
        matched_entities = sorted(list(set(matched_entities)))
        matched_explicit_paths = sorted(list(set(matched_explicit_paths)))
        
        # Deduce Relationship Strength
        relationship_strength = "WEAK"
        # Check if direct matching path exists with non-IGNORE evidence
        has_non_ignore_direct = False
        if direct_evidence_score > 0:
            # check if any matched evidence ref is not IGNORE
            for ref_key in matched_evidence_refs:
                ev_item = evidence_map[ref_key]
                if ev_item.strength != "IGNORE" and ev_item.evidence_type == "EXPLICIT_PATH":
                    has_non_ignore_direct = True
                    break
                    
        if has_non_ignore_direct:
            relationship_strength = "DIRECT"
        elif relationship_score >= 60.0:
            # Requires at least one CRITICAL or STRONG evidence-bound signal
            has_strong_evidence_bound = False
            for ref_key in matched_evidence_refs:
                ev_item = evidence_map[ref_key]
                if ev_item.strength in ["CRITICAL", "STRONG"]:
                    has_strong_evidence_bound = True
                    break
            if has_strong_evidence_bound:
                relationship_strength = "STRONG"
            else:
                relationship_strength = "MODERATE"
        elif relationship_score >= 35.0:
            relationship_strength = "MODERATE"
            
        # Deduce Investigation Priority
        investigation_priority = "LOW_CONFIDENCE"
        
        has_critical_or_strong = False
        for ref_key in matched_evidence_refs:
            ev_item = evidence_map[ref_key]
            if ev_item.strength in ["CRITICAL", "STRONG"]:
                has_critical_or_strong = True
                break
                
        has_supporting = False
        for ref_key in matched_evidence_refs:
            ev_item = evidence_map[ref_key]
            if ev_item.strength in ["SUPPORTING"]:
                has_supporting = True
                break
                
        # Hard Rule check: Ranking-only candidates cannot become PRIMARY/SECONDARY
        is_ranking_only = (not matched_evidence_refs)
        
        if not is_ranking_only:
            if relationship_strength == "DIRECT":
                investigation_priority = "PRIMARY"
            elif relationship_score >= 65.0 and has_critical_or_strong:
                investigation_priority = "PRIMARY"
            elif relationship_score >= 40.0 and (has_critical_or_strong or has_supporting):
                investigation_priority = "SECONDARY"
            elif relationship_score >= 15.0:
                investigation_priority = "SUPPORTING"
        else:
            # Ranking only
            if relationship_score >= 15.0:
                investigation_priority = "SUPPORTING"
            else:
                investigation_priority = "LOW_CONFIDENCE"
                
        # Format candidate ranking reasons
        candidate_ranking_reasons = c.get("reasons", []) or []
        
        # Build rationale
        rationale_parts = []
        if relationship_strength == "DIRECT":
            rationale_parts.append("Direct explicit path matching grounds this file.")
        elif relationship_strength == "STRONG":
            rationale_parts.append("Strongly grounded by technical entities and category/subsystem alignment.")
        elif relationship_strength == "MODERATE":
            rationale_parts.append("Moderately aligned with issue context elements.")
        else:
            rationale_parts.append("Weakly grounded candidate.")
            
        if matched_entities:
            rationale_parts.append(f"Matched entities: {', '.join(matched_entities[:3])}.")
            
        rationale = " ".join(rationale_parts)
        
        candidate_relationships.append(CandidateFileRelationship(
            path=path,
            candidate_rank=idx + 1,
            candidate_score=c.get("score", 0.0),
            relationship_score=relationship_score,
            relationship_strength=relationship_strength,
            investigation_priority=investigation_priority,
            relationship_types=relationship_types,
            matched_evidence_refs=matched_evidence_refs,
            matched_evidence_types=matched_evidence_types,
            matched_evidence_strengths=matched_evidence_strengths,
            matched_entities=matched_entities,
            matched_explicit_paths=matched_explicit_paths,
            subsystem_alignment=subsystem_alignment,
            category_alignment=category_alignment,
            repository_map_alignment=repository_map_alignment,
            direct_evidence_score=direct_evidence_score,
            entity_evidence_score=entity_evidence_score,
            structural_alignment_score=structural_alignment_score,
            ranking_support_score=ranking_support_score,
            candidate_ranking_reasons=candidate_ranking_reasons,
            rationale=rationale
        ))

    # 5. Deterministic Sort & Order
    priority_order_map = {
        "PRIMARY": 3,
        "SECONDARY": 2,
        "SUPPORTING": 1,
        "LOW_CONFIDENCE": 0
    }
    
    strength_order_map = {
        "DIRECT": 3,
        "STRONG": 2,
        "MODERATE": 1,
        "WEAK": 0
    }
    
    def get_max_authority_val(rel: CandidateFileRelationship) -> float:
        max_auth = 0.0
        for st in rel.matched_evidence_strengths:
            auth = EVIDENCE_AUTHORITY.get(st, 0.0)
            if auth > max_auth:
                max_auth = auth
        return max_auth

    # Ordering sort key
    def rel_sort_key(rel: CandidateFileRelationship):
        return (
            -priority_order_map.get(rel.investigation_priority, 0),
            -strength_order_map.get(rel.relationship_strength, 0),
            -rel.relationship_score,
            -1.0 if "DIRECT_MATCH" in rel.relationship_types or "EXPLICIT_PATH_MATCH" in rel.relationship_types or "PATH_SUFFIX_MATCH" in rel.relationship_types else 0.0,
            -get_max_authority_val(rel),
            -rel.candidate_score,
            rel.candidate_rank,
            rel.path.lower().casefold() # Lexical tie-breaker
        )

    candidate_relationships.sort(key=rel_sort_key)
    investigation_order = [r.path for r in candidate_relationships]
    
    # 6. Candidate-to-Candidate Relationship Graph
    file_relationship_edges: List[CandidateRelationshipEdge] = []
    
    # We build edges among the top candidate files (limit to top 10 for performance and layout)
    top_graph_candidates = candidate_relationships[:10]
    
    for i in range(len(top_graph_candidates)):
        for j in range(i + 1, len(top_graph_candidates)):
            c1 = top_graph_candidates[i]
            c2 = top_graph_candidates[j]
            
            shared_entities = sorted(list(set(c1.matched_entities).intersection(set(c2.matched_entities))))
            shared_evidence = sorted(list(set(c1.matched_evidence_refs).intersection(set(c2.matched_evidence_refs))))
            
            # Shared evidence scoring weighted by evidence authority
            shared_evidence_score = 0.0
            for ref_key in shared_evidence:
                ev_item = evidence_map[ref_key]
                if ev_item.strength == "CRITICAL":
                    shared_evidence_score += EDGE_WEIGHTS["SHARED_CRITICAL_EVIDENCE"]
                elif ev_item.strength == "STRONG":
                    shared_evidence_score += EDGE_WEIGHTS["SHARED_STRONG_EVIDENCE"]
                elif ev_item.strength == "SUPPORTING":
                    shared_evidence_score += EDGE_WEIGHTS["SHARED_SUPPORTING_EVIDENCE"]
                    
            shared_entities_score = len(shared_entities) * EDGE_WEIGHTS["SHARED_ENTITY"]
            
            # Directory proximity
            shared_parent_path = None
            shared_parent_score = 0.0
            
            p1_parts = c1.path.split("/")[:-1]
            p2_parts = c2.path.split("/")[:-1]
            
            common_parts = []
            for p1, p2 in zip(p1_parts, p2_parts):
                if p1.lower().casefold() == p2.lower().casefold():
                    common_parts.append(p1)
                else:
                    break
                    
            if common_parts:
                # Deepest meaningful parent path: check if it's not root or generic shallow level
                is_generic = False
                if len(common_parts) == 1:
                    # Generic direct child folders of root are blacklisted from directory relationship score
                    if common_parts[0].lower().casefold() in ["src", "lib", "libs", "app", "packages", "backend", "frontend", "tests"]:
                        is_generic = True
                if not is_generic:
                    shared_parent_path = "/".join(common_parts)
                    shared_parent_score = EDGE_WEIGHTS["MEANINGFUL_SHARED_PARENT"]
                    
            # Shared repo map area
            shared_area_score = 0.0
            c1_cat = c1.category_alignment
            c2_cat = c2.category_alignment
            if c1_cat and c2_cat:
                shared_area_score = EDGE_WEIGHTS["REPOSITORY_MAP_AREA"]
                
            edge_score = shared_evidence_score + shared_entities_score + shared_parent_score + shared_area_score
            
            if edge_score > 0:
                edge_types = []
                if shared_entities:
                    edge_types.append("SHARED_ENTITY_RELATIONSHIP")
                if shared_evidence:
                    edge_types.append("SHARED_EVIDENCE_RELATIONSHIP")
                if shared_parent_path:
                    edge_types.append("MEANINGFUL_DIRECTORY_RELATIONSHIP")
                if c1_cat and c2_cat:
                    edge_types.append("REPOSITORY_MAP_AREA_RELATIONSHIP")
                    
                edge_types = sorted(list(set(edge_types)))
                
                rationale_edge = f"Candidate files relate via: {', '.join(edge_types)}."
                file_relationship_edges.append(CandidateRelationshipEdge(
                    source_path=c1.path,
                    target_path=c2.path,
                    relationship_types=edge_types,
                    shared_entities=shared_entities,
                    shared_evidence_count=len(shared_evidence),
                    shared_parent_path=shared_parent_path,
                    relationship_score=edge_score,
                    rationale=rationale_edge
                ))
                
    # Sort edges descending by relationship score
    file_relationship_edges.sort(key=lambda x: -x.relationship_score)

    # 7. Grounding telemetries count
    direct_count = len([x for x in candidate_relationships if x.relationship_strength == "DIRECT"])
    strong_count = len([x for x in candidate_relationships if x.relationship_strength == "STRONG"])
    moderate_count = len([x for x in candidate_relationships if x.relationship_strength == "MODERATE"])
    weak_count = len([x for x in candidate_relationships if x.relationship_strength == "WEAK"])
    
    primary_count = len([x for x in candidate_relationships if x.investigation_priority == "PRIMARY"])
    secondary_count = len([x for x in candidate_relationships if x.investigation_priority == "SECONDARY"])
    supporting_count = len([x for x in candidate_relationships if x.investigation_priority == "SUPPORTING"])
    low_confidence_count = len([x for x in candidate_relationships if x.investigation_priority == "LOW_CONFIDENCE"])
    
    avail_explicit = len([x for x in evidence_items if x.evidence_type == "EXPLICIT_PATH"])
    grounded_explicit = len([x for x in explicit_path_resolutions if x.resolution_status == "GROUNDED"])
    ambiguous_explicit = len([x for x in explicit_path_resolutions if x.resolution_status == "AMBIGUOUS"])
    ungrounded_explicit = len([x for x in explicit_path_resolutions if x.resolution_status == "UNGROUNDED"])
    
    latency_ms = (time.perf_counter() - start_time) * 1000.0
    
    return FileRelationshipGroundingResult(
        status="SUCCESS",
        explicit_path_resolutions=explicit_path_resolutions,
        candidate_relationships=candidate_relationships,
        file_relationship_edges=file_relationship_edges,
        investigation_order=investigation_order,
        total_candidates=len(candidate_relationships),
        direct_relationship_count=direct_count,
        strong_relationship_count=strong_count,
        moderate_relationship_count=moderate_count,
        weak_relationship_count=weak_count,
        primary_count=primary_count,
        secondary_count=secondary_count,
        supporting_count=supporting_count,
        low_confidence_count=low_confidence_count,
        explicit_paths_available=avail_explicit,
        explicit_paths_grounded=grounded_explicit,
        explicit_paths_ambiguous=ambiguous_explicit,
        explicit_paths_ungrounded=ungrounded_explicit,
        grounding_latency_ms=latency_ms
    )
