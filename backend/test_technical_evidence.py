import unittest
from unittest.mock import patch, MagicMock
from app.utils.evidence_extractor import (
    TechnicalEvidenceItem,
    extract_technical_evidence,
    segment_text,
    _extract_explicit_paths,
    _extract_error_signatures,
    _extract_named_classes,
    _extract_named_functions,
    _extract_named_modules,
    _extract_technical_dependencies
)
from app.services.issue_guidance_service import IssueGuidanceService, IssueEvidence, IssueIntelligence

class TestTechnicalEvidence(unittest.TestCase):

    def test_import_validation(self):
        """Ensure all required classes import and instantiate successfully without syntax or dependency errors."""
        item = TechnicalEvidenceItem(
            evidence_type="EXPLICIT_PATH",
            strength="STRONG",
            source="TITLE",
            text="libs/core/base.py",
            normalized_value="libs/core/base.py",
            rationale="Test import rationale"
        )
        self.assertEqual(item.evidence_type, "EXPLICIT_PATH")
        self.assertEqual(item.strength, "STRONG")

    def test_segmentation_preservation(self):
        """Ensure segmentation preserves paths, functions, namespaces, and version numbers."""
        test_text = "This is a sentence. BaseTool.run and langchain_core.tools are here. Check tools/base.py. Python 3.12 is used."
        segments = segment_text(test_text)
        
        # Verify that the symbols are preserved intact within segments (not split by period)
        self.assertTrue(any("BaseTool.run" in s for s in segments))
        self.assertTrue(any("langchain_core.tools" in s for s in segments))
        self.assertTrue(any("tools/base.py" in s for s in segments))
        self.assertTrue(any("Python 3.12" in s for s in segments))

    def test_1_contributor_noise(self):
        """TEST 1 — Contributor noise: 'I'd like to work on this issue.'"""
        res = extract_technical_evidence(
            title="Fix bug",
            body="I'd like to work on this issue.",
            labels=[],
            comments=[]
        )
        # Find CONTRIBUTOR_NOISE items
        noise_items = [x for x in res.items if x.evidence_type == "CONTRIBUTOR_NOISE"]
        self.assertTrue(len(noise_items) > 0)
        for item in noise_items:
            self.assertEqual(item.strength, "IGNORE")
            
        # Assert no CRITICAL technical evidence
        critical_items = [x for x in res.items if x.strength == "CRITICAL"]
        self.assertEqual(len(critical_items), 0)

    def test_2_assignment_with_technology(self):
        """TEST 2 — Assignment request with technology word: 'Can you assign this to me? I know Python.'"""
        res = extract_technical_evidence(
            title="Fix bug",
            body="Can you assign this to me? I know Python.",
            labels=[],
            comments=[]
        )
        
        # Python should match TECHNICAL_DEPENDENCY
        python_items = [x for x in res.items if x.evidence_type == "TECHNICAL_DEPENDENCY"]
        self.assertTrue(len(python_items) > 0)
        # Verify its strength is weak (due to contributor noise context penalty)
        for item in python_items:
            self.assertEqual(item.strength, "WEAK")

    def test_3_azure_implementation(self):
        """TEST 3 — Azure implementation evidence: 'AzureChatOpenAI creates a new httpx client on every instantiation.'"""
        res = extract_technical_evidence(
            title="Azure connection leaks",
            body="AzureChatOpenAI creates a new httpx client on every instantiation.",
            labels=[],
            comments=[]
        )
        
        types = [x.evidence_type for x in res.items]
        self.assertIn("NAMED_CLASS", types)
        self.assertIn("TECHNICAL_DEPENDENCY", types)
        self.assertIn("IMPLEMENTATION_STATEMENT", types)
        self.assertIn("ACTUAL_BEHAVIOR", types)
        
        # Verify classes and dependencies extracted
        classes = []
        for x in res.items:
            classes.extend(x.technical_entities)
        self.assertIn("AzureChatOpenAI", classes)
        self.assertIn("httpx", classes)
        
        # Assert at least one strong technical evidence item
        strong_or_critical = [x for x in res.items if x.strength in ["STRONG", "CRITICAL"]]
        self.assertTrue(len(strong_or_critical) > 0)

    def test_4_langchain_root_cause(self):
        """TEST 4 — LangChain root cause: 'The issue occurs because BaseTool.run inspects _get_runnable_config_param(self._run), while StructuredTool._run always declares config: RunnableConfig.'"""
        text = "The issue occurs because BaseTool.run inspects _get_runnable_config_param(self._run), while StructuredTool._run always declares config: RunnableConfig."
        res = extract_technical_evidence(
            title="RunnableConfig issue",
            body=text,
            labels=[],
            comments=[]
        )
        
        types = [x.evidence_type for x in res.items]
        self.assertIn("ROOT_CAUSE_STATEMENT", types)
        self.assertIn("NAMED_FUNCTION", types)
        self.assertIn("NAMED_CLASS", types)
        
        # Check entities
        entities = []
        for x in res.items:
            entities.extend(x.technical_entities)
            
        self.assertIn("BaseTool.run", entities)
        self.assertIn("_get_runnable_config_param", entities)
        self.assertIn("StructuredTool._run", entities)
        self.assertIn("RunnableConfig", entities)
        
        # Assert root-cause is CRITICAL
        rc_items = [x for x in res.items if x.evidence_type == "ROOT_CAUSE_STATEMENT"]
        self.assertTrue(len(rc_items) > 0)
        for item in rc_items:
            self.assertEqual(item.strength, "CRITICAL")

    def test_5_concrete_error_signature(self):
        """TEST 5 — Concrete error signature: 'TypeError: foo() missing 1 required positional argument: 'config''"""
        res = extract_technical_evidence(
            title="Error",
            body="TypeError: foo() missing 1 required positional argument: 'config'",
            labels=[],
            comments=[]
        )
        
        types = [x.evidence_type for x in res.items]
        self.assertIn("ERROR_SIGNATURE", types)
        
        err_items = [x for x in res.items if x.evidence_type == "ERROR_SIGNATURE"]
        self.assertTrue(len(err_items) > 0)
        for item in err_items:
            self.assertIn(item.strength, ["STRONG", "CRITICAL"])

    def test_6_generic_failure_text(self):
        """TEST 6 — Generic failure text: 'It doesn't work.'"""
        res = extract_technical_evidence(
            title="Help",
            body="It doesn't work.",
            labels=[],
            comments=[]
        )
        
        # Assert no critical or strong items
        strong_or_critical = [x for x in res.items if x.strength in ["STRONG", "CRITICAL"]]
        self.assertEqual(len(strong_or_critical), 0)

    def test_7_reproduction_detail(self):
        """TEST 7 — Reproduction detail: 'Run the test with Python 3.12 and call tool.invoke() without passing config.'"""
        res = extract_technical_evidence(
            title="Test run",
            body="Run the test with Python 3.12 and call tool.invoke() without passing config.",
            labels=[],
            comments=[]
        )
        
        types = [x.evidence_type for x in res.items]
        self.assertIn("REPRODUCTION_DETAIL", types)
        
        repro_items = [x for x in res.items if x.evidence_type == "REPRODUCTION_DETAIL"]
        self.assertTrue(len(repro_items) > 0)
        for item in repro_items:
            self.assertEqual(item.strength, "STRONG")

    def test_8_explicit_paths(self):
        """TEST 8 — Explicit paths: 'Check tools/base.py and tools/structured.py.'"""
        res = extract_technical_evidence(
            title="Path check",
            body="Check tools/base.py and tools/structured.py.",
            labels=[],
            comments=[]
        )
        
        paths = []
        for x in res.items:
            if x.evidence_type == "EXPLICIT_PATH":
                paths.append(x.normalized_value)
                self.assertIn(x.strength, ["STRONG", "CRITICAL"])
                
        self.assertIn("tools/base.py", paths)
        self.assertIn("tools/structured.py", paths)

    def test_9_generic_acknowledgement(self):
        """TEST 9 — Generic acknowledgement: 'Thanks for reporting this.'"""
        res = extract_technical_evidence(
            title="Report",
            body="Thanks for reporting this.",
            labels=[],
            comments=[]
        )
        
        types = [x.evidence_type for x in res.items]
        self.assertIn("GENERIC_DISCUSSION", types)
        for item in res.items:
            if item.evidence_type == "GENERIC_DISCUSSION":
                self.assertEqual(item.strength, "IGNORE")

    def test_10_multi_evidence_extraction(self):
        """TEST 10 — Multi-evidence extraction: 'AzureChatOpenAI creates a new httpx client on every instantiation.'"""
        res = extract_technical_evidence(
            title="Client leaks",
            body="AzureChatOpenAI creates a new httpx client on every instantiation.",
            labels=[],
            comments=[]
        )
        
        # Verify one segment produces multiple evidence types
        types = [x.evidence_type for x in res.items if x.text == "AzureChatOpenAI creates a new httpx client on every instantiation"]
        self.assertTrue(len(types) > 1)
        self.assertIn("NAMED_CLASS", types)
        self.assertIn("TECHNICAL_DEPENDENCY", types)

    def test_11_deduplication(self):
        """TEST 11 — Deduplication: Use the same path in BODY, COMMENT 1, COMMENT 2."""
        res = extract_technical_evidence(
            title="Bug",
            body="Look at tools/base.py",
            labels=[],
            comments=[
                {"author": "user1", "body": "See tools/base.py"},
                {"author": "user2", "body": "Refer to tools/base.py"}
            ]
        )
        
        path_items = [x for x in res.items if x.evidence_type == "EXPLICIT_PATH" and x.normalized_value == "tools/base.py"]
        # Should be deduplicated into 1 item
        self.assertEqual(len(path_items), 1)
        item = path_items[0]
        # Should record multiple sources (3 unique source entries)
        self.assertEqual(item.occurrence_count, 3)
        self.assertEqual(len(item.sources), 3)

    def test_12_bot_technical_evidence(self):
        """TEST 12 — Bot technical evidence: Bot posts concrete stack trace."""
        res = extract_technical_evidence(
            title="Build error",
            body="CI automated message",
            labels=[],
            comments=[
                {"author": "github-actions[bot]", "body": "TypeError: foo() missing 1 required positional argument: 'config'"}
            ]
        )
        
        # The bot comment body should still produce ERROR_SIGNATURE evidence
        err_items = [x for x in res.items if x.evidence_type == "ERROR_SIGNATURE"]
        self.assertTrue(len(err_items) > 0)
        # Even though author is a bot, the stack trace error signature strength is high
        for item in err_items:
            self.assertIn(item.strength, ["STRONG", "CRITICAL"])

    def test_13_public_schema_compatibility(self):
        """TEST 13 — Public schema compatibility: Ensure no Stage 12.2.1 fields appear in the public guidance JSON."""
        service = IssueGuidanceService()
        
        # Mock payload
        payload = {
            "issue": {
                "title": "RunnableConfig collision",
                "body": "BaseTool.run issues config",
                "labels": ["bug"],
                "owner": "langchain-ai",
                "repo": "langchain",
                "number": 34029
            },
            "repo_summary": {
                "metadata": {"name": "langchain", "description": "LangChain"}
            },
            "repository_map": {},
            "comments": [],
            "all_files": [],
            "all_dirs": []
        }
        
        # Patch cache manager to prevent database hits
        with patch.object(service.cache_manager, 'get', return_value=None), \
             patch.object(service.cache_manager, 'set', return_value=True), \
             patch.object(service.llm_service, 'generate_json') as mock_llm:
             
             mock_llm.return_value = {
                 "analysis": {
                     "beginner_explanation": "Explain it simply.",
                     "skills_required": ["Python"],
                     "affected_area": "core",
                     "difficulty": "Beginner",
                     "confidence_score": 90
                 },
                 "exploration_hints": {
                     "affected_area": "core",
                     "likely_directories": ["libs/core"],
                     "possible_files": ["libs/core/base.py"],
                     "reasoning": "Reason",
                     "confidence": 85
                 }
             }
             
             result = service.generate_guidance(payload)
             
             # Assert no new fields from Stage 12.2.1 are present in public JSON
             self.assertNotIn("technical_evidence", result)
             self.assertNotIn("critical_evidence", result)
             self.assertNotIn("strong_evidence", result)
             self.assertNotIn("top_technical_entities", result)
             self.assertNotIn("strength_counts", result)

    def test_14_zero_additional_llm_calls(self):
        """TEST 14 — Zero additional LLM calls: Run technical evidence extraction, assert LLM calls = 0."""
        # Setup mocks on LLMService
        mock_llm = MagicMock()
        
        with patch('app.services.llm_service.LLMService.generate_json', mock_llm):
            # Run extraction
            res = extract_technical_evidence(
                title="Langchain runnable config",
                body="BaseTool.run collision with RunnableConfig",
                labels=[],
                comments=[]
            )
            # Verify no LLM calls were made
            mock_llm.assert_not_called()

    def test_extraction_failure_fallback_boundary(self):
        """Assert that if the extractor raises an exception, the guidance pipeline handles it cleanly and returns successfully."""
        service = IssueGuidanceService()
        
        payload = {
            "issue": {
                "title": "RunnableConfig collision",
                "body": "BaseTool.run issues config",
                "labels": ["bug"],
                "owner": "langchain-ai",
                "repo": "langchain",
                "number": 34029
            },
            "repo_summary": {
                "metadata": {"name": "langchain", "description": "LangChain"}
            },
            "repository_map": {},
            "comments": [],
            "all_files": [],
            "all_dirs": []
        }
        
        # Patch extract_technical_evidence to raise an error
        with patch('app.services.issue_guidance_service.extract_technical_evidence', side_effect=ValueError("Simulated extractor error")), \
             patch.object(service.cache_manager, 'get', return_value=None), \
             patch.object(service.cache_manager, 'set', return_value=True), \
             patch.object(service.llm_service, 'generate_json') as mock_llm:
             
             mock_llm.return_value = {
                 "analysis": {
                     "beginner_explanation": "Explain it simply.",
                     "skills_required": ["Python"],
                     "affected_area": "core",
                     "difficulty": "Beginner",
                     "confidence_score": 90
                 },
                 "exploration_hints": {
                     "affected_area": "core",
                     "likely_directories": ["libs/core"],
                     "possible_files": ["libs/core/base.py"],
                     "reasoning": "Reason",
                     "confidence": 85
                 }
             }
             
             # The generate_guidance call should complete successfully
             result = service.generate_guidance(payload)
             self.assertIsNotNone(result)
             self.assertEqual(result.get("guidance_source"), "llm")
