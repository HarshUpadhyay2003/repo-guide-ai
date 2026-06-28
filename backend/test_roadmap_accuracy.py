import unittest
import sys
import os
import datetime

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
sys.path.append(os.path.dirname(__file__))

from app.services.roadmap_service import RoadmapService, calculate_issue_score, get_issue_age_days
from app.services.exploration_hints_service import ExplorationHintsService

class TestRoadmapAccuracy(unittest.TestCase):
    def setUp(self):
        self.roadmap_service = RoadmapService()

    def test_get_issue_age_days(self):
        # Fresh issue (now)
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.assertEqual(get_issue_age_days(now_str), 0)

        # 5 days old
        five_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5)
        self.assertEqual(get_issue_age_days(five_days_ago.isoformat()), 5)

        # Missing or invalid fallback
        self.assertEqual(get_issue_age_days(None), 30)
        self.assertEqual(get_issue_age_days("invalid-date"), 30)

    def test_calculate_issue_score(self):
        # Issue 1: Beginner, high confidence, good first issue, fresh
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        issue_1 = {
            "difficulty": "Beginner",
            "confidence_score": 90,
            "labels": ["good first issue", "easy"],
            "created_at": now_str
        }
        # S_diff = 40
        # S_conf = 90 * 0.2 = 18
        # S_gfi = 15
        # S_label = 5 (easy)
        # S_age = 10
        # Total = 40 + 18 + 15 + 5 + 10 = 88
        self.assertEqual(calculate_issue_score(issue_1), 88.0)

        # Issue 2: Advanced, stale, no labels
        stale_str = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=100)).isoformat()
        issue_2 = {
            "difficulty": "Advanced",
            "confidence_score": 50,
            "labels": [],
            "created_at": stale_str
        }
        # S_diff = 5
        # S_conf = 50 * 0.2 = 10
        # S_gfi = 0
        # S_label = 0
        # S_age = 0
        # Total = 5 + 10 = 15
        self.assertEqual(calculate_issue_score(issue_2), 15.0)

    def test_deterministic_roadmap_ranking(self):
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        stale_str = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=100)).isoformat()
        
        mock_payload = {
            "repo_summary": {
                "metadata": {
                    "name": "test-repo",
                    "description": "A test repository"
                }
            },
            "repository_map": {
                "backend": ["backend/api"]
            },
            "issues": [
                {
                    "raw_issue": {
                        "number": 10,
                        "title": "Low priority issue",
                        "labels": [],
                        "created_at": stale_str
                    },
                    "analysis": {
                        "difficulty": "Advanced",
                        "skills_required": [],
                        "affected_area": "core",
                        "confidence_score": 50,
                        "beginner_explanation": "Too hard"
                    },
                    "exploration_hints": {
                        "likely_directories": ["backend/api"],
                        "possible_files": []
                    }
                },
                {
                    "raw_issue": {
                        "number": 42,
                        "title": "High priority issue",
                        "labels": ["good first issue"],
                        "created_at": now_str
                    },
                    "analysis": {
                        "difficulty": "Beginner",
                        "skills_required": ["Python"],
                        "affected_area": "api",
                        "confidence_score": 90,
                        "beginner_explanation": "Very easy starting issue"
                    },
                    "exploration_hints": {
                        "likely_directories": ["backend/api"],
                        "possible_files": ["backend/api/server.py"]
                    }
                }
            ],
            "all_files": ["backend/api/server.py"],
            "all_dirs": ["backend/api"]
        }

        result = self.roadmap_service.analyze_roadmap(mock_payload)
        
        # Verify that issue #42 was selected as the best issue to start
        self.assertEqual(result["best_issue_to_start"]["issue_number"], 42)
        self.assertEqual(result["best_issue_to_start"]["title"], "High priority issue")
        self.assertIn("Very easy starting issue", result["why_this_issue"])
        self.assertIn("backend/api/server.py", result["files_to_read_first"])

    def test_filter_hallucinations_with_evidence(self):
        mock_payload = {
            "repo_summary": {
                "metadata": {
                    "name": "test-repo",
                    "description": "A test repository"
                }
            },
            "repository_map": {
                "frontend": ["frontend/src/components"],
                "backend": ["backend/api"]
            },
            "issues": [
                {
                    "raw_issue": {
                        "number": 42,
                        "title": "Fix alignment of survey button",
                        "labels": ["good first issue"]
                    },
                    "analysis": {
                        "difficulty": "Beginner",
                        "skills_required": ["CSS", "React"],
                        "affected_area": "Frontend layout styling",
                        "confidence_score": 90,
                        "beginner_explanation": "Fix css margin"
                    },
                    "exploration_hints": {
                        "likely_directories": ["frontend/src/components"],
                        "possible_files": [
                            "frontend/src/components/Survey.tsx",
                            "frontend/src/components/SurveyButton.tsx" # HALLUCINATED!
                        ]
                    }
                }
            ],
            "all_files": [
                "frontend/src/components/Survey.tsx",
                "backend/api/server.py"
            ],
            "all_dirs": [
                "frontend/src/components",
                "backend/api"
            ]
        }

        result = self.roadmap_service.analyze_roadmap(mock_payload)
        
        # Verify that the hallucinated file was filtered out
        files_to_read = result["files_to_read_first"]
        self.assertIn("frontend/src/components/Survey.tsx", files_to_read)
        self.assertNotIn("frontend/src/components/SurveyButton.tsx", files_to_read)

    def test_zero_issues_roadmap(self):
        mock_payload = {
            "repo_summary": {
                "metadata": {
                    "name": "test-repo",
                    "description": "A test repository"
                }
            },
            "repository_map": {
                "backend": ["backend/api"]
            },
            "issues": [],
            "all_files": ["backend/api/server.py"],
            "all_dirs": ["backend/api"]
        }

        result = self.roadmap_service.analyze_roadmap(mock_payload)
        
        # Verify that the roadmap is an empty dict
        self.assertEqual(result, {})

    def test_repo_service_zero_issues(self):
        from app.services.repo_service import RepoService
        from unittest.mock import MagicMock
        
        repo_service = RepoService()
        repo_service.github_service = MagicMock()
        repo_service.llm_service = MagicMock()
        
        # Mock github_service calls
        repo_service.github_service.get_repo_metadata.return_value = {
            "name": "empty-repo",
            "description": "An empty repository",
            "stars": 0
        }
        repo_service.github_service.get_readme.return_value = ""
        repo_service.github_service.get_contributing.return_value = ""
        repo_service.github_service.get_repository_tree.return_value = []
        repo_service.github_service.get_good_first_issues.return_value = [] # Zero issues!
        
        # Mock LLM calls
        repo_service.llm_service.generate_json.return_value = {"repository_purpose": "Test"}
        
        result = repo_service.analyze_repository("https://github.com/test/empty-repo")
        
        # Verify that issues remains empty
        self.assertEqual(result["issues"], [])
        # Verify that roadmap is an empty dict
        self.assertEqual(result["roadmap"], {})

    def test_infer_issue_category(self):
        from app.utils.file_ranking import infer_issue_category
        # Frontend keywords
        self.assertEqual(infer_issue_category("Positioning error of survey button", "Frontend UI", ["css"]), "frontend")
        # Backend keywords
        self.assertEqual(infer_issue_category("DB postgres migration query timeout", "", []), "backend")
        # Workflow/CI
        self.assertEqual(infer_issue_category("Workflow pipeline failure in github actions", "", ["ci"]), "config")
        # Unclear keywords
        self.assertIsNone(infer_issue_category("hello world", "", []))

    def test_prefilter_candidates(self):
        from app.utils.file_ranking import prefilter_candidates
        
        # Scenario: Enough Tier 1 files (>= 100) -> returns Tier 1 files
        tier1_files = [f"src/components/Survey{i}.tsx" for i in range(120)]
        other_files = [f"src/backend/model{i}.py" for i in range(50)]
        
        candidates = tier1_files + other_files
        result = prefilter_candidates(candidates, "survey positioning", "", [])
        
        # Verify it filtered to Tier 1 files (max 300)
        self.assertEqual(len(result), 120)
        self.assertTrue(all("Survey" in f for f in result))
        
        # Scenario: Small Tier 1 (< 100) -> backfills from Tier 2/Tier 3
        tier1_files = [f"src/components/Survey{i}.tsx" for i in range(10)]
        tier2_files = [f"src/config/Survey{i}.json" for i in range(20)]
        tier3_files = [f"src/components/button{i}.tsx" for i in range(50)]
        
        candidates = tier1_files + tier2_files + tier3_files + [f"backend/server{i}.png" for i in range(20)]
        result = prefilter_candidates(candidates, "survey positioning", "", [])
        
        # Since Tier 1 < 100, pool = Tier1 + Tier2 = 30 files.
        # Since pool (30) < 200, we add Tier 3 (50) -> pool becomes 80 files.
        self.assertEqual(len(result), 80)
        
        # Scenario: Final pool < 50 -> returns original candidates list
        tier1_files = ["src/components/Survey.tsx"]
        result = prefilter_candidates(tier1_files, "survey positioning", "", [])
        self.assertEqual(result, tier1_files)

    def test_retry_strategy_on_schema_failure_compatibility(self):
        # Since we no longer call LLM for Roadmap, schema failures are impossible.
        # We verify that passing invalid payload raises appropriate errors.
        invalid_payload = {}
        with self.assertRaises(Exception):
            self.roadmap_service.analyze_roadmap(invalid_payload)

if __name__ == '__main__':
    unittest.main()
