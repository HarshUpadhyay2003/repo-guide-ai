import unittest
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# Import production code to verify
from app.utils.file_relationship_grounder import ground_file_relationships, classify_entity_specificity
from app.utils.classification_reconciler import reconcile_issue_classification

# --- Reusable Synthetic Repository Fixtures ---

# Fixture A: Python Service
FIXTURE_A_FILES = [
    "pyproject.toml",
    "README.md",
    "app/__init__.py",
    "app/main.py",
    "app/api/endpoints.py",
    "app/services/worker.py",
    "app/utils/helpers.py",
    "tests/conftest.py",
    "tests/test_api.py"
]

# Fixture B: TypeScript Web App
FIXTURE_B_FILES = [
    "package.json",
    "tsconfig.json",
    "README.md",
    "src/index.tsx",
    "src/components/UserPanel.tsx",
    "src/components/common/Button.tsx",
    "src/hooks/useAuth.ts",
    "src/services/apiClient.ts",
    "src/utils/formatters.ts"
]

# Fixture C: Go Service
FIXTURE_C_FILES = [
    "go.mod",
    "go.sum",
    "README.md",
    "cmd/server/main.go",
    "internal/api/handler.go",
    "internal/db/connection.go",
    "pkg/logger/logger.go"
]

# Fixture D: Java Application
FIXTURE_D_FILES = [
    "pom.xml",
    "README.md",
    "src/main/java/com/example/service/PaymentService.java",
    "src/main/java/com/example/model/Invoice.java",
    "src/main/java/com/example/controller/InvoiceController.java",
    "src/test/java/com/example/service/PaymentServiceTest.java"
]

# Fixture E: Rust Project
FIXTURE_E_FILES = [
    "Cargo.toml",
    "src/main.rs",
    "src/client.rs",
    "src/client/mod.rs",
    "src/utils.rs",
    "tests/integration_test.rs"
]

# Fixture F: Monorepo without libs/
FIXTURE_F_FILES = [
    "package.json",
    "packages/web/package.json",
    "packages/web/src/index.ts",
    "packages/web/src/components/App.tsx",
    "packages/server/package.json",
    "packages/server/src/index.ts",
    "packages/server/src/routes/api.ts"
]

# Fixture G: Extensionless / Infrastructure Repository
FIXTURE_G_FILES = [
    "Dockerfile",
    "Makefile",
    "Jenkinsfile",
    ".env",
    ".env.example",
    "nginx.conf"
]

# --- Mock Classes for Testing ---

@dataclass
class DummyIntelligence:
    category: str = "backend"
    subsystem: str = "core/tools"

@dataclass
class DummyEvidenceItem:
    evidence_type: str
    strength: str
    source: str
    text: str
    normalized_value: str
    rationale: str = ""
    technical_entities: List[str] = field(default_factory=list)

@dataclass
class DummyEvidence:
    technical_evidence: List[DummyEvidenceItem] = field(default_factory=list)

@dataclass
class DummyCandidateEvidence:
    candidates: List[Dict[str, Any]] = field(default_factory=list)


# --- Test Classes ---

