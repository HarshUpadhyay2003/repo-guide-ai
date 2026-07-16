import re
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple

@dataclass
class EvidenceSourceReference:
    source: str
    source_index: Optional[int] = None

@dataclass
class TechnicalEvidenceItem:
    evidence_type: str
    strength: str
    source: str
    text: str
    normalized_value: str
    rationale: str
    technical_entities: List[str] = field(default_factory=list)
    source_index: Optional[int] = None
    confidence_score: Optional[float] = None
    matched_patterns: List[str] = field(default_factory=list)
    sources: List[EvidenceSourceReference] = field(default_factory=list)
    occurrence_count: int = 1

@dataclass
class TechnicalEvidenceResult:
    items: List[TechnicalEvidenceItem]
    evidence_type_counts: Dict[str, int]
    strength_counts: Dict[str, int]
    top_technical_entities: List[str]
    duplicate_count: int
    extraction_ms: float = 0.0

# Centralized Scoring Constants
BASE_SCORES = {
    "MAINTAINER_DIAGNOSIS": 85,
    "ROOT_CAUSE_STATEMENT": 75,
    "ERROR_SIGNATURE": 75,
    "EXPLICIT_PATH": 70,
    "REPRODUCTION_DETAIL": 60,
    "ACTUAL_BEHAVIOR": 50,
    "IMPLEMENTATION_STATEMENT": 50,
    "EXPECTED_BEHAVIOR": 40,
    "NAMED_CLASS": 35,
    "NAMED_FUNCTION": 35,
    "NAMED_MODULE": 30,
    "TECHNICAL_DEPENDENCY": 25,
    "GENERIC_DISCUSSION": 10,
    "CONTRIBUTOR_NOISE": 5,
    "BOT_NOISE": 5,
}

# Positive adjustment signals
BONUS_EXPLICIT_PATH = 15
BONUS_ERROR_SIGNATURE = 15
BONUS_CLASS_OR_FUNCTION = 10
BONUS_TECHNICAL_DEPENDENCY = 5
BONUS_MAINTAINER = 15
BONUS_MULTI_ENTITY = 5  # per extra entity
MAX_BONUS_MULTI_ENTITY = 15

# Negative adjustment signals
PENALTY_CONTRIBUTOR_NOISE = 40
PENALTY_NO_ENTITIES = 20
PENALTY_SHORT_TEXT = 10
PENALTY_BOT_NOISE = 40

# Technology Vocabulary
TECH_VOCAB = {
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "react": "React",
    "docker": "Docker",
    "redis": "Redis",
    "groq": "Groq",
    "fastapi": "FastAPI",
    "pydantic": "Pydantic",
    "httpx": "httpx",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "go": "Go",
    "golang": "Go",
    "rust": "Rust",
    "bash": "Bash",
    "shell": "Shell",
    "yaml": "YAML",
    "json": "JSON",
    "flask": "Flask",
    "django": "Django",
    "aws": "AWS",
    "azure": "Azure",
    "git": "Git"
}

