import os
import sys
import argparse
import time
import json
import logging
from typing import List

# Setup python path to include backend root
backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_root)

# Import the existing production run_evaluation
from evaluation.evaluation_runner import run_evaluation
from evaluation.benchmark_models import EvaluationReport

def sanitize_folder_name(name: str) -> str:
    """Sanitize repository name for local folder creation."""
    return "".join(c for c in name if c.isalnum() or c in ("-", "_")).strip()

def main():
    parser = argparse.ArgumentParser(description="RepoPilot Multi-Repository Sequential Evaluation Harness")
    parser.add_argument("--repo", action="append", default=[], help="Repeatable GitHub repository URL(s)")
    parser.add_argument("--repos-file", help="Path to text file containing repository URLs (one per line)")
    parser.add_argument("--output", required=True, help="Base output directory for reports and artifacts")
    parser.add_argument("--no-cache", action="store_true", help="Bypass and clear cache for clean pipeline evaluation")
    parser.add_argument("--mode", default="FAST_MVP", help="RepoService run mode (FAST_MVP or FULL)")
    parser.add_argument("--exec-mode", choices=["prod", "ci"], default="prod", help="Harness execution mode")

    args = parser.parse_args()

    repo_urls = list(args.repo)
    if args.repos_file:
        if os.path.exists(args.repos_file):
            with open(args.repos_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        repo_urls.append(line)
        else:
            print(f"Error: Repositories file not found at {args.repos_file}", file=sys.stderr)
            sys.exit(1)

    if not repo_urls:
        print("Error: No repository URLs specified. Use --repo or --repos-file.", file=sys.stderr)
        sys.exit(1)

    # Dedup repository URLs
    repo_urls = list(dict.fromkeys(repo_urls))

    print("=================================================")
    print(f"Starting Multi-Repository Evaluation Run ({len(repo_urls)} repositories)")
    print("=================================================")

    summary_results = []
    
    # Ensure base output directory exists
    os.makedirs(args.output, exist_ok=True)

    for idx, repo_url in enumerate(repo_urls, 1):
        url_parts = repo_url.strip("/").split("/")
        if len(url_parts) < 5:
            print(f"\n[{idx}/{len(repo_urls)}] Skipping invalid URL: {repo_url}", file=sys.stderr)
            continue
            
        owner = url_parts[-2]
        repo_name = url_parts[-1].replace(".git", "")
        sanitized_name = f"{sanitize_folder_name(owner)}_{sanitize_folder_name(repo_name)}"
        repo_output_dir = os.path.join(args.output, sanitized_name)
        
        print(f"\n[{idx}/{len(repo_urls)}] Processing: {owner}/{repo_name}")
        print(f"Target Directory: {repo_output_dir}")
        print("-------------------------------------------------")
        
        t0 = time.perf_counter()
        status = "SUCCESS"
        error_type = ""
        error_summary = ""
        issues_analyzed = 0
        selected_attempts = []
        estimated_prompt_tokens = 0
        
        try:
            # Execute conformed production runner sequentially
            report = run_evaluation(
                repo_url=repo_url,
                github_token=os.environ.get("GITHUB_TOKEN", ""),
                output_dir=repo_output_dir,
                bypass_cache=args.no_cache,
                mode=args.mode,
                exec_mode=args.exec_mode
            )
            
            issues_analyzed = len(report.issues)
            for trace in report.issues:
                # Extract attempts
                budget_info = getattr(trace, "context_budgeting", None)
                if budget_info and getattr(budget_info, "capture_status", "NOT_OBSERVED") != "NOT_OBSERVED":
                    selected_attempts.append(budget_info.selected_attempt)
                    estimated_prompt_tokens += getattr(budget_info, "estimated_prompt_tokens", 0)
                else:
                    selected_attempts.append(trace.successful_attempt)
                    
        except Exception as e:
            status = "FAILED"
            error_type = type(e).__name__
            error_summary = str(e)
            print(f"Error evaluating {repo_url}: {e}", file=sys.stderr)
            
        duration = time.perf_counter() - t0
        
        summary_results.append({
            "repository_url": repo_url,
            "repository_name": f"{owner}/{repo_name}",
            "status": status,
            "duration_seconds": round(duration, 2),
            "output_directory": os.path.abspath(repo_output_dir),
            "error_type": error_type,
            "error_summary": error_summary,
            "issues_analyzed": issues_analyzed,
            "selected_attempts": selected_attempts,
            "estimated_prompt_tokens": estimated_prompt_tokens
        })
        
        print(f"[{idx}/{len(repo_urls)}] Finished {owner}/{repo_name} with status: {status}")

    # Generate master summary report (JSON)
    summary_path = os.path.join(args.output, "multi_repo_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_results, f, indent=2)

    # Generate master summary report (Markdown)
    md_path = os.path.join(args.output, "multi_repo_summary.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# RepoPilot Multi-Repository Evaluation Summary\n\n")
        f.write(f"Run completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("| Repository | Status | Duration (s) | Issues | Attempts | Estimated Tokens | Error |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- |\n")
        for res in summary_results:
            attempts_str = ",".join(map(str, res["selected_attempts"]))
            err_str = f"**{res['error_type']}**: {res['error_summary']}" if res["error_type"] else "None"
            f.write(f"| [{res['repository_name']}]({res['repository_url']}) | {res['status']} | {res['duration_seconds']} | {res['issues_analyzed']} | {attempts_str} | {res['estimated_prompt_tokens']} | {err_str} |\n")

    print("\n=================================================")
    print("Multi-Repository Run Completed Successfully.")
    print(f"Master Summary JSON: {summary_path}")
    print(f"Master Summary MD  : {md_path}")
    print("=================================================")

if __name__ == "__main__":
    main()
