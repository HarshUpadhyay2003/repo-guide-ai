import os
import csv
import json
import logging
from typing import Any, Dict, List
from evaluation.benchmark_models import EvaluationReport, IssueGuidanceTrace, PDFStats
from app.utils.performance_utils import estimate_tokens

logger = logging.getLogger(__name__)

class MarkdownWriter:
    """Formatter and writer for V2 conformed Markdown reports, CSV summaries, and dashboards."""

    @staticmethod
    def save_artifacts(report: EvaluationReport, output_dir: str) -> Dict[str, Any]:
        """Save raw prompts, LLM responses, JSONs, PDFs, and metrics to target subdirectories."""
        repo_name = report.repo_metadata.name.replace(".git", "")
        repo_dir = os.path.join(output_dir, repo_name)
        
        # Define subdirectories
        dirs = {
            "prompts": os.path.join(repo_dir, "prompts"),
            "llm": os.path.join(repo_dir, "llm"),
            "json": os.path.join(repo_dir, "json"),
            "pdf": os.path.join(repo_dir, "pdf"),
            "metrics": os.path.join(repo_dir, "metrics"),
            "github": os.path.join(repo_dir, "github"),
            "logs": os.path.join(repo_dir, "logs")
        }
        
        for d in dirs.values():
            os.makedirs(d, exist_ok=True)

        artifact_filenames = {}

        # 1. Save Prompts
        artifact_filenames["prompts"] = []
        for trace in report.issues:
            issue_num = trace.issue_number
            for att in trace.attempts:
                p_file = f"issue_{issue_num}_attempt_{att.attempt_number}.txt"
                p_path = os.path.join(dirs["prompts"], p_file)
                with open(p_path, "w", encoding="utf-8") as f:
                    f.write(att.prompt)
                artifact_filenames["prompts"].append(f"prompts/{p_file}")

        # 2. Save LLM Responses
        artifact_filenames["llm"] = []
        for trace in report.issues:
            issue_num = trace.issue_number
            llm_file = f"issue_{issue_num}_llm_response.json"
            llm_path = os.path.join(dirs["llm"], llm_file)
            with open(llm_path, "w", encoding="utf-8") as f:
                json.dump({
                    "raw_text": trace.raw_llm_response,
                    "parsed_json": trace.parsed_json,
                    "normalized_json": trace.normalized_json
                }, f, indent=2)
            artifact_filenames["llm"].append(f"llm/{llm_file}")

        # 3. Save JSON response components
        artifact_filenames["json"] = []
        json_components = {
            "metadata.json": report.repo_metadata.model_dump(),
            "summary.json": report.summary.raw_json,
            "map.json": report.repo_map.map_json,
            "roadmap.json": report.roadmap.raw_json
        }
        for name, data in json_components.items():
            f_path = os.path.join(dirs["json"], name)
            with open(f_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            artifact_filenames["json"].append(f"json/{name}")

        # 4. Copy generated PDFs to pdf/ directory
        artifact_filenames["pdf"] = []
        for pdf in report.pdfs:
            if pdf.file_path and os.path.exists(pdf.file_path):
                dest_path = os.path.join(dirs["pdf"], os.path.basename(pdf.file_path))
                try:
                    with open(pdf.file_path, "rb") as src, open(dest_path, "wb") as dst:
                        dst.write(src.read())
                    pdf.file_path = dest_path
                    artifact_filenames["pdf"].append(f"pdf/{os.path.basename(dest_path)}")
                except Exception as e:
                    logger.warning("Could not copy PDF file: %s", e)

        # 5. Save Metrics scores
        artifact_filenames["metrics"] = ["metrics/scores.json"]
        m_path = os.path.join(dirs["metrics"], "scores.json")
        with open(m_path, "w", encoding="utf-8") as f:
            json.dump(report.metrics_scores.model_dump(), f, indent=2)

        # 6. Save GitHub Ground Truths
        artifact_filenames["github"] = []
        for issue_num, gt in report.ground_truths.items():
            gt_file = f"issue_{issue_num}_ground_truth.json"
            gt_path = os.path.join(dirs["github"], gt_file)
            with open(gt_path, "w", encoding="utf-8") as f:
                json.dump(gt.model_dump(), f, indent=2)
            artifact_filenames["github"].append(f"github/{gt_file}")

        return artifact_filenames

    @staticmethod
    def write_report(report: EvaluationReport, output_dir: str, artifact_files: Dict[str, Any]) -> str:
        """Write the comprehensive conformed V2 Markdown report conformed to 20 sections."""
        from evaluation.comparison_utils import compare_issue_predictions, infer_actual_difficulty
        
        repo_name = report.repo_metadata.name.replace(".git", "")
        repo_dir = os.path.join(output_dir, repo_name)
        os.makedirs(repo_dir, exist_ok=True)

        report_path = os.path.join(repo_dir, f"{repo_name}_Evaluation.md")
        
        with open(report_path, "w", encoding="utf-8") as md:
            md.write(f"# RepoPilot V2 Live Production Evaluation Report: {repo_name}\n\n")

            # 1. Repository Metadata
            md.write("## 1. Repository Metadata\n\n")
            md.write(f"| Attribute | Value |\n")
            md.write(f"| --- | --- |\n")
            md.write(f"| **Repository** | {report.repo_metadata.name} |\n")
            md.write(f"| **URL** | [{report.repo_metadata.url}]({report.repo_metadata.url}) |\n")
            md.write(f"| **Stars** | {report.repo_metadata.stars} |\n")
            md.write(f"| **Forks** | {report.repo_metadata.forks} |\n")
            md.write(f"| **Language** | {report.repo_metadata.language} |\n")
            md.write(f"| **Topics** | {', '.join(report.repo_metadata.topics) or 'None'} |\n")
            md.write(f"| **Repository Size** | {report.repo_metadata.size_kb} KB |\n")
            md.write(f"| **Total Files** | {report.repo_metadata.total_files} |\n")
            md.write(f"| **Total Directories** | {report.repo_metadata.total_directories} |\n")
            md.write(f"| **README Size** | {report.repo_metadata.readme_size_bytes} Bytes |\n")
            md.write(f"| **Contributing Present** | {'Yes' if report.repo_metadata.contributing_present else 'No'} |\n\n")

            # 2. Repository Summary
            md.write("## 2. Repository Summary\n\n")
            md.write(f"- **Timing**: {report.summary.timing:.2f} s\n")
            md.write(f"- **Prompt Tokens**: {report.summary.prompt_tokens}\n")
            md.write(f"- **Response Tokens**: {report.summary.response_tokens}\n")
            md.write(f"- **Model Used**: {report.summary.model}\n\n")
            md.write("### Pretty Formatted Summary\n")
            md.write(f"```json\n{report.summary.pretty_formatted}\n```\n\n")

            # 3. Repository Map
            md.write("## 3. Repository Map\n\n")
            md.write(f"- **Timing**: {report.repo_map.timing:.2f} s\n")
            md.write(f"- **Important Directories**: {', '.join(report.repo_map.important_directories) or 'None'}\n\n")
            md.write("### Categorized Folders Map\n")
            md.write("```json\n" + json.dumps(report.repo_map.categorized_folders, indent=2) + "\n```\n\n")

            # 4. Issue List
            md.write("## 4. Issue List\n\n")
            for trace in report.issues:
                issue = trace.issue_payload
                md.write(f"### Issue #{trace.issue_number}: {trace.title}\n\n")
                md.write(f"- **URL**: https://github.com/{report.repo_metadata.url.split('/')[-2]}/{report.repo_metadata.url.split('/')[-1]}/issues/{trace.issue_number}\n")
                md.write(f"- **Labels**: {', '.join(issue.get('labels', [])) or 'None'}\n")
                md.write(f"- **Difficulty**: {trace.issue_intel.get('difficulty', 'Beginner')}\n\n")
                md.write(f"**Description Snippet**:\n")
                body = issue.get('body') or 'No description'
                md.write(f"{body[:400]}...\n\n")

            # 5. Issue Intelligence (Stage 12.1 Internal Objects conformed format)
            md.write("## 5. Issue Intelligence\n\n")
            for trace in report.issues:
                md.write(f"### Issue #{trace.issue_number} Internal Intelligence\n\n")
                
                # A. Issue Intelligence
                intel = trace.issue_intel
                md.write("#### Issue Intelligence\n")
                md.write(f"- **Category**: {intel.get('category', 'None')}\n")
                md.write(f"- **Intent**: {intel.get('intent', 'None')}\n")
                md.write(f"- **Subsystem**: {intel.get('subsystem', 'None')}\n")
                md.write(f"- **Technologies**: {', '.join(intel.get('technologies', [])) or 'None'}\n")
                md.write(f"- **Keywords**: {', '.join(intel.get('keywords', [])) or 'None'}\n")
                md.write(f"- **Difficulty**: {intel.get('difficulty', 'Beginner')}\n")
                md.write(f"- **Implementation Hints**:\n")
                for hint in intel.get('implementation_hints', []):
                    md.write(f"  - {hint}\n")
                md.write("\n")

                # B. Issue Evidence
                evidence = trace.issue_evidence
                md.write("#### Issue Evidence\n")
                md.write(f"- **Evidence Items**:\n")
                for item in evidence.get('evidence', []):
                    md.write(f"  - {item}\n")
                md.write(f"- **Matched Labels**: {', '.join(evidence.get('matched_labels', [])) or 'None'}\n")
                md.write(f"- **Matched Keywords**: {', '.join(evidence.get('matched_keywords', [])) or 'None'}\n")
                md.write(f"- **Detected Stack**: {', '.join(evidence.get('detected_stack', [])) or 'None'}\n")
                md.write(f"- **Explicit Paths**: {', '.join(evidence.get('explicit_paths', [])) or 'None'}\n\n")

                # E. Stage 12.2.1 — Technical Evidence
                te_captured = getattr(trace, "technical_evidence", None)
                md.write("#### Stage 12.2.1 — Technical Evidence\n\n")
                if te_captured:
                    md.write(f"- **Capture Status**: {te_captured.technical_evidence_capture_status}\n")
                    md.write(f"- **Total Evidence Items**: {len(te_captured.technical_evidence)}\n")
                    md.write(f"- **Critical Evidence Count**: {te_captured.critical_evidence_count}\n")
                    md.write(f"- **Strong Evidence Count**: {te_captured.strong_evidence_count}\n")
                    md.write(f"- **Ignored Evidence Count**: {te_captured.ignored_evidence_count}\n")
                    md.write(f"- **Duplicate Evidence Count**: {te_captured.duplicate_evidence_count}\n")
                    md.write(f"- **Additional LLM Calls Delta**: {te_captured.additional_llm_calls_from_evidence_extraction}\n")
                    md.write(f"- **Extraction Time**: {te_captured.technical_evidence_extraction_ms:.2f} ms\n")
                    md.write(f"- **Top Technical Entities**: {', '.join(te_captured.top_technical_entities) or 'None'}\n")
                    md.write(f"- **Evidence Counts by Type**: {te_captured.evidence_type_counts}\n")
                    md.write(f"- **Evidence Counts by Strength**: {te_captured.strength_counts}\n\n")
                    
                    md.write("| Strength | Evidence Type | Source | Evidence Text / Normalized Value | Technical Entities | Rationale |\n")
                    md.write("| --- | --- | --- | --- | --- | --- |\n")
                    for item in te_captured.technical_evidence:
                        escaped_text = item.text.replace("|", "\\|").replace("\n", " ")
                        escaped_norm = item.normalized_value.replace("|", "\\|").replace("\n", " ")
                        text_val = escaped_text
                        if escaped_norm and escaped_norm != escaped_text:
                            text_val = f"`{escaped_norm}`<br><span style='font-size:0.8em;color:gray;'>{escaped_text}</span>"
                        entities_str = ", ".join(f"`{e}`" for e in item.technical_entities) or "None"
                        source_str = item.source
                        if item.source_index is not None:
                            source_str += f" (Index: {item.source_index})"
                        md.write(f"| **{item.strength}** | {item.evidence_type} | {source_str} | {text_val} | {entities_str} | {item.rationale} |\n")
                    md.write("\n")
                else:
                    md.write("*No technical evidence captured.*\n\n")

                # F. Stage 12.2.2 — Classification Reconciliation
                recon_captured = getattr(trace, "classification_reconciliation", None)
                md.write("#### Stage 12.2.2 — Classification Reconciliation\n\n")
                if recon_captured and recon_captured.capture_status != "NOT_OBSERVED":
                    md.write(f"- **Capture Status**: {recon_captured.capture_status}\n")
                    md.write(f"- **Decision**: **{recon_captured.decision}**\n")
                    md.write(f"- **Confidence Score**: {recon_captured.confidence_score:.1f}\n")
                    md.write(f"- **Original Classification**: `{recon_captured.original_category}` (Subsystem: `{recon_captured.original_subsystem or 'None'}`)\n")
                    md.write(f"- **Resolved Classification**: `{recon_captured.resolved_category}` (Subsystem: `{recon_captured.resolved_subsystem or 'None'}`)\n")
                    md.write(f"- **Conflicting Evidence Items**: {recon_captured.conflicting_evidence_count}\n")
                    md.write(f"- **Supporting Evidence Items**: {recon_captured.supporting_evidence_count}\n")
                    md.write(f"- **Reconciliation Latency**: {recon_captured.classification_reconciliation_ms:.2f} ms\n")
                    md.write(f"- **Additional LLM Calls**: {recon_captured.additional_llm_calls_from_reconciliation}\n")
                    md.write(f"- **Rationale**: {recon_captured.rationale}\n")
                    md.write(f"- **Entities involved**: {', '.join(recon_captured.evidence_entities) or 'None'}\n\n")
                else:
                    md.write("*No classification reconciliation telemetry captured.*\n\n")

                # G. Stage 12.2.3 — Evidence-Priority Context Budgeting
                budget_captured = getattr(trace, "context_budgeting", None)
                md.write("#### Stage 12.2.3 — Evidence-Priority Context Budgeting\n\n")
                if budget_captured and budget_captured.capture_status != "NOT_OBSERVED":
                    md.write(f"- **Capture Status**: {budget_captured.capture_status}\n")
                    md.write(f"- **Budget Status**: **{budget_captured.budget_status}**\n\n")
                    
                    md.write("| Metric | Value |\n")
                    md.write("| --- | --- |\n")
                    md.write(f"| **Budget Limit** | {budget_captured.budget_limit} |\n")
                    md.write(f"| **Selected Attempt** | {budget_captured.selected_attempt} |\n")
                    md.write(f"| **Selected Mode** | {budget_captured.selected_mode} |\n")
                    md.write(f"| **Estimated Prompt Tokens** | {budget_captured.estimated_prompt_tokens} |\n")
                    md.write(f"| **Static Template Tokens** | {budget_captured.static_template_tokens} |\n")
                    md.write(f"| **Dynamic Context Tokens** | {budget_captured.dynamic_context_tokens} |\n")
                    md.write(f"| **Protected Core Integrity** | {budget_captured.protected_core_integrity_status} |\n")
                    md.write(f"| **Emergency Core Used** | {budget_captured.emergency_core_used} |\n")
                    md.write(f"| **Additional LLM Calls** | {budget_captured.additional_llm_calls_from_context_budgeting} |\n")
                    md.write(f"| **Budgeting Latency** | {budget_captured.context_budgeting_ms:.2f} ms |\n\n")
                    
                    md.write(f"- **Included Sections**: {', '.join(budget_captured.included_sections) or 'None'}\n")
                    md.write(f"- **Removed Sections**: {', '.join(budget_captured.removed_sections) or 'None'}\n\n")
                    
                    md.write("**Evidence Preservation Metrics:**\n")
                    md.write(f"- Critical Evidence: {budget_captured.critical_evidence_available_count} available / {budget_captured.critical_evidence_included_count} included\n")
                    md.write(f"- Strong Evidence: {budget_captured.strong_evidence_available_count} available / {budget_captured.strong_evidence_included_count} included\n")
                    md.write(f"- Explicit Paths: {budget_captured.explicit_paths_available_count} available / {budget_captured.explicit_paths_included_count} included\n")
                    md.write(f"- Candidate Files: {budget_captured.candidate_files_available_count} available / {budget_captured.candidate_files_included_count} included\n\n")
                    
                    md.write("**Included Candidate File Paths:**\n")
                    if budget_captured.candidate_files_included:
                        for path in budget_captured.candidate_files_included:
                            md.write(f"- `{path}`\n")
                    else:
                        md.write("- *None*\n")
                    md.write("\n")
                else:
                    md.write("*No context budgeting telemetry captured.*\n\n")

                # C. Repository Context
                ctx = trace.repo_context
                md.write("#### Repository Context\n")
                md.write(f"- **Relevant Summary**: {ctx.get('relevant_summary', 'None')}\n")
                md.write(f"- **Relevant Technologies**: {', '.join(ctx.get('relevant_technologies', [])) or 'None'}\n")
                md.write(f"- **Relevant Modules**: {', '.join(ctx.get('relevant_modules', [])) or 'None'}\n")
                md.write(f"- **Relevant Directories**: {', '.join(ctx.get('relevant_directories', [])) or 'None'}\n")
                md.write(f"- **Architecture Notes**: {ctx.get('architectural_notes', 'None')}\n\n")

                # D. Candidate Evidence Table
                md.write("#### Candidate Evidence\n")
                candidates = trace.candidate_evidence.get("candidates", [])
                md.write("| Candidate File | Score | Subsystem Match | Technology Match | Keyword Match | Ranking Reason |\n")
                md.write("| --- | --- | --- | --- | --- | --- |\n")
                for c in candidates[:10]: # Top 10
                    tech_match = ", ".join(c.get("technology_match", [])) or "None"
                    kw_match = ", ".join(c.get("keyword_match", [])) or "None"
                    md.write(f"| `{c.get('path')}` | {c.get('score')} | {c.get('subsystem_match')} | {tech_match} | {kw_match} | {c.get('explanation')} |\n")
                md.write("\n")

            # 6. Prompt Attempts
            md.write("## 6. Prompt Attempts\n\n")
            for trace in report.issues:
                md.write(f"### Issue #{trace.issue_number} Prompt Attempts\n\n")
                for att in trace.attempts:
                    is_selected = " (SELECTED ATTEMPT)" if trace.successful_attempt == att.attempt_number else ""
                    md.write(f"#### Attempt {att.attempt_number}{is_selected}\n")
                    md.write(f"- **Tokens**: {att.prompt_tokens}\n")
                    md.write(f"- **Compression Stage**: Attempt {att.attempt_number}\n")
                    md.write(f"- **Removed Context**: {att.removed_context}\n")
                    md.write(f"- **Remaining Context**: {att.remaining_context}\n\n")
                    md.write(f"<details>\n<summary>View Rendered Prompt</summary>\n\n")
                    md.write(f"```\n{att.prompt}\n```\n\n")
                    md.write("</details>\n\n")

            # 7. Prompt Statistics
            md.write("## 7. Prompt Statistics\n\n")
            for trace in report.issues:
                md.write(f"### Issue #{trace.issue_number} Prompt Statistics\n\n")
                succ_attempt_idx = trace.successful_attempt - 1 if (trace.successful_attempt and trace.successful_attempt <= len(trace.attempts)) else None
                if succ_attempt_idx is not None:
                    att = trace.attempts[succ_attempt_idx]
                    first_att = trace.attempts[0]
                    comp_ratio = att.prompt_tokens / first_att.prompt_tokens if first_att.prompt_tokens > 0 else 1.0
                    md.write(f"- **Selected Attempt**: Attempt {trace.successful_attempt}\n")
                    md.write(f"- **Prompt Length**: {len(att.prompt)} characters\n")
                    md.write(f"- **Prompt Tokens**: {att.prompt_tokens}\n")
                    md.write(f"- **Compression Stage**: {trace.successful_attempt}\n")
                    md.write(f"- **Removed Context**: {att.removed_context}\n")
                    md.write(f"- **Remaining Context**: {att.remaining_context}\n")
                    md.write(f"- **Compression Ratio**: {comp_ratio:.2%}\n\n")
                else:
                    md.write("No successful prompt attempt (Graceful fallback used).\n\n")

            # 8. Raw LLM Output
            md.write("## 8. Raw LLM Output\n\n")
            for trace in report.issues:
                md.write(f"### Issue #{trace.issue_number} Raw Outputs\n\n")
                md.write("#### Raw Response\n")
                md.write(f"```\n{trace.raw_llm_response}\n```\n\n")
                md.write("#### Parsed JSON\n")
                md.write(f"```json\n{json.dumps(trace.parsed_json, indent=2)}\n```\n\n")

            # 9. Normalization
            md.write("## 9. Normalization\n\n")
            for trace in report.issues:
                md.write(f"### Issue #{trace.issue_number} Normalization\n\n")
                md.write(f"```json\n{json.dumps(trace.normalized_json, indent=2)}\n```\n\n")

            # 10. Grounding Validation
            md.write("## 10. Grounding Validation\n\n")
            for trace in report.issues:
                md.write(f"### Issue #{trace.issue_number} Grounding\n\n")
                stats = trace.grounding_stats
                if stats:
                    md.write(f"- **Confidence Before**: {stats.confidence_before}\n")
                    md.write(f"- **Confidence After**: {stats.confidence_after}\n")
                    md.write(f"- **Recommended Files**: {stats.recommended_files}\n")
                    md.write(f"- **Existing Files (Grounded)**: {stats.existing_files}\n")
                    md.write(f"- **Removed Files (Failed Grounding)**: {stats.removed_files}\n")
                    md.write(f"- **Recommended Directories**: {stats.recommended_directories}\n")
                    md.write(f"- **Existing Directories (Grounded)**: {stats.existing_directories}\n")
                    md.write(f"- **Removed Directories (Failed Grounding)**: {stats.removed_directories}\n\n")
                else:
                    md.write("No grounding stats recorded (Graceful fallback used).\n\n")

            # 11. Roadmap
            md.write("## 11. Roadmap\n\n")
            md.write(f"- **Roadmap Time**: {report.roadmap.timing:.2f} s\n\n")
            md.write("### Rendered Roadmap\n")
            md.write(f"```json\n{report.roadmap.rendered_roadmap}\n```\n\n")

            # 12. Generated PDFs
            md.write("## 12. Generated PDFs\n\n")
            md.write(f"| PDF Name | File Size (Bytes) | Generation Time (ms) | Output Path |\n")
            md.write(f"| --- | --- | --- | --- |\n")
            for pdf in report.pdfs:
                md.write(f"| {pdf.name} | {pdf.file_size_bytes} | {pdf.generation_time_ms} ms | `{os.path.basename(pdf.file_path)}` |\n")
            md.write("\n")

            # 13. Performance
            md.write("## 13. Performance\n\n")
            avg_guidance_dur = sum(t.timings.get("total", 0.0) for t in report.issues) / len(report.issues) if report.issues else 0.0
            sum_pdf_dur = sum(pdf.generation_time_ms for pdf in report.pdfs) / 1000.0
            md.write(f"- **Repository Summary Time**: {report.summary.timing:.2f} s\n")
            md.write(f"- **Repository Map Time**: {report.repo_map.timing:.2f} s\n")
            md.write(f"- **Issue Guidance Time (Average)**: {avg_guidance_dur:.2f} s\n")
            md.write(f"- **Roadmap Time**: {report.roadmap.timing:.2f} s\n")
            md.write(f"- **PDF Time (Total)**: {sum_pdf_dur:.2f} s\n")
            md.write(f"- **Total Runtime**: {report.total_runtime:.2f} s\n")
            md.write(f"- **Memory Usage**: {report.memory_usage_mb:.2f} MB\n")
            md.write(f"- **CPU Usage**: {report.cpu_usage_pct:.2f}%\n\n")

            # 14. Cache
            md.write("## 14. Cache\n\n")
            md.write(f"- **Cache Backend**: {report.cache.backend_name}\n")
            md.write(f"- **Cache Hits**: {report.cache.hits}\n")
            md.write(f"- **Cache Misses**: {report.cache.misses}\n")
            md.write(f"- **Cache Writes**: {report.cache.writes}\n")
            md.write(f"- **Lookup Time**: {report.cache.lookup_time_ms:.1f} ms\n")
            md.write(f"- **Write Time**: {report.cache.write_time_ms:.1f} ms\n\n")

            # 15. Errors
            md.write("## 15. Errors\n\n")
            md.write(f"- **GitHub API Errors**: {len(report.errors.github_errors)}\n")
            for err in report.errors.github_errors:
                md.write(f"  - `{err}`\n")
            md.write(f"- **LLM Generation Errors**: {len(report.errors.llm_errors)}\n")
            for err in report.errors.llm_errors:
                md.write(f"  - `{err}`\n")
            md.write(f"- **Validation Errors**: {len(report.errors.validation_errors)}\n")
            for err in report.errors.validation_errors:
                md.write(f"  - `{err}`\n")
            md.write(f"- **Groq API Retries**: {report.errors.retries}\n")
            md.write(f"- **Rate Limits Hit**: {report.errors.rate_limits}\n\n")

            # 16. GitHub Ground Truth
            md.write("## 16. GitHub Ground Truth\n\n")
            for trace in report.issues:
                gt = report.ground_truths.get(trace.issue_number)
                md.write(f"### Issue #{trace.issue_number} Ground Truth\n\n")
                if not gt or gt.state != "closed" or not gt.merged_pr_number:
                    md.write(f"**State**: {gt.state if gt else 'Unknown'}\n")
                    md.write(f"**Status**: {gt.status_text if gt else 'No merged PR available'}\n\n")
                else:
                    md.write(f"- **Merged PR**: #{gt.merged_pr_number} ([View PR]({gt.merged_pr_url}))\n")
                    md.write(f"- **PR Title**: {gt.pr_title}\n")
                    md.write(f"- **Closing Commit**: `{gt.closing_commit}`\n")
                    md.write(f"- **Commits Count**: {len(gt.commits)}\n")
                    md.write(f"- **Files Changed**: {gt.files_changed}\n")
                    md.write(f"- **Directories Changed**: {gt.directories_changed}\n")
                    md.write(f"- **Changed Languages**: {gt.changed_languages}\n\n")
                    md.write("<details>\n<summary>View PR Description</summary>\n\n")
                    md.write(f"{gt.pr_description or 'No PR description'}\n\n")
                    md.write("</details>\n\n")

            # 17. RepoPilot vs Ground Truth
            md.write("## 17. RepoPilot vs Ground Truth\n\n")
            for trace in report.issues:
                gt = report.ground_truths.get(trace.issue_number)
                md.write(f"### Issue #{trace.issue_number} Comparison\n\n")
                if not gt or getattr(gt, "ground_truth_status", "available") != "available":
                    md.write("Ground-truth comparison unavailable: issue is open and has no merged linked PR.\n\n")
                    continue

                hints = trace.final_guidance_json.get("exploration_hints", {}) if trace.final_guidance_json else {}
                pred_files = hints.get("possible_files", [])
                pred_dirs = hints.get("likely_directories", [])
                
                actual_diff = infer_actual_difficulty(len(gt.files_changed), len(gt.commits))
                cmp = compare_issue_predictions(
                    predicted_files=pred_files,
                    actual_files=gt.files_changed,
                    predicted_dirs=pred_dirs,
                    actual_dirs=gt.directories_changed,
                    predicted_techs=trace.issue_intel.get("technologies", []),
                    actual_techs=gt.changed_languages,
                    predicted_difficulty=trace.issue_intel.get("difficulty", "Beginner"),
                    actual_difficulty=actual_diff,
                    confidence_score=hints.get("confidence", 0.0)
                )

                md.write(f"| Attribute | Predicted | Ground Truth | Overlap / Match |\n")
                md.write(f"| --- | --- | --- | --- |\n")
                md.write(f"| **Files** | {pred_files} | {gt.files_changed} | Match count: {len(cmp['files']['matched'])} |\n")
                md.write(f"| **Directories** | {pred_dirs} | {gt.directories_changed} | Match count: {len(cmp['directories']['matched'])} |\n")
                md.write(f"| **Technologies** | {trace.issue_intel.get('technologies')} | {gt.changed_languages} | Overlap: {cmp['tech_matched']} |\n")
                md.write(f"| **Difficulty** | {trace.issue_intel.get('difficulty')} | {actual_diff} | {'Match' if cmp['difficulty_match'] else 'Mismatch'} |\n")
                md.write(f"| **Confidence** | {cmp['confidence_score']}% | N/A | N/A |\n\n")

                md.write("**Calculated Metrics**:\n")
                md.write(f"- **Directory Precision**: {cmp['directories']['precision']:.2%}\n")
                md.write(f"- **Directory Recall**: {cmp['directories']['recall']:.2%}\n")
                md.write(f"- **File Precision**: {cmp['files']['precision']:.2%}\n")
                md.write(f"- **File Recall**: {cmp['files']['recall']:.2%}\n")
                md.write(f"- **Overall Match %**: {cmp['overall_match_pct']:.2%}\n\n")

            # 18. Evaluation Metrics
            md.write("## 18. Evaluation Metrics\n\n")
            md.write(f"| Metric | Score (out of 10.0) | Description |\n")
            md.write(f"| --- | --- | --- |\n")
            md.write(f"| **Repository Summary Score** | {report.metrics_scores.summary_score} | Structure & main language presence |\n")
            md.write(f"| **Repository Map Score** | {report.metrics_scores.map_score} | Schema categories & mapped files coverage |\n")
            md.write(f"| **Issue Guidance Score** | {report.metrics_scores.guidance_score} | Attempt efficiency & guidance structure |\n")
            md.write(f"| **Candidate Ranking Score** | {report.metrics_scores.candidate_ranking_score} | Ground truth file presence in rank |\n")
            md.write(f"| **Grounding Score** | {report.metrics_scores.grounding_score} | Existence ratio of suggested items |\n")
            md.write(f"| **Roadmap Score** | {report.metrics_scores.roadmap_score} | Completeness & linked steps |\n")
            md.write(f"| **Overall Intelligence Score** | **{report.metrics_scores.overall_score}** | **Average of all evaluation metrics** |\n\n")

            # 19. Production Call Trace
            md.write("## 19. Production Call Trace\n\n")
            md.write("A step-by-step execution path of the POST /repo/analyze request:\n\n")
            
            md.write("| Stage | Duration | Cache | Input Summary | Output Summary |\n")
            md.write("| --- | --- | --- | --- | --- |\n")
            
            for event in report.production_trace:
                cache_text = event.cache_action or "N/A"
                inp_summary = event.input[:60] + "..." if event.input and len(event.input) > 60 else (event.input or "None")
                out_summary = event.output[:60] + "..." if event.output and len(event.output) > 60 else (event.output or "None")
                md.write(f"| {event.stage_name} | {event.duration:.2f} s | {cache_text} | {inp_summary} | {out_summary} |\n")
            md.write("\n")

            for event in report.production_trace:
                md.write(f"### Stage: {event.stage_name}\n\n")
                md.write(f"- **Execution Time**: {event.duration:.3f} s\n")
                if event.exceptions:
                    md.write(f"- **Exceptions**: {', '.join(event.exceptions)}\n")
                if event.prompt:
                    md.write(f"<details>\n<summary>View Prompt Sent to LLM</summary>\n\n```\n{event.prompt}\n```\n\n</details>\n\n")
                if event.llm_response:
                    md.write(f"<details>\n<summary>View Raw LLM Response</summary>\n\n```\n{event.llm_response}\n```\n\n</details>\n\n")
                md.write(f"<details>\n<summary>View Log Messages</summary>\n\n")
                if event.logs:
                    md.write("```text\n" + "\n".join(event.logs) + "\n```\n\n")
                else:
                    md.write("*No logs captured for this stage.*\n\n")
                md.write("</details>\n\n")

            # 20. Observations
            md.write("## 20. Observations\n\n")
            md.write("### Evaluation Findings\n\n")
            
            # Caching Observation
            total_cache_lookups = report.cache.hits + report.cache.misses
            hit_ratio = report.cache.hits / total_cache_lookups if total_cache_lookups > 0 else 0.0
            md.write(f"1. **Cache Performance**: Hit ratio was {hit_ratio:.1%} ({report.cache.hits} hits out of {total_cache_lookups} lookups).\n")
            
            # Prompt degradation Observation
            degrade_noted = False
            for trace in report.issues:
                if trace.successful_attempt and trace.successful_attempt > 1:
                    md.write(f"2. **Budget Management**: Issue #{trace.issue_number} exceeded initial budget limits and degraded successfully to Attempt {trace.successful_attempt}.\n")
                    degrade_noted = True
                    break
            if not degrade_noted:
                md.write("2. **Budget Management**: All issue prompts fit within the initial target token budget (Attempt 1 selected) without degradation.\n")

            # PDF generation Observation
            total_pdfs = len(report.pdfs)
            total_pdf_size = sum(pdf.file_size_bytes for pdf in report.pdfs)
            md.write(f"3. **PDF Generator**: Successfully generated {total_pdfs} conformed guides (Total size: {total_pdf_size} bytes).\n")

            # Errors Observation
            total_errors = len(report.errors.github_errors) + len(report.errors.llm_errors) + len(report.errors.validation_errors)
            if total_errors > 0:
                md.write(f"4. **Error logs**: Caution: {total_errors} exceptions or warnings were registered during pipeline trace execution. Inspect Section 15 for details.\n")
            else:
                md.write("4. **Error logs**: The pipeline completed without raising any exceptions or errors.\n")

            # 21. Evaluation Integrity Self-Validation
            from evaluation.integrity_validator import validate_integrity
            val_status, val_findings = validate_integrity(report)
            md.write("## 21. Evaluation Integrity Self-Validation\n\n")
            md.write(f"- **Integrity Status**: **{val_status}**\n")
            md.write("- **Validation Findings**:\n")
            for finding in val_findings:
                md.write(f"  - {finding}\n")
            md.write("\n")

            # 22. Artifacts
            md.write("## 22. Artifacts\n\n")
            for key, paths in artifact_files.items():
                md.write(f"- **{key.capitalize()}**:\n")
                for p in paths:
                    md.write(f"  - [{os.path.basename(p)}](file:///{os.path.join(repo_dir, p).replace(os.sep, '/')})\n")
            md.write("\n")

        return report_path

    @staticmethod
    def update_dashboard(reports: List[EvaluationReport], output_dir: str) -> None:
        """Compile a conformed V2 Master comparison Markdown dashboard and CSV file."""
        # --- 1. Write evaluation_summary.csv ---
        csv_path = os.path.join(output_dir, "evaluation_summary.csv")

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Repository", "Issue", "Prompt Attempt Used", "Prompt Tokens", "Completion Tokens",
                "Repository Summary Time", "Issue Guidance Time", "Roadmap Time", "Runtime",
                "Predicted Files", "Actual Files", "Predicted Directories", "Actual Directories",
                "Directory Precision", "Directory Recall", "File Precision", "File Recall",
                "Overall Match %", "Cache Hits", "Cache Misses"
            ])
            
            for r in reports:
                repo_name = r.repo_metadata.name.replace(".git", "")
                for trace in r.issues:
                    gt = r.ground_truths.get(trace.issue_number)
                    act_files = gt.files_changed if gt else []
                    act_dirs = gt.directories_changed if gt else []
                    
                    hints = trace.final_guidance_json.get("exploration_hints", {}) if trace.final_guidance_json else {}
                    pred_files = hints.get("possible_files", [])
                    pred_dirs = hints.get("likely_directories", [])
                    
                    matched_files = set(f.lower() for f in pred_files).intersection(set(f.lower() for f in act_files))
                    matched_dirs = set(d.lower() for d in pred_dirs).intersection(set(d.lower() for d in act_dirs))
                    
                    # Overlaps & F1 comparison metrics
                    file_len = len(pred_files)
                    act_file_len = len(act_files)
                    
                    dir_len = len(pred_dirs)
                    act_dir_len = len(act_dirs)
                    
                    is_available = gt and getattr(gt, "ground_truth_status", "available") == "available"
                    
                    if is_available:
                        file_prec = len(matched_files) / file_len if file_len > 0 else 0.0
                        file_rec = len(matched_files) / act_file_len if act_file_len > 0 else 0.0
                        dir_prec = len(matched_dirs) / dir_len if dir_len > 0 else 0.0
                        dir_rec = len(matched_dirs) / act_dir_len if act_dir_len > 0 else 0.0
                        
                        weights = []
                        if act_files:
                            weights.append(file_rec)
                        if act_dirs:
                            weights.append(dir_rec)
                        overall_match = (sum(weights) / len(weights)) * 100.0 if weights else 0.0
                        
                        dir_prec_str = f"{dir_prec:.2%}"
                        dir_rec_str = f"{dir_rec:.2%}"
                        file_prec_str = f"{file_prec:.2%}"
                        file_rec_str = f"{file_rec:.2%}"
                        overall_match_str = f"{overall_match:.1f}%"
                    else:
                        dir_prec_str = "N/A"
                        dir_rec_str = "N/A"
                        file_prec_str = "N/A"
                        file_rec_str = "N/A"
                        overall_match_str = "N/A"
                    
                    budget_info = getattr(trace, "context_budgeting", None)
                    if budget_info and getattr(budget_info, "capture_status", "NOT_OBSERVED") != "NOT_OBSERVED":
                        succ_attempt = budget_info.selected_attempt
                        prompt_t = budget_info.estimated_prompt_tokens
                        completion_t = estimate_tokens(trace.raw_llm_response) if getattr(trace, "raw_llm_response", None) else 0
                    else:
                        succ_attempt = trace.successful_attempt or "Fallback"
                        prompt_t = 0
                        completion_t = 0
                        if isinstance(succ_attempt, int) and succ_attempt <= len(trace.attempts):
                            prompt_t = trace.attempts[succ_attempt - 1].prompt_tokens
                            completion_t = estimate_tokens(trace.raw_llm_response)
                        
                    writer.writerow([
                        repo_name,
                        trace.issue_number,
                        f"Attempt {succ_attempt}",
                        prompt_t,
                        completion_t,
                        f"{r.summary.timing:.2f}",
                        f"{trace.timings.get('total', 0.0):.2f}",
                        f"{r.roadmap.timing:.2f}",
                        f"{trace.timings.get('total', 0.0):.2f}",
                        len(pred_files),
                        len(act_files) if is_available else "N/A",
                        len(pred_dirs),
                        len(act_dirs) if is_available else "N/A",
                        dir_prec_str,
                        dir_rec_str,
                        file_prec_str,
                        file_rec_str,
                        overall_match_str,
                        r.cache.hits,
                        r.cache.misses
                    ])

        # --- 2. Write dashboard.md ---
        dash_path = os.path.join(output_dir, "dashboard.md")
        
        with open(dash_path, "w", encoding="utf-8") as f:
            f.write("# RepoPilot Backend Live Production Comparison Dashboard\n\n")
            f.write("This dashboard compares live production execution runs of the RepoPilot backend.\n\n")
            f.write("## V2 Master Summary\n\n")
            
            f.write("| Repository | Issue | Summary Score | Guidance Score | Prompt Attempt | Prompt Tokens | Runtime | Overall Match % | Cache Hits | Cache Misses |\n")
            f.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
            
            for r in reports:
                repo_name = r.repo_metadata.name.replace(".git", "")
                for trace in r.issues:
                    gt = r.ground_truths.get(trace.issue_number)
                    act_files = gt.files_changed if gt else []
                    act_dirs = gt.directories_changed if gt else []
                    
                    hints = trace.final_guidance_json.get("exploration_hints", {}) if trace.final_guidance_json else {}
                    pred_files = hints.get("possible_files", [])
                    pred_dirs = hints.get("likely_directories", [])
                    
                    matched_files = set(f.lower() for f in pred_files).intersection(set(f.lower() for f in act_files))
                    matched_dirs = set(d.lower() for d in pred_dirs).intersection(set(d.lower() for d in act_dirs))
                    
                    is_available = gt and getattr(gt, "ground_truth_status", "available") == "available"
                    
                    if is_available:
                        weights = []
                        if act_files:
                            weights.append(len(matched_files) / len(act_files))
                        if act_dirs:
                            weights.append(len(matched_dirs) / len(act_dirs))
                        overall_match = (sum(weights) / len(weights)) * 100.0 if weights else 0.0
                        overall_match_str = f"{overall_match:.1f}%"
                    else:
                        overall_match_str = "N/A"
                    
                    budget_info = getattr(trace, "context_budgeting", None)
                    if budget_info and getattr(budget_info, "capture_status", "NOT_OBSERVED") != "NOT_OBSERVED":
                        succ_attempt = budget_info.selected_attempt
                        prompt_t = budget_info.estimated_prompt_tokens
                    else:
                        succ_attempt = trace.successful_attempt or "Fallback"
                        prompt_t = 0
                        if isinstance(succ_attempt, int) and succ_attempt <= len(trace.attempts):
                            prompt_t = trace.attempts[succ_attempt - 1].prompt_tokens
                        
                    f.write(f"| {repo_name} | #{trace.issue_number} | {r.metrics_scores.summary_score} | {r.metrics_scores.guidance_score} | {succ_attempt} | {prompt_t} | {trace.timings.get('total', 0.0):.1f} s | {overall_match_str} | {r.cache.hits} | {r.cache.misses} |\n")
            
            f.write("\n\n*Last compiled: July 2026*")
