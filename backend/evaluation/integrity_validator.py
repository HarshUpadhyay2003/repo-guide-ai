import json
import logging
from typing import List, Tuple
from evaluation.benchmark_models import EvaluationReport

logger = logging.getLogger(__name__)

def validate_integrity(report: EvaluationReport) -> Tuple[str, List[str]]:
    """Inspect the generated evaluation model for logical contradictions.
    
    Returns:
        A tuple of (status, findings) where status is "PASS", "WARN", or "FAIL".
    """
    findings = []
    status = "PASS"

    # 1. successful LLM call + empty raw response capture
    for trace in report.issues:
        if trace.final_guidance_json and not trace.raw_llm_response:
            findings.append(f"FAIL: Issue #{trace.issue_number} has final_guidance_json but raw_llm_response is empty.")
            status = "FAIL"

    # 2. successful summary + summary_score == 0
    if report.summary.raw_json and report.metrics_scores.summary_score == 0.0:
        findings.append("FAIL: Repository summary is present but summary_score is 0.0.")
        status = "FAIL"

    # 3. production prompt exists + prompt_tokens reported as 0/default
    for trace in report.issues:
        for att in trace.attempts:
            if att.prompt and att.prompt_tokens <= 0:
                findings.append(f"FAIL: Issue #{trace.issue_number} Attempt {att.attempt_number} prompt is present but prompt_tokens is {att.prompt_tokens}.")
                status = "FAIL"

    # 4. total runtime observed + runtime == 0.0
    if report.total_runtime == 0.0:
        findings.append("FAIL: Total runtime is 0.0.")
        status = "FAIL"

    # 5. Repository Summary has repository_purpose + prompt says "No purpose description available"
    summary_section = report.summary.raw_json.get("summary", {}) if "summary" in report.summary.raw_json else report.summary.raw_json
    purpose = summary_section.get("repository_purpose", "") if isinstance(summary_section, dict) else ""
    if purpose and purpose != "No purpose description available.":
        for trace in report.issues:
            for att in trace.attempts:
                if "No purpose description available" in att.prompt:
                    findings.append(f"FAIL: Repository summary has purpose but Issue #{trace.issue_number} Attempt {att.attempt_number} prompt contains fallback 'No purpose description available'.")
                    status = "FAIL"

    # 6. tech_stack populated + prompt Relevant Technologies blank without valid reason
    tech_stack = summary_section.get("tech_stack", []) if isinstance(summary_section, dict) else []
    for trace in report.issues:
        intel_techs = trace.issue_intel.get("technologies", [])
        common_techs = [t for t in tech_stack if t.lower() in [it.lower() for it in intel_techs]]
        if common_techs:
            for att in trace.attempts:
                if "Relevant Technologies:" in att.prompt and "Relevant Technologies: \n" in att.prompt:
                    findings.append(f"WARN: Issue #{trace.issue_number} Attempt {att.attempt_number} has common technologies but 'Relevant Technologies' appears blank in prompt.")
                    if status != "FAIL":
                        status = "WARN"

    # 7. sent_to_llm prompt count != actual successful LLM call count
    for trace in report.issues:
        sent_prompts_count = sum(1 for att in trace.attempts if getattr(att, "sent_to_llm", False))
        if trace.final_guidance_json and trace.final_guidance_json.get("guidance_source", "llm") == "llm" and sent_prompts_count != 1:
            findings.append(f"FAIL: Issue #{trace.issue_number} guidance is LLM-generated but sent_to_llm count is {sent_prompts_count} (expected 1).")
            status = "FAIL"

    if not findings:
        findings.append("PASS: No evaluation integrity contradictions detected.")

    return status, findings
