from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class RepositoryMetadata(BaseModel):
    name: str = ""
    url: str = ""
    stars: int = 0
    forks: int = 0
    language: str = ""
    topics: List[str] = []
    size_kb: int = 0
    total_files: int = 0
    total_directories: int = 0
    readme_size_bytes: int = 0
    contributing_present: bool = False

class RepoSummaryCaptured(BaseModel):
    raw_json: Dict[str, Any] = Field(default_factory=dict)
    pretty_formatted: str = ""
    timing: float = 0.0
    prompt_tokens: int = 0
    response_tokens: int = 0
    model: str = ""

class RepoMapCaptured(BaseModel):
    map_json: Dict[str, Any] = Field(default_factory=dict)
    important_directories: List[str] = Field(default_factory=list)
    categorized_folders: Dict[str, List[str]] = Field(default_factory=dict)
    architecture_notes: str = ""
    timing: float = 0.0

class IssueSelected(BaseModel):
    number: int
    title: str = ""
    labels: List[str] = Field(default_factory=list)
    difficulty: str = "Beginner"
    body: str = ""
    comments: List[Dict[str, Any]] = Field(default_factory=list)
    url: str = ""
    good_first_issue_score: float = 0.0

class IssueGuidanceAttempt(BaseModel):
    attempt_number: int
    prompt: str = ""
    prompt_tokens: int = 0
    status: str = ""  # e.g., "Budget Exceeded", "LLM Failed", "Success"
    include_readme: bool = False
    include_contributing: bool = False
    include_comments: bool = False
    include_map: bool = False
    compress_readme: bool = False
    compress_contributing: bool = False
    removed_context: str = "None"
    remaining_context: str = ""
    sent_to_llm: bool = False

class GroundingValidationStats(BaseModel):
    recommended_files: List[str] = Field(default_factory=list)
    existing_files: List[str] = Field(default_factory=list)
    removed_files: List[str] = Field(default_factory=list)
    recommended_directories: List[str] = Field(default_factory=list)
    existing_directories: List[str] = Field(default_factory=list)
    removed_directories: List[str] = Field(default_factory=list)
    confidence_before: float = 0.0
    confidence_after: float = 0.0
class TechnicalEvidenceItemCaptured(BaseModel):
    evidence_type: str
    strength: str
    source: str
    source_index: Optional[int] = None
    text: str
    normalized_value: str
    rationale: str
    technical_entities: List[str] = Field(default_factory=list)
    confidence_score: Optional[float] = None
    matched_patterns: List[str] = Field(default_factory=list)
    occurrence_count: int = 1

class TechnicalEvidenceCaptured(BaseModel):
    technical_evidence: List[TechnicalEvidenceItemCaptured] = Field(default_factory=list)
    evidence_type_counts: Dict[str, int] = Field(default_factory=dict)
    strength_counts: Dict[str, int] = Field(default_factory=dict)
    top_technical_entities: List[str] = Field(default_factory=list)
    critical_evidence_count: int = 0
    strong_evidence_count: int = 0
    ignored_evidence_count: int = 0
    duplicate_evidence_count: int = 0
    additional_llm_calls_from_evidence_extraction: int = 0
    technical_evidence_extraction_ms: float = 0.0
    technical_evidence_capture_status: str = "NOT_OBSERVED"

class ClassificationReconciliationCaptured(BaseModel):
    original_category: str = ""
    original_subsystem: str = ""
    resolved_category: str = ""
    resolved_subsystem: str = ""
    decision: str = ""
    confidence_score: float = 0.0
    evidence_entities: List[str] = Field(default_factory=list)
    conflicting_evidence_count: int = 0
    supporting_evidence_count: int = 0
    rationale: str = ""
    additional_llm_calls_from_reconciliation: int = 0
    classification_reconciliation_ms: float = 0.0
    capture_status: str = "NOT_OBSERVED"

