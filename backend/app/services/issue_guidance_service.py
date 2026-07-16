import json
import logging
import time
import re
import os
from typing import Any, Dict, List, Tuple, Optional
from dataclasses import dataclass, field

from app.schema.issue_guidance import IssueGuidanceInput, IssueGuidanceOutput
from app.services.llm_service import LLMGenerationError, LLMService
from app.utils.file_ranking import score_file, get_candidate_files, infer_issue_category, extract_keywords, get_path_category
from constants import ENABLE_PERF_DIAGNOSTICS
from app.utils.performance_utils import estimate_tokens
from app.utils.evidence_extractor import TechnicalEvidenceItem, extract_technical_evidence
from app.utils.classification_reconciler import reconcile_issue_classification, ClassificationReconciliationResult
from app.utils.context_budgeter import budget_and_assemble_prompt, BudgetedPromptContext

logger = logging.getLogger(__name__)

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

COMPRESSED_GUIDANCE_PROMPT_INSTRUCTIONS = """Instructions for generating each JSON field:
1. "analysis":
   - "beginner_explanation": Explain the issue simply for a beginner. Treat PROTECTED TECHNICAL EVIDENCE as higher authority than generic repository descriptions.
   - "skills_required": List of required skills (e.g. Python, React).
   - "affected_area": Module or layout area affected.
   - "difficulty": Must be "Beginner", "Intermediate", or "Advanced".
   - "confidence_score": Confidence score from 0 to 100.
2. "exploration_hints":
   - "affected_area": Module or layout area affected.
   - "likely_directories": Most likely directories (CRITICAL: Must be selected from Candidate Directories).
   - "possible_files": Possible files to explore (CRITICAL: Prefer files marked with PRIMARY or SECONDARY investigation priority. Align exploration hints with the provided file relationship order. Never invent or guess file names).
   - "reasoning": Explain why these are relevant.
   - "confidence": Confidence score from 0 to 100."""

COMPRESSED_GUIDANCE_PROMPT_SCHEMA = """{{
  "analysis": {{
    "beginner_explanation": "String",
    "skills_required": ["String", "String"],
    "affected_area": "String",
    "difficulty": "Beginner | Intermediate | Advanced",
    "confidence_score": Integer
  }},
  "exploration_hints": {{
    "affected_area": "String",
    "likely_directories": ["String", "String"],
    "possible_files": ["String", "String"],
    "reasoning": "String",
    "confidence": Integer
  }}
}}"""

# Keep old constant for backward compatibility
COMPRESSED_GUIDANCE_PROMPT = COMPRESSED_GUIDANCE_PROMPT_TEMPLATE

# Cache imports
from app.core.cache.dependencies import get_cache_manager
from app.core.cache.manager import CacheManager
from app.core.cache.keys import get_issue_guidance_key
from app.core.cache.config import CACHE_TTL_ISSUE_GUIDANCE

# ----------------------------------------------------------------------
# Internal Data Contracts (Stage 12.1 Internal Data Structures)
# ----------------------------------------------------------------------

@dataclass
class IssueIntelligence:
    category: str
    intent: str
    subsystem: str
    technologies: List[str]
    keywords: List[str]
    difficulty: str
    implementation_hints: List[str]

@dataclass
class IssueEvidence:
    evidence: List[str] = field(default_factory=list)
    matched_labels: List[str] = field(default_factory=list)
    matched_keywords: List[str] = field(default_factory=list)
    detected_stack: List[str] = field(default_factory=list)
    explicit_paths: List[str] = field(default_factory=list)
    
    # Stage 12.2.1 Conformed Type Annotations
    technical_evidence: List[TechnicalEvidenceItem] = field(default_factory=list)
    critical_evidence: List[TechnicalEvidenceItem] = field(default_factory=list)
    strong_evidence: List[TechnicalEvidenceItem] = field(default_factory=list)
    supporting_evidence: List[TechnicalEvidenceItem] = field(default_factory=list)
    weak_evidence: List[TechnicalEvidenceItem] = field(default_factory=list)
    ignored_evidence: List[TechnicalEvidenceItem] = field(default_factory=list)
    evidence_type_counts: Dict[str, int] = field(default_factory=dict)
    strength_counts: Dict[str, int] = field(default_factory=dict)
    top_technical_entities: List[str] = field(default_factory=list)
    technical_evidence_capture_status: str = "NOT_OBSERVED"
    reconciliation_result: Optional[ClassificationReconciliationResult] = None

@dataclass
class RepositoryContext:
    relevant_summary: str
    relevant_technologies: List[str]
    architectural_notes: str
    relevant_directories: List[str]
    relevant_modules: List[str]
    repository_purpose: str = ""
    beginner_summary: str = ""
    relevant_concepts: List[str] = field(default_factory=list)
    target_users: str = ""
    difficulty_level: str = ""
    estimated_learning_time: str = ""
    first_steps: List[str] = field(default_factory=list)
    relevant_structures: str = ""

@dataclass
class CandidateEvidence:
    candidates: List[Dict[str, Any]]

# ----------------------------------------------------------------------
# Compression Helper Functions
# ----------------------------------------------------------------------

def compress_markdown(text: str, keep_keywords: list, remove_keywords: list) -> str:
    """Perform semantic compression on markdown files (README / CONTRIBUTING)."""
    if not text:
        return ""
    
    # 1. Strip HTML comments/tags
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    
    # 2. Omit large code blocks
    def code_replacer(match):
        code_content = match.group(2)
        if len(code_content.splitlines()) > 5 or len(code_content) > 200:
            return "```\n[Code block omitted for brevity]\n```"
        return match.group(0)
    
    text = re.sub(r"```(python|javascript|typescript|bash|sh|json|yaml|yml|html|css)?\n(.*?)\n```", code_replacer, text, flags=re.DOTALL | re.IGNORECASE)
    
    # 3. Split by headers
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
        
    # 4. Filter sections
    filtered_sections = []
    for header, content in sections:
        header_lower = header.lower()
        if any(kw in header_lower for kw in remove_keywords):
            continue
        if keep_keywords:
            if "intro" in header_lower or header == "Intro" or any(kw in header_lower for kw in keep_keywords):
                filtered_sections.append(f"{header}\n{content}")
        else:
            filtered_sections.append(f"{header}\n{content}")
            
    return "\n\n".join(filtered_sections)

