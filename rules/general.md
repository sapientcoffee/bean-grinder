# ⚙️ Bean-Grinder: Modernization & Migration Rules

Welcome to **Bean-Grinder**, the automated code modernization and migration engine for the Antigravity CLI (`agy`).

## 1. Migration Discipline
* **Parity First:** Never alter business logic behavior during a pure modernization or migration pass. Functional and contract parity is paramount.
* **Dynamic Runtime Parity:** Beyond static AST comparisons, verify functional and performance parity by replaying synthetic traffic with `@runtime-parity-verifier` into `docs/parity_discrepancies.md`.
* **GCP Credential Guard:** Verify active credentials with `gcloud auth print-access-token` prior to triggering remote `codmod` jobs.
* **Cost Shield:** Always perform a dry-run cost estimation via `codmod create --estimate-cost` before analyzing large codebases (>100k LOC).
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

## 3. Dashboard Lifecycle & Dual-Write Mirroring
* **11-Tab Unified Modernization Dashboard:** Every modernization plan must generate or update `modernization_dashboard.html` containing all 11 tabs (Scorecard, Slices, Hubs, Modules, 7 Rs Strategy, Seams, Outbox CDC, CodMod, Graphify, Adversarial Review, and Migration Plan).
* **Dual-Write Guarantee:** Always mirror `modernization_dashboard.html` to `00_visual-dashboard.html` in the conversation system artifacts directory (`~/.gemini/antigravity/brain/<conversation-id>/`) so it renders immediately in the UI artifact viewer.