class TestPythonRepositoryGrounding(unittest.TestCase):
    def test_python_path_grounding(self):
        """1: Python repository-relative explicit path grounding."""
        intel = DummyIntelligence()
        candidate_ev = DummyCandidateEvidence(candidates=[{"path": "app/main.py"}])
        item = DummyEvidenceItem(
            evidence_type="EXPLICIT_PATH",
            strength="STRONG",
            source="BODY",
            text="app/main.py",
            normalized_value="app/main.py"
        )
        evid = DummyEvidence(technical_evidence=[item])
        res = ground_file_relationships(FIXTURE_A_FILES, {}, candidate_ev, intel, evid)
        self.assertTrue(any(r.resolution_status == "GROUNDED" and r.normalized_value == "app/main.py" for r in res.explicit_path_resolutions))

    def test_windows_suffix_resolution(self):
        """2: Windows suffix path resolution (api\\\\endpoints.py -> api/endpoints.py)."""
        intel = DummyIntelligence()
        candidate_ev = DummyCandidateEvidence()
        item = DummyEvidenceItem(
            evidence_type="EXPLICIT_PATH",
            strength="STRONG",
            source="BODY",
            text="api\\endpoints.py",
            normalized_value="api\\endpoints.py"
        )
        evid = DummyEvidence(technical_evidence=[item])
        res = ground_file_relationships(FIXTURE_A_FILES, {}, candidate_ev, intel, evid)
        self.assertTrue(any(r.resolution_status == "GROUNDED" and r.normalized_value == "api/endpoints.py" for r in res.explicit_path_resolutions))

    def test_suffix_matching_nested(self):
        """3: Suffix matching for nested Python files (services/worker.py -> app/services/worker.py)."""
        intel = DummyIntelligence()
        candidate_ev = DummyCandidateEvidence()
        item = DummyEvidenceItem(
            evidence_type="EXPLICIT_PATH",
            strength="STRONG",
            source="BODY",
            text="services/worker.py",
            normalized_value="services/worker.py"
        )
        evid = DummyEvidence(technical_evidence=[item])
        res = ground_file_relationships(FIXTURE_A_FILES, {}, candidate_ev, intel, evid)
        self.assertTrue(any(r.resolution_status == "GROUNDED" and "app/services/worker.py" in r.grounded_paths for r in res.explicit_path_resolutions))


class TestTypeScriptRepositoryGrounding(unittest.TestCase):
    def test_typescript_tsx_grounding(self):
        """5: TypeScript .tsx path grounding."""
        intel = DummyIntelligence(category="frontend", subsystem="ui/component")
        candidate_ev = DummyCandidateEvidence(candidates=[{"path": "src/components/UserPanel.tsx"}])
        item = DummyEvidenceItem(
            evidence_type="EXPLICIT_PATH",
            strength="STRONG",
            source="BODY",
            text="src/components/UserPanel.tsx",
            normalized_value="src/components/UserPanel.tsx"
        )
        evid = DummyEvidence(technical_evidence=[item])
        res = ground_file_relationships(FIXTURE_B_FILES, {}, candidate_ev, intel, evid)
        self.assertTrue(any(r.resolution_status == "GROUNDED" and "src/components/UserPanel.tsx" in r.grounded_paths for r in res.explicit_path_resolutions))

    def test_typescript_camelcase_alignment(self):
        """8: TypeScript camelCase entity/path alignment."""
        intel = DummyIntelligence()
        # Entity UserPanel aligns with src/components/UserPanel.tsx
        candidate_ev = DummyCandidateEvidence(candidates=[{"path": "src/components/UserPanel.tsx"}])
        item = DummyEvidenceItem(
            evidence_type="IMPLEMENTATION_STATEMENT",
            strength="STRONG",
            source="BODY",
            text="UserPanel renders user data",
            normalized_value="UserPanel",
            technical_entities=["UserPanel"]
        )
        evid = DummyEvidence(technical_evidence=[item])
        res = ground_file_relationships(FIXTURE_B_FILES, {}, candidate_ev, intel, evid)
        self.assertTrue(any(c.path == "src/components/UserPanel.tsx" and c.relationship_score > 0 for c in res.candidate_relationships))


class TestGoRepositoryGrounding(unittest.TestCase):
    def test_go_suffix_resolution(self):
        """9: Go suffix path resolution."""
        intel = DummyIntelligence()
        candidate_ev = DummyCandidateEvidence()
        item = DummyEvidenceItem(
            evidence_type="EXPLICIT_PATH",
            strength="STRONG",
            source="BODY",
            text="server/main.go",
            normalized_value="server/main.go"
        )
        evid = DummyEvidence(technical_evidence=[item])
        res = ground_file_relationships(FIXTURE_C_FILES, {}, candidate_ev, intel, evid)
        self.assertTrue(any(r.resolution_status == "GROUNDED" and "cmd/server/main.go" in r.grounded_paths for r in res.explicit_path_resolutions))


