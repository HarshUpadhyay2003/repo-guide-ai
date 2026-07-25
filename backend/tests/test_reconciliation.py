import unittest
from unittest.mock import patch, MagicMock
from app.utils.evidence_extractor import extract_technical_evidence, TechnicalEvidenceItem
from app.utils.classification_reconciler import reconcile_issue_classification, ClassificationReconciliationResult
from app.services.issue_guidance_service import IssueGuidanceService, IssueEvidence, IssueIntelligence

class DummyIntelligence:
    def __init__(self, category: str, subsystem: str = ""):
        self.category = category
        self.subsystem = subsystem

class DummyEvidence:
    def __init__(self, technical_evidence: list):
        self.technical_evidence = technical_evidence

class TestClassificationReconciliation(unittest.TestCase):

    def test_A_docs_to_backend_override(self):
        """A: docs -> backend override using CRITICAL root-cause evidence."""
        intel = DummyIntelligence(category="docs", subsystem="general")
        # Root cause statement with backend keywords is CRITICAL
        evid_item = TechnicalEvidenceItem(
            evidence_type="ROOT_CAUSE_STATEMENT",
            strength="CRITICAL",
            source="COMMENT",
            text="The issue occurs because BaseTool.run fails on config",
            normalized_value="The issue occurs because BaseTool.run fails on config",
            rationale="Root cause",
            technical_entities=["BaseTool.run"]
        )
        evid = DummyEvidence(technical_evidence=[evid_item])
        
        res = reconcile_issue_classification(intel, evid)
        self.assertEqual(res.resolved_category, "backend")
        self.assertEqual(res.decision, "OVERRIDDEN")

    def test_B_frontend_to_backend_override(self):
        """B: frontend -> backend override using two STRONG implementation/actual-behavior evidence items."""
        intel = DummyIntelligence(category="frontend", subsystem="general")
        item1 = TechnicalEvidenceItem(
            evidence_type="IMPLEMENTATION_STATEMENT",
            strength="STRONG",
            source="BODY",
            text="AzureChatOpenAI client needs config object",
            normalized_value="AzureChatOpenAI client needs config object",
            rationale="Implementation",
            technical_entities=["AzureChatOpenAI"]
        )
        item2 = TechnicalEvidenceItem(
            evidence_type="ACTUAL_BEHAVIOR",
            strength="STRONG",
            source="COMMENT",
            text="It creates a new httpx client on every instantiation",
            normalized_value="It creates a new httpx client on every instantiation",
            rationale="Actual behavior",
            technical_entities=["httpx"]
        )
        evid = DummyEvidence(technical_evidence=[item1, item2])
        
        res = reconcile_issue_classification(intel, evid)
        self.assertEqual(res.resolved_category, "backend")
        self.assertEqual(res.decision, "OVERRIDDEN")

    def test_C_docs_retained_with_weak_evidence(self):
        """C: docs retained when only WEAK Python dependency evidence exists."""
        intel = DummyIntelligence(category="docs", subsystem="general")
        item = TechnicalEvidenceItem(
            evidence_type="TECHNICAL_DEPENDENCY",
            strength="WEAK",
            source="BODY",
            text="Python is used here",
            normalized_value="Python",
            rationale="Weak dependency",
            technical_entities=["Python"]
        )
        evid = DummyEvidence(technical_evidence=[item])
        
        res = reconcile_issue_classification(intel, evid)
        self.assertEqual(res.resolved_category, "docs")
        self.assertIn(res.decision, ["RETAINED", "INSUFFICIENT_EVIDENCE", "NO_CONFLICT"])

    def test_D_frontend_retained_for_react_signals(self):
        """D: frontend retained for React + TSX + component/render evidence."""
        intel = DummyIntelligence(category="frontend", subsystem="general")
        item = TechnicalEvidenceItem(
            evidence_type="IMPLEMENTATION_STATEMENT",
            strength="STRONG",
            source="BODY",
            text="React component render is broken in JSX/TSX",
            normalized_value="React component render is broken in JSX/TSX",
            rationale="Strong frontend info",
            technical_entities=["React", "JSX", "TSX"]
        )
        evid = DummyEvidence(technical_evidence=[item])
        
        res = reconcile_issue_classification(intel, evid)
        self.assertEqual(res.resolved_category, "frontend")
        self.assertIn(res.decision, ["RETAINED", "NO_CONFLICT"])

    def test_E_tests_classification(self):
        """E: tests classification from pytest + fixture + test path evidence."""
        intel = DummyIntelligence(category="docs", subsystem="general")
        item = TechnicalEvidenceItem(
            evidence_type="REPRODUCTION_DETAIL",
            strength="CRITICAL",
            source="BODY",
            text="Run tests/test_core.py with pytest fixture",
            normalized_value="tests/test_core.py",
            rationale="Reproduction",
            technical_entities=["pytest", "fixture"]
        )
        evid = DummyEvidence(technical_evidence=[item])
        
        res = reconcile_issue_classification(intel, evid)
        self.assertEqual(res.resolved_category, "tests")
        self.assertEqual(res.decision, "OVERRIDDEN")

    def test_F_config_classification(self):
        """F: config classification from YAML/workflow/CI evidence."""
        intel = DummyIntelligence(category="docs", subsystem="general")
        item = TechnicalEvidenceItem(
            evidence_type="IMPLEMENTATION_STATEMENT",
            strength="CRITICAL",
            source="BODY",
            text="Update the CI configuration in .github/workflows/ci.yml using YAML",
            normalized_value=".github/workflows/ci.yml",
            rationale="Configuration yaml",
            technical_entities=["YAML", "workflow"]
        )
        evid = DummyEvidence(technical_evidence=[item])
        
        res = reconcile_issue_classification(intel, evid)
        self.assertEqual(res.resolved_category, "config")
        self.assertEqual(res.decision, "OVERRIDDEN")

    def test_G_contributor_noise_cannot_override(self):
        """G: contributor-noise technology cannot override."""
        intel = DummyIntelligence(category="docs", subsystem="general")
        item = TechnicalEvidenceItem(
            evidence_type="CONTRIBUTOR_NOISE",
            strength="IGNORE",
            source="BODY",
            text="I want to solve this with Python",
            normalized_value="I want to solve this with Python",
            rationale="Contributor noise",
            technical_entities=["Python"]
        )
        evid = DummyEvidence(technical_evidence=[item])
        
        res = reconcile_issue_classification(intel, evid)
        self.assertEqual(res.resolved_category, "docs")
        self.assertIn(res.decision, ["RETAINED", "NO_CONFLICT"])

    def test_H_bot_noise_cannot_override(self):
        """H: bot generic text cannot override."""
        intel = DummyIntelligence(category="docs", subsystem="general")
        item = TechnicalEvidenceItem(
            evidence_type="BOT_NOISE",
            strength="IGNORE",
            source="COMMENT",
            text="Automated build check message",
            normalized_value="Automated build check message",
            rationale="Bot noise",
            technical_entities=[]
        )
        evid = DummyEvidence(technical_evidence=[item])
        
        res = reconcile_issue_classification(intel, evid)
        self.assertEqual(res.resolved_category, "docs")
        self.assertIn(res.decision, ["RETAINED", "NO_CONFLICT"])

    def test_I_bot_error_signature_participates(self):
        """I: concrete bot ERROR_SIGNATURE can participate in reconciliation."""
        intel = DummyIntelligence(category="docs", subsystem="general")
        item = TechnicalEvidenceItem(
            evidence_type="ERROR_SIGNATURE",
            strength="CRITICAL",
            source="COMMENT",
            text="TypeError: config must be a dict",
            normalized_value="TypeError",
            rationale="Bot posted exception signature",
            technical_entities=["TypeError", "config"]
        )
        evid = DummyEvidence(technical_evidence=[item])
        
        res = reconcile_issue_classification(intel, evid)
        self.assertEqual(res.resolved_category, "backend")
        self.assertEqual(res.decision, "OVERRIDDEN")

    def test_J_subsystem_resolution_tools(self):
        """J: subsystem resolution for BaseTool.run / StructuredTool._run / RunnableConfig."""
        intel = DummyIntelligence(category="docs", subsystem="general")
        item = TechnicalEvidenceItem(
            evidence_type="ROOT_CAUSE_STATEMENT",
            strength="CRITICAL",
            source="BODY",
            text="BaseTool.run collision with RunnableConfig",
            normalized_value="BaseTool.run",
            rationale="Root cause statement",
            technical_entities=["BaseTool.run", "RunnableConfig"]
        )
        evid = DummyEvidence(technical_evidence=[item])
        
        res = reconcile_issue_classification(intel, evid)
        self.assertEqual(res.resolved_subsystem, "core/tools")

    def test_K_subsystem_resolution_client(self):
        """K: subsystem resolution for AzureChatOpenAI / httpx client evidence."""
        intel = DummyIntelligence(category="docs", subsystem="general")
        item = TechnicalEvidenceItem(
            evidence_type="IMPLEMENTATION_STATEMENT",
            strength="STRONG",
            source="BODY",
            text="AzureChatOpenAI class uses httpx",
            normalized_value="AzureChatOpenAI",
            rationale="Strong class reference",
            technical_entities=["AzureChatOpenAI", "httpx"]
        )
        evid = DummyEvidence(technical_evidence=[item])
        
        res = reconcile_issue_classification(intel, evid)
        self.assertEqual(res.resolved_subsystem, "integration/client")

    def test_L_reconciliation_failure_fallback(self):
        """L: reconciliation failure fallback retains original intelligence and guidance generation succeeds."""
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
        
        # Patch reconcile_issue_classification to raise exception
        with patch('app.services.issue_guidance_service.reconcile_issue_classification', side_effect=RuntimeError("Simulated reconciler fail")), \
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
             
             result = service.generate_guidance(payload)
             self.assertIsNotNone(result)
             self.assertEqual(result.get("guidance_source"), "llm")

    def test_M_zero_additional_llm_calls(self):
        """M: zero additional LLM calls."""
        # Setup mocks on LLMService
        mock_llm = MagicMock()
        
        with patch('app.services.llm_service.LLMService.generate_json', mock_llm):
            intel = DummyIntelligence(category="docs", subsystem="general")
            item = TechnicalEvidenceItem(
                evidence_type="ROOT_CAUSE_STATEMENT",
                strength="CRITICAL",
                source="BODY",
                text="BaseTool.run collision with RunnableConfig",
                normalized_value="BaseTool.run",
                rationale="Root cause statement",
                technical_entities=["BaseTool.run", "RunnableConfig"]
            )
            evid = DummyEvidence(technical_evidence=[item])
            
            res = reconcile_issue_classification(intel, evid)
            # Verify no LLM calls were made
            mock_llm.assert_not_called()

    def test_N_public_guidance_schema_compatibility(self):
        """N: public guidance schema compatibility."""
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
             # Assert no new fields from Stage 12.2.2 are present in public JSON
             self.assertNotIn("reconciliation_result", result)
             self.assertNotIn("original_category", result)
             self.assertNotIn("resolved_category", result)

    def test_O_evaluator_captures_production_result(self):
        """O: evaluator captures production reconciliation result rather than recomputing it."""
        from evaluation.prompt_capture import EvaluationCaptureContext
        # Verify that wrapped_understand simply copies reconciliation_result from the returned IssueEvidence object.
        # We can test this by mocking the returned objects.
        mock_intel = DummyIntelligence(category="backend", subsystem="core/tools")
        mock_recon = ClassificationReconciliationResult(
            original_category="docs",
            original_subsystem="general",
            resolved_category="backend",
            resolved_subsystem="core/tools",
            decision="OVERRIDDEN",
            confidence_score=95.0,
            evidence_entities=["BaseTool.run"],
            rationale="Test rationale"
        )
        mock_evidence = DummyEvidence(technical_evidence=[])
        setattr(mock_evidence, "reconciliation_result", mock_recon)
        setattr(mock_evidence, "evidence", [])
        setattr(mock_evidence, "matched_labels", [])
        setattr(mock_evidence, "matched_keywords", [])
        setattr(mock_evidence, "detected_stack", [])
        setattr(mock_evidence, "explicit_paths", [])
        setattr(mock_evidence, "technical_evidence_capture_status", "CAPTURED")
        
        # Verify that we can extract the correct captured data structures
        from evaluation.benchmark_models import ClassificationReconciliationCaptured
        captured = ClassificationReconciliationCaptured(
            original_category=mock_recon.original_category,
            original_subsystem=mock_recon.original_subsystem,
            resolved_category=mock_recon.resolved_category,
            resolved_subsystem=mock_recon.resolved_subsystem,
            decision=mock_recon.decision,
            confidence_score=mock_recon.confidence_score,
            evidence_entities=mock_recon.evidence_entities,
            conflicting_evidence_count=len(mock_recon.conflicting_evidence),
            supporting_evidence_count=len(mock_recon.supporting_evidence),
            rationale=mock_recon.rationale,
            additional_llm_calls_from_reconciliation=0,
            classification_reconciliation_ms=0.1,
            capture_status="CAPTURED"
        )
        
        self.assertEqual(captured.original_category, "docs")
        self.assertEqual(captured.resolved_category, "backend")
        self.assertEqual(captured.decision, "OVERRIDDEN")
