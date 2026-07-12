import unittest
import os
import sys
import shutil
import tempfile
import json
from unittest.mock import patch, MagicMock

# Add backend root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app'))

from evaluation.evaluation_runner import run_evaluation
from evaluation.benchmark_models import EvaluationReport

class TestEvaluationHarness(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for output artifacts
        self.test_dir = tempfile.mkdtemp()
        self.repo_url = "https://github.com/mock-owner/mock-repo"
        self.github_token = "mock_github_token_12345"

    def tearDown(self):
        # Clean up temporary directory
        shutil.rmtree(self.test_dir)

    @patch('requests.get')
    @patch('app.services.github_service.GitHubService')
    @patch('app.services.llm_service.Groq')
    def test_complete_evaluation_pipeline(self, mock_groq_class, mock_gh_service_class, mock_requests_get):
        # 1. Setup Mock for Groq client completions
        mock_groq_client = MagicMock()
        mock_groq_class.return_value = mock_groq_client
        
        # Mock completions.create response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        
        # We will mock the returns for repository summary, issue guidance, and roadmap
        # Note: self.llm_service.generate_json parses the text response from client.chat.completions.create
        mock_responses = [
            # 1. Repository Summary JSON response
            {
                "tech_stack": ["Python", "TypeScript", "React"],
                "key_concepts": ["API routing", "Cache management"],
                "repository_purpose": "A mock repository for testing evaluation harnesses.",
                "beginner_friendly_summary": "Easy starter repo."
            },
            # 2. Issue Guidance JSON response
            {
                "analysis": {
                    "beginner_explanation": "Fix the routing bug in backend.",
                    "skills_required": ["Python"],
                    "affected_area": "backend",
                    "difficulty": "Beginner",
                    "confidence_score": 95
                },
                "exploration_hints": {
                    "affected_area": "backend/api",
                    "likely_directories": ["backend/api"],
                    "possible_files": ["backend/api/routes_repo.py"],
                    "reasoning": "The route handler resides here.",
                    "confidence": 90
                }
            },
            # 3. Roadmap JSON response
            {
                "steps": [
                    {
                        "step_number": 1,
                        "description": "Examine backend/api/routes_repo.py",
                        "related_issue": 42
                    }
                ],
                "prerequisites": ["Python installed"],
                "estimated_time": "1 hour"
            }
        ]
        
        # Helper to construct mock completion response
        def make_completion(data_dict):
            m_choice = MagicMock()
            m_choice.message.content = json.dumps(data_dict)
            m_res = MagicMock()
            m_res.choices = [m_choice]
            return m_res
            
        mock_groq_client.chat.completions.create.side_effect = [
            make_completion(mock_responses[0]),
            make_completion(mock_responses[1]),
            make_completion(mock_responses[2])
        ]

        # 2. Setup Mock for GitHubService tree, readme, contributing, and good first issues
        mock_gh_instance = MagicMock()
        mock_gh_service_class.return_value = mock_gh_instance
        
        mock_gh_instance.get_repository_tree.return_value = [
            {"path": "backend/api/routes_repo.py", "type": "blob"},
            {"path": "backend/api/__init__.py", "type": "blob"},
            {"path": "backend/api", "type": "tree"},
            {"path": "README.md", "type": "blob"},
            {"path": "CONTRIBUTING.md", "type": "blob"}
        ]
        mock_gh_instance.get_readme.return_value = "# README\nThis is a mock repository."
        mock_gh_instance.get_contributing.return_value = "# CONTRIBUTING\nContributions welcome."
        mock_gh_instance.get_good_first_issues.return_value = [
            {
                "number": 42,
                "title": "Fix API bug",
                "body": "The /repo/analyze route is failing.",
                "labels": ["bug", "good first issue"],
                "url": "https://github.com/mock-owner/mock-repo/issues/42",
                "good_first_issue_score": 9.5
            }
        ]
        mock_gh_instance.get_issue_comments.return_value = [
            {"body": "I can replicate this bug.", "user": {"login": "tester"}}
        ]

        # 3. Setup mock requests.get for GitHub REST API calls (Ground Truth)
        def mock_requests_side_effect(url, headers=None, params=None, timeout=None):
            m_resp = MagicMock()
            m_resp.status_code = 200
            
            # Match endpoints
            if "/issues/42/timeline" in url:
                m_resp.json.return_value = [
                    {
                        "event": "connected",
                        "source": {
                            "type": "issue",
                            "issue": {
                                "number": 100,  # Pull request number
                                "pull_request": {}
                            }
                        }
                    },
                    {
                        "event": "closed",
                        "commit_id": "commitsha12345"
                    }
                ]
            elif "/issues/42" in url:
                m_resp.json.return_value = {
                    "number": 42,
                    "state": "closed",
                    "title": "Fix API bug",
                    "body": "The /repo/analyze route is failing.",
                    "labels": ["bug", "good first issue"]
                }
            elif "/pulls/100/files" in url:
                m_resp.json.return_value = [
                    {"filename": "backend/api/routes_repo.py"}
                ]
            elif "/pulls/100/commits" in url:
                m_resp.json.return_value = [
                    {"commit": {"message": "Fix API bug by correcting validator"}}
                ]
            elif "/pulls/100" in url:
                m_resp.json.return_value = {
                    "number": 100,
                    "html_url": "https://github.com/mock-owner/mock-repo/pull/100",
                    "title": "Fix API bug PR",
                    "body": "This PR fixes the API issue #42.",
                    "merged": True,
                    "state": "closed",
                    "merge_commit_sha": "commitsha12345"
                }
            elif "/repos/mock-owner/mock-repo" in url:
                m_resp.json.return_value = {
                    "stargazers_count": 150,
                    "forks_count": 30,
                    "language": "Python",
                    "topics": ["evaluation", "benchmark"],
                    "size": 1200
                }
            else:
                m_resp.json.return_value = {}
                
            return m_resp

        mock_requests_get.side_effect = mock_requests_side_effect

        # 4. Run the Evaluation Runner
        report = run_evaluation(
            repo_url=self.repo_url,
            github_token=self.github_token,
            output_dir=self.test_dir,
            bypass_cache=True,
            mode="FAST_MVP",
            exec_mode="ci"
        )

        # 5. Assertions on conformed output directories and report contents
        self.assertIsInstance(report, EvaluationReport)
        
        # Verify repo directory exists
        repo_output_dir = os.path.join(self.test_dir, "mock-repo")
        self.assertTrue(os.path.exists(repo_output_dir))
        
        # Verify subdirectories exist
        subdirs = ["prompts", "llm", "json", "pdf", "metrics", "github", "logs"]
        for sd in subdirs:
            self.assertTrue(os.path.exists(os.path.join(repo_output_dir, sd)))
            
        # Verify report markdown file exists
        report_file_path = os.path.join(repo_output_dir, "mock-repo_Evaluation.md")
        self.assertTrue(os.path.exists(report_file_path))
        
        # Verify CSV summary and Dashboard exists
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "evaluation_summary.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "dashboard.md")))
        
        # Check some conformed sections inside the written report
        with open(report_file_path, "r", encoding="utf-8") as f:
            md_content = f.read()
            self.assertIn("## 1. Repository Metadata", md_content)
            self.assertIn("## 2. Repository Summary", md_content)
            self.assertIn("## 5. Issue Intelligence", md_content)
            self.assertIn("## 6. Prompt Attempts", md_content)
            self.assertIn("## 16. GitHub Ground Truth", md_content)
            self.assertIn("## 17. RepoPilot vs Ground Truth", md_content)
            self.assertIn("## 18. Evaluation Metrics", md_content)
            self.assertIn("## 19. Production Call Trace", md_content)
            self.assertIn("## 20. Observations", md_content)
            
        # Check computed scores
        self.assertGreaterEqual(report.metrics_scores.summary_score, 0.0)
        self.assertGreaterEqual(report.metrics_scores.guidance_score, 0.0)
        self.assertGreaterEqual(report.metrics_scores.overall_score, 0.0)
        
        print("Mock integration test verified successfully. All conformed V2 files, schemas, and directories created.")

if __name__ == "__main__":
    unittest.main()
