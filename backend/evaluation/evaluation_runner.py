import os
import sys
import time
import argparse
import logging
import json
from typing import List
from dotenv import load_dotenv

# Setup python path to include backend root
backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_root)

# Automatically locate and load the project's .env file (located in the backend root)
load_dotenv(os.path.join(backend_root, ".env"))

# Import production app & PDF templates
from main import app
from fastapi.testclient import TestClient
from app.pdf.templates.repository_report import RepositoryReportTemplate
from app.pdf.templates.issue_report import IssueReportTemplate
from app.pdf.templates.contribution_report import ContributionReportTemplate
from app.core.cache.dependencies import get_cache_manager

# Import evaluation harness modules
from evaluation.benchmark_models import EvaluationReport, PDFStats, RepositoryMetadata
from evaluation.prompt_capture import EvaluationCaptureContext
from evaluation.repository_capture import RepositoryCapture
from evaluation.report_builder import ReportBuilder
from evaluation.markdown_writer import MarkdownWriter

eval_logger = logging.getLogger("evaluation_logger")

def setup_evaluation_logging(output_dir: str, repo_name: str) -> None:
    """Set up the dedicated evaluation logger and root log handlers."""
    repo_log_dir = os.path.join(output_dir, repo_name, "logs")
    os.makedirs(repo_log_dir, exist_ok=True)
    
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 1. Setup Root Logger Handlers (for pipeline tracing logs)
    root_logger = logging.getLogger()
    # Clear existing root handlers
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)
        
    root_file_handler = logging.FileHandler(os.path.join(repo_log_dir, "run.log"), encoding="utf-8")
    root_file_handler.setFormatter(log_formatter)
    root_file_handler.setLevel(logging.INFO)
    root_logger.addHandler(root_file_handler)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)
    
    # 2. Setup Evaluation Logger Handlers
    eval_logger.handlers = []
    eval_logger.propagate = False
    
    eval_file_handler = logging.FileHandler(os.path.join(repo_log_dir, "evaluation.log"), encoding="utf-8")
    eval_file_handler.setFormatter(log_formatter)
    eval_file_handler.setLevel(logging.INFO)
    eval_logger.addHandler(eval_file_handler)
    eval_logger.setLevel(logging.INFO)
    
    eval_logger.info("Evaluation logging initialized successfully.")

def shutdown_evaluation_logging() -> None:
    """Close and remove all handlers from loggers to release file locks on Windows."""
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        handler.close()
        root_logger.removeHandler(handler)
        
    for handler in list(eval_logger.handlers):
        handler.close()
        eval_logger.removeHandler(handler)

