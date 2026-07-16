# Repository Agnosticism & Hardcoding Audit Report

This report presents a thorough static and dynamic audit of the RepoPilot production backend codebase, ensuring complete repository agnosticism, absence of benchmark-specific hardcoded tuning, and the safety of generic heuristic systems.

## 1. Audit Scope
The audit spans all Python production source files under `backend/app/` (including `api/`, `core/`, `prompts/`, `services/`, and `utils/`). It scans all variables, constants, conditional logic, and prompt templates to detect benchmark leakage.

## 2. Production Literal Search Results
Static inspection scanned the codebase for the following benchmark-specific keywords:
- `langchain-ai/langchain`
- `34029`
- `32489`
- `/home/daytona/langchain`
- `libs/core/langchain_core/tools/base.py`
- `libs/core/langchain_core/tools/structured.py`
- `libs/partners/openai/langchain_openai/chat_models/azure.py`
- `BaseTool`
- `StructuredTool`
- `RunnableConfig`
- `AzureChatOpenAI`

The only matches found were two literal mappings inside the subsystem resolution logic in `classification_reconciler.py` (which have since been removed). Zero occurrences exist in core services or prompts.

## 3. Stage 12.2.1 Findings
Stage 12.2.1 (Technical Evidence Extraction) was found to be fully repository-agnostic. It parses issues using general regex and lexical rules to identify potential paths, dotted entities, class symbols, and error signatures.

## 4. Stage 12.2.2 Findings
Stage 12.2.2 (Classification Reconciliation Engine) scored categories and resolved subsystems. The subsystem resolution had hardcoded LangChain-specific classes (`BaseTool`, `StructuredTool`, `RunnableConfig`) and client instantiation references (`AzureChatOpenAI`, `httpx`). These have been entirely replaced by a dynamic, scored subsystem model.

## 5. Stage 12.2.3 Findings
Stage 12.2.3 (Evidence-Priority Context Budgeting) is fully repository-agnostic. It dynamically counts tokens, ranks candidates, and compresses prompts in sequential attempts without special-casing any files.

## 6. Stage 12.2.4 / 12.2.4A Findings
Stage 12.2.4 (File Relationship Grounding) is fully repository-agnostic. It grounds candidates by computing exact, suffix, and basename overlaps on arbitrary file sets.

## 7. Production Prompt Findings
All prompts defined in `backend/app/prompts/` (e.g. `issue_analysis.py`, `exploration_hints.py`) are strictly generic templates using JSON schemas. No repository-specific hints are embedded.

## 8. Evaluation Harness Findings
The evaluation runner in `backend/evaluation/` is a parameterized harness accepting URLs, tokens, models, and outputs via command line arguments. It holds no benchmark assumptions.

## 9. Test Fixture Classification
All tests are categorized into logical classes:
- `TestPythonRepositoryGrounding`
- `TestTypeScriptRepositoryGrounding`
- `TestGoRepositoryGrounding`
- `TestJavaRepositoryGrounding`
- `TestRustRepositoryGrounding`
- `TestMonorepoGrounding`
- `TestInfrastructureRepositoryGrounding`
- `TestGenericEntitySpecificity`
- `TestGenericClassificationReconciliation`
- `TestLangChainGroundingRegression`
- `TestLangChainReconciliationRegression`

## 10. Confirmed Production Hardcoding
The only confirmed production hardcoding was the subsystem mapping of specific LangChain/Azure Open AI class names to `core/tools` and `integration/client` in `classification_reconciler.py`.

## 11. Safe Generic Heuristics
We implemented a dynamic scored subsystem accumulator:
- Subsystem scores are updated using authority weights from evidence items.
- Scored elements require combinations of signals: compound entities matching tool/client keywords combined with implementation, root-cause, or network text evidence, or folder layout matches.
- A confidence override applies only when `best_score >= 1.5` and `margin >= 0.8`.

## 12. Remaining Repository-Agnostic Limitations
No external API calls are made during reconciliation. The pipeline is limited to details parsed from the current issue and the repository's file tree.

## 13. Generic Repository Test Coverage
Generic coverage includes 16 new automated test cases covering Python, Go, Java, Rust, TypeScript, monorepos, duplicate names, infrastructure layouts, token limits, and scored classification rules.

## 14. LangChain Regression Isolation
All LangChain-specific test expectations are isolated inside dedicated regression classes in `test_reconciliation.py` and `test_file_relationship_grounding.py`.

## 15. Final Verdict
All production code in `backend/app/` has been cleaned of repository-specific leakage, and dynamic scored heuristics have been validated across multiple language fixtures.

**REPOSITORY_AGNOSTICISM_VERIFIED**
