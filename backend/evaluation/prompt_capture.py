import time
import functools
import threading
import json
import logging
from typing import Generator, List, Dict, Any, Optional
from contextlib import contextmanager

# Import production services
from app.services.llm_service import LLMService
from app.services.repository_summary_service import RepositorySummaryService
from app.services.repository_map_service import RepositoryMapService
from app.services.roadmap_service import RoadmapService
from app.services.issue_guidance_service import IssueGuidanceService
from app.services.github_service import GitHubService
from app.core.cache.manager import CacheManager
from app.utils.performance_utils import estimate_tokens

# Import evaluation models
from evaluation.benchmark_models import (
    EvaluationReport, RepoSummaryCaptured, RepoMapCaptured,
    IssueGuidanceTrace, IssueGuidanceAttempt, GroundingValidationStats,
    RoadmapCaptured, CacheStats, ErrorStats, TraceEvent,
    TechnicalEvidenceCaptured, TechnicalEvidenceItemCaptured,
    ClassificationReconciliationCaptured
)

logger = logging.getLogger(__name__)
eval_logger = logging.getLogger("evaluation_logger")

# Thread-local storage to track active issue and active stage name
_eval_thread_local = threading.local()

# Global dictionary to accumulate log records captured per stage in a thread-safe manner
captured_logs = {}
lock = threading.Lock()

class TraceLogHandler(logging.Handler):
    """Custom logging handler to record logs per stage passively."""
    def __init__(self):
        super().__init__()
        self.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    def emit(self, record):
        stage = getattr(_eval_thread_local, "current_stage", "General")
        msg = self.format(record)
        with lock:
            if stage not in captured_logs:
                captured_logs[stage] = []
            captured_logs[stage].append(msg)

@contextmanager
def trace_stage_context(stage_name: str, report: EvaluationReport, input_val: Optional[str] = None, operation: Optional[str] = None):
    """Timing and trace event capture context manager."""
    prev_stage = getattr(_eval_thread_local, "current_stage", None)
    _eval_thread_local.current_stage = stage_name
    
    t0 = time.perf_counter()
    start_time = time.time()
    
    event = TraceEvent(
        stage_name=stage_name,
        operation=operation or stage_name,
        start_time=start_time,
        input=input_val,
        status="Success"
    )
    
    # Track logs length at start
    with lock:
        logs_start_idx = len(captured_logs.get(stage_name, []))
        
    try:
        yield event
    except Exception as exc:
        event.exceptions.append(str(exc))
        event.exception_type = type(exc).__name__
        event.status = "Failure"
        eval_logger.error("Exception in stage %s: %s", stage_name, exc)
        raise
    finally:
        event.duration = time.perf_counter() - t0
        event.duration_ms = event.duration * 1000.0
        event.end_time = start_time + event.duration
        
        # Capture stage logs
        with lock:
            all_logs = captured_logs.get(stage_name, [])
            event.logs = list(all_logs[logs_start_idx:])
            
        with lock:
            report.production_trace.append(event)
            
        _eval_thread_local.current_stage = prev_stage

