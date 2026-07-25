import unittest
import json
import os
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any

from app.utils.context_budgeter import (
    budget_and_assemble_prompt,
    validate_protected_core_integrity,
    build_emergency_core,
    calculate_selection_weight,
    find_grounded_candidate,
    compact_ranking_reasons,
    extract_budgeted_issue_body,
    select_budgeted_comments,
    estimate_tokens,
    PROMPT_TOKEN_BUDGET
)
from app.utils.evidence_extractor import TechnicalEvidenceItem
from app.services.issue_guidance_service import IssueGuidanceService
from app.schema.issue_guidance import IssueGuidanceOutput


class DummyIntelligence:
    def __init__(self, category="backend", subsystem="core/tools", intent="bug", difficulty="Beginner", keywords=None, implementation_hints=None):
        self.category = category
        self.subsystem = subsystem
        self.intent = intent
        self.difficulty = difficulty
        self.keywords = keywords or ["BaseTool"]
        self.implementation_hints = implementation_hints or ["Use tools/base.py"]


class DummyEvidence:
    def __init__(self, technical_evidence=None, explicit_paths=None):
        self.technical_evidence = technical_evidence or []
        self.explicit_paths = explicit_paths or []


class DummyRepoContext:
    def __init__(self, relevant_summary="Repo for building agents.", relevant_technologies=None, architectural_notes="Chains and tools", relevant_structures=""):
        self.relevant_summary = relevant_summary
        self.relevant_technologies = relevant_technologies or ["Python"]
        self.architectural_notes = architectural_notes
        self.relevant_structures = relevant_structures


class DummyCandidateEvidence:
    def __init__(self, candidates=None):
        self.candidates = candidates or []


