# ⚙️ Bean-Grinder: Modernization & Migration Rules

Welcome to **Bean-Grinder**, the automated code modernization and migration engine for the Antigravity CLI (`agy`).

## 1. Migration Discipline
* **Parity First:** Never alter business logic behavior during a pure modernization or migration pass. Functional and contract parity is paramount.
* **Dynamic Runtime Parity:** Beyond static AST comparisons, verify functional and performance parity by replaying synthetic traffic with `@runtime-parity-verifier` into `docs/parity_discrepancies.md`.
* **GCP Credential Guard:** Verify active credentials with `gcloud auth print-access-token` prior to triggering remote `codmod` jobs.
* **Cost Shield:** Always perform a dry-run cost estimation via `codmod create --estimate-cost` before analyzing large codebases (>100k LOC).
* **Safe Subprocesses:** Execute CLI commands with `shell=False` equivalent argument lists to prevent shell injection.