@contextmanager
def EvaluationCaptureContext(report: EvaluationReport, exec_mode: str = "prod", bypass_cache: bool = False):
    """Context manager to passively instrument RepoPilot backend services.
    
    In 'prod' mode, it passively intercepts execution parameters, Stage 12.1 intelligence,
    prompts, and trace performance without changing production behaviour.
    In 'ci' mode, it overrides external calls to run offline for CI/CD checks.
    """
    _eval_thread_local.current_issue_number = None
    _eval_thread_local.current_stage = "General"
    
    # Save original methods
    orig_generate_json = LLMService.generate_json
    orig_summary_gen = RepositorySummaryService.generate_summary
    orig_map_gen = RepositoryMapService.generate_map
    orig_roadmap_analyze = RoadmapService.analyze_roadmap
    
    orig_github_tree = GitHubService.get_repository_tree
    orig_github_meta = GitHubService.get_repo_metadata
    orig_github_readme = GitHubService.get_readme
    orig_github_contrib = GitHubService.get_contributing
    orig_github_issues = GitHubService.get_good_first_issues
    orig_github_comments = GitHubService.get_issue_comments
    
    orig_guidance_gen = IssueGuidanceService.generate_guidance
    orig_understand = IssueGuidanceService._understand_issue
    orig_extract_context = IssueGuidanceService._extract_repository_context
    orig_rank = IssueGuidanceService._rank_candidates
    orig_assemble = IssueGuidanceService._assemble_prompt
    orig_ground = IssueGuidanceService._ground_and_validate_guidance
    orig_normalize = IssueGuidanceService.normalize_guidance_response
    
    orig_cache_get = CacheManager.get
    orig_cache_set = CacheManager.set

    # Register logging intercept handler
    log_handler = TraceLogHandler()
    logging.getLogger().addHandler(log_handler)

    # Initialize captured logs dict
    with lock:
        captured_logs.clear()

    import groq
    orig_groq_create = groq.resources.chat.completions.Completions.create
    
    with lock:
        _eval_thread_local.llm_calls = []

    @functools.wraps(orig_groq_create)
    def wrapped_groq_create(self_resource, *args, **kwargs):
        t_req = time.perf_counter()
        model = kwargs.get("model", "")
        temp = kwargs.get("temperature", 0.0)
        max_tokens = kwargs.get("max_tokens")
        top_p = kwargs.get("top_p")
        
        # Extract prompt text
        messages = kwargs.get("messages", [])
        prompt_text = ""
        for m in messages:
            if m.get("role") == "user":
                prompt_text = m.get("content", "")
                
        stage = getattr(_eval_thread_local, "current_stage", "General")
        
        with lock:
            if not hasattr(_eval_thread_local, "llm_calls") or _eval_thread_local.llm_calls is None:
                _eval_thread_local.llm_calls = []
            stage_calls = [c for c in _eval_thread_local.llm_calls if c.get("stage") == stage]
            retry_num = len(stage_calls) + 1
            
        call_record = {
            "stage": stage,
            "model": model,
            "temperature": temp,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "prompt": prompt_text,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "latency": 0.0,
            "raw_response": "",
            "parsed_json": None,
            "exception": None,
            "retry_number": retry_num,
            "rate_limit_hit": False,
            "status": "Failure"
        }
        
        if exec_mode == "ci":
            # Return a mock chat completion object
            from groq.types.chat.chat_completion import ChatCompletion, Choice
            from groq.types.chat.chat_completion_message import ChatCompletionMessage
            
            stage = getattr(_eval_thread_local, "current_stage", "General")
            if stage == "Repository Summary" or "summary" in stage.lower():
                content = '{"tech_stack": ["Python"], "key_concepts": ["API Routing"], "repository_purpose": "Test", "beginner_friendly_summary": "Easy"}'
            elif stage == "Roadmap":
                content = '{"steps": [{"step_number": 1, "description": "CI Roadmap step", "related_issue": 42}], "prerequisites": ["CI Python"], "estimated_time": "30 mins"}'
            else: # Issue Guidance
                content = '{"analysis": {"beginner_explanation": "CI Issue analysis", "skills_required": ["Python"], "affected_area": "backend", "difficulty": "Beginner", "confidence_score": 99}, "exploration_hints": {"affected_area": "backend", "likely_directories": ["backend"], "possible_files": ["backend/main.py"], "reasoning": "CI mock reasoning", "confidence": 99}}'
                
            mock_choice = Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(
                    content=content,
                    role="assistant"
                )
            )
            mock_cc = ChatCompletion(
                id="mock-chat-completion-id",
                choices=[mock_choice],
                created=int(time.time()),
                model=model or "mock-model",
                object="chat.completion"
            )
            
            call_record.update({
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
                "latency": 0.01,
                "raw_response": content,
                "status": "Success",
                "parsed_json": json.loads(content)
            })
            
            with lock:
                if not hasattr(_eval_thread_local, "llm_calls") or _eval_thread_local.llm_calls is None:
                    _eval_thread_local.llm_calls = []
                _eval_thread_local.llm_calls.append(call_record)
                
            return mock_cc

        try:
            res = orig_groq_create(self_resource, *args, **kwargs)
            dur_req = time.perf_counter() - t_req
            content = res.choices[0].message.content or ""
            
            usage = getattr(res, "usage", None)
            prompt_t = getattr(usage, "prompt_tokens", 0) if usage else estimate_tokens(prompt_text)
            completion_t = getattr(usage, "completion_tokens", 0) if usage else estimate_tokens(content)
            total_t = getattr(usage, "total_tokens", 0) if usage else (prompt_t + completion_t)
            
            call_record.update({
                "prompt_tokens": prompt_t,
                "completion_tokens": completion_t,
                "total_tokens": total_t,
                "latency": dur_req,
                "raw_response": content,
                "status": "Success"
            })
            
            # Try to parse JSON
            try:
                call_record["parsed_json"] = json.loads(content)
            except Exception:
                try:
                    import re
                    cleaned = content.strip()
                    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
                    cleaned = re.sub(r"\s*```$", "", cleaned)
                    cleaned = re.sub(r"(?is)<reasoning>.*?</reasoning>", "", cleaned)
                    first_brace = cleaned.find("{")
                    last_brace = cleaned.rfind("}")
                    if first_brace != -1 and last_brace != -1:
                        cleaned = cleaned[first_brace:last_brace + 1]
                    call_record["parsed_json"] = json.loads(cleaned)
                except Exception:
                    pass
            
            with lock:
                if not hasattr(_eval_thread_local, "llm_calls") or _eval_thread_local.llm_calls is None:
                    _eval_thread_local.llm_calls = []
                _eval_thread_local.llm_calls.append(call_record)
            
            eval_logger.info("Groq Call Success. Stage: %s. Latency: %.2fs. Tokens: %d", stage, dur_req, total_t)
            return res
        except Exception as exc:
            dur_req = time.perf_counter() - t_req
            exc_str = str(exc)
            
            call_record.update({
                "latency": dur_req,
                "exception": exc_str,
                "status": "Failure",
                "rate_limit_hit": "rate_limit" in exc_str.lower() or "429" in exc_str.lower()
            })
            
            with lock:
                if not hasattr(_eval_thread_local, "llm_calls") or _eval_thread_local.llm_calls is None:
                    _eval_thread_local.llm_calls = []
                _eval_thread_local.llm_calls.append(call_record)
                report.errors.retries += 1
                if call_record["rate_limit_hit"]:
                    report.errors.rate_limits += 1
            eval_logger.warning("Groq Call Failed. Stage: %s. Error: %s", stage, exc_str)
            raise

    # --- LLMService Interceptor ---
    @functools.wraps(orig_generate_json)
    def wrapped_generate_json(self, prompt: str, service_name: str = "General") -> Dict[str, Any]:
        eval_logger.info("Groq Request triggered for: %s", service_name)
        
        # Define mock outputs for CI mode
        if exec_mode == "ci":
            eval_logger.info("Running LLM call in mock CI mode.")
            mock_data = {}
            if service_name == "Roadmap":
                mock_data = {
                    "steps": [{"step_number": 1, "description": "CI Roadmap step", "related_issue": 42}],
                    "prerequisites": ["CI Python"], "estimated_time": "30 mins"
                }
            elif service_name == "Issue Guidance":
                mock_data = {
                    "analysis": {
                        "beginner_explanation": "CI Issue analysis", "skills_required": ["Python"],
                        "affected_area": "backend", "difficulty": "Beginner", "confidence_score": 99
                    },
                    "exploration_hints": {
                        "affected_area": "backend", "likely_directories": ["backend"],
                        "possible_files": ["backend/main.py"], "reasoning": "CI mock reasoning", "confidence": 99
                    }
                }
            else: # Summary
                mock_data = {
                    "tech_stack": ["Python"], "key_concepts": ["CI testing"],
                    "repository_purpose": "CI test repo", "beginner_friendly_summary": "CI friendly"
                }
            
            # Record mock values
            with lock:
                issue_number = getattr(_eval_thread_local, "current_issue_number", None)
                if issue_number and service_name == "Issue Guidance":
                    trace = next((t for t in report.issues if t.issue_number == issue_number), None)
                    if trace:
                        trace.raw_llm_response = json.dumps(mock_data)
                        trace.parsed_json = mock_data
                        if trace.attempts:
                            trace.attempts[-1].status = "Success"
                            trace.attempts[-1].sent_to_llm = True
                            trace.successful_attempt = len(trace.attempts)
                elif service_name == "Roadmap":
                    report.roadmap.raw_json = mock_data
                else:
                    report.summary.raw_json = mock_data
            return mock_data

        t0 = time.perf_counter()
        try:
            parsed_res = orig_generate_json(self, prompt, service_name)
            dur = time.perf_counter() - t0
            
            stage = getattr(_eval_thread_local, "current_stage", "General")
            with lock:
                stage_calls = [c for c in getattr(_eval_thread_local, "llm_calls", []) if c.get("stage") == stage and c.get("status") == "Success"]
            
            issue_number = getattr(_eval_thread_local, "current_issue_number", None)
            
            if issue_number and service_name == "Issue Guidance":
                with lock:
                    trace = next((t for t in report.issues if t.issue_number == issue_number), None)
                    if trace:
                        if stage_calls:
                            last_call = stage_calls[-1]
                            trace.raw_llm_response = last_call["raw_response"]
                            trace.parsed_json = last_call["parsed_json"] or parsed_res
                            trace.timings["llm_call"] = last_call["latency"]
                            if trace.attempts:
                                trace.attempts[-1].status = "Success"
                                trace.attempts[-1].sent_to_llm = True
                                trace.successful_attempt = len(trace.attempts)
                        else:
                            trace.raw_llm_response = json.dumps(parsed_res)
                            trace.parsed_json = parsed_res
                            trace.timings["llm_call"] = dur
                            if trace.attempts:
                                trace.attempts[-1].status = "Success"
                                trace.attempts[-1].sent_to_llm = True
                                trace.successful_attempt = len(trace.attempts)
            elif service_name == "Roadmap":
                with lock:
                    report.roadmap.raw_json = parsed_res
                    report.roadmap.timing = dur
            elif service_name == "General" or "summary" in service_name.lower():
                with lock:
                    report.summary.raw_json = parsed_res
                    report.summary.timing = dur
                    if stage_calls:
                        last_call = stage_calls[-1]
                        report.summary.prompt_tokens = last_call["prompt_tokens"]
                        report.summary.response_tokens = last_call["completion_tokens"]
                        report.summary.model = last_call["model"]
                    else:
                        report.summary.prompt_tokens = estimate_tokens(prompt)
                        report.summary.response_tokens = estimate_tokens(json.dumps(parsed_res))
                        report.summary.model = self.model
            
            # Record LLM info in the trace event
            stage_event = getattr(_eval_thread_local, "active_stage_event", None)
            if stage_event:
                stage_event.prompt = prompt
                stage_event.llm_response = parsed_res if isinstance(parsed_res, str) else json.dumps(parsed_res)
                
            return parsed_res
            
        except Exception as exc:
            dur = time.perf_counter() - t0
            with lock:
                report.errors.llm_errors.append(f"{service_name}: {exc}")
                issue_number = getattr(_eval_thread_local, "current_issue_number", None)
                if issue_number and service_name == "Issue Guidance":
                    trace = next((t for t in report.issues if t.issue_number == issue_number), None)
                    if trace and trace.attempts:
                        trace.attempts[-1].status = f"LLM Failed: {exc}"
                        trace.attempts[-1].sent_to_llm = True
                        trace.timings["llm_call"] = dur
            raise

    # --- GitHubService Interceptor ---
    @functools.wraps(orig_github_tree)
    def wrapped_github_tree(self, owner, repo):
        if exec_mode == "ci":
            return [
                {"path": "backend/main.py", "type": "blob"},
                {"path": "README.md", "type": "blob"}
            ]
        eval_logger.info("GitHub API: Fetching repository tree")
        return orig_github_tree(self, owner, repo)

    @functools.wraps(orig_github_meta)
    def wrapped_github_meta(self, owner, repo):
        if exec_mode == "ci":
            return {"name": repo, "stargazers_count": 10, "forks_count": 2, "language": "Python"}
        eval_logger.info("GitHub API: Fetching repository metadata")
        return orig_github_meta(self, owner, repo)

    @functools.wraps(orig_github_readme)
    def wrapped_github_readme(self, owner, repo):
        if exec_mode == "ci":
            return "CI README"
        eval_logger.info("GitHub API: Fetching README")
        return orig_github_readme(self, owner, repo)

    @functools.wraps(orig_github_contrib)
    def wrapped_github_contrib(self, owner, repo):
        if exec_mode == "ci":
            return "CI CONTRIBUTING"
        eval_logger.info("GitHub API: Fetching CONTRIBUTING guide")
        return orig_github_contrib(self, owner, repo)

    @functools.wraps(orig_github_issues)
    def wrapped_github_issues(self, owner, repo):
        if exec_mode == "ci":
            return [{"number": 42, "title": "CI Bug", "body": "Fix this bug.", "labels": ["good first issue"], "html_url": ""}]
        eval_logger.info("GitHub API: Fetching good first issues")
        return orig_github_issues(self, owner, repo)

    @functools.wraps(orig_github_comments)
    def wrapped_github_comments(self, owner, repo, issue_number):
        if exec_mode == "ci":
            return [{"body": "CI comment"}]
        eval_logger.info("GitHub API: Fetching comments for issue #%d", issue_number)
        return orig_github_comments(self, owner, repo, issue_number)

    # --- RepositorySummaryService Interceptor ---
    @functools.wraps(orig_summary_gen)
    def wrapped_summary_gen(self, metadata, readme, contributing, prompt):
        _eval_thread_local.current_stage = "Repository Summary"
        t0 = time.perf_counter()
        with trace_stage_context("Repository Summary", report, input_val="Metadata & Readme", operation="generate_summary") as ev:
            res = orig_summary_gen(self, metadata, readme, contributing, prompt)
            ev.output = json.dumps(res)
        
        dur = time.perf_counter() - t0
        with lock:
            stage_calls = [c for c in getattr(_eval_thread_local, "llm_calls", []) if c.get("stage") == "Repository Summary" and c.get("status") == "Success"]
            report.summary.pretty_formatted = json.dumps(res, indent=2)
            report.summary.raw_json = res
            report.summary.timing = dur
            if stage_calls:
                last_call = stage_calls[-1]
                report.summary.prompt_tokens = last_call["prompt_tokens"]
                report.summary.response_tokens = last_call["completion_tokens"]
                report.summary.model = last_call["model"]
            else:
                report.summary.prompt_tokens = estimate_tokens(prompt)
                report.summary.response_tokens = estimate_tokens(json.dumps(res))
                report.summary.model = getattr(self.llm_service, "model", "unknown-model")
        return res

    # --- RepositoryMapService Interceptor ---
    @functools.wraps(orig_map_gen)
    def wrapped_map_gen(self, owner, repo, tree):
        _eval_thread_local.current_stage = "Repository Map"
        t0 = time.perf_counter()
        with trace_stage_context("Repository Map", report, input_val=f"Tree with {len(tree)} items", operation="generate_map") as ev:
            res = orig_map_gen(self, owner, repo, tree)
            ev.output = json.dumps(res)
            
        dur = time.perf_counter() - t0
        all_dirs = set()
        for cat, paths in res.items():
            if isinstance(paths, list):
                for p in paths:
                    parts = p.split('/')
                    if parts:
                        all_dirs.add(parts[0])
        with lock:
            report.repo_map.map_json = res
            report.repo_map.categorized_folders = res
            report.repo_map.important_directories = sorted(list(all_dirs))
            report.repo_map.timing = dur
        return res

    # --- RoadmapService Interceptor ---
    @functools.wraps(orig_roadmap_analyze)
    def wrapped_roadmap_analyze(self, payload):
        _eval_thread_local.current_stage = "Roadmap"
        t0 = time.perf_counter()
        with trace_stage_context("Roadmap", report, input_val="Issues Guidance List", operation="analyze_roadmap") as ev:
            res = orig_roadmap_analyze(self, payload)
            ev.output = json.dumps(res)
            
        dur = time.perf_counter() - t0
        with lock:
            report.roadmap.raw_json = res
            report.roadmap.rendered_roadmap = json.dumps(res, indent=2)
            report.roadmap.timing = dur
        return res

    def _capture_budgeting_telemetry(service_inst, issue_trace):
        budget_ctx = getattr(service_inst, "_last_budgeted_context", None)
        if budget_ctx:
            from evaluation.benchmark_models import ContextBudgetingCaptured, IssueGuidanceAttempt
            captured = ContextBudgetingCaptured(
                budget_status=budget_ctx.budget_status,
                budget_limit=budget_ctx.budget_limit,
                selected_attempt=budget_ctx.selected_attempt,
                selected_mode=budget_ctx.selected_mode,
                estimated_prompt_tokens=budget_ctx.estimated_tokens,
                static_template_tokens=budget_ctx.static_template_tokens,
                dynamic_context_tokens=budget_ctx.dynamic_context_tokens,
                included_sections=budget_ctx.included_sections,
                removed_sections=budget_ctx.removed_sections,
                protected_evidence_count=budget_ctx.protected_evidence_count,
                critical_evidence_included_count=budget_ctx.critical_evidence_included_count,
                strong_evidence_included_count=budget_ctx.strong_evidence_included_count,
                explicit_path_count=budget_ctx.explicit_path_count,
                explicit_paths_included_count=budget_ctx.explicit_paths_included_count,
                candidate_files_available_count=budget_ctx.candidate_files_available_count,
                candidate_files_included_count=budget_ctx.candidate_files_included_count,
                candidate_files_included=budget_ctx.candidate_files_included,
                issue_segments_included_count=budget_ctx.issue_segments_included_count,
                comment_segments_included_count=budget_ctx.comment_segments_included_count,
                protected_core_integrity_status=budget_ctx.protected_core_integrity_status,
                integrity_failures=budget_ctx.integrity_failures,
                emergency_core_used=budget_ctx.emergency_core_used,
                additional_llm_calls_from_context_budgeting=budget_ctx.additional_llm_calls_from_context_budgeting,
                context_budgeting_ms=budget_ctx.context_budgeting_ms,
                capture_status=budget_ctx.capture_status,
                critical_evidence_available_count=budget_ctx.critical_evidence_available_count,
                strong_evidence_available_count=budget_ctx.strong_evidence_available_count,
                explicit_paths_available_count=budget_ctx.explicit_paths_available_count
            )
            
            attempts_list = []
            attempt_configs = {
                1: {
                    "include_readme": True, "compress_readme": False,
                    "include_contributing": True, "compress_contributing": False,
                    "include_comments": True, "include_map": True,
                    "removed_context": "None",
                    "remaining_context": "README, CONTRIBUTING, COMMENTS, REPOSITORY MAP"
                },
                2: {
                    "include_readme": True, "compress_readme": False,
                    "include_contributing": True, "compress_contributing": False,
                    "include_comments": True, "include_map": True,
                    "removed_context": "COMMENTS",
                    "remaining_context": "README, CONTRIBUTING, REPOSITORY MAP"
                },
                3: {
                    "include_readme": True, "compress_readme": True,
                    "include_contributing": True, "compress_contributing": True,
                    "include_comments": False, "include_map": True,
                    "removed_context": "COMMENTS (Removed), README/CONTRIBUTING (Compressed)",
                    "remaining_context": "README (Compressed), CONTRIBUTING (Compressed), REPOSITORY MAP"
                },
                4: {
                    "include_readme": False, "compress_readme": False,
                    "include_contributing": False, "compress_contributing": False,
                    "include_comments": False, "include_map": True,
                    "removed_context": "COMMENTS, README, CONTRIBUTING, REPOSITORY MAP",
                    "remaining_context": "None (Minimal Mode)"
                },
                5: {
                    "include_readme": False, "compress_readme": False,
                    "include_contributing": False, "compress_contributing": False,
                    "include_comments": False, "include_map": True,
                    "removed_context": "COMMENTS, README, CONTRIBUTING, REPOSITORY MAP",
                    "remaining_context": "EMERGENCY CORE"
                }
            }
            
            all_prompts = getattr(budget_ctx, "all_attempt_prompts", {}) or {}
            for att_num, att_prompt in sorted(all_prompts.items()):
                is_success = (att_num == budget_ctx.selected_attempt)
                status = "Success" if is_success else "Budget Exceeded"
                
                cfg = attempt_configs.get(att_num, {
                    "include_readme": False, "compress_readme": False,
                    "include_contributing": False, "compress_contributing": False,
                    "include_comments": False, "include_map": False,
                    "removed_context": "None", "remaining_context": ""
                })
                
                attempt_obj = IssueGuidanceAttempt(
                    attempt_number=att_num,
                    prompt=att_prompt,
                    prompt_tokens=estimate_tokens(att_prompt),
                    status=status,
                    include_readme=cfg["include_readme"],
                    include_contributing=cfg["include_contributing"],
                    include_comments=cfg["include_comments"],
                    include_map=cfg["include_map"],
                    compress_readme=cfg["compress_readme"],
                    compress_contributing=cfg["compress_contributing"],
                    removed_context=cfg["removed_context"],
                    remaining_context=cfg["remaining_context"],
                    sent_to_llm=is_success
                )
                attempts_list.append(attempt_obj)
                
            with lock:
                issue_trace.context_budgeting = captured
                issue_trace.attempts = attempts_list
                issue_trace.successful_attempt = budget_ctx.selected_attempt

    # --- IssueGuidanceService Interceptors ---
    @functools.wraps(orig_guidance_gen)
    def wrapped_guidance_gen(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        issue = payload.get("issue", {})
        issue_number = issue.get("number", 0)
        
        _eval_thread_local.current_issue_number = issue_number
        
        trace = IssueGuidanceTrace(
            issue_number=issue_number,
            title=issue.get("title", ""),
            issue_payload=issue,
            comments=payload.get("comments", [])
        )
        with lock:
            report.issues.append(trace)
            
        t0 = time.perf_counter()
        with trace_stage_context(f"Issue Guidance #{issue_number}", report, input_val=json.dumps(issue), operation="generate_guidance") as ev:
            try:
                res = orig_guidance_gen(self, payload)
                ev.output = json.dumps(res)
                dur = time.perf_counter() - t0
                
                # Capture Stage 12.2.3 Context Budgeting telemetry
                _capture_budgeting_telemetry(self, trace)

                with lock:
                    trace.final_guidance_json = res
                    trace.timings["total"] = dur
                return res
            except Exception as exc:
                _capture_budgeting_telemetry(self, trace)
                with lock:
                    report.errors.validation_errors.append(f"Issue #{issue_number}: {exc}")
                raise
            finally:
                _eval_thread_local.current_issue_number = None

    @functools.wraps(orig_understand)
    def wrapped_understand(self, title, body, labels, comments):
        t0 = time.perf_counter()
        
        # Track LLM call count delta
        calls_before = len(getattr(_eval_thread_local, "llm_calls", []))
        
        intel, evidence = orig_understand(self, title, body, labels, comments)
        
        calls_after = len(getattr(_eval_thread_local, "llm_calls", []))
        llm_calls_delta = calls_after - calls_before
        
        dur = time.perf_counter() - t0
        
        issue_number = getattr(_eval_thread_local, "current_issue_number", None)
        if issue_number:
            with lock:
                trace = next((t for t in report.issues if t.issue_number == issue_number), None)
                if trace:
                    trace.issue_intel = {
                        "category": intel.category,
                        "intent": intel.intent,
                        "subsystem": intel.subsystem,
                        "technologies": intel.technologies,
                        "keywords": intel.keywords,
                        "difficulty": intel.difficulty,
                        "implementation_hints": intel.implementation_hints,
                    }
                    trace.issue_evidence = {
                        "evidence": evidence.evidence,
                        "matched_labels": evidence.matched_labels,
                        "matched_keywords": evidence.matched_keywords,
                        "detected_stack": evidence.detected_stack,
                        "explicit_paths": evidence.explicit_paths,
                    }
                    
                    # Capture Stage 12.2.1 Technical Evidence telemetry
                    capture_status = getattr(evidence, "technical_evidence_capture_status", "NOT_OBSERVED")
                    captured_items = []
                    technical_evidence_list = getattr(evidence, "technical_evidence", [])
                    
                    if technical_evidence_list:
                        for item in technical_evidence_list:
                            captured_items.append(TechnicalEvidenceItemCaptured(
                                evidence_type=item.evidence_type,
                                strength=item.strength,
                                source=item.source,
                                source_index=item.source_index,
                                text=item.text,
                                normalized_value=item.normalized_value,
                                rationale=item.rationale,
                                technical_entities=item.technical_entities,
                                confidence_score=item.confidence_score,
                                matched_patterns=item.matched_patterns,
                                occurrence_count=item.occurrence_count
                            ))
                            
                    type_counts = getattr(evidence, "evidence_type_counts", {})
                    strength_counts = getattr(evidence, "strength_counts", {})
                    top_entities = getattr(evidence, "top_technical_entities", [])
                    
                    critical_count = len([x for x in captured_items if x.strength == "CRITICAL"])
                    strong_count = len([x for x in captured_items if x.strength == "STRONG"])
                    ignored_count = len([x for x in captured_items if x.strength == "IGNORE"])
                    
                    dup_count = sum(max(0, x.occurrence_count - 1) for x in captured_items)
                    
                    trace.technical_evidence = TechnicalEvidenceCaptured(
                        technical_evidence=captured_items,
                        evidence_type_counts=type_counts,
                        strength_counts=strength_counts,
                        top_technical_entities=top_entities,
                        critical_evidence_count=critical_count,
                        strong_evidence_count=strong_count,
                        ignored_evidence_count=ignored_count,
                        duplicate_evidence_count=dup_count,
                        additional_llm_calls_from_evidence_extraction=llm_calls_delta,
                        technical_evidence_extraction_ms=dur * 1000.0,
                        technical_evidence_capture_status=capture_status
                    )
                    
                    # Capture Stage 12.2.2 Classification Reconciliation telemetry
                    recon_res = getattr(evidence, "reconciliation_result", None)
                    if recon_res:
                        trace.classification_reconciliation = ClassificationReconciliationCaptured(
                            original_category=recon_res.original_category,
                            original_subsystem=recon_res.original_subsystem,
                            resolved_category=recon_res.resolved_category,
                            resolved_subsystem=recon_res.resolved_subsystem,
                            decision=recon_res.decision,
                            confidence_score=recon_res.confidence_score,
                            evidence_entities=recon_res.evidence_entities,
                            conflicting_evidence_count=len(recon_res.conflicting_evidence),
                            supporting_evidence_count=len(recon_res.supporting_evidence),
                            rationale=recon_res.rationale,
                            additional_llm_calls_from_reconciliation=0,
                            classification_reconciliation_ms=0.1,
                            capture_status="CAPTURED"
                        )
                    else:
                        trace.classification_reconciliation = ClassificationReconciliationCaptured(
                            capture_status="NOT_OBSERVED"
                        )
                    
                    trace.timings["understanding_evidence"] = dur
        return intel, evidence

    @functools.wraps(orig_extract_context)
    def wrapped_extract_context(self, repo_summary, repository_map, issue_intel):
        t0 = time.perf_counter()
        res = orig_extract_context(self, repo_summary, repository_map, issue_intel)
        dur = time.perf_counter() - t0
        
        issue_number = getattr(_eval_thread_local, "current_issue_number", None)
        if issue_number:
            with lock:
                trace = next((t for t in report.issues if t.issue_number == issue_number), None)
                if trace:
                    trace.repo_context = {
                        "relevant_summary": res.relevant_summary,
                        "relevant_technologies": res.relevant_technologies,
                        "architectural_notes": res.architectural_notes,
                        "relevant_directories": res.relevant_directories,
                        "relevant_modules": res.relevant_modules,
                    }
                    trace.timings["repo_context"] = dur
        return res

    @functools.wraps(orig_rank)
    def wrapped_rank(self, *args, **kwargs):
        t0 = time.perf_counter()
        res = orig_rank(self, *args, **kwargs)
        dur = time.perf_counter() - t0
        
        issue_number = getattr(_eval_thread_local, "current_issue_number", None)
        if issue_number:
            with lock:
                trace = next((t for t in report.issues if t.issue_number == issue_number), None)
                if trace:
                    trace.candidate_evidence = {
                        "candidates": [
                            {
                                "path": c.get("path"),
                                "score": c.get("score"),
                                "subsystem_match": c.get("subsystem_match"),
                                "technology_match": c.get("technology_match"),
                                "keyword_match": c.get("keyword_match"),
                                "reasons": c.get("reasons", []),
                                "explanation": c.get("explanation")
                            }
                            for c in res.candidates
                        ]
                    }
                    trace.timings["candidate_ranking"] = dur
        return res

    @functools.wraps(orig_assemble)
    def wrapped_assemble(self, *args, **kwargs):
        t0 = time.perf_counter()
        prompt = orig_assemble(self, *args, **kwargs)
        dur = time.perf_counter() - t0
        
        issue_number = getattr(_eval_thread_local, "current_issue_number", None)
        if issue_number:
            with lock:
                trace = next((t for t in report.issues if t.issue_number == issue_number), None)
                if trace:
                    # Map position args
                    kwargs_keys = [
                        "repo_name", "repo_desc", "repo_context", "candidate_evidence", "candidate_dirs",
                        "issue_intel", "issue_evidence", "readme_raw", "contributing_raw", "issue_body",
                        "issue_labels_str", "comments", "instructions_text", "json_schema_text",
                        "include_map", "include_comments", "compress_readme", "compress_contributing",
                        "include_readme", "include_contributing"
                    ]
                    params = {}
                    for idx, key in enumerate(kwargs_keys):
                        if key in kwargs:
                            params[key] = kwargs[key]
                        elif idx < len(args):
                            params[key] = args[idx]
                            
                    attempt_num = len(trace.attempts) + 1
                    
                    # Deduce removed and remaining context based on budget degradation level
                    removed_ctx = "None"
                    remaining_ctx = "README, CONTRIBUTING, COMMENTS, REPOSITORY MAP"
                    if attempt_num == 2:
                        removed_ctx = "COMMENTS"
                        remaining_ctx = "README, CONTRIBUTING, REPOSITORY MAP"
                    elif attempt_num == 3:
                        removed_ctx = "COMMENTS (Removed), README/CONTRIBUTING (Compressed)"
                        remaining_ctx = "README (Compressed), CONTRIBUTING (Compressed), REPOSITORY MAP"
                    elif attempt_num >= 4:
                        removed_ctx = "COMMENTS, README, CONTRIBUTING, REPOSITORY MAP"
                        remaining_ctx = "None (Minimal Mode)"
                        
                    attempt = IssueGuidanceAttempt(
                        attempt_number=attempt_num,
                        prompt=prompt,
                        prompt_tokens=estimate_tokens(prompt),
                        status="Budget Exceeded",
                        include_readme=params.get("include_readme", False),
                        include_contributing=params.get("include_contributing", False),
                        include_comments=params.get("include_comments", False),
                        include_map=params.get("include_map", False),
                        compress_readme=params.get("compress_readme", False),
                        compress_contributing=params.get("compress_contributing", False),
                        removed_context=removed_ctx,
                        remaining_context=remaining_ctx
                    )
                    trace.attempts.append(attempt)
                    trace.timings[f"prompt_assembly_attempt_{attempt_num}"] = dur
                    
                    if "candidate_dirs" in params:
                        trace.candidate_dirs = params["candidate_dirs"]
                    
                    eval_logger.info("Prompt Built for Issue #%d Attempt %d. Length: %d chars.", issue_number, attempt_num, len(prompt))
                    if attempt.prompt_tokens > 1500:
                        eval_logger.info("Prompt Compressed/Degraded: Issue #%d Attempt %d budget exceeded.", issue_number, attempt_num)
                    else:
                        eval_logger.info("Attempt Selected: Issue #%d Attempt %d fits budget.", issue_number, attempt_num)
                        
        return prompt

    @functools.wraps(orig_ground)
    def wrapped_ground(self, response, all_files, all_dirs, candidate_evidence, issue_intel):
        eval_logger.info("Grounding validation triggered.")
        t0 = time.perf_counter()
        
        rec_files_before = list(response.get("exploration_hints", {}).get("possible_files", []))
        rec_dirs_before = list(response.get("exploration_hints", {}).get("likely_directories", []))
        
        conf_before = float(response.get("exploration_hints", {}).get("confidence", 0.0))
        if not conf_before and "analysis" in response:
            conf_before = float(response.get("analysis", {}).get("confidence_score", 0.0))
            
        res = orig_ground(self, response, all_files, all_dirs, candidate_evidence, issue_intel)
        dur = time.perf_counter() - t0
        
        rec_files_after = list(res.get("exploration_hints", {}).get("possible_files", []))
        rec_dirs_after = list(res.get("exploration_hints", {}).get("likely_directories", []))
        
        conf_after = float(res.get("exploration_hints", {}).get("confidence", 0.0))
        if not conf_after and "analysis" in res:
            conf_after = float(res.get("analysis", {}).get("confidence_score", 0.0))
            
        existing_files = [f for f in rec_files_before if f in rec_files_after]
        removed_files = [f for f in rec_files_before if f not in rec_files_after]
        
        existing_dirs = [d for d in rec_dirs_before if d in rec_dirs_after]
        removed_dirs = [d for d in rec_dirs_before if d not in rec_dirs_after]
        
        issue_number = getattr(_eval_thread_local, "current_issue_number", None)
        if issue_number:
            with lock:
                trace = next((t for t in report.issues if t.issue_number == issue_number), None)
                if trace:
                    trace.grounding_stats = GroundingValidationStats(
                        recommended_files=rec_files_before,
                        existing_files=existing_files,
                        removed_files=removed_files,
                        recommended_directories=rec_dirs_before,
                        existing_directories=existing_dirs,
                        removed_directories=removed_dirs,
                        confidence_before=conf_before,
                        confidence_after=conf_after
                    )
                    trace.timings["grounding_validation"] = dur
                    
        eval_logger.info("Grounding completed. Removed %d files, %d directories.", len(removed_files), len(removed_dirs))
        return res

    @functools.wraps(orig_normalize)
    def wrapped_normalize(self, response, fallback_affected_area):
        eval_logger.info("Normalization triggered.")
        t0 = time.perf_counter()
        res = orig_normalize(self, response, fallback_affected_area)
        dur = time.perf_counter() - t0
        
        issue_number = getattr(_eval_thread_local, "current_issue_number", None)
        if issue_number:
            with lock:
                trace = next((t for t in report.issues if t.issue_number == issue_number), None)
                if trace:
                    trace.normalized_json = res
                    trace.timings["normalization"] = dur
        eval_logger.info("Normalization completed.")
        return res

    # --- CacheManager Interceptors ---
    @functools.wraps(orig_cache_get)
    def wrapped_cache_get(self, key: str):
        if bypass_cache:
            with lock:
                report.cache.misses += 1
            eval_logger.info("Cache lookup for key %s: BYPASS MISS", key)
            return None
            
        start_time = time.perf_counter()
        res = orig_cache_get(self, key)
        dur_ms = (time.perf_counter() - start_time) * 1000.0
        
        with lock:
            report.cache.lookup_time_ms += dur_ms
            if res is not None:
                report.cache.hits += 1
                eval_logger.info("Cache lookup for key %s: HIT", key)
            else:
                report.cache.misses += 1
                eval_logger.info("Cache lookup for key %s: MISS", key)
        return res

    @functools.wraps(orig_cache_set)
    def wrapped_cache_set(self, key: str, value: Any, ttl: Optional[int] = None):
        start_time = time.perf_counter()
        res = orig_cache_set(self, key, value, ttl)
        dur_ms = (time.perf_counter() - start_time) * 1000.0
        
        with lock:
            report.cache.writes += 1
            report.cache.write_time_ms += dur_ms
        eval_logger.info("Cache write for key %s successfully.", key)
        return res

    # --- Install Interceptors ---
    groq.resources.chat.completions.Completions.create = wrapped_groq_create
    LLMService.generate_json = wrapped_generate_json
    RepositorySummaryService.generate_summary = wrapped_summary_gen
    RepositoryMapService.generate_map = wrapped_map_gen
    RoadmapService.analyze_roadmap = wrapped_roadmap_analyze
    
    GitHubService.get_repository_tree = wrapped_github_tree
    GitHubService.get_repo_metadata = wrapped_github_meta
    GitHubService.get_readme = wrapped_github_readme
    GitHubService.get_contributing = wrapped_github_contrib
    GitHubService.get_good_first_issues = wrapped_github_issues
    GitHubService.get_issue_comments = wrapped_github_comments
    
    IssueGuidanceService.generate_guidance = wrapped_guidance_gen
    IssueGuidanceService._understand_issue = wrapped_understand
    IssueGuidanceService._extract_repository_context = wrapped_extract_context
    IssueGuidanceService._rank_candidates = wrapped_rank
    IssueGuidanceService._assemble_prompt = wrapped_assemble
    IssueGuidanceService._ground_and_validate_guidance = wrapped_ground
    IssueGuidanceService.normalize_guidance_response = wrapped_normalize
    
    CacheManager.get = wrapped_cache_get
    CacheManager.set = wrapped_cache_set
    
    # Store cache backend name
    try:
        from app.core.cache.dependencies import get_cache_manager
        cm = get_cache_manager()
        report.cache.backend_name = cm.backend_name
    except Exception:
        pass

    try:
        yield
    finally:
        # --- Restore Original Methods ---
        groq.resources.chat.completions.Completions.create = orig_groq_create
        LLMService.generate_json = orig_generate_json
        RepositorySummaryService.generate_summary = orig_summary_gen
        RepositoryMapService.generate_map = orig_map_gen
        RoadmapService.analyze_roadmap = orig_roadmap_analyze
        
        GitHubService.get_repository_tree = orig_github_tree
        GitHubService.get_repo_metadata = orig_github_meta
        GitHubService.get_readme = orig_github_readme
        GitHubService.get_contributing = orig_github_contrib
        GitHubService.get_good_first_issues = orig_github_issues
        GitHubService.get_issue_comments = orig_github_comments
        
        IssueGuidanceService.generate_guidance = orig_guidance_gen
        IssueGuidanceService._understand_issue = orig_understand
        IssueGuidanceService._extract_repository_context = orig_extract_context
        IssueGuidanceService._rank_candidates = orig_rank
        IssueGuidanceService._assemble_prompt = orig_assemble
        IssueGuidanceService._ground_and_validate_guidance = orig_ground
        IssueGuidanceService.normalize_guidance_response = orig_normalize
        
        CacheManager.get = orig_cache_get
        CacheManager.set = orig_cache_set
        
        # Remove logging handler
        logging.getLogger().removeHandler(log_handler)