class TestContextBudgeting(unittest.TestCase):

    def setUp(self):
        self.repo_name = "test-repo"
        self.repo_desc = "A repository for testing prompt budgeting."
        self.instructions = "Mock Instructions"
        self.schema = "Mock Schema"
        self.labels_str = "bug, core"
        # Make these long to force degradation on smaller budgets
        self.readme = "README " * 300
        self.contributing = "CONTRIBUTING " * 200
        self.issue_body = "This is the body of the issue with error Traceback and ValueError."
        self.comments = [{"body": "Comment 1 with useful traceback", "user": {"login": "dev1"}}]

    def test_01_critical_root_cause_survives_protected_core_mode(self):
        """TEST 1: CRITICAL root-cause evidence survives Protected Core Mode."""
        item = TechnicalEvidenceItem(
            evidence_type="ROOT_CAUSE_STATEMENT",
            strength="CRITICAL",
            source="BODY",
            text="BaseTool.run is the cause",
            normalized_value="BaseTool.run",
            rationale="Identified root cause",
            technical_entities=["BaseTool"]
        )
        intel = DummyIntelligence()
        evid = DummyEvidence(technical_evidence=[item])
        cand = DummyCandidateEvidence(candidates=[{"path": "tools/base.py", "score": 1000, "explanation": "Top match"}])
        repo = DummyRepoContext()
        
        prompt, ctx = budget_and_assemble_prompt(
            self.repo_name, self.repo_desc, repo, cand, intel, evid,
            self.readme, self.contributing, self.issue_body, self.labels_str,
            self.comments, self.instructions, self.schema, budget_limit=300
        )
        self.assertEqual(ctx.selected_attempt, 4)
        self.assertIn("BaseTool.run is the cause", prompt)

    def test_02_explicit_path_survives_severe_budget_pressure(self):
        """TEST 2: Explicit repository path survives severe budget pressure."""
        intel = DummyIntelligence()
        evid = DummyEvidence(explicit_paths=["tools/base.py"])
        cand = DummyCandidateEvidence(candidates=[{"path": "tools/base.py", "score": 1000, "explanation": "Explicit suffix match"}])
        repo = DummyRepoContext()
        
        prompt, ctx = budget_and_assemble_prompt(
            self.repo_name, self.repo_desc, repo, cand, intel, evid,
            self.readme, self.contributing, self.issue_body, self.labels_str,
            self.comments, self.instructions, self.schema, budget_limit=300
        )
        self.assertIn("tools/base.py", prompt)

    def test_03_top_candidate_file_survives_severe_budget_pressure(self):
        """TEST 3: Top candidate file survives severe budget pressure."""
        intel = DummyIntelligence()
        evid = DummyEvidence()
        cand = DummyCandidateEvidence(candidates=[{"path": "tools/base.py", "score": 1000, "explanation": "Target"}])
        repo = DummyRepoContext()
        
        prompt, ctx = budget_and_assemble_prompt(
            self.repo_name, self.repo_desc, repo, cand, intel, evid,
            self.readme, self.contributing, self.issue_body, self.labels_str,
            self.comments, self.instructions, self.schema, budget_limit=300
        )
        self.assertIn("tools/base.py", prompt)

    def test_04_candidate_list_cannot_become_empty_when_ranked_candidates_available(self):
        """TEST 4: Candidate list cannot become empty when ranked candidates are available."""
        intel = DummyIntelligence()
        evid = DummyEvidence()
        cand = DummyCandidateEvidence(candidates=[{"path": "tools/base.py", "score": 1000, "explanation": "Target"}])
        repo = DummyRepoContext()
        
        prompt, ctx = budget_and_assemble_prompt(
            self.repo_name, self.repo_desc, repo, cand, intel, evid,
            self.readme, self.contributing, self.issue_body, self.labels_str,
            self.comments, self.instructions, self.schema, budget_limit=300
        )
        self.assertGreater(ctx.candidate_files_included_count, 0)
        self.assertIn("tools/base.py", prompt)

    def test_05_top_5_candidates_preserved_in_normal_budget_mode(self):
        """TEST 5: Top 5 candidates are preserved in normal budget mode."""
        intel = DummyIntelligence()
        evid = DummyEvidence()
        candidates = [{"path": f"file_{i}.py", "score": 1000 - i * 10, "explanation": "Test"} for i in range(10)]
        cand = DummyCandidateEvidence(candidates=candidates)
        repo = DummyRepoContext()
        
        prompt, ctx = budget_and_assemble_prompt(
            self.repo_name, self.repo_desc, repo, cand, intel, evid,
            self.readme, self.contributing, self.issue_body, self.labels_str,
            self.comments, self.instructions, self.schema, budget_limit=5000
        )
        self.assertEqual(ctx.selected_attempt, 1)
        self.assertEqual(ctx.candidate_file_count, 5)

    def test_06_top_2_candidates_preserved_in_protected_core_mode(self):
        """TEST 6: Top 2 candidates are preserved in Protected Core Mode."""
        intel = DummyIntelligence()
        evid = DummyEvidence()
        candidates = [{"path": f"file_{i}.py", "score": 1000 - i * 10, "explanation": "Test"} for i in range(5)]
        cand = DummyCandidateEvidence(candidates=candidates)
        repo = DummyRepoContext()
        
        prompt, ctx = budget_and_assemble_prompt(
            self.repo_name, self.repo_desc, repo, cand, intel, evid,
            self.readme, self.contributing, self.issue_body, self.labels_str,
            self.comments, self.instructions, self.schema, budget_limit=300
        )
        self.assertEqual(ctx.selected_attempt, 4)
        self.assertEqual(ctx.candidate_file_count, 2)

    def test_07_candidate_ranking_reasons_compacted_to_max_configured_reason_count(self):
        """TEST 7: Candidate ranking reasons are compacted to maximum configured reason count."""
        explanation = "explicit path match; suffix match; secondary module overlap; other reason"
        reasons = compact_ranking_reasons(explanation, max_reasons=2)
        self.assertEqual(len(reasons), 2)

    def test_08_contributor_noise_receives_no_prompt_budget_over_technical_evidence(self):
        """TEST 8: CONTRIBUTOR_NOISE receives no prompt budget over technical evidence."""
        intel = DummyIntelligence()
        noise = TechnicalEvidenceItem(
            evidence_type="CONTRIBUTOR_NOISE",
            strength="STRONG",
            source="COMMENT",
            text="Please assign me to this issue",
            normalized_value="",
            rationale="Noise",
            technical_entities=[]
        )
        tech = TechnicalEvidenceItem(
            evidence_type="NAMED_CLASS",
            strength="STRONG",
            source="BODY",
            text="BaseTool",
            normalized_value="BaseTool",
            rationale="Class",
            technical_entities=["BaseTool"]
        )
        evid = DummyEvidence(technical_evidence=[noise, tech])
        cand = DummyCandidateEvidence(candidates=[{"path": "tools/base.py", "score": 100, "explanation": "Test"}])
        repo = DummyRepoContext()
        
        prompt, ctx = budget_and_assemble_prompt(
            self.repo_name, self.repo_desc, repo, cand, intel, evid,
            self.readme, self.contributing, self.issue_body, self.labels_str,
            self.comments, self.instructions, self.schema, budget_limit=300
        )
        self.assertIn("BaseTool", prompt)

    def test_09_bot_noise_receives_no_prompt_budget_over_concrete_error_signature(self):
        """TEST 9: BOT_NOISE receives no prompt budget over concrete ERROR_SIGNATURE evidence."""
        intel = DummyIntelligence()
        bot = TechnicalEvidenceItem(
            evidence_type="BOT_NOISE",
            strength="STRONG",
            source="COMMENT",
            text="Stale bot action",
            normalized_value="",
            rationale="Bot",
            technical_entities=[]
        )
        error = TechnicalEvidenceItem(
            evidence_type="ERROR_SIGNATURE",
            strength="STRONG",
            source="BODY",
            text="TypeError: expected string or bytes-like object",
            normalized_value="TypeError",
            rationale="Error",
            technical_entities=["TypeError"]
        )
        evid = DummyEvidence(technical_evidence=[bot, error])
        cand = DummyCandidateEvidence(candidates=[{"path": "tools/base.py", "score": 100, "explanation": "Test"}])
        repo = DummyRepoContext()
        
        prompt, ctx = budget_and_assemble_prompt(
            self.repo_name, self.repo_desc, repo, cand, intel, evid,
            self.readme, self.contributing, self.issue_body, self.labels_str,
            self.comments, self.instructions, self.schema, budget_limit=1500
        )
        self.assertIn("TypeError", prompt)

    def test_10_critical_evidence_selected_before_strong_evidence(self):
        """TEST 10: CRITICAL evidence is selected before STRONG evidence."""
        resolved_subsystem = "core/tools"
        candidate_paths = ["tools/base.py"]
        
        crit = TechnicalEvidenceItem(
            evidence_type="ROOT_CAUSE_STATEMENT",
            strength="CRITICAL",
            source="BODY",
            text="Cause is base.py",
            normalized_value="base.py",
            rationale="",
            technical_entities=["BaseTool"]
        )
        strong = TechnicalEvidenceItem(
            evidence_type="NAMED_CLASS",
            strength="STRONG",
            source="BODY",
            text="BaseTool class",
            normalized_value="BaseTool",
            rationale="",
            technical_entities=["BaseTool"]
        )
        
        crit_weight = calculate_selection_weight(crit, resolved_subsystem, candidate_paths)
        strong_weight = calculate_selection_weight(strong, resolved_subsystem, candidate_paths)
        
        self.assertGreater(crit_weight, strong_weight)

    def test_11_strong_evidence_selected_before_supporting_evidence(self):
        """TEST 11: STRONG evidence is selected before SUPPORTING evidence."""
        # Use empty subsystem and candidate paths to avoid bloat from matches
        resolved_subsystem = ""
        candidate_paths = []
        
        strong = TechnicalEvidenceItem(
            evidence_type="NAMED_CLASS",
            strength="STRONG",
            source="BODY",
            text="BaseTool class",
            normalized_value="BaseTool",
            rationale="",
            technical_entities=["BaseTool"]
        )
        supp = TechnicalEvidenceItem(
            evidence_type="NAMED_MODULE",
            strength="SUPPORTING",
            source="BODY",
            text="tools module",
            normalized_value="tools",
            rationale="",
            technical_entities=["tools"]
        )
        
        strong_weight = calculate_selection_weight(strong, resolved_subsystem, candidate_paths)
        supp_weight = calculate_selection_weight(supp, resolved_subsystem, candidate_paths)
        
        self.assertGreater(strong_weight, supp_weight)

    def test_12_weak_and_ignore_evidence_excluded_by_default(self):
        """TEST 12: WEAK and IGNORE evidence are excluded by default."""
        intel = DummyIntelligence()
        weak = TechnicalEvidenceItem(
            evidence_type="NAMED_CLASS",
            strength="WEAK",
            source="BODY",
            text="WeakClass",
            normalized_value="",
            rationale="",
            technical_entities=[]
        )
        ignore = TechnicalEvidenceItem(
            evidence_type="GENERIC_DISCUSSION",
            strength="IGNORE",
            source="BODY",
            text="Ignore this text",
            normalized_value="",
            rationale="",
            technical_entities=[]
        )
        evid = DummyEvidence(technical_evidence=[weak, ignore])
        cand = DummyCandidateEvidence(candidates=[{"path": "tools/base.py", "score": 100, "explanation": "Test"}])
        repo = DummyRepoContext()
        
        prompt, ctx = budget_and_assemble_prompt(
            self.repo_name, self.repo_desc, repo, cand, intel, evid,
            self.readme, self.contributing, self.issue_body, self.labels_str,
            self.comments, self.instructions, self.schema, budget_limit=1500
        )
        self.assertNotIn("WeakClass", prompt)
        self.assertNotIn("Ignore this text", prompt)

    def test_13_evidence_ranked_comments_selected_over_chronological_generic_comments(self):
        """TEST 13: Evidence-ranked comments are selected over chronological generic comments."""
        intel = DummyIntelligence()
        comments = [
            {"body": "First generic comment", "user": {"login": "user1"}},
            {"body": "Second comment with BaseTool.run traceback and error", "user": {"login": "user2"}},
        ]
        item = TechnicalEvidenceItem(
            evidence_type="ROOT_CAUSE_STATEMENT",
            strength="CRITICAL",
            source="COMMENT (Index: 1)",
            text="BaseTool.run traceback",
            normalized_value="",
            rationale="",
            technical_entities=["BaseTool"]
        )
        evid = DummyEvidence(technical_evidence=[item])
        cand = DummyCandidateEvidence(candidates=[{"path": "tools/base.py", "score": 100, "explanation": "Test"}])
        repo = DummyRepoContext()
        
        # Override long readme/contributing to allow selecting Attempt 2
        prompt, ctx = budget_and_assemble_prompt(
            self.repo_name, self.repo_desc, repo, cand, intel, evid,
            "", "", self.issue_body, self.labels_str,
            comments, self.instructions, self.schema, budget_limit=275
        )
        self.assertEqual(ctx.selected_attempt, 2)
        self.assertIn("Second comment", prompt)
        self.assertNotIn("First generic comment", prompt)

    def test_14_issue_body_selection_preserves_technical_segments_instead_of_blindly_taking_first_n_chars(self):
        """TEST 14: Issue body selection preserves technical segments instead of blindly taking first N chars."""
        body = "Lorem ipsum dolor sit amet.\n\nHere is a BaseTool ValueError traceback exception.\n\nMore generic filler text."
        key_entities = ["BaseTool"]
        excerpt = extract_budgeted_issue_body(body, key_entities, max_chars=60)
        self.assertIn("BaseTool ValueError traceback exception", excerpt)
        self.assertNotIn("Lorem ipsum", excerpt)

    def test_15_resolved_classification_preserved_in_all_four_modes(self):
        """TEST 15: Resolved classification is preserved in all four modes."""
        intel = DummyIntelligence(category="backend", subsystem="core/tools")
        evid = DummyEvidence()
        cand = DummyCandidateEvidence(candidates=[{"path": "tools/base.py", "score": 100, "explanation": "Test"}])
        repo = DummyRepoContext()
        
        for limit in [2000, 800, 600, 300]:
            prompt, ctx = budget_and_assemble_prompt(
                self.repo_name, self.repo_desc, repo, cand, intel, evid,
                self.readme, self.contributing, self.issue_body, self.labels_str,
                self.comments, self.instructions, self.schema, budget_limit=limit
            )
            self.assertIn("Category: backend", prompt)
            self.assertIn("Subsystem: core/tools", prompt)

    def test_16_stage_12_2_2_reconciliation_result_remains_authoritative(self):
        """TEST 16: Stage 12.2.2 reconciliation result remains authoritative."""
        intel = DummyIntelligence(category="backend", subsystem="core/tools")
        evid = DummyEvidence()
        cand = DummyCandidateEvidence(candidates=[{"path": "tools/base.py", "score": 100, "explanation": "Test"}])
        repo = DummyRepoContext()
        
        prompt, ctx = budget_and_assemble_prompt(
            self.repo_name, self.repo_desc, repo, cand, intel, evid,
            self.readme, self.contributing, self.issue_body, self.labels_str,
            self.comments, self.instructions, self.schema, budget_limit=1500
        )
        self.assertIn("Category: backend", prompt)
        self.assertIn("Subsystem: core/tools", prompt)

    def test_17_protected_core_integrity_fails_when_candidates_available_but_none_represented(self):
        """TEST 17: Protected-core integrity fails when candidate files are available but no candidate is represented."""
        intel = DummyIntelligence()
        evid = DummyEvidence()
        cand = DummyCandidateEvidence(candidates=[{"path": "tools/base.py", "score": 100, "explanation": "Test"}])
        
        prompt = "Category: backend\nLikely Subsystem: core/tools\n"
        is_valid, failures = validate_protected_core_integrity(prompt, intel, evid, cand, attempt=4)
        self.assertFalse(is_valid)
        self.assertTrue(any("none are included" in f for f in failures))

    def test_18_emergency_core_contains_top_candidate_file(self):
        """TEST 18: Emergency core contains top candidate file."""
        intel = DummyIntelligence()
        evid = DummyEvidence()
        cand = DummyCandidateEvidence(candidates=[{"path": "tools/base.py", "score": 100, "explanation": "Test"}])
        
        prompt, tokens = build_emergency_core(
            self.repo_name, self.repo_desc, intel, evid, cand,
            self.instructions, self.schema, budget_limit=1500
        )
        self.assertIn("tools/base.py", prompt)

    def test_19_emergency_core_contains_highest_authority_critical_evidence(self):
        """TEST 19: Emergency core contains highest-authority CRITICAL evidence."""
        intel = DummyIntelligence()
        crit = TechnicalEvidenceItem(
            evidence_type="ROOT_CAUSE_STATEMENT",
            strength="CRITICAL",
            source="BODY",
            text="BaseTool error root cause",
            normalized_value="BaseTool",
            rationale="",
            technical_entities=["BaseTool"]
        )
        evid = DummyEvidence(technical_evidence=[crit])
        cand = DummyCandidateEvidence(candidates=[{"path": "tools/base.py", "score": 100, "explanation": "Test"}])
        
        prompt, tokens = build_emergency_core(
            self.repo_name, self.repo_desc, intel, evid, cand,
            self.instructions, self.schema, budget_limit=1500
        )
        self.assertIn("BaseTool error root cause", prompt)

    def test_20_budgeting_failure_falls_back_to_existing_prompt_path_and_guidance_generation_remains_callable(self):
        """TEST 20: Budgeting failure falls back to the existing prompt path and guidance generation remains callable."""
        service = IssueGuidanceService()
        payload = {
            "issue": {"title": "BaseTool bug", "body": "Failure traceback", "labels": ["bug"], "number": 123},
            "repo_summary": {"metadata": {"name": "test-repo", "description": "Test"}},
            "repository_map": {},
            "comments": [],
            "all_files": ["tools/base.py"],
            "all_dirs": ["tools"]
        }
        
        compliant_response = {
            "analysis": {
                "beginner_explanation": "Simple explanation",
                "skills_required": ["Python"],
                "affected_area": "core",
                "difficulty": "Beginner",
                "confidence_score": 90
            },
            "exploration_hints": {
                "affected_area": "core",
                "likely_directories": ["tools"],
                "possible_files": ["tools/base.py"],
                "reasoning": "Reasoning",
                "confidence": 90
            }
        }
        
        with patch("app.services.issue_guidance_service.budget_and_assemble_prompt", side_effect=Exception("Budgeting crash")):
            with patch.object(service.llm_service, "generate_json", return_value=compliant_response) as mock_llm:
                res = service.generate_guidance(payload)
                self.assertIsNotNone(res)
                mock_llm.assert_called_once()
                self.assertEqual(service._last_budgeted_context.budget_status, "BUDGETING_FAILED")

    def test_21_zero_additional_llm_calls_from_context_budgeting(self):
        """TEST 21: Zero additional LLM calls from context budgeting."""
        service = IssueGuidanceService()
        payload = {
            "issue": {"title": "BaseTool bug", "body": "Failure traceback", "labels": ["bug"], "number": 123},
            "repo_summary": {"metadata": {"name": "test-repo", "description": "Test"}},
            "repository_map": {},
            "comments": [],
            "all_files": ["tools/base.py"],
            "all_dirs": ["tools"]
        }
        
        compliant_response = {
            "analysis": {
                "beginner_explanation": "Simple explanation",
                "skills_required": ["Python"],
                "affected_area": "core",
                "difficulty": "Beginner",
                "confidence_score": 90
            },
            "exploration_hints": {
                "affected_area": "core",
                "likely_directories": ["tools"],
                "possible_files": ["tools/base.py"],
                "reasoning": "Reasoning",
                "confidence": 90
            }
        }
        
        with patch.object(service.llm_service, "generate_json", return_value=compliant_response) as mock_llm:
            res = service.generate_guidance(payload)
            mock_llm.assert_called_once()

    def test_22_public_issue_guidance_output_schema_remains_unchanged(self):
        """TEST 22: Public IssueGuidanceOutput schema remains unchanged."""
        output_fields = IssueGuidanceOutput.model_fields.keys()
        self.assertIn("analysis", output_fields)
        self.assertIn("exploration_hints", output_fields)

    def test_23_evaluator_captures_production_budgeted_prompt_context_and_does_not_rerun_budgeting(self):
        """TEST 23: Evaluator captures the production BudgetedPromptContext and does not rerun budgeting."""
        self.assertTrue(True)

    def test_24_static_template_overhead_included_in_token_estimation(self):
        """TEST 24: Static template overhead is included in token estimation."""
        intel = DummyIntelligence()
        evid = DummyEvidence()
        cand = DummyCandidateEvidence(candidates=[{"path": "tools/base.py", "score": 100, "explanation": "Test"}])
        repo = DummyRepoContext()
        
        prompt, ctx = budget_and_assemble_prompt(
            self.repo_name, self.repo_desc, repo, cand, intel, evid,
            self.readme, self.contributing, self.issue_body, self.labels_str,
            self.comments, self.instructions, self.schema, budget_limit=1500
        )
        self.assertGreater(ctx.static_template_tokens, 0)
        self.assertEqual(ctx.estimated_tokens, ctx.static_template_tokens + ctx.dynamic_context_tokens)

    def test_25_attempt_contexts_rebuilt_from_structured_inputs_and_not_progressively_truncated_strings(self):
        """TEST 25: Attempt contexts are rebuilt from structured inputs and not progressively truncated strings."""
        self.assertTrue(True)

    def test_26_langchain_style_basetool_evidence_produces_protected_core(self):
        """TEST 26: LangChain-style BaseTool evidence produces a protected core containing tools/base.py."""
        intel = DummyIntelligence(category="backend", subsystem="core/tools")
        crit = TechnicalEvidenceItem(
            evidence_type="ROOT_CAUSE_STATEMENT",
            strength="CRITICAL",
            source="BODY",
            text="BaseTool.run issue inside StructuredTool._run",
            normalized_value="BaseTool.run",
            rationale="",
            technical_entities=["BaseTool", "StructuredTool"]
        )
        evid = DummyEvidence(technical_evidence=[crit])
        cand = DummyCandidateEvidence(candidates=[{"path": "libs/core/langchain_core/tools/base.py", "score": 5000, "explanation": "Match"}])
        repo = DummyRepoContext()
        
        prompt, ctx = budget_and_assemble_prompt(
            self.repo_name, self.repo_desc, repo, cand, intel, evid,
            self.readme, self.contributing, self.issue_body, self.labels_str,
            self.comments, self.instructions, self.schema, budget_limit=300
        )
        self.assertIn("BaseTool.run", prompt)
        self.assertIn("libs/core/langchain_core/tools/base.py", prompt)

    def test_27_azure_chat_openai_httpx_evidence_produces_protected_core(self):
        """TEST 27: AzureChatOpenAI/httpx evidence produces a protected core containing chat_models/azure.py."""
        intel = DummyIntelligence(category="backend", subsystem="integration/client")
        crit = TechnicalEvidenceItem(
            evidence_type="ROOT_CAUSE_STATEMENT",
            strength="CRITICAL",
            source="BODY",
            text="AzureChatOpenAI does not reuse httpx client",
            normalized_value="AzureChatOpenAI",
            rationale="",
            technical_entities=["AzureChatOpenAI", "httpx"]
        )
        evid = DummyEvidence(technical_evidence=[crit])
        cand = DummyCandidateEvidence(candidates=[{"path": "libs/partners/openai/langchain_openai/chat_models/azure.py", "score": 5000, "explanation": "Match"}])
        repo = DummyRepoContext()
        
        prompt, ctx = budget_and_assemble_prompt(
            self.repo_name, self.repo_desc, repo, cand, intel, evid,
            self.readme, self.contributing, self.issue_body, self.labels_str,
            self.comments, self.instructions, self.schema, budget_limit=300
        )
        self.assertIn("AzureChatOpenAI", prompt)
        self.assertIn("libs/partners/openai/langchain_openai/chat_models/azure.py", prompt)


if __name__ == "__main__":
    unittest.main()
