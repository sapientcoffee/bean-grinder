---
name: assess
description: Exposes the app modernization assessment skill, performing parallel agentic codebase scans, GCP credential verification, optional cost estimation checks, and coordinating CodMod and Graphify subagents.
---

# ☕ Skill: CodMod App Modernization Assessment (Parallel Orchestrator)

You are executing the application modernization assessment workflow. Follow this step-by-step orchestrator protocol to run semantic and architectural assessments concurrently via context-isolated subagents.

---

## 1. Initial Setup & GCP Credential Guard

1. **Verify active GCP credentials and projects:**
   - Execute a shell command to ensure local authorization and target project parameters are set:
     ```bash
     gcloud config get-value project
     gcloud auth print-access-token
     ```
   - If credentials are missing or the command errors out, halt execution immediately and print a helpful, step-by-step resolution guide instructing the user to configure credentials (e.g., run `gcloud auth application-default login` or configure `GOOGLE_APPLICATION_CREDENTIALS`).

---

## 2. Optional Pre-Flight Cost Shield

> [!NOTE]
> Cost estimation is kept strictly outside of subagents and is **optional**. Do not run cost estimation unless the user explicitly passes `--estimate-cost` or asks for a dry-run budget estimate upfront.

1. **If `--estimate-cost` is explicitly requested:**
   - Run the cost-estimation dry-run using Vertex AI Gemini pricing parameters:
     ```bash
     codmod create --estimate-cost --intent <intent> --optional-sections <optional-sections> --modelset <computed-modelset> --region global
     ```
   - Print the calculated bill and codebase file count to the terminal.
   - If the codebase size exceeds 100,000 LOC or the estimated cost is substantial, halt execution and prompt the user for explicit confirmation (`y/N`) before proceeding.
2. **Default (No cost flag requested):**
   - Skip directly to Section 3.

---

## 3. Dispatch Parallel Assessment Subagents

To maximize context hygiene and cut discovery execution time in half, dispatch **both** specialized subagents concurrently in a single `invoke_subagent` tool call:

```json
{
  "Subagents": [
    {
      "TypeName": "codmod-assessor",
      "Role": "CodMod Assessor",
      "Prompt": "You are the CodMod Assessor subagent. Execute the Google Cloud codmod modernization assessment on codebase directory: {{target_dir}} (or current workspace).\n1. Inspect the codebase to detect frameworks and select optimal --intent and --optional-sections.\n2. Apply modelset routing (default --modelset=gemini-3.6-flash --region=global, or --modelset=gemini-3.1-pro if pro is requested).\n3. Execute 'codmod create' non-interactively to generate modernization_report.html. Trap any failures with 'codmod collect-logs'.\n4. Extract key findings, LOC scale, top modernization blockers, and report path, returning a concise structured summary.",
      "Model": "flash"
    },
    {
      "TypeName": "graphify-scout",
      "Role": "Graphify Scout",
      "Prompt": "You are the Graphify Scout subagent. Perform an architectural dependency and AST scan on codebase directory: {{target_dir}} (or current workspace).\n1. Run 'graphify . --directed' to construct the topological knowledge graph.\n2. Verify the generation of graphify-out/graph.json, graphify-out/graph.html, and graphify-out/GRAPH_REPORT.md.\n3. Parse the graph to extract total nodes, total edges, component module count, and top central dependency hubs (high blast radius).\n4. Return a concise structured summary with artifact paths.",
      "Model": "flash"
    }
  ]
}
```

- **Zero Context Pollution:** Both subagents run in isolated execution sandboxes, keeping raw CLI output, AST details, and intermediate HTML parsing out of the parent conversation context.
- **Concurrent Execution:** Neither subagent depends on the other. `codmod` is I/O & cloud-API bound; `graphify` is local CPU & AST bound.
- **Optional Seam & Spec Deep-Scan:** For complex monoliths, invoke `@seam-scout` (to map Michael Feathers' Object/Link/Preprocessor seams and Sprout/Wrap opportunities) and `@spec-recovery-agent` (for business rule recovery under Human-in-the-Loop review).

---

## 4. Ingest Subagent Findings & Automated Digestion

1. **Receive Concise Subagent Returns:**
   - Wait for both subagents to report completion.
   - Confirm both deliverables exist:
     * `modernization_report.html` (from `@codmod-assessor`)
     * `graphify-out/graph.json` (from `@graphify-scout`)

2. **Execute Automated Digestion & Unified Modernization Dashboard:**
   - Synthesize the dual-lens outputs into vertical slices, 7 Rs portfolio rationalization, Feathers' seams, Transactional Outbox + CDC data architectures, and the unified modernization dashboard:
     ```bash
     python3 scripts/digest_report.py \
       --report modernization_report.html \
       --graph graphify-out/graph.json \
       --output-dir plans/<slug>/<timestamp>
     ```
   - This automatically produces:
     * `plans/<slug>/<timestamp>/modernization_dashboard.html` (Unified multi-tab glass pane including 7 Rs Strategy, Seams, Data CDC, and Mikado Graph)
     * `plans/<slug>/<timestamp>/migration_matrix.json` (Machine-readable dataset with quantum metrics and CDC cutover phases)
     * `plans/<slug>/<timestamp>/05_PLAN.md` (Mikado dependency-ordered implementation plan)
     * `00_visual-dashboard.html` (Automatically mirrored to the active conversation brain for instant UI inspection)

---

## 5. Report Mirroring & Telemetry

1. **Artifact Mirroring (Rule 5 compliance):**
   - The unified dashboard is automatically mirrored to `<appDataDir>/brain/<conversation-id>/00_visual-dashboard.html` by `digest_report.py`.
   - If manual mirroring of the raw assessment report is required, copy `modernization_report.html` into your active chat session's system artifacts directory as `08_visual-recap.html`.

2. **Write Telemetry Logs:**
   - Append a single structured JSON line containing execution metadata to:
     `plans/feature/<timestamp>/codmod_telemetry.log`
   - Ensure the log object conforms to the defined schema:
     ```json
     {
       "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
       "command": "assess",
       "project": "<project-id>",
       "codebase_loc": <loc>,
       "detected_intent": "<intent>",
       "sections": ["<sections>"],
       "modelset": "<computed-modelset>",
       "status": "success",
       "duration_ms": <duration>
     }
     ```

3. **Present Scorecard:**
   - Present the Executive Scorecard, Central Dependency Hubs table, and planned vertical slices from `05_PLAN.md` to the user, highlighting the link to `modernization_dashboard.html` / `00_visual-dashboard.html`.