class IssueGuidanceTrace(BaseModel):
    issue_number: int
    title: str = ""
    issue_payload: Dict[str, Any] = Field(default_factory=dict)
    comments: List[Dict[str, Any]] = Field(default_factory=list)
    issue_intel: Dict[str, Any] = Field(default_factory=dict)
    issue_evidence: Dict[str, Any] = Field(default_factory=dict)
    repo_context: Dict[str, Any] = Field(default_factory=dict)
    candidate_evidence: Dict[str, Any] = Field(default_factory=dict)
    candidate_dirs: List[str] = Field(default_factory=list)
    attempts: List[IssueGuidanceAttempt] = Field(default_factory=list)
    successful_attempt: Optional[int] = None
    raw_llm_response: str = ""
    parsed_json: Optional[Dict[str, Any]] = None
    normalized_json: Optional[Dict[str, Any]] = None
    final_guidance_json: Optional[Dict[str, Any]] = None
    grounding_stats: Optional[GroundingValidationStats] = None
    timings: Dict[str, float] = Field(default_factory=dict)
    technical_evidence: Optional[TechnicalEvidenceCaptured] = None
    classification_reconciliation: Optional[ClassificationReconciliationCaptured] = None

class RoadmapCaptured(BaseModel):
    raw_json: Dict[str, Any] = Field(default_factory=dict)
    rendered_roadmap: str = ""
    timing: float = 0.0

class PDFStats(BaseModel):
    name: str = ""
    file_size_bytes: int = 0
    generation_time_ms: int = 0
    file_path: str = ""

class CacheStats(BaseModel):
    backend_name: str = "memory"
    hits: int = 0
    misses: int = 0
    writes: int = 0
    lookup_time_ms: float = 0.0
    write_time_ms: float = 0.0

class ErrorStats(BaseModel):
    github_errors: List[str] = Field(default_factory=list)
    llm_errors: List[str] = Field(default_factory=list)
    retries: int = 0
    rate_limits: int = 0
    validation_errors: List[str] = Field(default_factory=list)

class GitHubGroundTruth(BaseModel):
    issue_number: int
    state: str = "open"  # "open" or "closed"
    ground_truth_status: str = "available"  # "available", "unavailable_open_issue", "unavailable_no_linked_pr", "unavailable_pr_not_merged", "capture_failed"
    merged_pr_number: Optional[int] = None
    merged_pr_url: Optional[str] = None
    pr_title: Optional[str] = None
    pr_description: Optional[str] = None
    files_changed: List[str] = Field(default_factory=list)
    directories_changed: List[str] = Field(default_factory=list)
    commits: List[str] = Field(default_factory=list)
    closing_commit: Optional[str] = None
    changed_languages: List[str] = Field(default_factory=list)
    status_text: str = ""

class MetricsScores(BaseModel):
    summary_score: float = 0.0
    map_score: float = 0.0
    guidance_score: float = 0.0
    candidate_ranking_score: float = 0.0
    grounding_score: float = 0.0
    roadmap_score: float = 0.0
    overall_score: float = 0.0

class TraceEvent(BaseModel):
    stage_name: str
    duration: float = 0.0
    input: Optional[str] = None
    output: Optional[str] = None
    logs: List[str] = Field(default_factory=list)
    exceptions: List[str] = Field(default_factory=list)
    cache_action: Optional[str] = None
    prompt: Optional[str] = None
    llm_response: Optional[str] = None
    operation: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: Optional[str] = "Success"
    exception_type: Optional[str] = None

class EvaluationReport(BaseModel):
    repo_metadata: RepositoryMetadata = Field(default_factory=RepositoryMetadata)
    summary: RepoSummaryCaptured = Field(default_factory=RepoSummaryCaptured)
    repo_map: RepoMapCaptured = Field(default_factory=RepoMapCaptured)
    issues: List[IssueGuidanceTrace] = Field(default_factory=list)
    roadmap: RoadmapCaptured = Field(default_factory=RoadmapCaptured)
    pdfs: List[PDFStats] = Field(default_factory=list)
    cache: CacheStats = Field(default_factory=CacheStats)
    errors: ErrorStats = Field(default_factory=ErrorStats)
    ground_truths: Dict[int, GitHubGroundTruth] = Field(default_factory=dict)
    metrics_scores: MetricsScores = Field(default_factory=MetricsScores)
    total_runtime: float = 0.0
    production_trace: List[TraceEvent] = Field(default_factory=list)
    observations: str = ""
    memory_usage_mb: float = 0.0
    cpu_usage_pct: float = 0.0
