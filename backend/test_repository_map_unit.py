import unittest
import sys
import os

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
sys.path.append(os.path.dirname(__file__))

from app.services.repository_map_service import RepositoryMapService

class TestRepositoryMapClassification(unittest.TestCase):
    def setUp(self):
        # We don't need a real github_service since we are testing internal methods directly
        self.service = RepositoryMapService(github_service=None)

    def test_extract_important_directories(self):
        # Tree with depth 1, 2, 3, and ignored paths
        mock_tree = [
            {"path": "frontend", "type": "tree"},
            {"path": "frontend/src", "type": "tree"},
            {"path": "frontend/src/components", "type": "tree"},  # Depth 3, components does NOT match HIGH_PRIORITY_NAMES
            {"path": "frontend/src/unrelated", "type": "tree"},   # Depth 3, unrelated should be filtered out
            {"path": "node_modules", "type": "tree"},             # Ignored
            {"path": "venv", "type": "tree"},                     # Ignored
            {"path": "posthog/queries/tests", "type": "tree"},    # Depth 3, tests matches HIGH_PRIORITY_NAMES
            {"path": "supabase/packages/config", "type": "tree"}, # Depth 3, config matches HIGH_PRIORITY_NAMES
            {"path": "docs", "type": "tree"},
            {"path": "docs/contributing", "type": "tree"},
        ]
        
        extracted = self.service._extract_important_directories(mock_tree)
        
        # Verify depth-3 logic
        self.assertNotIn("frontend/src/components", extracted)
        self.assertIn("posthog/queries/tests", extracted)
        self.assertIn("supabase/packages/config", extracted)
        self.assertNotIn("frontend/src/unrelated", extracted)
        self.assertNotIn("node_modules", extracted)

    def test_classification_logic(self):
        test_cases = [
            # Path, expected category
            ("frontend/src/components", "frontend"),
            ("ee/api", "backend"),
            ("posthog/queries/tests", "tests"),
            ("docs/contributing", "docs"),
            ("tools/pr-approval-agent", "scripts"),  # Ensure 'app' inside 'approval' doesn't cause false positive frontend
            (".github/workflows", "config"),
            ("libs/langchain/tests", "tests"),
            ("libs/langchain/docs", "docs"),
            ("supabase/packages/config", "config"),
            ("examples", "docs"),
            ("scripts/deploy", "scripts"),
        ]
        
        paths = [case[0] for case in test_cases]
        repo_map, diagnostics = self.service._classify_paths(paths)
        
        # Check diagnostics structure
        self.assertEqual(len(diagnostics), len(paths))
        for diag in diagnostics:
            self.assertIn("path", diag)
            self.assertIn("category", diag)
            self.assertIn("score", diag)
            self.assertIn("reason", diag)
            self.assertTrue(isinstance(diag["reason"], list))

        # Check results
        for path, expected in test_cases:
            found_cat = None
            for cat, items in repo_map.items():
                if path in items:
                    found_cat = cat
                    break
            self.assertEqual(found_cat, expected, f"Path '{path}' expected category '{expected}', got '{found_cat}'")

    def test_per_category_limits(self):
        # Create a repo map where frontend has 25 items, tests has 5 items
        repo_map = {
            "frontend": [f"front/dir{i}" for i in range(30)],
            "backend": [],
            "tests": ["tests/dir1", "tests/dir2"],
            "docs": [],
            "config": [],
            "scripts": [],
            "other": []
        }
        
        limited = self.service._limit_entries(repo_map)
        
        self.assertEqual(len(limited["frontend"]), 20)  # MAX_DIRECTORY_ENTRIES is 20
        self.assertEqual(len(limited["tests"]), 2)      # Keeps all if under limit
        self.assertEqual(limited["frontend"][0], "front/dir0")
        self.assertEqual(limited["frontend"][-1], "front/dir19")

if __name__ == '__main__':
    unittest.main()
