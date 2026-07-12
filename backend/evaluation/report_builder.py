import logging
import time
from typing import Any, Dict, List
from app.utils.performance_utils import estimate_tokens

from evaluation.benchmark_models import EvaluationReport, MetricsScores, GitHubGroundTruth
from evaluation.issue_capture import GitHubIssueCapture
from evaluation.comparison_utils import compare_issue_predictions, infer_actual_difficulty

logger = logging.getLogger(__name__)

class ReportBuilder:
    """Aggregator that calculates final benchmark scores and prepares the report data structure."""

    def __init__(self, token: str) -> None:
        self.issue_capture = GitHubIssueCapture(token)

    def build_report(self, report: EvaluationReport) -> EvaluationReport:
        """Run post-execution aggregation, fetch ground truths, and calculate metrics."""
        parsed_url = report.repo_metadata.url.split("/")
        if len(parsed_url) >= 5:
            owner = parsed_url[-2]
            repo = parsed_url[-1].replace(".git", "")
        else:
            owner = ""
            repo = ""

        # Check if we are running in CI offline mock mode
        is_mock_run = self.issue_capture.token == "mock_github_token_12345"

        # 1. Fetch GitHub Ground Truth for each issue analyzed
        for issue_trace in report.issues:
            issue_num = issue_trace.issue_number
            if is_mock_run:
                logger.info("Mock CI run detected. Injected offline ground truth for issue #%d.", issue_num)
                gt = GitHubGroundTruth(
                    issue_number=issue_num,
                    state="closed",
                    merged_pr_number=100,
                    merged_pr_url=f"https://github.com/{owner}/{repo}/pull/100" if owner else "https://github.com/mock/pull/100",
                    pr_title="CI Mock PR Title",
                    pr_description="CI Mock PR Description",
                    files_changed=["backend/main.py"],
                    directories_changed=["backend"],
                    commits=["Mock commit message"],
                    closing_commit="mockcommitsha12345",
                    changed_languages=["Python"],
                    status_text="Success"
                )
            else:
                logger.info("Fetching real ground truth for issue #%d...", issue_num)
                gt = self.issue_capture.fetch_issue_ground_truth(owner, repo, issue_num)
            
            report.ground_truths[issue_num] = gt

        # 2. Calculate individual metric scores
        report.metrics_scores = self._calculate_scores(report)
        return report

    def _calculate_scores(self, report: EvaluationReport) -> MetricsScores:
        """Calculate deterministic metrics based on schema overlap and validation."""
        scores = MetricsScores()

        # --- A. Repository Summary Score (out of 10) ---
        summary_raw = report.summary.raw_json or {}
        summary_score = 0.0
        
        # Check presence of expected keys
        expected_summary_keys = ["tech_stack", "key_concepts", "repository_purpose", "beginner_friendly_summary"]
        keys_present = sum(1 for k in expected_summary_keys if summary_raw.get(k))
        summary_score += keys_present * 1.5  # Max 6.0 points

        # Tech stack validation against main repo language
        main_lang = report.repo_metadata.language.lower()
        tech_stack = [t.lower() for t in summary_raw.get("tech_stack", []) if isinstance(t, str)]
        
        if main_lang and main_lang in tech_stack:
            summary_score += 4.0  # Found main language
        elif tech_stack:
            summary_score += 2.0  # Stack is populated but doesn't explicitly match main language
        else:
            summary_score += 0.0
            
        scores.summary_score = round(summary_score, 1)

        # --- B. Repository Map Score (out of 10) ---
        map_raw = report.repo_map.map_json or {}
        map_score = 0.0
        
        if isinstance(map_raw, dict) and len(map_raw) > 0:
            map_score += 3.0  # Valid dict schema
            
            # Rate non-empty categories out of 7 standard categories
            categories = ["frontend", "backend", "tests", "docs", "config", "scripts", "other"]
            non_empty_cats = sum(1 for c in categories if map_raw.get(c))
            map_score += (non_empty_cats / len(categories)) * 4.0  # Max 4.0 points

            # Tree file coverage
            total_mapped_files = sum(len(files) for files in map_raw.values() if isinstance(files, list))
            total_repo_files = report.repo_metadata.total_files
            if total_repo_files > 0:
                coverage_ratio = min(1.0, total_mapped_files / total_repo_files)
                map_score += coverage_ratio * 3.0  # Max 3.0 points
            else:
                map_score += 3.0

        scores.map_score = round(map_score, 1)

        # --- C. Issue Guidance Score (out of 10) ---
        guidance_scores_list = []
        for trace in report.issues:
            issue_guidance_score = 0.0
            guidance_data = trace.final_guidance_json or {}
            
            # 1. Output completeness (out of 4.0)
            analysis = guidance_data.get("analysis", {}) or {}
            hints = guidance_data.get("exploration_hints", {}) or {}
            
            if analysis.get("beginner_explanation"):
                issue_guidance_score += 1.0
            if analysis.get("skills_required"):
                issue_guidance_score += 1.0
            if hints.get("likely_directories"):
                issue_guidance_score += 1.0
            if hints.get("possible_files"):
                issue_guidance_score += 1.0
                
            # 2. Success level of budget compression / attempts (out of 6.0)
            succ_attempt = trace.successful_attempt
            if succ_attempt == 1:
                issue_guidance_score += 6.0
            elif succ_attempt == 2:
                issue_guidance_score += 5.0
            elif succ_attempt == 3:
                issue_guidance_score += 4.0
            elif succ_attempt == 4:
                issue_guidance_score += 3.0
            else:
                issue_guidance_score += 1.0
                
            guidance_scores_list.append(issue_guidance_score)
            
        scores.guidance_score = round(sum(guidance_scores_list) / len(guidance_scores_list), 1) if guidance_scores_list else 0.0

        # --- D. Candidate Ranking Score (out of 10) ---
        ranking_scores_list = []
        for trace in report.issues:
            issue_num = trace.issue_number
            gt = report.ground_truths.get(issue_num)
            
            if not gt or getattr(gt, "ground_truth_status", "available") != "available" or not gt.files_changed:
                continue
                
            candidates = trace.candidate_evidence.get("candidates", []) if trace.candidate_evidence else []
            candidate_paths = [c.get("path", "").lower() for c in candidates if c.get("path")]
            
            actual_paths = [f.lower() for f in gt.files_changed]
            
            best_rank = 999
            for act_f in actual_paths:
                if act_f in candidate_paths:
                    rank = candidate_paths.index(act_f) + 1
                    if rank < best_rank:
                        best_rank = rank
            
            issue_ranking_score = 0.0
            if best_rank <= 3:
                issue_ranking_score = 10.0
            elif best_rank <= 5:
                issue_ranking_score = 8.0
            elif best_rank <= 10:
                issue_ranking_score = 6.0
            elif best_rank <= 20:
                issue_ranking_score = 4.0
                
            ranking_scores_list.append(issue_ranking_score)
            
        scores.candidate_ranking_score = round(sum(ranking_scores_list) / len(ranking_scores_list), 1) if ranking_scores_list else 10.0

        # --- E. Grounding Score (out of 10) ---
        grounding_scores_list = []
        for trace in report.issues:
            stats = trace.grounding_stats
            if not stats:
                continue
                
            total_recommended = len(stats.recommended_files) + len(stats.recommended_directories)
            if total_recommended == 0:
                grounding_scores_list.append(10.0)
            else:
                total_existing = len(stats.existing_files) + len(stats.existing_directories)
                ratio = total_existing / total_recommended
                grounding_scores_list.append(ratio * 10.0)
                
        scores.grounding_score = round(sum(grounding_scores_list) / len(grounding_scores_list), 1) if grounding_scores_list else 10.0

        # --- F. Roadmap Score (out of 10) ---
        roadmap_raw = report.roadmap.raw_json or {}
        roadmap_score = 0.0
        
        if isinstance(roadmap_raw, dict) and len(roadmap_raw) > 0:
            steps = roadmap_raw.get("steps", [])
            roadmap_score += 4.0 if steps else 0.0
            
            has_prereq = "prerequisites" in roadmap_raw or any("prereq" in k.lower() for k in roadmap_raw)
            has_time = "estimated_time" in roadmap_raw or any("time" in k.lower() for k in roadmap_raw) or any("duration" in k.lower() for k in roadmap_raw)
            
            if has_prereq:
                roadmap_score += 1.5
            if has_time:
                roadmap_score += 1.5
                
            has_issue_link = False
            analyzed_nums = set(t.issue_number for t in report.issues)
            steps_str = str(steps).lower()
            for num in analyzed_nums:
                if str(num) in steps_str:
                    has_issue_link = True
                    break
            
            if has_issue_link:
                roadmap_score += 3.0
            else:
                roadmap_score += 1.5

        scores.roadmap_score = round(roadmap_score, 1)

        # --- G. Overall Intelligence Score (average of valid scores) ---
        all_valid_scores = [
            scores.summary_score,
            scores.map_score,
            scores.guidance_score,
            scores.candidate_ranking_score,
            scores.grounding_score,
            scores.roadmap_score
        ]
        scores.overall_score = round(sum(all_valid_scores) / len(all_valid_scores), 1)

        return scores
