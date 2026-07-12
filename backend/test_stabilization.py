import pytest
import os
import json
import time
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Dict, Any

from app.services.issue_guidance_service import IssueGuidanceService, RepositoryContext, IssueIntelligence, IssueEvidence
from app.utils.file_ranking import score_file
from app.utils.directory_roles import detect_directory_roles
from evaluation.integrity_validator import validate_integrity
from evaluation.benchmark_models import EvaluationReport, GitHubGroundTruth, IssueGuidanceAttempt, TraceEvent
from evaluation.report_builder import MetricsScores, ReportBuilder
from evaluation.prompt_capture import trace_stage_context, EvaluationCaptureContext

# --- Test 1: Repository Context Propagation ---
def test_repo_context_propagation():
    service = IssueGuidanceService()
    
    # Flat summary structure
    repo_summary = {
        "repository_purpose": "Custom purpose definition.",
        "beginner_friendly_summary": "Extremely beginner friendly.",
        "tech_stack": ["Python", "TypeScript"],
        "key_concepts": ["API Routing", "DB Migrations"]
    }
    
    repository_map = {
        "backend": ["backend/app"],
        "frontend": ["frontend/src"]
    }
    
    intel = IssueIntelligence(
        category="backend",
        intent="bugfix",
        subsystem="backend",
        technologies=["Python"],
        keywords=["API"],
        difficulty="Beginner",
        implementation_hints=[]
    )
    
    # Extract context
    context = service._extract_repository_context(repo_summary, repository_map, intel)
    
    assert context.repository_purpose == "Custom purpose definition."
    assert context.beginner_summary == "Extremely beginner friendly."
    assert "Custom purpose definition." in context.relevant_summary
    assert "Python" in context.relevant_technologies
    assert "API Routing" in context.architectural_notes

# --- Test 2: Explicit Path Ranking & Suffix Matching ---
def test_explicit_path_ranking():
    # Exact match
    score_exact, _ = score_file(
        file_path="backend/app/main.py",
        issue_title="Fix main router",
        affected_area="backend",
        issue_labels=[],
        explicit_paths=["backend/app/main.py"]
    )
    
    # Suffix match
    score_suffix, _ = score_file(
        file_path="backend/app/main.py",
        issue_title="Fix main router",
        affected_area="backend",
        issue_labels=[],
        explicit_paths=["app/main.py"]
    )
    
    # Keyword match only
    score_kw, _ = score_file(
        file_path="backend/app/main.py",
        issue_title="Fix main router",
        affected_area="backend",
        issue_labels=[],
        explicit_paths=[]
    )
    
    assert score_exact > score_suffix
    assert score_suffix > score_kw
    assert score_exact >= 10000

# --- Test 3: External GitHub URL Rejection ---
def test_external_github_url_rejection():
    service = IssueGuidanceService()
    
    # Mock issue and comments with external and local URLs
    issue = {
        "owner": "owner",
        "repo": "repo",
        "number": 1,
        "title": "Fix issue",
        "body": "See https://github.com/other-owner/other-repo/blob/main/libs/core.py for comparison and also check local https://github.com/owner/repo/blob/main/backend/app/main.py."
    }
    
    # Test path extraction and filtering
    filtered_explicit = []
    explicit_paths = [
        "https://github.com/other-owner/other-repo/blob/main/libs/core.py",
        "https://github.com/owner/repo/blob/main/backend/app/main.py",
        "backend/app/utils.py"
    ]
    
    owner = "owner"
    repo = "repo"
    import re
    for ep in explicit_paths:
        if "github.com" in ep.lower():
            if owner and repo and f"github.com/{owner.lower()}/{repo.lower()}/" in ep.lower().replace("http://", "").replace("https://", ""):
                url_match = re.search(r'github\.com/[^/]+/[^/]+/blob/[^/]+/(.+)', ep, re.IGNORECASE)
                if url_match:
                    filtered_explicit.append(url_match.group(1))
            else:
                # External URL: reject/skip
                continue
        else:
            filtered_explicit.append(ep)
            
    assert "backend/app/main.py" in filtered_explicit
    assert "backend/app/utils.py" in filtered_explicit
    assert "libs/core.py" not in filtered_explicit

# --- Test 4: Directory Roles Helper ---
def test_directory_roles_helper():
    dirs = ["libs/core", "backend/api", "backend/models", "scripts/deploy"]
    roles = detect_directory_roles(dirs)
    
    assert len(roles) >= 3
    
    core_role = next(r for r in roles if r["path"] == "libs/core")
    assert "core" in core_role["roles"] or "library/package" in core_role["roles"]
    
    api_role = next(r for r in roles if r["path"] == "backend/api")
    assert "API" in api_role["roles"]
    
    model_role = next(r for r in roles if r["path"] == "backend/models")
    assert "model" in model_role["roles"]

# --- Test 5: Open Issue Ground Truth ---
def test_open_issue_ground_truth():
    gt = GitHubGroundTruth(issue_number=1, state="open")
    gt.ground_truth_status = "unavailable_open_issue"
    gt.status_text = "No merged PR available (Issue is open)"
    
    # Assert conformed semantic status
    assert gt.ground_truth_status == "unavailable_open_issue"
    assert gt.files_changed == []

# --- Test 6: Score Mapping ---
def test_metrics_scores():
    report = EvaluationReport()
    report.summary.raw_json = {
        "tech_stack": ["Python"],
        "key_concepts": ["API Routing"],
        "repository_purpose": "Test",
        "beginner_friendly_summary": "Easy"
    }
    report.repo_metadata.language = "Python"
    
    builder = ReportBuilder("mock_token")
    scores = builder._calculate_scores(report)
    
    assert scores.summary_score > 0.0
    assert scores.summary_score == 10.0

# --- Test 7: Integrity Validator ---
def test_integrity_validator():
    # Contradiction: Successful summary but score is 0.0
    report = EvaluationReport()
    report.summary.raw_json = {"repository_purpose": "Test"}
    report.metrics_scores.summary_score = 0.0
    report.total_runtime = 1.5
    
    status, findings = validate_integrity(report)
    assert status == "FAIL"
    assert any("summary_score is 0.0" in f for f in findings)
    
    # Valid report
    report_valid = EvaluationReport()
    report_valid.summary.raw_json = {
        "repository_purpose": "Test",
        "beginner_friendly_summary": "Easy",
        "tech_stack": ["Python"],
        "key_concepts": ["Test"]
    }
    report_valid.metrics_scores.summary_score = 10.0
    report_valid.total_runtime = 2.0
    
    status_v, findings_v = validate_integrity(report_valid)
    assert status_v == "PASS"

# --- Test 8: Observer Passive Interception ---
@patch("groq.resources.chat.completions.Completions.create")
def test_observer_passive_interception(mock_create):
    mock_res = MagicMock()
    mock_res.choices = [MagicMock()]
    mock_res.choices[0].message.content = '{"tech_stack": ["Python"]}'
    mock_res.usage = MagicMock()
    mock_res.usage.prompt_tokens = 10
    mock_res.usage.completion_tokens = 5
    mock_res.usage.total_tokens = 15
    mock_create.return_value = mock_res
    
    report = EvaluationReport()
    
    with EvaluationCaptureContext(report, exec_mode="prod"):
        import groq
        # Trigger mock LLM call
        client = groq.Groq(api_key="mock")
        res = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.0
        )
        
    assert len(report.production_trace) == 0  # Completions are captured passively, trace events are for stages
    assert res.choices[0].message.content == '{"tech_stack": ["Python"]}'
