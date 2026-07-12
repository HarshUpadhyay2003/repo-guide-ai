# RepoPilot V2 Live Production Evaluation & Benchmark Harness

The RepoPilot Live Production Evaluation Harness V2 upgrades the evaluation framework into a client-like engine that calls the production backend endpoint `POST /repo/analyze` using FastAPI's `TestClient`. It passively observes and traces the entire pipeline trace, capturing Groq latencies, Stage 12.1 internal intelligence objects, raw responses, and telemetry.

## Directory Structure

All evaluation-related files live inside `backend/evaluation/`:
- `evaluation_runner.py` — The V2 CLI orchestrator.
- `report_builder.py` — Score builder & ground truth connector.
- `benchmark_models.py` — Pydantic models for evaluation statistics & Stage 12.1 structures.
- `repository_capture.py` — Tree-categorization profiling.
- `issue_capture.py` — Ground truth retrieval from GitHub.
- `prompt_capture.py` — Passive observers & offline CI mock handlers.
- `comparison_utils.py` — Overlap precision, recall, and F1 calculations.
- `markdown_writer.py` — Report conformer (20 sections) & comparison dashboard generator.

---

## Execution Modes

The V2 runner supports two modes via the `--exec-mode` argument:

### Mode 1: Production Evaluation (Default)
Executes the exact production services using real GitHub and Groq APIs with no mocks.
```bash
python backend/evaluation/evaluation_runner.py --repo <REPO_URL> --token <GITHUB_TOKEN> --output <OUTPUT_DIR> --exec-mode prod
```

### Mode 2: Offline CI Mode
Uses local mock data to simulate completions and API trees completely offline for CI/CD pipeline validation.
```bash
python backend/evaluation/evaluation_runner.py --repo <REPO_URL> --token <GITHUB_TOKEN> --output <OUTPUT_DIR> --exec-mode ci
```

### Options
* `--repo` (str, Required): GitHub repository URL (e.g. `https://github.com/owner/repo`).
* `--token` (str, Required): GitHub personal access token with access to the repo.
* `--output` (str, Required): Path to save reports and subfolders.
* `--no-cache` (flag): Bypasses and clears the cache for clean pipeline evaluation.
* `--mode` (str): RepoService mode. Defaults to `FAST_MVP` (top 2 issues).

---

## Output Folders
For each repository, the harness generates the conformed directories inside `[output_dir]/[repository_name]/`:
* `report.md` — The V2 conformed Markdown report.
* `prompts/` — Every fully rendered prompt attempt.
* `llm/` — Raw request and response logs.
* `json/` — Parsed component response JSONs.
* `pdf/` — Generated PDF reports.
* `metrics/` — Deterministic scores.
* `github/` — Resolved GitHub Ground Truth.
* `logs/` — Isolated logging output (`run.log` and `evaluation.log`).

A global dashboard is compiled at the parent `[output_dir]` directory:
* `evaluation_summary.csv` — Comprehensive comparison CSV.
* `dashboard.md` — High-level comparison dashboard.

---

## Numbered Report Sections (1 to 20)

1. **Repository Metadata**: Stars, forks, language, topics, size, file/directory counts.
2. **Repository Summary**: Production repository summary output.
3. **Repository Map**: Category listings and architecture files.
4. **Issue List**: Selected beginner issues for guidance.
5. **Issue Intelligence**: Enriched Stage 12.1 intelligence items (`IssueIntelligence`, `IssueEvidence`, `RepositoryContext`, and candidate directories/file tables).
6. **Prompt Attempts**: Fully rendered prompts (Attempts 1-4) with compression configurations.
7. **Prompt Statistics**: Length, tokens, degradation, and compression ratio.
8. **Raw LLM Output**: Raw API responses and parsed objects.
9. **Normalization**: Cleaned schema responses.
10. **Grounding Validation**: Valid vs invalid path listings and confidence scoring adjustments.
11. **Roadmap**: Dynamic roadmap JSON.
12. **Generated PDFs**: Repository, Issue, and Contribution guide PDF metrics.
13. **Performance**: Individual stage durations, CPU/memory usage, and total runtime.
14. **Cache**: Backend type, hit/miss logs, and read/write latencies.
15. **Errors**: Captured GitHub, LLM, rate-limit, and validation errors.
16. **GitHub Ground Truth**: Linked closed PR description, commits, changed files, and languages.
17. **RepoPilot vs Ground Truth**: Accuracy metrics (precision, recall, F1, match percentage).
18. **Evaluation Metrics**: Deterministic scores (Summary, Map, Guidance, Ranking, Grounding, Roadmap, Overall).
19. **Production Call Trace**: Diagram and execution details (timings, logs, prompts, responses) per stage.
20. **Observations**: Passive conclusions based on execution outputs.