def segment_text(text: str) -> List[str]:
    """Segment raw issue/comment text into sentences and code blocks deterministically.
    
    Preserves version numbers (e.g. Python 3.12), explicit paths, and dot-notation symbols intact.
    """
    if not text:
        return []
        
    # Normalize line endings
    text = text.replace('\r\n', '\n')
    
    segments = []
    lines = text.splitlines()
    in_block = False
    block_lines = []
    
    for line in lines:
        if line.strip().startswith('```'):
            if in_block:
                block_lines.append(line)
                segments.append('\n'.join(block_lines))
                block_lines = []
                in_block = False
            else:
                in_block = True
                block_lines.append(line)
        else:
            if in_block:
                block_lines.append(line)
            else:
                segments.append(line)
                
    if in_block and block_lines:
        segments.append('\n'.join(block_lines))
        
    final_segments = []
    for seg in segments:
        seg_strip = seg.strip()
        if not seg_strip:
            continue
            
        # Preserve fenced blocks intact
        if seg_strip.startswith('```') and seg_strip.endswith('```') and len(seg_strip) > 6:
            final_segments.append(seg_strip)
            continue
            
        # Split prose by paragraph double newlines
        sub_segs = [s.strip() for s in re.split(r'\n\n+', seg_strip) if s.strip()]
        for sub in sub_segs:
            # Split list elements (bullet/numbered)
            list_segs = []
            current_item = []
            sub_lines = sub.splitlines()
            for sl in sub_lines:
                sl_strip = sl.strip()
                if sl_strip.startswith(('-', '*')) or re.match(r'^\d+\.', sl_strip):
                    if current_item:
                        list_segs.append('\n'.join(current_item))
                    current_item = [sl_strip]
                else:
                    current_item.append(sl)
            if current_item:
                list_segs.append('\n'.join(current_item))
                
            for lseg in list_segs:
                lseg_strip = lseg.strip()
                if not lseg_strip:
                    continue
                    
                # Split prose sentences conservatively.
                # Uses dot-space boundaries, avoiding single dots in dot-notation or path names.
                pattern = r'(?<!\b[a-zA-Z])(?<!\bpy)(?<!\bjs)(?<!\bts)(?<!\btsx)(?<!\bjsx)(?<!\bjson)(?<!\byml)(?<!\byaml)(?<!\bmd)(?<!\bcss)(?<!\bhtml)(?<!\bsh)(?<!\bgo)(?<!\brs)(?<!\bjava)(?<!\bcpp)(?<!\bcs)\. +|\?\s+|\!\s+|\n+'
                sent_segs = [s.strip() for s in re.split(pattern, lseg_strip) if s.strip()]
                for s_seg in sent_segs:
                    if s_seg.endswith('.'):
                        s_seg = s_seg[:-1].strip()
                    if s_seg:
                        final_segments.append(s_seg)
                        
    return final_segments

def _extract_explicit_paths(text: str) -> List[str]:
    """Extract repository style file paths."""
    path_regex = r'\b[a-zA-Z0-9_\-\./]+\.[a-zA-Z0-9_\-]{2,4}\b'
    matches = re.findall(path_regex, text)
    paths = []
    for m in matches:
        if not re.match(r'^\d+\.\d+$', m) and ('/' in m or m.endswith(('.py', '.ts', '.tsx', '.js', '.jsx', '.json', '.yml', '.yaml', '.md', '.css', '.html', '.sh', '.go', '.rs', '.java', '.h', '.c', '.cpp', '.cs'))):
            paths.append(m)
    return sorted(list(set(paths)))

def _extract_error_signatures(text: str) -> List[str]:
    """Extract Exception names or HTTP error codes."""
    sigs = []
    exception_matches = re.findall(r'\b[A-Z][a-zA-Z]+(?:Error|Exception)\b', text)
    sigs.extend(exception_matches)
    http_matches = re.findall(r'\bHTTP \d{3}\b', text)
    sigs.extend(http_matches)
    return sorted(list(set(sigs)))

def _extract_named_classes(text: str) -> List[str]:
    """Extract CamelCase class names and class-suffix names."""
    classes = []
    # CamelCase: Starts with uppercase, followed by lowercase, and has at least one other uppercase
    matches = re.findall(r'\b[A-Z][a-z0-9]+[A-Z][a-zA-Z0-9]*\b', text)
    for mc in matches:
        if mc not in ["GitHub", "Git", "HTML", "CSS", "JSON", "YAML", "TOML", "REST", "API", "URL", "HTTP", "HTTPS", "Python", "TypeScript", "JavaScript"]:
            classes.append(mc)
            
    # Suffix matching
    suffixes = ["Service", "Client", "Tool", "Config", "Handler", "Manager", "Parser", "Runner", "Builder", "Factory", "Adapter", "Provider", "Repository", "Model", "Controller", "Context", "Exception", "Error"]
    for suffix in suffixes:
        matches_s = re.findall(rf'\b[A-Z][a-z]+{suffix}\b', text)
        classes.extend(matches_s)
    return sorted(list(set(classes)))