class TestJavaRepositoryGrounding(unittest.TestCase):
    def test_java_package_import_grounding(self):
        """13: Java dotted package import grounding (com.example.service.PaymentService -> PaymentService.java)."""
        intel = DummyIntelligence()
        candidate_ev = DummyCandidateEvidence(candidates=[{"path": "src/main/java/com/example/service/PaymentService.java"}])
        item = DummyEvidenceItem(
            evidence_type="IMPLEMENTATION_STATEMENT",
            strength="STRONG",
            source="BODY",
            text="com.example.service.PaymentService",
            normalized_value="com.example.service.PaymentService",
            technical_entities=["com.example.service.PaymentService"]
        )
        evid = DummyEvidence(technical_evidence=[item])
        res = ground_file_relationships(FIXTURE_D_FILES, {}, candidate_ev, intel, evid)
        self.assertTrue(any(c.path == "src/main/java/com/example/service/PaymentService.java" and c.relationship_score > 0 for c in res.candidate_relationships))


class TestRustRepositoryGrounding(unittest.TestCase):
    def test_rust_module_suffix_resolution(self):
        """17: Rust module suffix resolution."""
        intel = DummyIntelligence()
        candidate_ev = DummyCandidateEvidence()
        item = DummyEvidenceItem(
            evidence_type="EXPLICIT_PATH",
            strength="STRONG",
            source="BODY",
            text="client.rs",
            normalized_value="client.rs"
        )
        evid = DummyEvidence(technical_evidence=[item])
        res = ground_file_relationships(FIXTURE_E_FILES, {}, candidate_ev, intel, evid)
        # Should match client.rs
        resolutions = [r for r in res.explicit_path_resolutions if r.original_value == "client.rs"]
        self.assertTrue(len(resolutions) > 0)
        self.assertTrue("src/client.rs" in resolutions[0].grounded_paths)


class TestMonorepoGrounding(unittest.TestCase):
    def test_monorepo_package_suffix(self):
        """21: Suffix matching in monorepo layouts (web/src/index.ts -> packages/web/src/index.ts)."""
        intel = DummyIntelligence()
        candidate_ev = DummyCandidateEvidence()
        item = DummyEvidenceItem(
            evidence_type="EXPLICIT_PATH",
            strength="STRONG",
            source="BODY",
            text="web/src/index.ts",
            normalized_value="web/src/index.ts"
        )
        evid = DummyEvidence(technical_evidence=[item])
        res = ground_file_relationships(FIXTURE_F_FILES, {}, candidate_ev, intel, evid)
        self.assertTrue(any(r.resolution_status == "GROUNDED" and "packages/web/src/index.ts" in r.grounded_paths for r in res.explicit_path_resolutions))

    def test_duplicate_basenames_ambiguity(self):
        """24: Duplicate basenames ambiguity resolution (web/src/index.ts vs server/src/index.ts when only index.ts is given)."""
        intel = DummyIntelligence()
        candidate_ev = DummyCandidateEvidence()
        item = DummyEvidenceItem(
            evidence_type="EXPLICIT_PATH",
            strength="STRONG",
            source="BODY",
            text="index.ts",
            normalized_value="index.ts"
        )
        evid = DummyEvidence(technical_evidence=[item])
        res = ground_file_relationships(FIXTURE_F_FILES, {}, candidate_ev, intel, evid)
        # It matches multiple: web/src/index.ts & server/src/index.ts -> status should be AMBIGUOUS
        resolutions = [r for r in res.explicit_path_resolutions if r.original_value == "index.ts"]
        self.assertTrue(len(resolutions) > 0)
        self.assertEqual(resolutions[0].resolution_status, "AMBIGUOUS")