def compress_comments(comments: list) -> str:
    """Clean and filter issue comments to preserve only useful telemetry."""
    if not comments:
        return "None"
        
    cleaned_comments = []
    discard_patterns = [
        r"^\s*\+1\s*$",
        r"^\s*thanks\s*$",
        r"^\s*thank you\s*$",
        r"^\s*me too\s*$",
        r"^\s*lgtm\s*$",
        r"^\s*:+1:\s*$",
        r"^\s*bump\s*$"
    ]
    
    for c in comments:
        body = c.get("body", "")
        if not body:
            continue
            
        body_lower = body.strip().lower()
        if any(re.match(p, body_lower) for p in discard_patterns):
            continue
            
        if len(body_lower) < 10 and not any(char.isalnum() for char in body_lower):
            continue
            
        author = c.get("author") or c.get("user", {}).get("login", "User")
        cleaned_body = body[:300].strip() + ("..." if len(body) > 300 else "")
        cleaned_comments.append(f"@{author}: {cleaned_body}")
        
    if not cleaned_comments:
        return "None"
        
    return "\n".join(cleaned_comments)

# ----------------------------------------------------------------------
# Issue Guidance Service
# ----------------------------------------------------------------------

class IssueGuidanceService:
    """Analyze GitHub issues and generate exploration hints in a single LLM request."""

    def __init__(
        self,
        llm_service: LLMService | None = None,
        cache_manager: CacheManager | None = None
    ) -> None:
        self.llm_service = llm_service or LLMService()
        self.cache_manager = cache_manager or get_cache_manager()

    # ----------------------------------------------------------------------
    # Stage 1: Issue Understanding & Stage 2: Issue Evidence
    # ----------------------------------------------------------------------
    def _understand_issue(self, title: str, body: str, labels: List[str], comments: List[Dict[str, Any]]) -> Tuple[IssueIntelligence, IssueEvidence]:
        """Stage 1 & 2: Understand the issue deterministically and generate structured evidence.
        
        Analyzes the title, labels, body, and comments to extract issue intent, subsystem,
        category, technologies, keywords, difficulty, implementation hints, and supporting evidence.
        """
        evidence_list = []
        matched_labels = []
        matched_keywords = []
        detected_stack = []
        explicit_paths = []
        
        # Normalize labels
        labels_lower = [l.lower().strip() for l in labels]
        
        # 1. Category and Subsystem inference
        category = infer_issue_category(title, "", labels)
        if not category:
            # Fallback checks in body/comments
            full_text = (title + " " + body).lower()
            if any(w in full_text for w in ["frontend", "ui", "react", "css", "html", "style"]):
                category = "frontend"
                evidence_list.append("Inferred category 'frontend' from body keyword matches.")
            elif any(w in full_text for w in ["backend", "server", "api", "db", "database", "sql"]):
                category = "backend"
                evidence_list.append("Inferred category 'backend' from body keyword matches.")
            elif "test" in full_text:
                category = "tests"
                evidence_list.append("Inferred category 'tests' from 'test' keywords in body.")
            else:
                category = "backend" # Default fallback
                evidence_list.append("Defaulted category to 'backend'.")
        else:
            evidence_list.append(f"Category '{category}' inferred by label/title matching.")

        subsystem = category # Align subsystem with category
        
        # 2. Intent inference
        intent = "general maintenance"
        bug_keywords = ["bug", "fault", "error", "defect", "fail", "crash", "broken", "unable", "cannot", "prevent", "issue"]
        feat_keywords = ["feature", "addition", "enhancement", "proposal", "request", "add", "new", "implement", "support", "create", "introduce"]
        docs_keywords = ["docs", "documentation", "readme", "comment", "doc"]
        setup_keywords = ["setup", "install", "config", "docker", "ci", "cd", "workflow", "pipeline", "dockerfile", "github actions"]

        text_to_search = (title + " " + body + " " + " ".join(labels_lower)).lower()
        
        has_bug_label = any(any(bk in lbl for bk in ["bug", "error", "defect", "fail"]) for lbl in labels_lower)
        has_feat_label = any(any(fk in lbl for fk in ["feature", "enhancement", "proposal"]) for lbl in labels_lower)
        has_docs_label = any(any(dk in lbl for dk in ["docs", "documentation"]) for lbl in labels_lower)
        has_setup_label = any(any(sk in lbl for sk in ["setup", "config", "docker", "ci", "cd"]) for lbl in labels_lower)

        if has_bug_label or any(bk in text_to_search for bk in bug_keywords):
            intent = "bug fix"
            evidence_list.append("Intent 'bug fix' detected from label/text analysis.")
            if has_bug_label:
                matched_labels.append("bug/error related label")
        elif has_feat_label or any(fk in text_to_search for fk in feat_keywords):
            intent = "feature enhancement"
            evidence_list.append("Intent 'feature enhancement' detected from label/text analysis.")
            if has_feat_label:
                matched_labels.append("feature/enhancement related label")
        elif has_docs_label or any(dk in text_to_search for dk in docs_keywords):
            intent = "documentation"
            evidence_list.append("Intent 'documentation' detected from label/text analysis.")
            if has_docs_label:
                matched_labels.append("docs related label")
        elif has_setup_label or any(sk in text_to_search for sk in setup_keywords):
            intent = "setup configuration"
            evidence_list.append("Intent 'setup configuration' detected from label/text analysis.")
            if has_setup_label:
                matched_labels.append("setup/config related label")
        else:
            evidence_list.append("Defaulted intent to 'general maintenance'.")

        # 3. Technologies Match
        tech_map = {
            "python": "Python",
            "javascript": "JavaScript",
            "typescript": "TypeScript",
            "react": "React",
            "html": "HTML",
            "css": "CSS",
            "docker": "Docker",
            "sql": "SQL",
            "postgres": "PostgreSQL",
            "redis": "Redis",
            "go": "Go",
            "golang": "Go",
            "rust": "Rust",
            "bash": "Bash",
            "shell": "Shell",
            "yaml": "YAML",
            "toml": "TOML",
            "json": "JSON"
        }
        detected_techs = set()
        for t_key, t_val in tech_map.items():
            pattern = r'\b' + re.escape(t_key) + r'\b'
            if re.search(pattern, text_to_search):
                detected_techs.add(t_val)
                matched_keywords.append(t_key)
                
        technologies = sorted(list(detected_techs))
        if technologies:
            evidence_list.append(f"Matched technologies: {', '.join(technologies)}.")
        else:
            evidence_list.append("No explicit technology matches found.")

        # 4. Keywords
        keywords = extract_keywords(title)
        
        # 5. Difficulty signals
        difficulty = "Beginner"
        beginner_indicators = ["good first issue", "beginner", "easy", "starter", "help wanted"]
        intermediate_indicators = ["intermediate", "medium", "moderate"]
        advanced_indicators = ["advanced", "hard", "difficult", "complex"]
        
        if any(any(ind in lbl for ind in advanced_indicators) for lbl in labels_lower) or any(ind in text_to_search for ind in advanced_indicators):
            difficulty = "Advanced"
            evidence_list.append("Difficulty 'Advanced' detected from advanced keywords.")
        elif any(any(ind in lbl for ind in intermediate_indicators) for lbl in labels_lower) or any(ind in text_to_search for ind in intermediate_indicators):
            difficulty = "Intermediate"
            evidence_list.append("Difficulty 'Intermediate' detected from intermediate keywords.")
        else:
            evidence_list.append("Difficulty defaulted to 'Beginner'.")

        # 6. Explicit file/directory references
        # Find path-like strings in body and comments
        path_regex = r'\b[a-zA-Z0-9_\-\./]+\.[a-zA-Z0-9_\-]{2,4}\b'
        for text_block in [body] + [c.get("body", "") for c in comments]:
            matches = re.findall(path_regex, text_block)
            for m in matches:
                # filter out false positives like numbers or versions (e.g. 1.0, v1.2)
                if not re.match(r'^\d+\.\d+$', m) and ('/' in m or m.endswith(('.py', '.ts', '.tsx', '.js', '.jsx', '.json', '.yml', '.yaml', '.md', '.css', '.html', '.sh'))):
                    explicit_paths.append(m)
        explicit_paths = sorted(list(set(explicit_paths)))
        if explicit_paths:
            evidence_list.append(f"Found explicit path references: {', '.join(explicit_paths)}.")

        # 7. Stack traces / Error messages
        traceback_indicators = [
            r"Traceback \(most recent call last\):",
            r"\bTypeError\b",
            r"\bValueError\b",
            r"\bKeyError\b",
            r"\bAttributeError\b",
            r"\bRuntimeError\b",
            r"\bException\b",
            r"\bIndexError\b",
            r"\bImportError\b",
            r"\bModuleNotFoundError\b"
        ]
        for indicator in traceback_indicators:
            if re.search(indicator, body, re.IGNORECASE):
                detected_stack.append(indicator.replace(r"\b", "").replace(r"\(most recent call last\):", ""))
        if detected_stack:
            evidence_list.append(f"Detected stack trace / error markers: {', '.join(detected_stack)}.")

        # 8. Implementation hints
        # Extract backticked code snippets and sentences with verbs
        impl_hints = []
        code_snippets = re.findall(r'`([^`]+)`', body)
        for c_snap in code_snippets:
            if len(c_snap) > 3 and len(c_snap) < 100:
                impl_hints.append(f"Code mention: `{c_snap}`")
                
        # Split body into sentences and search for action verbs
        sentences = re.split(r'\. |\n', body)
        action_indicators = ["should", "need to", "please", "make sure", "fix", "implement", "update", "modify", "remove", "change"]
        for sent in sentences:
            sent_clean = sent.strip()
            if len(sent_clean) > 15 and len(sent_clean) < 150:
                if any(f" {act} " in f" {sent_clean.lower()} " for act in action_indicators):
                    impl_hints.append(sent_clean)
                    
        impl_hints = impl_hints[:10] # limit count to avoid overflow
        
        intel = IssueIntelligence(
            category=category,
            intent=intent,
            subsystem=subsystem,
            technologies=technologies,
            keywords=keywords,
            difficulty=difficulty,
            implementation_hints=impl_hints
        )
        
        evid = IssueEvidence(
            evidence=evidence_list,
            matched_labels=matched_labels,
            matched_keywords=matched_keywords,
            detected_stack=detected_stack,
            explicit_paths=explicit_paths
        )
        
        # Stage 12.2.1 Extraction call with narrow failure fallback boundary
        try:
            res = extract_technical_evidence(title, body, labels, comments)
            evid.technical_evidence = res.items
            evid.critical_evidence = [x for x in res.items if x.strength == "CRITICAL"]
            evid.strong_evidence = [x for x in res.items if x.strength == "STRONG"]
            evid.supporting_evidence = [x for x in res.items if x.strength == "SUPPORTING"]
            evid.weak_evidence = [x for x in res.items if x.strength == "WEAK"]
            evid.ignored_evidence = [x for x in res.items if x.strength == "IGNORE"]
            evid.evidence_type_counts = res.evidence_type_counts
            evid.strength_counts = res.strength_counts
            evid.top_technical_entities = res.top_technical_entities
            evid.technical_evidence_capture_status = "EMPTY" if not res.items else "CAPTURED"
            
            logger.info("[IssueGuidance][Evidence] issue=%s total=%d critical=%d strong=%d supporting=%d weak=%d ignored=%d", 
                        title[:20], len(res.items), len(evid.critical_evidence), len(evid.strong_evidence), 
                        len(evid.supporting_evidence), len(evid.weak_evidence), len(evid.ignored_evidence))
            logger.info("[IssueGuidance][Evidence] issue=%s types=%s", title[:20], res.evidence_type_counts)
            logger.info("[IssueGuidance][Evidence] issue=%s top_entities=%s", title[:20], res.top_technical_entities)
        except Exception as exc:
            logger.exception("Failed to extract technical evidence for issue %s: %s", title[:20], exc)
            # Default empty collections
            evid.technical_evidence = []
            evid.critical_evidence = []
            evid.strong_evidence = []
            evid.supporting_evidence = []
            evid.weak_evidence = []
            evid.ignored_evidence = []
            evid.evidence_type_counts = {}
            evid.strength_counts = {}
            evid.top_technical_entities = []
            evid.technical_evidence_capture_status = "EXTRACTION_FAILED"
            
        # Stage 12.2.2 Classification Reconciliation with narrow safety fallback
        try:
            recon_res = reconcile_issue_classification(intel, evid)
            evid.reconciliation_result = recon_res
            # Override original intelligence values for downstream pipelines
            intel.category = recon_res.resolved_category
            intel.subsystem = recon_res.resolved_subsystem
            logger.info("[IssueGuidance][Reconciliation] original=%s/%s resolved=%s/%s decision=%s score=%.1f",
                        recon_res.original_category, recon_res.original_subsystem,
                        recon_res.resolved_category, recon_res.resolved_subsystem,
                        recon_res.decision, recon_res.confidence_score)
        except Exception as exc:
            logger.exception("Classification reconciliation failed: %s", exc)
            evid.reconciliation_result = None
            
        return intel, evid

    # ----------------------------------------------------------------------
    # Stage 3: Repository Context Extraction
    # ----------------------------------------------------------------------
    def _extract_repository_context(self, repo_summary: Dict[str, Any], repository_map: Dict[str, Any], issue_intel: IssueIntelligence) -> RepositoryContext:
        """Stage 3: Extract focused repository context relevant to the current issue.
        
        Selects only the summary parts, tech stack, key concepts, and map categories
        that match the issue's category and technology keywords.
        """
        summary_section = repo_summary.get("summary", {}) if "summary" in repo_summary else repo_summary
        if not isinstance(summary_section, dict):
            summary_section = repo_summary

        purpose = summary_section.get("repository_purpose", "")
        if not purpose or purpose == "No purpose description available.":
            purpose = "No purpose description available."
            
        beginner_friendly = summary_section.get("beginner_friendly_summary", "")
        if not beginner_friendly or beginner_friendly == "No beginner friendly summary available.":
            beginner_friendly = "No beginner friendly summary available."

        relevant_summary = f"Purpose: {purpose}\nBeginner Summary: {beginner_friendly}"
        
        # Technology matching
        repo_stack = summary_section.get("tech_stack", [])
        if not isinstance(repo_stack, list):
            repo_stack = []
        issue_techs_lower = [t.lower() for t in issue_intel.technologies]
        relevant_techs = [tech for tech in repo_stack if tech.lower() in issue_techs_lower]
        if not relevant_techs:
            relevant_techs = repo_stack[:5] # Fallback to top 5 stack items
            
        # Concepts matching
        concepts = summary_section.get("key_concepts", [])
        if not isinstance(concepts, list):
            concepts = []
        relevant_concepts = []
        issue_kws = [k.lower() for k in issue_intel.keywords]
        for c in concepts:
            if any(kw in c.lower() for kw in issue_kws) or any(t.lower() in c.lower() for t in issue_intel.technologies):
                relevant_concepts.append(c)
        if not relevant_concepts:
            relevant_concepts = concepts[:3] # Fallback to top 3 concepts
            
        # Category/Subsystem map selection
        relevant_map = {}
        category = issue_intel.category
        
        # Priority mapping
        category_priorities = {
            "frontend": ["frontend", "tests", "config", "docs"],
            "backend": ["backend", "tests", "config", "docs"],
            "tests": ["tests", "backend", "frontend"],
            "docs": ["docs", "other"],
            "config": ["config", "scripts", "backend"],
            "scripts": ["scripts", "config", "backend"],
            "other": ["other", "backend", "frontend"]
        }
        
        target_categories = category_priorities.get(category, ["backend", "frontend", "tests", "docs", "config", "scripts", "other"])
        
        relevant_directories = []
        relevant_modules = []
        for cat in target_categories:
            paths = repository_map.get(cat, [])
            if paths:
                relevant_map[cat] = paths
                relevant_directories.extend(paths)
                relevant_modules.append(cat)
                
        # Internal Directory Roles signal (Component 4 V2)
        relevant_structures = ""
        try:
            from app.utils.directory_roles import detect_directory_roles
            structural_roles = detect_directory_roles(relevant_directories[:15])
            role_lines = []
            for sr in structural_roles:
                role_lines.append(f"- Directory `{sr['path']}` acts as: {', '.join(sr['roles'])} (Evidence: {', '.join(sr['evidence'])})")
            relevant_structures = "\n".join(role_lines)
        except Exception as e:
            logger.warning("Failed to run detect_directory_roles: %s", e)
            
        return RepositoryContext(
            relevant_summary=relevant_summary,
            relevant_technologies=relevant_techs,
            architectural_notes="; ".join(relevant_concepts),
            relevant_directories=relevant_directories,
            relevant_modules=relevant_modules,
            repository_purpose=purpose,
            beginner_summary=beginner_friendly,
            relevant_concepts=relevant_concepts,
            target_users=summary_section.get("target_users", ""),
            difficulty_level=summary_section.get("difficulty_level", ""),
            estimated_learning_time=summary_section.get("estimated_learning_time", ""),
            first_steps=summary_section.get("first_steps", []),
            relevant_structures=relevant_structures
        )

    # ----------------------------------------------------------------------
    # Stage 4: Candidate Ranking & Stage 5: Candidate Evidence
    # ----------------------------------------------------------------------
    def _rank_candidates(self, all_files: List[str], repository_map: Dict[str, Any], issue_intel: IssueIntelligence, title: str, labels: List[str], explicit_paths: List[str] = None) -> CandidateEvidence:
        """Stage 4 & 5: Score, rank, and extract structured candidate evidence.
        
        Computes relevance scores for candidate files and formats the top candidates
        with detailed category, keyword, technology, and path evidence.
        """
        candidate_files_list = get_candidate_files(all_files, repository_map)
        scored_candidates = []
        
        for f in candidate_files_list:
            score, reasons = score_file(f, title, issue_intel.subsystem, labels, explicit_paths=explicit_paths)
            
            # Additional enrichment
            f_lower = f.lower()
            depth = len(f.split("/"))
            cat = get_path_category(f)
            
            matched_techs = [tech for tech in issue_intel.technologies if tech.lower() in f_lower]
            matched_kws = [kw for kw in issue_intel.keywords if kw.lower() in f_lower]
            subsystem_match = "Yes" if cat == issue_intel.subsystem else "No"
            
            explanation_parts = []
            if subsystem_match == "Yes":
                explanation_parts.append(f"belongs to target subsystem '{issue_intel.subsystem}'")
            if matched_techs:
                explanation_parts.append(f"matches technology {', '.join(matched_techs)}")
            if matched_kws:
                explanation_parts.append(f"matches keyword(s) {', '.join(matched_kws)}")
            
            if explanation_parts:
                explanation = "This file " + " and ".join(explanation_parts) + "."
            else:
                explanation = f"Matched file in candidate directory at depth {depth}."
                
            scored_candidates.append({
                "path": f,
                "score": score,
                "subsystem_match": subsystem_match,
                "technology_match": matched_techs,
                "keyword_match": matched_kws,
                "category": cat,
                "depth": depth,
                "reasons": reasons,
                "explanation": explanation
            })
            
        # Sort candidates: score DESC, depth ASC, path ASC
        scored_candidates.sort(key=lambda x: (-x["score"], x["depth"], x["path"]))
        
        # Limit to top 25
        top_candidates = scored_candidates[:25]
        
        return CandidateEvidence(candidates=top_candidates)

    # ----------------------------------------------------------------------
    # Stage 6: Prompt Assembly Helper
    # ----------------------------------------------------------------------
    def _assemble_prompt(
        self,
        repo_name: str,
        repo_desc: str,
        repo_context: RepositoryContext,
        candidate_evidence: CandidateEvidence,
        candidate_dirs: List[str],
        issue_intel: IssueIntelligence,
        issue_evidence: IssueEvidence,
        readme_raw: str,
        contributing_raw: str,
        issue_body: str,
        issue_labels_str: str,
        comments: List[Dict[str, Any]],
        instructions_text: str,
        json_schema_text: str,
        include_map: bool,
        include_comments: bool,
        compress_readme: bool,
        compress_contributing: bool,
        include_readme: bool,
        include_contributing: bool
    ) -> str:
        """Stage 6: Assemble a clean, high information density prompt using structured intelligence."""
        
        # 1. Format Repository Summary Context
        summary_text = (
            f"Repository Purpose:\n{repo_context.relevant_summary}\n\n"
            f"Relevant Technologies: {', '.join(repo_context.relevant_technologies)}\n"
            f"Architectural Concepts: {repo_context.architectural_notes}"
        )
        if getattr(repo_context, "relevant_structures", ""):
            summary_text += f"\n\nInternal Directory Roles & Structure:\n{repo_context.relevant_structures}"
        
        # 2. Format Repository Map / Candidate Files Evidence
        if include_map:
            candidate_files_text = "\n".join(
                f"- File: '{c['path']}' (Score: {c['score']}) - Reason: {c['explanation']}"
                for c in candidate_evidence.candidates[:15] # Keep top 15 in the prompt to prevent bloat
            )
            map_text = (
                f"Candidate Directories:\n{json.dumps(candidate_dirs, ensure_ascii=False)}\n\n"
                f"Candidate Files & Evidence:\n{candidate_files_text}\n"
            )
        else:
            map_text = ""

        # 3. Format README Context
        if include_readme:
            if compress_readme:
                readme_excerpt = compress_markdown(
                    readme_raw,
                    keep_keywords=["setup", "install", "getting started", "quick start", "contrib", "build", "run"],
                    remove_keywords=["example", "demo", "tutorial", "license", "changelog", "history", "roadmap", "status", "badge", "sponsors", "sponsorship"]
                )
            else:
                readme_excerpt = readme_raw[:2500]
            readme_text = f"Relevant README Context:\n{readme_excerpt}\n" if readme_excerpt else ""
        else:
            readme_text = ""

        # 4. Format CONTRIBUTING Context
        if include_contributing:
            if compress_contributing:
                contributing_excerpt = compress_markdown(
                    contributing_raw,
                    keep_keywords=["workflow", "pull request", "pr", "test", "lint", "style", "standard", "guide"],
                    remove_keywords=["history", "notes", "example", "tutorial", "sponsorship", "thanks"]
                )
            else:
                contributing_excerpt = contributing_raw[:1500]
            contributing_text = f"Relevant CONTRIBUTING Context:\n{contributing_excerpt}\n" if contributing_excerpt else ""
        else:
            contributing_text = ""

        # 5. Format Issue Understanding & Description
        issue_body_truncated = issue_body
        if len(issue_body_truncated) > 1500:
            issue_body_truncated = issue_body_truncated[:1500] + "\n[Body truncated for length]"

        hints_text = "\n".join(f"- {h}" for h in issue_intel.implementation_hints) if issue_intel.implementation_hints else "None"
        
        body_text = (
            f"ISSUE UNDERSTANDING:\n"
            f"Category: {issue_intel.category}\n"
            f"Intent: {issue_intel.intent}\n"
            f"Difficulty: {issue_intel.difficulty}\n"
            f"Likely Subsystem: {issue_intel.subsystem}\n\n"
            f"Detected Keywords: {', '.join(issue_intel.keywords)}\n"
            f"Implementation Hints:\n{hints_text}\n\n"
            f"ISSUE DESCRIPTION:\n{issue_body_truncated}\n"
        )

        # 6. Format Comments & Issue Analysis Evidence
        if include_comments and comments:
            compressed_comments = compress_comments(comments)
            evidence_text = "\n".join(f"- {ev}" for ev in issue_evidence.evidence)
            
            comments_text = (
                f"Comments:\n{compressed_comments}\n\n"
                f"ISSUE ANALYSIS EVIDENCE:\n{evidence_text}\n"
            )
            if issue_evidence.detected_stack:
                comments_text += f"Detected stack trace error: {', '.join(issue_evidence.detected_stack)}\n"
            if issue_evidence.explicit_paths:
                comments_text += f"Explicit path references: {', '.join(issue_evidence.explicit_paths)}\n"
        else:
            comments_text = ""

        # Assemble final template
        prompt = COMPRESSED_GUIDANCE_PROMPT_TEMPLATE.format(
            repo_name=repo_name,
            repo_desc=repo_desc,
            repo_summary=summary_text,
            repository_map=map_text,
            readme=readme_text,
            contributing=contributing_text,
            title=issue_intel.keywords[0] if issue_intel.keywords else "Issue",
            labels=issue_labels_str,
            body=body_text,
            comments=comments_text,
            instructions=instructions_text,
            json_schema=json_schema_text
        )
        
        return prompt

    # ----------------------------------------------------------------------
    # Stage 9: Grounding Validation
    # ----------------------------------------------------------------------
    def _ground_and_validate_guidance(
        self,
        response: Dict[str, Any],
        all_files: List[str],
        all_dirs: List[str],
        candidate_evidence: CandidateEvidence,
        issue_intel: IssueIntelligence
    ) -> Dict[str, Any]:
        """Stage 9: Ground and validate all LLM suggestions against codebase reality.
        
        Prunes hallucinated file/directory paths, aligns affected areas, validates 
        suggested skills, and adjusts confidence metrics based on evidence strength.
        """
        full_files_set = set(all_files)
        full_dirs_set = set(all_dirs)
        
        analysis = response.get("analysis", {})
        hints = response.get("exploration_hints", {})
        
        pruned_files_count = 0
        pruned_dirs_count = 0
        
        if full_files_set or full_dirs_set:
            # Validate directories
            original_dirs = hints.get("likely_directories", [])
            valid_dirs = [d for d in original_dirs if d in full_dirs_set]
            pruned_dirs_count = len(original_dirs) - len(valid_dirs)
            hints["likely_directories"] = valid_dirs
            
            # Validate files
            original_files = hints.get("possible_files", [])
            valid_files = [f for f in original_files if f in full_files_set]
            pruned_files_count = len(original_files) - len(valid_files)
            hints["possible_files"] = valid_files
            
        # Adjust confidence scores based on validation pruning penalties
        penalty = (pruned_files_count * 15) + (pruned_dirs_count * 15)
        
        # Also adjust based on candidate scoring evidence:
        # If the top candidate score is very low (e.g. < 50), penalize confidence
        top_score = 0
        if candidate_evidence.candidates:
            top_score = candidate_evidence.candidates[0]["score"]
            
        if top_score < 50:
            penalty += 10
        elif top_score < 30:
            penalty += 20
            
        if penalty > 0:
            analysis["confidence_score"] = max(20, analysis.get("confidence_score", 50) - penalty)
            hints["confidence"] = max(20, hints.get("confidence", 50) - penalty)
            logger.info("Reduced confidence due to grounding penalties (files/dirs pruned or low candidate score). New confidence: %d", hints["confidence"])

        # Ground technologies / skills
        skills = analysis.get("skills_required", [])
        if skills:
            # Let's filter out non-string/empty entries
            skills = [s.strip() for s in skills if isinstance(s, str) and s.strip()]
            analysis["skills_required"] = skills
            
        # Ground affected area to the likely subsystem if it's too generic
        generic_areas = {"unknown", "general", "general codebase", "n/a", "none", ""}
        if analysis.get("affected_area", "").lower() in generic_areas:
            analysis["affected_area"] = issue_intel.subsystem
        if hints.get("affected_area", "").lower() in generic_areas:
            hints["affected_area"] = issue_intel.subsystem
            
        response["analysis"] = analysis
        response["exploration_hints"] = hints
        return response

    # ----------------------------------------------------------------------
    # Heuristic Fallback Generator
    # ----------------------------------------------------------------------
    def _generate_graceful_fallback(
        self,
        issue_title: str,
        issue_labels: List[str],
        metadata: Dict[str, Any],
        top_candidates: List[str],
        candidate_dirs: List[str]
    ) -> Dict[str, Any]:
        """Generate a deterministic default analysis when LLM call is bypassed or fails."""
        difficulty = "Beginner"
        labels_lower = [l.lower() for l in issue_labels]
        if "advanced" in labels_lower or "hard" in labels_lower:
            difficulty = "Advanced"
        elif "intermediate" in labels_lower or "medium" in labels_lower:
            difficulty = "Intermediate"
            
        skills = []
        lang = metadata.get("language")
        if lang:
            skills.append(lang)
        for l in labels_lower:
            if "python" in l:
                skills.append("Python")
            elif "react" in l:
                skills.append("React")
            elif "typescript" in l:
                skills.append("TypeScript")
            elif "javascript" in l:
                skills.append("JavaScript")
            elif "css" in l:
                skills.append("CSS")
        if not skills:
            skills = ["General Codebase Concepts"]
        else:
            skills = list(set(skills))
            
        affected_area = "General Codebase"
        for l in labels_lower:
            if "bug" in l:
                affected_area = "Bug Fix / Troubleshooting"
            elif "feature" in l:
                affected_area = "Feature Request / Enhancement"
            elif "docs" in l or "documentation" in l:
                affected_area = "Documentation"
                
        beginner_explanation = (
            f"This issue relates to the title: '{issue_title}'. "
            f"It is classified as a '{difficulty}' difficulty task and targets the '{affected_area}' module. "
            "You can resolve it by setting up the local environment and investigating the suggested paths."
        )
        
        fallback_possible_files = top_candidates[:3] if top_candidates else ["README.md"]
        fallback_likely_dirs = candidate_dirs[:2] if candidate_dirs else ["."]
        reasoning = (
            f"These codebase locations were identified based on keyword matching with the issue title "
            f"and labels: {', '.join(issue_labels) if issue_labels else 'None'}."
        )
        
        fallback_data = {
            "analysis": {
                "difficulty": difficulty,
                "skills_required": skills,
                "affected_area": affected_area,
                "beginner_explanation": beginner_explanation,
                "confidence_score": 50
            },
            "exploration_hints": {
                "affected_area": affected_area,
                "likely_directories": fallback_likely_dirs,
                "possible_files": fallback_possible_files,
                "reasoning": reasoning,
                "confidence": 50
            }
        }
        
        val_guidance = IssueGuidanceOutput.model_validate(fallback_data)
        return val_guidance.model_dump()

    # ----------------------------------------------------------------------
    # Normalizer Helper Function (Stage 8)
    # ----------------------------------------------------------------------
    def normalize_guidance_response(self, data: Dict[str, Any], fallback_affected_area: str = "Unknown Area") -> Dict[str, Any]:
        """Repairs common schema deviations before Pydantic validation."""
        # Normalize the "analysis" sub-object
        analysis = data.get("analysis", {})
        if not isinstance(analysis, dict):
            analysis = {}
            data["analysis"] = analysis
            
        if "beginner_explanation" not in analysis:
            if "explanation" in analysis:
                analysis["beginner_explanation"] = analysis.pop("explanation")
            elif "beginner_friendly_explanation" in analysis:
                analysis["beginner_friendly_explanation"] = analysis.pop("beginner_friendly_explanation")
            else:
                analysis["beginner_explanation"] = "No explanation provided."

        if "affected_area" in analysis and isinstance(analysis["affected_area"], list):
            analysis["affected_area"] = " ".join(str(x) for x in analysis["affected_area"])
        elif "affected_area" not in analysis:
            analysis["affected_area"] = fallback_affected_area

        if "confidence_score" in analysis and isinstance(analysis["confidence_score"], str):
            score_str = analysis["confidence_score"].strip().lower()
            if score_str == "low":
                analysis["confidence_score"] = 40
            elif score_str == "medium":
                analysis["confidence_score"] = 70
            elif score_str == "high":
                analysis["confidence_score"] = 90
            else:
                analysis["confidence_score"] = 50
        elif "confidence_score" not in analysis:
            analysis["confidence_score"] = 50

        if "skills_required" not in analysis:
            analysis["skills_required"] = []
        if "difficulty" not in analysis:
            analysis["difficulty"] = "Beginner"

        # Normalize the "exploration_hints" sub-object
        hints = data.get("exploration_hints", {})
        if not isinstance(hints, dict):
            hints = {}
            data["exploration_hints"] = hints

        if "affected_area" not in hints:
            hints["affected_area"] = fallback_affected_area

        if "confidence" not in hints:
            if "confidence_score" in hints:
                hints["confidence"] = hints.pop("confidence_score")
            elif "confidenceLevel" in hints:
                hints["confidence"] = hints.pop("confidenceLevel")
            else:
                hints["confidence"] = 50

        if isinstance(hints.get("confidence"), str):
            score_str = hints["confidence"].strip().lower()
            if score_str == "low":
                hints["confidence"] = 40
            elif score_str == "medium":
                hints["confidence"] = 70
            elif score_str == "high":
                hints["confidence"] = 90
            else:
                try:
                    hints["confidence"] = int(score_str)
                except ValueError:
                    hints["confidence"] = 50
        elif "confidence" not in hints:
            hints["confidence"] = 50

        if "likely_directories" not in hints or hints["likely_directories"] is None:
            hints["likely_directories"] = []
        elif isinstance(hints["likely_directories"], str):
            hints["likely_directories"] = [hints["likely_directories"]]
            
        if "possible_files" not in hints or hints["possible_files"] is None:
            hints["possible_files"] = []
        elif isinstance(hints["possible_files"], str):
            hints["possible_files"] = [hints["possible_files"]]

        if "reasoning" not in hints:
            hints["reasoning"] = "No reasoning provided."

        return data

    # ----------------------------------------------------------------------
    # Main Entry Point (Public API - Unchanged Signature)
    # ----------------------------------------------------------------------
    def generate_guidance(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze issue and generate exploration hints in a single LLM request."""
        logger.info("Starting issue guidance generation with payload: %s", payload)
        self._last_relationship_grounding = None

        try:
            start_total = time.perf_counter()
            
            validated_payload = IssueGuidanceInput.model_validate(payload)
            issue = validated_payload.issue
            repo_summary = validated_payload.repo_summary
            repository_map = validated_payload.repository_map
            comments = validated_payload.comments
            all_files = validated_payload.all_files
            all_dirs = validated_payload.all_dirs

            # 1. Cache Read Attempt
            owner = issue.get("owner")
            repo = issue.get("repo")
            issue_number = issue.get("number")

            key = None
            cached_guidance = None
            if owner and repo and issue_number:
                try:
                    key = get_issue_guidance_key(owner, repo, issue_number)
                    cached_guidance = self.cache_manager.get(key)
                except Exception as exc:
                    if isinstance(exc, (TypeError, ValueError)):
                        raise
                    logger.warning("[CACHE] Cache check failed for key %s: %s", key or "unknown", exc)

                if cached_guidance is not None:
                    print(f"[CACHE][Issue Guidance #{issue_number}] HIT")
                    return cached_guidance
                else:
                    print(f"[CACHE][Issue Guidance #{issue_number}] MISS")

            metadata = repo_summary.get("metadata", {}) if "metadata" in repo_summary else {}
            if not metadata and owner and repo:
                try:
                    from app.services.github_service import GitHubService
                    gh = GitHubService()
                    metadata = gh.get_repo_metadata(owner, repo) or {}
                except Exception as exc:
                    logger.warning("Failed to fetch repository metadata in generate_guidance: %s", exc)
                    metadata = {}
                    
            repo_name = metadata.get("name") or repo or "Unknown Repo"
            repo_desc = metadata.get("description") or "No description"
            
            # Fetch README and CONTRIBUTING from cache to support prompt builder
            try:
                from app.services.github_service import GitHubService
                gh = GitHubService()
                readme_raw = gh.get_readme(owner, repo) or ""
                contributing_raw = gh.get_contributing(owner, repo) or ""
            except Exception:
                readme_raw = ""
                contributing_raw = ""

            issue_title = issue.get("title", "")
            issue_body = issue.get("body", "")
            issue_labels = issue.get("labels", [])
            issue_labels_str = ", ".join(issue_labels)

            # Stage 1: Issue Understanding & Stage 2: Issue Evidence
            t_stage = time.perf_counter()
            issue_intel, issue_evidence = self._understand_issue(
                title=issue_title,
                body=issue_body,
                labels=issue_labels,
                comments=comments
            )
            logger.info("Issue Understanding & Evidence generation completed in %.4fs", time.perf_counter() - t_stage)
            print("Issue Understanding & Evidence generated.")

            # Filter explicit paths to reject external GitHub URLs and parse local URLs (Component 3 V2)
            filtered_explicit = []
            if issue_evidence and issue_evidence.explicit_paths:
                for ep in issue_evidence.explicit_paths:
                    if "github.com" in ep.lower():
                        if owner and repo and f"github.com/{owner.lower()}/{repo.lower()}/" in ep.lower().replace("http://", "").replace("https://", ""):
                            url_match = re.search(r'github\.com/[^/]+/[^/]+/blob/[^/]+/(.+)', ep, re.IGNORECASE)
                            if url_match:
                                filtered_explicit.append(url_match.group(1))
                        else:
                            continue
                    else:
                        filtered_explicit.append(ep)

            # Stage 3: Repository Context Extraction
            t_stage = time.perf_counter()
            repo_context = self._extract_repository_context(
                repo_summary=repo_summary,
                repository_map=repository_map,
                issue_intel=issue_intel
            )
            logger.info("Repository Context Selected in %.4fs", time.perf_counter() - t_stage)
            print("Repository Context Selected.")

            # Stage 4: Candidate Ranking & Stage 5: Candidate Evidence
            t_stage = time.perf_counter()
            candidate_evidence = self._rank_candidates(
                all_files=all_files,
                repository_map=repository_map,
                issue_intel=issue_intel,
                title=issue_title,
                labels=issue_labels,
                explicit_paths=filtered_explicit
            )
            logger.info("Candidate Ranking Completed in %.4fs", time.perf_counter() - t_stage)
            print("Candidate Ranking Completed.")

            # STAGE 12.2.4 FILE RELATIONSHIP GROUNDING
            t_ground = time.perf_counter()
            try:
                from app.utils.file_relationship_grounder import ground_file_relationships
                relationship_grounding = ground_file_relationships(
                    all_files=all_files,
                    repository_map=repository_map,
                    candidate_evidence=candidate_evidence,
                    issue_intelligence=issue_intel,
                    issue_evidence=issue_evidence
                )
                self._last_relationship_grounding = relationship_grounding
                logger.info("File Relationship Grounding Completed in %.4fs", time.perf_counter() - t_ground)
            except Exception as exc:
                logger.exception("File relationship grounding failed: %s", exc)
                from app.utils.file_relationship_grounder import FileRelationshipGroundingResult
                self._last_relationship_grounding = FileRelationshipGroundingResult(
                    status="FALLBACK",
                    explicit_path_resolutions=[],
                    candidate_relationships=[],
                    file_relationship_edges=[],
                    investigation_order=[c["path"] for c in candidate_evidence.candidates],
                    total_candidates=len(candidate_evidence.candidates),
                    direct_relationship_count=0, strong_relationship_count=0, moderate_relationship_count=0, weak_relationship_count=0,
                    primary_count=0, secondary_count=0, supporting_count=0, low_confidence_count=len(candidate_evidence.candidates),
                    explicit_paths_available=0, explicit_paths_grounded=0, explicit_paths_ambiguous=0, explicit_paths_ungrounded=0,
                    grounding_latency_ms=(time.perf_counter() - t_ground) * 1000.0
                )
                relationship_grounding = self._last_relationship_grounding

            # Format instructions and schema
            instructions_text = COMPRESSED_GUIDANCE_PROMPT_INSTRUCTIONS
            json_schema_text = COMPRESSED_GUIDANCE_PROMPT_SCHEMA

            # Adaptive prompt builder loop
            prompt = ""
            budget_success = False
            self._last_budgeted_context = None
            
            try:
                prompt, budgeted_context = budget_and_assemble_prompt(
                    repo_name=repo_name,
                    repo_desc=repo_desc,
                    repo_context=repo_context,
                    candidate_evidence=candidate_evidence,
                    issue_intel=issue_intel,
                    issue_evidence=issue_evidence,
                    readme_raw=readme_raw,
                    contributing_raw=contributing_raw,
                    issue_body=issue_body,
                    issue_labels_str=issue_labels_str,
                    comments=comments,
                    instructions_text=instructions_text,
                    json_schema_text=json_schema_text,
                    budget_limit=1500,
                    relationship_grounding=relationship_grounding
                )
                self._last_budgeted_context = budgeted_context
                prompt_tokens = budgeted_context.estimated_tokens
                budget_success = True
                print(f"Context Budgeting Successful: Selected Mode '{budgeted_context.selected_mode}' ({prompt_tokens} tokens)")
                logger.info("Context Budgeting Selected Mode: %s (%d tokens)", budgeted_context.selected_mode, prompt_tokens)
            except Exception as budgeting_err:
                logger.exception("Context Budgeting failed, using Stage 12.2.2 fallback: %s", budgeting_err)
                print("Context Budgeting failed, using Stage 12.2.2 fallback.")
                
                from app.utils.context_budgeter import BudgetedPromptContext
                self._last_budgeted_context = BudgetedPromptContext(
                    resolved_classification=f"{issue_intel.category} / {issue_intel.subsystem}",
                    protected_evidence="",
                    explicit_paths="",
                    candidate_files="",
                    issue_context="",
                    repository_context="",
                    optional_context="",
                    included_sections=[],
                    removed_sections=[],
                    estimated_tokens=0,
                    budget_limit=1500,
                    protected_evidence_count=0,
                    candidate_file_count=0,
                    explicit_path_count=0,
                    budget_status="BUDGETING_FAILED",
                    selected_attempt=0,
                    selected_mode="FALLBACK",
                    static_template_tokens=0,
                    dynamic_context_tokens=0,
                    candidate_files_available_count=len(candidate_evidence.candidates) if candidate_evidence else 0,
                    candidate_files_included_count=0,
                    candidate_files_included=[],
                    critical_evidence_included_count=0,
                    strong_evidence_included_count=0,
                    explicit_paths_included_count=0,
                    issue_segments_included_count=0,
                    comment_segments_included_count=0,
                    protected_core_integrity_status="FAILED",
                    integrity_failures=[str(budgeting_err)],
                    emergency_core_used=False,
                    capture_status="BUDGETING_FAILED"
                )

            # Execution block
            success = False
            response = None
            
            if budget_success:
                print("Sending budgeted prompt to LLM...")
                try:
                    response = self.llm_service.generate_json(prompt, service_name="Issue Guidance")
                    success = True
                    print("Guidance Generated Successfully via Budgeted Prompt")
                except Exception as e:
                    print(f"LLM Call failed on Budgeted Prompt: {e}")
                    logger.warning("LLM Call failed on Budgeted Prompt: %s", e)
            
            # Fallback to the existing Stage 12.2.2 degradation loop if budgeting failed or LLM failed on budgeted prompt
            if not success:
                print("Falling back to Stage 12.2.2 size-driven degradation loop...")
                MAX_PROMPT_TOKENS = 1500
                attempt = 0
                top_candidates = [c["path"] for c in candidate_evidence.candidates]
                candidate_dirs = sorted(list(set(os.path.dirname(f) for f in top_candidates if os.path.dirname(f))))

                while attempt < 4 and not success:
                    attempt += 1
                    if attempt == 1:
                        include_map = True
                        include_comments = True
                        compress_readme = False
                        compress_contributing = False
                        include_readme = True
                        include_contributing = True
                    elif attempt == 2:
                        include_map = True
                        include_comments = False
                        compress_readme = False
                        compress_contributing = False
                        include_readme = True
                        include_contributing = True
                    elif attempt == 3:
                        include_map = True
                        include_comments = False
                        compress_readme = True
                        compress_contributing = True
                        include_readme = True
                        include_contributing = True
                    else: # Attempt 4
                        include_map = False
                        include_comments = False
                        compress_readme = False
                        compress_contributing = False
                        include_readme = False
                        include_contributing = False

                    t_stage = time.perf_counter()
                    prompt = self._assemble_prompt(
                        repo_name=repo_name,
                        repo_desc=repo_desc,
                        repo_context=repo_context,
                        candidate_evidence=candidate_evidence,
                        candidate_dirs=candidate_dirs,
                        issue_intel=issue_intel,
                        issue_evidence=issue_evidence,
                        readme_raw=readme_raw,
                        contributing_raw=contributing_raw,
                        issue_body=issue_body,
                        issue_labels_str=issue_labels_str,
                        comments=comments,
                        instructions_text=instructions_text,
                        json_schema_text=json_schema_text,
                        include_map=include_map,
                        include_comments=include_comments,
                        compress_readme=compress_readme,
                        compress_contributing=compress_contributing,
                        include_readme=include_readme,
                        include_contributing=include_contributing
                    )
                    prompt_tokens = estimate_tokens(prompt)
                    
                    if prompt_tokens > MAX_PROMPT_TOKENS:
                        continue
                        
                    try:
                        response = self.llm_service.generate_json(prompt, service_name="Issue Guidance")
                        success = True
                        break
                    except Exception as e:
                        logger.warning("LLM Call failed on Fallback Attempt %d: %s", attempt, e)

            # Fallback Guidance Generation if all retries failed
            if not success:
                print("All attempts failed or exceeded budget. Using Graceful Fallback.")
                top_candidates = [c["path"] for c in candidate_evidence.candidates]
                candidate_dirs = sorted(list(set(os.path.dirname(f) for f in top_candidates if os.path.dirname(f))))
                fallback_data = self._generate_graceful_fallback(
                    issue_title=issue_title,
                    issue_labels=issue_labels,
                    metadata=metadata,
                    top_candidates=top_candidates,
                    candidate_dirs=candidate_dirs
                )
                fallback_data["guidance_source"] = "fallback"
                print("Fallback Guidance Used")
                return fallback_data

            # Stage 8: Normalization
            val_start = time.perf_counter()
            response = self.normalize_guidance_response(response, fallback_affected_area=issue_intel.subsystem)
            
            # Stage 9: Grounding Validation
            response = self._ground_and_validate_guidance(
                response=response,
                all_files=all_files,
                all_dirs=all_dirs,
                candidate_evidence=candidate_evidence,
                issue_intel=issue_intel
            )
            print("Grounding Validation Completed.")

            guidance = IssueGuidanceOutput.model_validate(response)
            val_dur = time.perf_counter() - val_start
            logger.info("[PERF] Issue Guidance Validation Time: %.2fs", val_dur)

            total_dur = time.perf_counter() - start_total
            logger.info("[PERF] Issue Guidance Total Time: %.2fs", total_dur)

            # Record profiling metrics
            if hasattr(self, "metrics") and isinstance(self.metrics, dict):
                if "guidance_runs" not in self.metrics:
                    self.metrics["guidance_runs"] = []
                self.metrics["guidance_runs"].append({
                    "prompt_tokens": prompt_tokens,
                    "guidance_time": total_dur,
                    "response_tokens": estimate_tokens(json.dumps(response)) if response else 0,
                    "issue_number": issue_number
                })

            result_guidance = guidance.model_dump()
            result_guidance["guidance_source"] = "llm"

            # Cache Write Attempt
            if key and issue_number:
                try:
                    self.cache_manager.set(key, result_guidance, CACHE_TTL_ISSUE_GUIDANCE)
                    print(f"[CACHE WRITE][Issue Guidance #{issue_number}]")
                except Exception as exc:
                    if isinstance(exc, (TypeError, ValueError)):
                        raise
                    logger.warning("[CACHE] Cache write failed for key %s: %s", key, exc)

            logger.info("Issue guidance generation completed successfully")
            return result_guidance

        except Exception as exc:
            logger.exception("Issue guidance generation failed (Validation/Execution): %s", exc)
            raise RuntimeError(f"Failed to generate issue guidance: {exc}") from exc
