---
name: assess
description: Orchestrates an application modernization assessment. Verifies GCP credentials, dispatches 5 discovery scouts concurrently (CodMod, Graphify, Seam, Spec Recovery, and Migration), digests findings into the assessment run hierarchy via digest_report.py, and presents the unified modernization dashboard. Use this skill when the user asks to assess, scan, or analyze an application codebase for modernization, cloud readiness, architectural debt, or discovery.
---

# Skill: Application Modernization Assessment

Orchestrate a comprehensive, non-destructive codebase discovery and modernization assessment across semantic, architectural, and procedural dimensions.

```mermaid
flowchart TD
    Start["Initiate Assessment"] --> CheckGCP{"Step 1: Check GCP Credentials<br/>gcloud auth print-access-token"}
    CheckGCP -->|Failed| Halt["Halt & Prompt Login Guide"]
    CheckGCP -->|Valid| Dispatch["Step 2: Dispatch 5 Subagents Concurrently<br/>invoke_subagent"]
    
    subgraph ParallelScouts["Parallel Discovery Scouts"]
        direction TB
        S1["@codmod-assessor<br/>codmod create --intent ..."]
        S2["@graphify-scout<br/>graphify . --directed --code-only"]
        S3["@seam-scout<br/>Object, Link & Preprocessor Seams"]
        S4["@spec-recovery-agent<br/>Invariants & [AMBIGUOUS_SPEC]"]
        S5["@migration-scout<br/>7 Rs Matrix & EOL Frameworks"]
    end
    
    Dispatch --> ParallelScouts
    ParallelScouts --> Wait["Await Reactive Notifications<br/>(Do not poll)"]
    Wait --> Digest["Step 3: Ingest & Digest<br/>python3 scripts/digest_report.py"]
    Digest --> Outputs["Step 4: Emit Artifacts & Report<br/>• assessments/index.html<br/>• assessments/runs/&lt;ts&gt;/index.html<br/>• 05_PLAN.md"]
```

---

## Operational Protocol

### Step 1: Pre-Flight Credential Verification
Verify active Google Cloud authorization before launching remote assessment operations.

1. Call `run_command` to inspect active GCP configuration:
   ```bash
   gcloud config get-value project
   gcloud auth print-access-token
   ```
2. **Evaluation**:
   - If both commands return exit code `0` and a non-empty token: Proceed to Step 2.
   - If either command fails or exits non-zero:
     - Output an error instructing the user to authenticate via `gcloud auth application-default login` or set `GOOGLE_APPLICATION_CREDENTIALS`.
     - Halt execution immediately. Do not proceed to subagent dispatch.

---

### Step 2: Concurrent Subagent Dispatch
Dispatch all five specialized discovery scouts simultaneously in a single `invoke_subagent` tool call.

#### Antigravity Subagent Execution Rules:
- Use specific subagent `TypeName`s (`codmod-assessor`, `graphify-scout`, `seam-scout`, `spec-recovery-agent`, `migration-scout`) so `/agents` in the TUI displays meaningful names instead of generic 'self' or 'research'.
- Set `Model: "inherit"` on all subagents to preserve the parent session's configured model tier.

#### Dispatch Payload:
Call `invoke_subagent` with the following configuration:

```json
{
  "Subagents": [
    {
      "TypeName": "codmod-assessor",
      "Role": "CodMod Assessor",
      "Prompt": "Execute Google Cloud codmod modernization assessment on directory: {{target_dir}} (or workspace root).\n1. Inspect codebase to detect frameworks and select optimal --intent and --optional-sections.\n2. Apply modelset routing (default --modelset=gemini-3.8-flash --region=global, or --modelset=gemini-3.1-pro if requested).\n3. Execute 'codmod create' non-interactively to generate modernization_report.html (do NOT pass '--estimate-cost', as custom modelsets lack client pricing tables and will abort). Trap failures with 'codmod collect-logs'.\n4. Extract key modernization blockers, LOC count, flagged files, and output report path. Return a concise structured summary.",
      "Model": "inherit"
    },
    {
      "TypeName": "graphify-scout",
      "Role": "Graphify Scout",
      "Prompt": "Perform architectural dependency analysis on directory: {{target_dir}} (or workspace root).\n1. Execute 'graphify . --directed --code-only && graphify cluster-only .' to build the topological knowledge graph (using --code-only avoids requiring an LLM API key).\n2. Verify generation of graphify-out/graph.json, graphify-out/graph.html, and graphify-out/GRAPH_REPORT.md.\n3. Extract graph metrics: total nodes, edges, component clusters, and top central dependency hubs (high blast radius).\n4. Return a concise structured summary with artifact paths.",
      "Model": "inherit"
    },
    {
      "TypeName": "seam-scout",
      "Role": "Seam Scout",
      "Prompt": "Conduct non-destructive structural seam exploration on directory: {{target_dir}} (or workspace root).\n1. Identify Michael Feathers' seams: Object Seams (polymorphism/DI), Link Seams (classpath/assembly injection), and Preprocessor Seams.\n2. Identify candidate sites for Sprout Method, Sprout Class, Wrap Method, and Wrap Class.\n3. Propose Branch by Abstraction boundaries for monolithic subsystems.\n4. Return a structured Markdown table: Component ID, Target Class, Seam Type, Decoupling Pattern, and Blast Radius.",
      "Model": "inherit"
    },
    {
      "TypeName": "spec-recovery-agent",
      "Role": "Spec Recovery Scout",
      "Prompt": "Perform specification archaeology on directory: {{target_dir}} (or workspace root).\n1. Reconstruct business rules, validation logic, entity lifecycle state machines, and implicit invariants from source code.\n2. Flag ambiguous, undocumented, or contradictory logic using '[AMBIGUOUS_SPEC: <description>]'.\n3. Return a structured Markdown table: Requirement ID, Summary, Source Location (file:line), Preconditions, Postconditions, and Review Status.",
      "Model": "inherit"
    },
    {
      "TypeName": "migration-scout",
      "Role": "Migration Scout",
      "Prompt": "Perform portfolio rationalization scan on directory: {{target_dir}} (or workspace root).\n1. Inspect build descriptors (pom.xml, build.gradle, *.csproj, package.json) for runtime versions, EOL frameworks, and third-party libraries.\n2. Classify major subsystems across the 7 Rs taxonomy: Retire, Retain, Rehost, Relocate, Repurchase, Replatform, Refactor/Re-architect.\n3. Map candidate Google Cloud target services (Cloud Run, GKE, Cloud SQL, Spanner).\n4. Return a structured 7 Rs classification matrix and migration risk summary.",
      "Model": "inherit"
    }
  ]
}
```

#### Execution Gate:
- **Do not poll or loop.**
- Stop calling tools and allow the Antigravity reactive messaging system to resume execution when subagents post completion messages.

---

### Step 3: Ingestion & Synthesis

1. **Verify Deliverables**:
   Confirm receipt of completion messages from all 5 subagents and ensure required files exist:
   - `modernization_report.html`
   - `graphify-out/graph.json`

2. **Execute Synthesis Pipeline**:
   Call `run_command` to execute `scripts/digest_report.py`, targeting a timestamped run directory:
   ```bash
   TIMESTAMP=$(date +%Y%m%d_%H%M%S)
   python3 scripts/digest_report.py \
     --report modernization_report.html \
     --graph graphify-out/graph.json \
     --output-dir assessments/runs/${TIMESTAMP}
   ```

3. **Verify Generated Artifacts**:
   Ensure the following output hierarchy is created:
   - `assessments/index.html` (Unified multi-run dashboard hub)
   - `assessments/latest` (Symlink pointing to active run)
   - `assessments/runs/<timestamp>/index.html` (Standalone 11-tab dashboard UI)
   - `assessments/runs/<timestamp>/run_manifest.json` (Structured scorecard metadata)
   - `assessments/runs/<timestamp>/01_discovery/` (Discovery reports and telemetry)
   - `assessments/runs/<timestamp>/02_synthesis/` (`migration_matrix.json`, `vertical_slices.json`)
   - `assessments/runs/<timestamp>/04_migration_plan/05_PLAN.md` (Initial migration plan)
   - `<appDataDir>/brain/<conversation-id>/00_visual-dashboard.html` (Mirrored conversation artifact)

---

### Step 4: Presentation & Next Phase Hand-Off

1. **Present Summary to User**:
   Provide a concise executive overview containing:
   - **Codebase Scale**: Lines of Code, file count, primary languages.
   - **Modernization Assessment**: Top 3 critical modernization blockers identified by CodMod.
   - **Topological Bottlenecks**: Top 3 high-blast-radius dependency hubs identified by Graphify.
   - **Strategic Posture**: 7 Rs breakdown summary (Refactor vs Replatform vs Retain).
   - **Discovered Seams & Ambiguous Rules**: Total seam intervention points and count of `[AMBIGUOUS_SPEC]` items requiring domain review.
   - **Dashboard Link**: Clickable link to [assessments/index.html](file:///home/robedwards/workspace/bean-grinder/assessments/index.html) (or `00_visual-dashboard.html`).

2. **Recommend Next Action**:
   Prompt the user to review the generated plan and initiate adversarial hardening:
   > "Assessment complete. Review [05_PLAN.md](file:///home/robedwards/workspace/bean-grinder/assessments/runs/latest/04_migration_plan/05_PLAN.md) and run `/adversarial-review` to stress-test the migration architecture."