def _extract_named_functions(text: str) -> List[str]:
    """Extract functions, Class.method, private method notations."""
    funcs = []
    # 1. Class.method or object.method (e.g. MyClass.my_method)
    method_matches = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*\b', text)
    for m in method_matches:
        if not m.endswith(('.py', '.js', '.ts', '.tsx', '.json', '.yml', '.yaml', '.md', '.css', '.html', '.sh', '.go', '.rs', '.java', '.h', '.c', '.cpp', '.cs')):
            if not re.match(r'^\d+\.\d+$', m):
                funcs.append(m)
                
    # 2. Function calls with open paren
    call_matches = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', text)
    for c in call_matches:
        if c not in ["if", "for", "while", "with", "print", "list", "dict", "set", "tuple", "str", "int", "float", "len", "range"]:
            funcs.append(c)
            
    # 3. Private underscores
    snake_matches = re.findall(r'\b_[a-zA-Z0-9_]+\b', text)
    funcs.extend(snake_matches)
    return sorted(list(set(funcs)))

def _extract_named_modules(text: str) -> List[str]:
    """Extract namespaces like langchain_core.tools and library names."""
    mods = []
    pkg_matches = re.findall(r'\b[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_\.]+\b', text)
    for pm in pkg_matches:
        if not pm.endswith(('.py', '.js', '.ts', '.tsx', '.json', '.yml', '.yaml', '.md', '.css', '.html', '.sh', '.go', '.rs', '.java', '.h', '.c', '.cpp', '.cs')):
            mods.append(pm)
            
    known_libs = ["httpx", "pydantic", "fastapi", "pytest", "langchain", "numpy", "pandas", "requests", "flask", "django", "uvicorn", "redis", "sqlalchemy", "react", "pydantic_core"]
    for lib in known_libs:
        pattern = rf'\b{lib}\b'
        if re.search(pattern, text, re.IGNORECASE):
            mods.append(lib)
    return sorted(list(set(mods)))

def _extract_technical_dependencies(text: str) -> List[str]:
    """Extract framework and technology dependencies."""
    deps = []
    text_lower = text.lower()
    for key, val in TECH_VOCAB.items():
        pattern = rf'\b{re.escape(key)}\b'
        if re.search(pattern, text_lower):
            deps.append(val)
    return sorted(list(set(deps)))

def _detect_symbolic_patterns(segment: str) -> List[str]:
    """Detect symbolic patterns within a text segment for debugging telemetry."""
    patterns = []
    segment_lower = segment.lower()
    
    # Causal
    if "because" in segment_lower:
        patterns.append("causal_because")
    if "due to" in segment_lower:
        patterns.append("causal_due_to")
    if "caused by" in segment_lower:
        patterns.append("causal_caused_by")
        
    # Exception/Errors
    if "traceback" in segment_lower:
        patterns.append("traceback_block")
    if re.search(r'\b[A-Z][a-zA-Z]+(?:Error|Exception)\b', segment):
        patterns.append("exception_signature")
        
    # Functions / Paths
    if "(" in segment:
        patterns.append("function_call_notation")
    if re.search(r'\b[A-Z][a-z0-9]+[A-Z][a-zA-Z0-9]*\b', segment):
        patterns.append("class_camel_case")
    if "/" in segment or segment.endswith(('.py', '.js', '.ts', '.tsx')):
        patterns.append("python_path")
        
    # Contributor requests
    if "assign" in segment_lower:
        patterns.append("assignment_request")
        
    return patterns