def load_previous_reports(output_dir: str) -> List[EvaluationReport]:
    """Scan output folder for existing report JSONs to dynamically rebuild the global dashboard."""
    reports = []
    if not os.path.exists(output_dir):
        return reports
        
    for item in os.listdir(output_dir):
        sub_dir = os.path.join(output_dir, item)
        if os.path.isdir(sub_dir):
            report_json_path = os.path.join(sub_dir, "json", "evaluation_report_data.json")
            if os.path.exists(report_json_path):
                try:
                    with open(report_json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        report_obj = EvaluationReport.model_validate(data)
                        reports.append(report_obj)
                except Exception as e:
                    print(f"Warning: Failed to load previous report from {report_json_path}: {e}")
    return reports

def generate_pdf_guides(repo_name: str, snapshot: dict, report: EvaluationReport) -> None:
    """Invoke PDF builders, calculate sizes and runtimes, and register PDFStats."""
    import tempfile
    eval_logger.info("PDF Generation: Started building guides.")
    
    # 1. Repository Guide PDF
    try:
        t0 = time.perf_counter()
        pdf_bytes = RepositoryReportTemplate.generate(repo_name=repo_name, analysis_data=snapshot)
        dur = int((time.perf_counter() - t0) * 1000)
        
        temp_fd, temp_path = tempfile.mkstemp(suffix=".pdf")
        os.write(temp_fd, pdf_bytes)
        os.close(temp_fd)
        
        report.pdfs.append(PDFStats(
            name="Repository Guide",
            file_size_bytes=len(pdf_bytes),
            generation_time_ms=dur,
            file_path=temp_path
        ))
        eval_logger.info("PDF Generation: Repository Guide created in %d ms (%d bytes)", dur, len(pdf_bytes))
    except Exception as e:
        eval_logger.error("PDF Generation: Failed to build Repository Guide: %s", e)
        report.errors.validation_errors.append(f"PDF Gen: Repository Guide: {e}")

    # 2. Issue Guide PDFs
    for trace in report.issues:
        issue_num = trace.issue_number
        matching_issue = None
        for issue_entry in snapshot.get("issues", []):
            if str(issue_entry.get("raw_issue", {}).get("number")) == str(issue_num):
                matching_issue = issue_entry
                break
                
        if matching_issue:
            try:
                t0 = time.perf_counter()
                pdf_bytes = IssueReportTemplate.generate(issue_data=matching_issue, repo_name=repo_name)
                dur = int((time.perf_counter() - t0) * 1000)
                
                temp_fd, temp_path = tempfile.mkstemp(suffix=".pdf")
                os.write(temp_fd, pdf_bytes)
                os.close(temp_fd)
                
                report.pdfs.append(PDFStats(
                    name=f"Issue Guide #{issue_num}",
                    file_size_bytes=len(pdf_bytes),
                    generation_time_ms=dur,
                    file_path=temp_path
                ))
                eval_logger.info("PDF Generation: Issue Guide #%d created in %d ms (%d bytes)", issue_num, dur, len(pdf_bytes))
            except Exception as e:
                eval_logger.error("PDF Generation: Failed to build Issue Guide #%d: %s", issue_num, e)
                report.errors.validation_errors.append(f"PDF Gen: Issue #{issue_num}: {e}")

    # 3. Contribution Guide PDF
    try:
        t0 = time.perf_counter()
        pdf_bytes = ContributionReportTemplate.generate(repo_name=repo_name, analysis_data=snapshot)
        dur = int((time.perf_counter() - t0) * 1000)
        
        temp_fd, temp_path = tempfile.mkstemp(suffix=".pdf")
        os.write(temp_fd, pdf_bytes)
        os.close(temp_fd)
        
        report.pdfs.append(PDFStats(
            name="Contribution Guide",
            file_size_bytes=len(pdf_bytes),
            generation_time_ms=dur,
            file_path=temp_path
        ))
        eval_logger.info("PDF Generation: Contribution Guide created in %d ms (%d bytes)", dur, len(pdf_bytes))
    except Exception as e:
        eval_logger.error("PDF Generation: Failed to build Contribution Guide: %s", e)
        report.errors.validation_errors.append(f"PDF Gen: Contribution Guide: {e}")

def get_system_telemetry() -> tuple[float, float]:
    """Capture current process memory (MB) and CPU usage percentage."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        mem = process.memory_info().rss / (1024.0 * 1024.0)
        cpu = process.cpu_percent(interval=0.1)
        return round(mem, 2), round(cpu, 2)
    except ImportError:
        return 0.0, 0.0

def run_evaluation(repo_url: str, github_token: str, output_dir: str, bypass_cache: bool = False, mode: str = "FAST_MVP", exec_mode: str = "prod") -> EvaluationReport:
    """Run RepoPilot V2 client-based live production evaluation pipeline."""
    url_parts = repo_url.strip("/").split("/")
    if len(url_parts) < 5:
        raise ValueError(f"Invalid GitHub repository URL: {repo_url}")
    owner = url_parts[-2]
    repo_name = url_parts[-1].replace(".git", "")

    # Set up process logger (evaluation.log + run.log)
    setup_evaluation_logging(output_dir, repo_name)
    eval_logger.info("Running Live Evaluation for %s/%s (Execution Mode: %s)", owner, repo_name, exec_mode)

    # Initialize evaluation report
    report = EvaluationReport()
    report.repo_metadata.url = repo_url
    
    try:
        # Configure token/keys/model in settings and environment
        from app.core.config import settings
        if github_token:
            settings.GITHUB_TOKEN = github_token
        if os.environ.get("GROQ_API_KEY"):
            settings.GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
        if os.environ.get("MODEL_NAME"):
            settings.MODEL_NAME = os.environ.get("MODEL_NAME")

        # Start timing
        t_start = time.perf_counter()

        # Call POST /repo/analyze via TestClient under the capture context
        with EvaluationCaptureContext(report, exec_mode=exec_mode, bypass_cache=bypass_cache):
            # Clear cache if requested
            if bypass_cache:
                try:
                    cm = get_cache_manager()
                    cm.clear()
                    eval_logger.info("Cache: Cleared existing cache backend.")
                except Exception as e:
                    eval_logger.warning("Cache: Failed to clear backend: %s", e)

            eval_logger.info("FastAPI Client: Invoking POST /repo/analyze")
            client = TestClient(app)
            
            try:
                # Execute exactly as an HTTP client would
                response = client.post("/repo/analyze", json={"url": repo_url})
                if response.status_code == 200:
                    snapshot = response.json()
                    eval_logger.info("FastAPI Client: POST /repo/analyze completed with status 200.")
                else:
                    eval_logger.error("FastAPI Client: POST /repo/analyze failed with status %d: %s", response.status_code, response.text)
                    report.errors.validation_errors.append(f"HTTP Endpoint Failed: {response.status_code} - {response.text}")
                    snapshot = {}
            except Exception as e:
                eval_logger.exception("FastAPI Client: Exception during endpoint call.")
                report.errors.validation_errors.append(f"Endpoint Exception: {e}")
                snapshot = {}

        report.total_runtime = time.perf_counter() - t_start
        eval_logger.info("Performance: Total pipeline runtime: %.2fs", report.total_runtime)

        # Get system stats
        mem, cpu = get_system_telemetry()
        report.memory_usage_mb = mem
        report.cpu_usage_pct = cpu
        eval_logger.info("Performance: System telemetry: Memory = %.2f MB, CPU = %.2f%%", mem, cpu)

        # 1. Fetch Repository Metadata
        eval_logger.info("GitHub: Fetching metadata and directory tree stats.")
        try:
            from app.services.github_service import GitHubService
            gh = GitHubService()
            tree = gh.get_repository_tree(owner, repo_name)
            readme = gh.get_readme(owner, repo_name) or ""
            contrib = gh.get_contributing(owner, repo_name) or ""
            
            rc = RepositoryCapture(github_token)
            report.repo_metadata = rc.fetch_repo_metadata(repo_url, tree, readme, contrib)
        except Exception as e:
            eval_logger.warning("GitHub: Failed to retrieve repository stats: %s", e)
            report.errors.github_errors.append(f"Metadata Profile: {e}")

        # 2. Build PDF guides conformed to production
        if snapshot:
            generate_pdf_guides(repo_name, snapshot, report)

        # 3. Post-Process (Fetch Ground Truth + Compute Metrics)
        eval_logger.info("Report Builder: Resolving GitHub PR ground truth and calculating scores.")
        rb = ReportBuilder(github_token)
        report = rb.build_report(report)

        # 4. Save Raw Artifacts
        eval_logger.info("Report Builder: Saving raw JSON, log, and PDF files.")
        artifacts = MarkdownWriter.save_artifacts(report, output_dir)
        
        # Save raw report JSON
        report_json_path = os.path.join(output_dir, repo_name, "json", "evaluation_report_data.json")
        with open(report_json_path, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))

        # 5. Write conformed report Markdown
        eval_logger.info("Report Builder: Rendering final conformed markdown report.")
        report_path = MarkdownWriter.write_report(report, output_dir, artifacts)
        eval_logger.info("Report Builder: Report generated successfully at: %s", report_path)

        # 6. Rebuild Master Dashboard
        eval_logger.info("Report Builder: Updating global comparison dashboard.")
        all_reports = load_previous_reports(output_dir)
        exists = False
        for i, r in enumerate(all_reports):
            if r.repo_metadata.url == report.repo_metadata.url:
                all_reports[i] = report
                exists = True
                break
        if not exists:
            all_reports.append(report)
            
        MarkdownWriter.update_dashboard(all_reports, output_dir)
        eval_logger.info("Report Builder: Master dashboard updated.")

        return report
    finally:
        # Shutdown logging cleanly to release handles
        shutdown_evaluation_logging()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RepoPilot Live Production Evaluation Harness V2 CLI")
    parser.add_argument("--repo", required=True, help="GitHub repository URL")
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"), help="GitHub Personal Access Token")
    parser.add_argument("--groq-key", default=os.environ.get("GROQ_API_KEY"), help="Groq API Key")
    parser.add_argument("--model", default=os.environ.get("MODEL_NAME"), help="LLM Model Name")
    parser.add_argument("--output", required=True, help="Output directory for reports and artifacts")
    parser.add_argument("--no-cache", action="store_true", help="Bypass and clear cache for clean pipeline evaluation")
    parser.add_argument("--mode", default="FAST_MVP", help="RepoService run mode (FAST_MVP or FULL)")
    parser.add_argument("--exec-mode", choices=["prod", "ci"], default="prod", help="Harness execution mode (prod or ci)")

    args = parser.parse_args()

    # Validate that token and groq key exist
    if not args.token:
        print("GitHub token not found. Provide --token or define GITHUB_TOKEN in .env", file=sys.stderr)
        sys.exit(1)
    if not args.groq_key:
        print("Groq API key not found. Define GROQ_API_KEY in .env", file=sys.stderr)
        sys.exit(1)

    # Update environment variables if provided/overridden
    os.environ["GITHUB_TOKEN"] = args.token
    os.environ["GROQ_API_KEY"] = args.groq_key
    if args.model:
        os.environ["MODEL_NAME"] = args.model

    # Print the loaded configuration at startup (hide secrets)
    print("-------------------------------------------------")
    print("RepoPilot Evaluation Harness")
    print(f"Execution Mode : {args.exec_mode}")
    print("GitHub Token   : Loaded [OK]")
    print("Groq API Key   : Loaded [OK]")
    print(f"Model          : {args.model or ''}")
    print(f"Output         : {args.output}")
    print("-------------------------------------------------")

    try:
        run_evaluation(
            repo_url=args.repo,
            github_token=args.token,
            output_dir=args.output,
            bypass_cache=args.no_cache,
            mode=args.mode,
            exec_mode=args.exec_mode
        )
        print("\nEvaluation Harness completed successfully.")
    except Exception as exc:
        print(f"\nEvaluation Harness failed: {exc}", file=sys.stderr)
        sys.exit(1)
