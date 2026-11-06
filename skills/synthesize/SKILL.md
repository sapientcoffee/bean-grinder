---
name: synthesize
description: Executes standalone architectural synthesis and migration planning on existing discovery artifacts. Reconciles CodMod, Graphify, Seam, Spec Recovery, and Migration scout reports into domain-driven vertical slices, Mikado refactoring trees, and an OKF-compatible 05_PLAN.md without re-running scouts. Use when the user asks to synthesize, re-slice, re-plan, or iterate on modernizing an assessed codebase.
---

# Skill: Standalone Architectural Synthesis & Slicing

Execute or re-run architectural synthesis on existing assessment discovery artifacts without re-dispatching heavy discovery scouts (`codmod`, `graphify`, etc.). Reconcile multi-scout findings, tailor vertical slices to domain boundaries, and compile an actionable OKF-compatible `05_PLAN.md` and `migration_matrix.json`.

```mermaid
flowchart TD
    Start["Initiate Standalone Synthesis"] --> CheckRun{"Step 1: Check Existing Discovery<br/>assessments/runs/latest/01_discovery/"}
    CheckRun -->|Missing Artifacts| Halt["Halt & Prompt to run /assess"]
    CheckRun -->|Artifacts Found| RunScript["Step 2: Run Synthesis Runner<br/>python3 skills/synthesize/scripts/synthesize_runner.py"]
    
    subgraph Ingestion["Artifact Ingestion (Preserved)"]
        A1["codmod_assessment_report.html"]
        A2["graphify_ast_graph.json"]
        A3["seam_findings.md (@seam-scout)"]
        A4["spec_invariants.md (@spec-recovery-agent)"]
        A5["migration_strategy.md (@migration-scout)"]
    end
    
    RunScript --> Ingestion
    Ingestion --> Math["Deterministic AST Synthesis<br/>• Blast Radius & Degree<br/>• Community Clustering<br/>• Baseline Matrix"]
    
    Math --> AgentGate{"Step 3: Domain Customization<br/>Needed?"}
    AgentGate -->|Yes / Interactive| Subagent["Dispatch @synthesis-agent<br/>• Inject empirical Feathers' seams<br/>• Bind [AMBIGUOUS_SPEC] into gates<br/>• Custom domain slicing"]
    AgentGate -->|No / Fast Path| StageOutputs
    
    Subagent --> StageOutputs["Step 4: Update Run Hierarchy<br/>• 02_synthesis/migration_matrix.json<br/>• 04_migration_plan/05_PLAN.md"]
    StageOutputs --> Next["Step 5: Hand-Off to /adversarial-review"]
```

---

## Operational Protocol

### Step 1: Target Run Resolution & Discovery Verification
1. Resolve the target assessment run directory:
   - Default: `assessments/runs/latest/` (or most recent run in `assessments/runs/`).
   - Custom: A specific directory or timestamp specified by the user (e.g., `assessments/runs/20260909_120000`).
2. Verify that `01_discovery/` contains the necessary baseline reports using `read_file`:
   - `codmod_assessment_report.html` (or `modernization_report.html`)
   - `graphify_ast_graph.json` (or `graph.json`)
3. If discovery artifacts are missing:
   - Inform the user: *"No previous assessment discovery artifacts found. Please execute `/assess` first to run discovery scouts."*
   - Halt execution cleanly.

---

### Step 2: Execute Standalone Synthesis Runner
Execute the colocated helper script:

```bash
python3 skills/synthesize/scripts/synthesize_runner.py --run-dir latest
```

#### Supported Options:
- `--run-dir <path|id>`: Target a specific historical run.
- `--summary-only`: Print scorecard to stdout without overwriting files.

The runner will:
1. Ingest `01_discovery/` reports.
2. Ingest empirical scout reports if present (`seam_findings.md`, `spec_invariants.md`, `migration_strategy.md`).
3. Compute graph degrees, community clusters, and vertical slices.
4. Emit `02_synthesis/migration_matrix.json`, `02_synthesis/vertical_slices.json`, and an OKF-compatible `04_migration_plan/05_PLAN.md`.
5. Update `run_manifest.json`.

---

### Step 3: Domain Customization with `@synthesis-agent` (Optional / On Demand)
If the user specifies custom domain requirements, requests non-standard slicing, or provides domain answers for ambiguous specifications:

1. Dispatch `@synthesis-agent` via `invoke_subagent` with `Model: "inherit"` to update `04_migration_plan/05_PLAN.md` and `02_synthesis/migration_matrix.json` using `read_file`, `edit_file`, and `write_file`.
2. Await completion notification.

---

### Step 4: Presentation & Next Action
Present a summary of the synthesized plan to the user:
- Total component modules & central dependency hubs.
- Ordered vertical migration slices.
- Paths to `04_migration_plan/05_PLAN.md` and `02_synthesis/migration_matrix.json`.
- Recommend next step:
  > *"Synthesis complete. Review `04_migration_plan/05_PLAN.md` and run `/adversarial-review` to stress-test the plan."*