def classify_segment(
    segment: str,
    entities: Dict[str, List[str]],
    author: str = "User"
) -> List[str]:
    """Determine matching evidence types for a single text segment."""
    types = []
    segment_lower = segment.lower()
    
    is_bot = "[bot]" in author.lower() or author.lower() in ["dependabot", "github-actions"]
    
    # 2. CONTRIBUTOR_NOISE
    is_contributor_noise = False
    contributor_patterns = [
        r"i'd like to work on this", r"can you assign this to me", r"please assign me",
        r"is this issue available", r"i want to contribute", r"i have opened a pr",
        r"can i take this", r"assign me please", r"would like to contribute",
        r"can i work on this", r"claim this issue", r"assign this to me",
        r"place assign", r"assign to me"
    ]
    if any(re.search(p, segment_lower) for p in contributor_patterns):
        types.append("CONTRIBUTOR_NOISE")
        is_contributor_noise = True
        
    # 3. GENERIC_DISCUSSION
    generic_patterns = [
        r"^interesting\.?$", r"^i agree\.?$", r"^this seems useful\.?$",
        r"^thanks for reporting\.?$", r"^thanks\.?$", r"^thank you\.?$",
        r"^any updates\??$", r"^bump\.?$", r"^lgtm\.?$", r"^thank you very much\.?$"
    ]
    if any(re.search(p, segment_lower) for p in generic_patterns):
        types.append("GENERIC_DISCUSSION")
        
    # 4. EXPLICIT_PATH
    if entities["paths"]:
        types.append("EXPLICIT_PATH")
        
    # 5. ERROR_SIGNATURE
    has_error_sig = False
    if entities["errors"] or "traceback" in segment_lower:
        types.append("ERROR_SIGNATURE")
        has_error_sig = True
        
    # 6. ROOT_CAUSE_STATEMENT
    causal_patterns = [
        r"\bbecause\b", r"\bcaused by\b", r"\bdue to\b", r"\bthe issue occurs when\b",
        r"\bthe problem happens because\b", r"\bthe root cause\b", r"\bthis happens when\b",
        r"\balways creates\b", r"\balways declares\b", r"\binjects\b", r"\boverrides\b",
        r"\bconflicts with\b", r"\bdoes not reuse\b", r"\bis recreated\b",
        r"\bis initialized each time\b", r"\bfails because\b", r"\bbreaks when\b"
    ]
    has_technical_entity = bool(entities["paths"] or entities["classes"] or entities["functions"] or entities["modules"])
    if has_technical_entity and any(re.search(p, segment_lower) for p in causal_patterns):
        types.append("ROOT_CAUSE_STATEMENT")
        
    # 7. IMPLEMENTATION_STATEMENT
    impl_patterns = [
        r"\bcreates a new\b", r"\bclient on every\b", r"\bclient for every\b",
        r"\bcreates a\b", r"\binspects the\b", r"\binitialized inside\b",
        r"\bpasses\s+\w+\s+to\b", r"\bdeclares\b", r"\binstantiation\b",
        r"\bconstructor\b", r"\binstantiated\b", r"\binitialized\b",
        r"\bdefines\b", r"\bdefines a\b", r"\bdeclares a\b", r"\bextends\b",
        r"\bimports\b", r"\bcalled inside\b"
    ]
    if (has_technical_entity or entities["dependencies"]) and any(re.search(p, segment_lower) for p in impl_patterns):
        types.append("IMPLEMENTATION_STATEMENT")
        
    # 8. NAMED_CLASS
    if entities["classes"]:
        types.append("NAMED_CLASS")
        
    # 9. NAMED_FUNCTION
    if entities["functions"]:
        types.append("NAMED_FUNCTION")
        
    # 10. NAMED_MODULE
    if entities["modules"]:
        types.append("NAMED_MODULE")
        
    # 11. TECHNICAL_DEPENDENCY
    if entities["dependencies"]:
        types.append("TECHNICAL_DEPENDENCY")
        
    # 12. REPRODUCTION_DETAIL
    repro_patterns = [
        r"\brun the test\b", r"\brun with\b", r"\binstantiate\b", r"\bcall\b",
        r"\breproduce\b", r"\bsteps to\b", r"\bhow to run\b", r"\btest with\b",
        r"\bin a loop\b", r"\btimes in\b", r"\bwithout passing\b", r"\bpytest\b",
        r"\bcommand\b", r"\brun\s+python\b"
    ]
    if any(re.search(p, segment_lower) for p in repro_patterns):
        if has_technical_entity or entities["dependencies"] or any(char.isdigit() for char in segment_lower):
            types.append("REPRODUCTION_DETAIL")
            
    # 13. EXPECTED_BEHAVIOR
    expected_patterns = [
        r"\bshould\b", r"\bexpected\b", r"\bshould reuse\b", r"\bshould return\b",
        r"\bshould preserve\b", r"\bshould not create\b", r"\bought to\b"
    ]
    if any(re.search(p, segment_lower) for p in expected_patterns):
        types.append("EXPECTED_BEHAVIOR")
        
    # 14. ACTUAL_BEHAVIOR
    actual_patterns = [
        r"\bcurrently\b", r"\binstead\b", r"\bactually\b", r"\bcreates a new\b",
        r"\breturns\b", r"\bfails\b", r"\bthrows\b", r"\bis missing\b",
        r"\bdoes not\b", r"\balways\b"
    ]
    if any(re.search(p, segment_lower) for p in actual_patterns):
        if has_technical_entity or entities["dependencies"] or has_error_sig:
            types.append("ACTUAL_BEHAVIOR")
            
    # 15. BOT_NOISE
    if is_bot:
        if not has_technical_entity and not has_error_sig:
            types.append("BOT_NOISE")
            
    return types

