import os
import re
import unittest

class TestRepositoryAgnosticism(unittest.TestCase):
    """Test suite ensuring zero hardcoded benchmark dependencies and clean import boundaries."""

    FORBIDDEN_LITERALS = [
        "langchain-ai/langchain",
        "34029",
        "32489",
        "/home/daytona/langchain",
        "libs/core/langchain_core/tools/base.py",
        "libs/core/langchain_core/tools/structured.py",
        "libs/partners/openai/langchain_openai/chat_models/azure.py",
        "BaseTool",
        "StructuredTool",
        "RunnableConfig",
        "AzureChatOpenAI"
    ]

    def test_production_code_for_forbidden_literals(self):
        """Verify that backend/app/ does not contain any hardcoded benchmark strings or symbol literals."""
        backend_root = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.join(backend_root, "app")
        
        failures = []
        
        for root, _, files in os.walk(app_dir):
            for file in files:
                if not file.endswith(".py"):
                    continue
                file_path = os.path.join(root, file)
                
                # Skip __pycache__ or similar
                if "__pycache__" in file_path:
                    continue
                    
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    
                for lit in self.FORBIDDEN_LITERALS:
                    # Case insensitive check for literals
                    if lit.lower() in content.lower():
                        # Make sure it's not a generic comment or tech vocab
                        # (e.g. "langchain" is allowed in known_libs list, but BaseTool / 34029 are not)
                        # We do a direct case-sensitive check or word-boundary check if appropriate.
                        # For class names/numbers, check strictly:
                        if lit in ["BaseTool", "StructuredTool", "RunnableConfig", "AzureChatOpenAI", "34029", "32489"]:
                            pattern = rf"\b{re.escape(lit)}\b"
                            if re.search(pattern, content):
                                failures.append(f"Forbidden symbol '{lit}' found in {os.path.relpath(file_path, backend_root)}")
                        else:
                            failures.append(f"Forbidden literal '{lit}' found in {os.path.relpath(file_path, backend_root)}")
                            
        self.assertEqual(failures, [], f"Agnosticism violation: {failures}")

    def test_production_code_import_boundaries(self):
        """Verify that backend/app/ does not import from tests or evaluation modules."""
        backend_root = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.join(backend_root, "app")
        
        failures = []
        
        import_patterns = [
            re.compile(r"^\s*import\s+(?:tests|evaluation)\b", re.MULTILINE),
            re.compile(r"^\s*from\s+(?:tests|evaluation)\b", re.MULTILINE)
        ]
        
        for root, _, files in os.walk(app_dir):
            for file in files:
                if not file.endswith(".py"):
                    continue
                file_path = os.path.join(root, file)
                
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    
                for pattern in import_patterns:
                    if pattern.search(content):
                        failures.append(f"Invalid import boundary in {os.path.relpath(file_path, backend_root)}")
                        
        self.assertEqual(failures, [], f"Import boundary violation: {failures}")