class TestInfrastructureRepositoryGrounding(unittest.TestCase):
    def test_extensionless_filenames(self):
        """25: Grounding of extensionless filenames (Dockerfile, Makefile)."""
        intel = DummyIntelligence()
        candidate_ev = DummyCandidateEvidence()
        item = DummyEvidenceItem(
            evidence_type="EXPLICIT_PATH",
            strength="STRONG",
            source="BODY",
            text="Dockerfile",
            normalized_value="Dockerfile"
        )
        evid = DummyEvidence(technical_evidence=[item])
        res = ground_file_relationships(FIXTURE_G_FILES, {}, candidate_ev, intel, evid)
        self.assertTrue(any(r.resolution_status == "GROUNDED" and "Dockerfile" in r.grounded_paths for r in res.explicit_path_resolutions))


class TestGenericEntitySpecificity(unittest.TestCase):
    def test_specificity_helper(self):
        """29: Specificity helper distinguishes generic vs specific tokens."""
        freq_map = {"helper": 10, "uniqueidentifier": 1}
        self.assertEqual(classify_entity_specificity("helper", freq_map, 10), "LOW")
        self.assertEqual(classify_entity_specificity("uniqueidentifier", freq_map, 10), "MEDIUM")


class TestGenericClassificationReconciliation(unittest.TestCase):
    def test_compound_tool_subsystem(self):
        """33: Generic compound tool entity plus strong implementation evidence can resolve tools subsystem."""
        intel = DummyIntelligence(category="backend", subsystem="general")
        item = DummyEvidenceItem(
            evidence_type="IMPLEMENTATION_STATEMENT",
            strength="STRONG",
            source="BODY",
            text="CustomTool subclass overrides run",
            normalized_value="CustomTool",
            technical_entities=["CustomTool", "run"]
        )
        evid = DummyEvidence(technical_evidence=[item])
        res = reconcile_issue_classification(intel, evid)
        self.assertEqual(res.resolved_subsystem, "core/tools")

    def test_single_tool_token_insufficient(self):
        """34: Single token 'tool' cannot independently force tools subsystem."""
        intel = DummyIntelligence(category="backend", subsystem="general")
        item = DummyEvidenceItem(
            evidence_type="IMPLEMENTATION_STATEMENT",
            strength="STRONG",
            source="BODY",
            text="using some tool",
            normalized_value="tool",
            technical_entities=["tool"]
        )
        evid = DummyEvidence(technical_evidence=[item])
        res = reconcile_issue_classification(intel, evid)
        # Should retain original 'general' subsystem because it's a single token
        self.assertEqual(res.resolved_subsystem, "general")

    def test_single_client_token_insufficient(self):
        """35: Single token 'client' cannot independently force client/integration subsystem."""
        intel = DummyIntelligence(category="backend", subsystem="general")
        item = DummyEvidenceItem(
            evidence_type="IMPLEMENTATION_STATEMENT",
            strength="STRONG",
            source="BODY",
            text="we have a client",
            normalized_value="client",
            technical_entities=["client"]
        )
        evid = DummyEvidence(technical_evidence=[item])
        res = reconcile_issue_classification(intel, evid)
        self.assertEqual(res.resolved_subsystem, "general")

    def test_compound_client_subsystem(self):
        """36: Generic compound HTTP client entity plus strong dependency evidence can resolve client/integration subsystem."""
        intel = DummyIntelligence(category="backend", subsystem="general")
        item = DummyEvidenceItem(
            evidence_type="IMPLEMENTATION_STATEMENT",
            strength="STRONG",
            source="BODY",
            text="HTTPClientInstance connection request",
            normalized_value="HTTPClientInstance",
            technical_entities=["HTTPClientInstance", "request"]
        )
        evid = DummyEvidence(technical_evidence=[item])
        res = reconcile_issue_classification(intel, evid)
        self.assertEqual(res.resolved_subsystem, "integration/client")