def _score_evidence_item(
    evidence_type: str,
    segment: str,
    technical_entities: List[str],
    context_flags: Dict[str, Any],
    source_metadata: Dict[str, Any]
) -> int:
    """Compute strength score (0-100) deterministically for an evidence item."""
    # 1. Base Score
    score = BASE_SCORES.get(evidence_type, 15)
    
    # 2. Contributor noise boundary
    if context_flags.get("is_contributor_noise", False):
        if evidence_type == "CONTRIBUTOR_NOISE":
            return min(14, score) # Must stay IGNORE
        else:
            score -= PENALTY_CONTRIBUTOR_NOISE
            return max(15, min(39, score)) # Keep in WEAK band
            
    # 3. Bot noise boundary
    if context_flags.get("is_bot_context", False):
        if evidence_type == "BOT_NOISE":
            return min(14, score) # Must stay IGNORE
        else:
            if evidence_type not in ["ERROR_SIGNATURE", "EXPLICIT_PATH"]:
                score -= PENALTY_BOT_NOISE
                
    # 4. Contextual Additive Bonuses
    if evidence_type in ["ROOT_CAUSE_STATEMENT", "IMPLEMENTATION_STATEMENT", "REPRODUCTION_DETAIL", "ACTUAL_BEHAVIOR", "EXPECTED_BEHAVIOR", "MAINTAINER_DIAGNOSIS"]:
        if context_flags.get("has_explicit_path", False):
            score += BONUS_EXPLICIT_PATH
        if context_flags.get("has_error_signature", False):
            score += BONUS_ERROR_SIGNATURE
        if context_flags.get("has_class_or_function", False):
            score += BONUS_CLASS_OR_FUNCTION
        if context_flags.get("has_technical_dependency", False):
            score += BONUS_TECHNICAL_DEPENDENCY
            
        # Multi-entity bonus
        entity_count = len(technical_entities)
        if entity_count > 1:
            extra_entities = entity_count - 1
            bonus = min(MAX_BONUS_MULTI_ENTITY, extra_entities * BONUS_MULTI_ENTITY)
            score += bonus
            
        # Maintainer bonus
        if context_flags.get("is_maintainer", False):
            score += BONUS_MAINTAINER

    # 5. Negative Penalties
    if not technical_entities and evidence_type not in ["CONTRIBUTOR_NOISE", "BOT_NOISE", "GENERIC_DISCUSSION"]:
        score -= PENALTY_NO_ENTITIES
        
    if len(segment.strip()) < 20 and not technical_entities:
        score -= PENALTY_SHORT_TEXT
        
    return max(0, min(100, score))

def _derive_strength(score: int) -> str:
    """Map numeric score (0-100) to conformed strength band."""
    if score >= 85:
        return "CRITICAL"
    elif score >= 65:
        return "STRONG"
    elif score >= 40:
        return "SUPPORTING"
    elif score >= 15:
        return "WEAK"
    return "IGNORE"

def _filter_duplicate_subentities(entities: List[str]) -> List[str]:
    """Remove sub-parts of dot-notation entities to prevent double counting/inflation."""
    to_remove = set()
    for e in entities:
        if '.' in e and '/' not in e and not e.endswith(('.py', '.js', '.ts', '.tsx', '.json', '.yml', '.yaml', '.md', '.css', '.html', '.sh', '.go', '.rs', '.java', '.h', '.c', '.cpp', '.cs')):
            parts = e.split('.')
            to_remove.update(parts)
    return [e for e in entities if e not in to_remove]

