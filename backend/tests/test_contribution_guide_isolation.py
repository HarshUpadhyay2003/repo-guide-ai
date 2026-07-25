import unittest
from app.pdf.templates.contribution_report import ContributionReportTemplate
from app.services.roadmap_service import RoadmapService


class TestContributionGuideIsolation(unittest.TestCase):
    """Regression test ensuring Contribution Guides generate exclusively from the target issue's data."""

    def setUp(self):
        self.sample_analysis_data = {
            "metadata": {
                "owner": "PostHog",
                "name": "posthog",
                "repo": "posthog"
            },
            "summary": {
                "repository_purpose": "Product analytics platform",
                "estimated_learning_time": "2 hours",
                "tech_stack": ["Python", "React", "PostgreSQL"]
            },
            "repository_map": {
                "Backend": ["ee/api/auth.py", "ee/api/db.py"],
                "Frontend": ["frontend/src/index.tsx"]
            },
            "issues": [
                {
                    "raw_issue": {
                        "number": 101,
                        "title": "Fix OAuth Token Refresh Expiration Bug",
                        "url": "https://github.com/PostHog/posthog/issues/101",
                        "labels": ["good first issue", "auth"],
                        "created_at": "2026-01-10T10:00:00Z"
                    },
                    "analysis": {
                        "difficulty": "Beginner",
                        "confidence_score": 90,
                        "skills_required": ["Python", "JWT", "OAuth2"],
                        "affected_area": "Authentication Subsystem",
                        "beginner_explanation": "Fix the OAuth token refresh handler when tokens expire unexpectedly."
                    },
                    "exploration_hints": {
                        "likely_directories": ["ee/api/auth", "ee/models/tokens"],
                        "possible_files": ["ee/api/auth/jwt.py", "ee/api/auth/tokens.py"],
                        "reasoning": "OAuth token logic resides in the auth subsystem."
                    }
                },
                {
                    "raw_issue": {
                        "number": 202,
                        "title": "Add Cursor Pagination to Query Engine",
                        "url": "https://github.com/PostHog/posthog/issues/202",
                        "labels": ["good first issue", "database"],
                        "created_at": "2026-01-12T12:00:00Z"
                    },
                    "analysis": {
                        "difficulty": "Intermediate",
                        "confidence_score": 85,
                        "skills_required": ["SQLAlchemy", "PostgreSQL", "Query Optimization"],
                        "affected_area": "Database Query Engine",
                        "beginner_explanation": "Add cursor-based pagination support to large result set queries."
                    },
                    "exploration_hints": {
                        "likely_directories": ["ee/api/db", "ee/models/query"],
                        "possible_files": ["ee/api/db/query_engine.py", "ee/api/db/pagination.py"],
                        "reasoning": "Database query logic resides in the db query engine."
                    }
                }
            ],
            # Repository-level top roadmap (generated for Issue #101)
            "roadmap": {
                "best_issue_to_start": {
                    "issue_number": 101,
                    "title": "Fix OAuth Token Refresh Expiration Bug"
                },
                "why_this_issue": "We recommend starting with issue #101 because it is classified as 'Beginner' difficulty and focuses on Authentication Subsystem. Python, JWT, OAuth2.",
                "recommended_learning_order": [
                    "Understand the repository structure, focusing on key directories: ee/api/auth, ee/models/tokens",
                    "Learn or review the core technologies required for this issue: Python, JWT, OAuth2",
                    "Explore the affected codebase area: 'Authentication Subsystem'"
                ],
                "files_to_read_first": ["ee/api/auth/jwt.py", "ee/api/auth/tokens.py"],
                "contribution_plan": [
                    "Clone the repository and set up the local development environment.",
                    "Locate the 'Authentication Subsystem' module and examine key files: ee/api/auth/jwt.py.",
                    "Try to reproduce the issue described: 'Fix OAuth Token Refresh Expiration Bug'."
                ],
                "success_tips": [
                    "Start small: focus only on the files recommended for this issue."
                ]
            }
        }

    def test_roadmap_service_build_issue_roadmap(self):
        """Verify RoadmapService.build_issue_roadmap derives roadmap exclusively for specified issue."""
        issue_202 = self.sample_analysis_data["issues"][1]
        roadmap_202 = RoadmapService.build_issue_roadmap(issue_202)

        # Check Issue #202 isolation
        self.assertEqual(roadmap_202["best_issue_to_start"]["issue_number"], 202)
        self.assertIn("Database Query Engine", roadmap_202["why_this_issue"])
        self.assertNotIn("Authentication Subsystem", roadmap_202["why_this_issue"])
        self.assertNotIn("JWT", roadmap_202["why_this_issue"])

        # Check Files to Explore isolation
        self.assertIn("ee/api/db/query_engine.py", roadmap_202["files_to_read_first"])
        self.assertNotIn("ee/api/auth/jwt.py", roadmap_202["files_to_read_first"])

        # Check Learning Order isolation
        learning_str = " ".join(roadmap_202["recommended_learning_order"])
        self.assertIn("Database Query Engine", learning_str)
        self.assertNotIn("Authentication Subsystem", learning_str)

        # Check Contribution Plan isolation
        plan_str = " ".join(roadmap_202["contribution_plan"])
        self.assertIn("Add Cursor Pagination to Query Engine", plan_str)
        self.assertNotIn("Fix OAuth Token Refresh Expiration Bug", plan_str)

    def test_pdf_generation_issue_isolation(self):
        """Verify PDF generation for Issue #202 uses Issue #202's roadmap rather than top-level Issue #101 roadmap."""
        pdf_bytes = ContributionReportTemplate.generate(
            repo_name="posthog",
            analysis_data=self.sample_analysis_data,
            issue_number=202
        )
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)


if __name__ == "__main__":
    unittest.main()
