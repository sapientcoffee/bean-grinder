# ⚙️ Bean-Grinder: Modernization & Migration Rules

Welcome to **Bean-Grinder**, the automated code modernization and migration engine for the Antigravity CLI (`agy`).

## 1. Migration Discipline
* **Parity First:** Never alter business logic behavior during a pure modernization or migration pass. Functional and contract parity is paramount.
* **Dynamic Runtime Parity:** Beyond static AST comparisons, verify functional and performance parity by replaying synthetic traffic with `@runtime-parity-verifier` into `docs/parity_discrepancies.md`.
* **GCP Credential Guard:** Verify active credentials with `gcloud auth print-access-token` prior to triggering remote `codmod` jobs.
* **Safe Subprocesses:** Execute CLI commands with `shell=False` equivalent argument lists to prevent shell injection.

## 2. Multi-Persona Adversarial Review Protocol
* **Mandatory Plan Hardening:** Before submitting any modernization plan (`05_PLAN.md`) to the user at the Stage 6 Human Gate, the plan MUST undergo the multi-persona adversarial review loop.
* **Opposing Persona Perspectives:**
  - `@reviewer-exec`: Audits TCO, cloud run-rate, licensing sunset timelines, and rollback RPO/MTD.
  - `@reviewer-engineer`: Audits AST transformation safety, dynamic reflection traps, build speeds, contract testing, and developer experience.
  - `@reviewer-architect`: Audits Central Dependency Hubs (`graphify`), Anti-Corruption Layers (ACLs), distributed state, and horizontal scalability.
  - `@reviewer-pm`: Audits behavioral parity, undocumented legacy quirks, acceptance criteria (Gherkin), and scope boundaries.
* **Arbiter Reconciliation & Convergence:**
  - `@review-arbiter` reconciles cross-functional trade-offs, computes consensus scores ($100 - (25C + 10H + 3M + 1L)$), and generates plan patch directives.
  - Convergence is achieved ONLY when consensus score $\ge 90.0\%$ and zero Critical or High severity blockers remain.
  - If consensus is not reached within 3 rounds, the circuit breaker trips, freezing the plan and documenting the deadlock for human decision-making.

## 3. Unified Directory Structure & Dashboard Lifecycle
* **Independent Single Directory (`assessments/`):** All assessment runs and modernization artifacts are self-contained within `assessments/runs/<run_id>/`, with `assessments/index.html` and `assessments/latest` providing root-level entry and navigation.
* **Human-Friendly Stage Organization:** Artifacts within each run are organized into clear stage directories:
  - `01_discovery/`: `codmod_assessment_report.html`, `graphify_ast_graph.json`, `graphify_visualizer.html`, `graphify_architecture_report.md`, `codmod_execution_telemetry.json`
  - `02_synthesis/`: `migration_matrix.json`, `vertical_slices.json`, `mikado_dependency_tree.md`
  - `03_adversarial_review/`: `adversarial_audit_report.md`, `adversarial_review_matrix.json`, `plan_hardening_directives.json`
  - `04_migration_plan/`: `05_PLAN.md`, `contracts/`
  - `05_parity_verification/`: `parity_discrepancies.md`, `golden_master_fixtures/`
* **Main HTML View at Root:** Every run produces `index.html` at the run root (with backward-compatible `modernization_dashboard.html` and `visual-dashboard.html` aliases), containing all 11 tabs. The root `assessments/index.html` serves as the run hub with an interactive switcher.
* **Dual-Write Guarantee:** Always mirror the main dashboard to `00_visual-dashboard.html` in the conversation system artifacts directory (`~/.gemini/antigravity/brain/<conversation-id>/`) so it renders immediately in the UI artifact viewer.