def extract_technical_evidence(
    title: str,
    body: str,
    labels: List[str],
    comments: List[Dict[str, Any]],
) -> TechnicalEvidenceResult:
    """Primary deterministic interface for local technical evidence extraction."""
    start_time = time.perf_counter()
    
    # 1. Gather all sources
    raw_sources: List[Tuple[str, str, Optional[int], Dict[str, Any]]] = [] # (source_type, text, index, metadata)
    raw_sources.append(("TITLE", title, None, {}))
    raw_sources.append(("BODY", body, None, {}))
    
    for lbl in labels:
        raw_sources.append(("LABEL", lbl, None, {}))
        
    for idx, c in enumerate(comments):
        author = c.get("author") or c.get("user", {}).get("login", "User")
        # Support metadata if injected
        is_maintainer = False
        assoc = c.get("author_association")
        if assoc in ["OWNER", "COLLABORATOR", "MEMBER"]:
            is_maintainer = True
        elif c.get("is_maintainer") or c.get("maintainer") or c.get("collaborator"):
            is_maintainer = True
            
        metadata = {
            "author": author,
            "is_maintainer": is_maintainer,
            "is_bot": "[bot]" in author.lower() or author.lower() in ["dependabot", "github-actions"]
        }
        raw_sources.append(("COMMENT", c.get("body", ""), idx, metadata))
        
    # 2. Extract evidence items from segments
    extracted_items: List[TechnicalEvidenceItem] = []
    
    for source_type, text, source_idx, meta in raw_sources:
        if not text:
            continue
            
        # Segment the text
        segments = segment_text(text)
        for segment in segments:
            # Extract entities
            paths = _extract_explicit_paths(segment)
            errors = _extract_error_signatures(segment)
            classes = _extract_named_classes(segment)
            funcs = _extract_named_functions(segment)
            mods = _extract_named_modules(segment)
            deps = _extract_technical_dependencies(segment)
            
            entities_dict = {
                "paths": paths,
                "errors": errors,
                "classes": classes,
                "functions": funcs,
                "modules": mods,
                "dependencies": deps
            }
            
            # Combine all entities for reporting
            all_entities = sorted(list(set(paths + errors + classes + funcs + mods + deps)))
            all_entities = _filter_duplicate_subentities(all_entities)
            
            # Detect types
            types = classify_segment(segment, entities_dict, author=meta.get("author", "User"))
            
            # Build context flags
            has_explicit_path = bool(paths)
            has_error_signature = bool(errors) or "traceback" in segment.lower()
            has_class_or_function = bool(classes or funcs)
            has_technical_dependency = bool(deps)
            is_contributor_noise = "CONTRIBUTOR_NOISE" in types
            is_bot_context = meta.get("is_bot", False) or "BOT_NOISE" in types
            
            context_flags = {
                "has_explicit_path": has_explicit_path,
                "has_error_signature": has_error_signature,
                "has_class_or_function": has_class_or_function,
                "has_technical_dependency": has_technical_dependency,
                "is_contributor_noise": is_contributor_noise,
                "is_bot_context": is_bot_context,
                "is_maintainer": meta.get("is_maintainer", False)
            }
            
            patterns = _detect_symbolic_patterns(segment)
            
            # If we matched maintainer diagnosis
            if meta.get("is_maintainer", False) and ("ROOT_CAUSE_STATEMENT" in types or "IMPLEMENTATION_STATEMENT" in types):
                types.append("MAINTAINER_DIAGNOSIS")
                
            # Fallback if no types detected, classify as generic discussion
            if not types:
                types.append("GENERIC_DISCUSSION")
                
            # Create separate items based on entity extraction to prevent loss of secondary paths/classes/etc.
            for t_type in types:
                values_to_emit = []
                if t_type == "EXPLICIT_PATH" and paths:
                    values_to_emit = [(p, [p]) for p in paths]
                elif t_type == "ERROR_SIGNATURE" and errors:
                    values_to_emit = [(e, [e]) for e in errors]
                elif t_type == "TECHNICAL_DEPENDENCY" and deps:
                    values_to_emit = [(d, [d]) for d in deps]
                elif t_type == "NAMED_CLASS" and classes:
                    values_to_emit = [(c, [c]) for c in classes]
                elif t_type == "NAMED_FUNCTION" and funcs:
                    values_to_emit = [(f, [f]) for f in funcs]
                elif t_type == "NAMED_MODULE" and mods:
                    values_to_emit = [(m, [m]) for m in mods]
                else:
                    values_to_emit = [(segment.strip(), all_entities)]

                for val, item_entities in values_to_emit:
                    # Score evidence item
                    score = _score_evidence_item(t_type, segment, all_entities, context_flags, meta)
                    strength = _derive_strength(score)
                    
                    # Derive conformed rationale
                    rationale = f"Detected {t_type} with score {score}."
                    if all_entities:
                        rationale += f" Technical signals: {', '.join(all_entities)}."
                    if is_contributor_noise:
                        rationale += " Flagged as contributor noise."
                        
                    ref = EvidenceSourceReference(source=source_type, source_index=source_idx)
                    
                    item = TechnicalEvidenceItem(
                        evidence_type=t_type,
                        strength=strength,
                        source=source_type,
                        text=segment.strip(),
                        normalized_value=val,
                        rationale=rationale,
                        technical_entities=item_entities,
                        source_index=source_idx,
                        confidence_score=float(score),
                        matched_patterns=patterns,
                        sources=[ref],
                        occurrence_count=1
                    )
                    extracted_items.append(item)
                
    # 3. Deduplicate
    deduped: Dict[Tuple[str, str], TechnicalEvidenceItem] = {}
    duplicate_count = 0
    
    for item in extracted_items:
        key = (item.evidence_type, item.normalized_value)
        if key in deduped:
            duplicate_count += 1
            existing = deduped[key]
            # Accumulate source reference
            existing.sources.extend(item.sources)
            existing.occurrence_count += 1
            # Repetition bonus
            bonus = min(6, (existing.occurrence_count - 1) * 2)
            # Recompute score and strength
            new_score = min(100, int(existing.confidence_score) + bonus)
            existing.confidence_score = float(new_score)
            existing.strength = _derive_strength(new_score)
            # Keep the longer text/rationale if helpful, or keep strongest
            if item.confidence_score > existing.confidence_score:
                existing.rationale = item.rationale
        else:
            deduped[key] = item
            
    final_items = list(deduped.values())
    
    # 4. Top Entity Ranking
    entity_scores: Dict[str, int] = {}
    entity_counts: Dict[str, int] = {}
    
    strength_weight = {
        "CRITICAL": 5,
        "STRONG": 4,
        "SUPPORTING": 3,
        "WEAK": 1,
        "IGNORE": 0
    }
    
    for item in final_items:
        weight = strength_weight.get(item.strength, 0)
        for ent in item.technical_entities:
            entity_scores[ent] = entity_scores.get(ent, 0) + weight
            entity_counts[ent] = entity_counts.get(ent, 0) + item.occurrence_count
            
    # Sort top entities
    sorted_entities = sorted(
        entity_scores.keys(),
        key=lambda x: (-entity_scores[x], -entity_counts[x], x)
    )
    top_entities = sorted_entities[:10]
    
    # 5. Type and Strength Counts
    type_counts: Dict[str, int] = {}
    strength_counts: Dict[str, int] = {
        "CRITICAL": 0,
        "STRONG": 0,
        "SUPPORTING": 0,
        "WEAK": 0,
        "IGNORE": 0
    }
    
    for item in final_items:
        type_counts[item.evidence_type] = type_counts.get(item.evidence_type, 0) + 1
        strength_counts[item.strength] = strength_counts.get(item.strength, 0) + 1
        
    duration_ms = (time.perf_counter() - start_time) * 1000.0
    
    return TechnicalEvidenceResult(
        items=final_items,
        evidence_type_counts=type_counts,
        strength_counts=strength_counts,
        top_technical_entities=top_entities,
        duplicate_count=duplicate_count,
        extraction_ms=duration_ms
    )
