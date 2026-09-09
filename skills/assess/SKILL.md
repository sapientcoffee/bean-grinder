---
name: assess
description: Exposes the app modernization assessment skill, performing agentic codebase scans, GCP credential verification, cost estimation checks, and executing the codmod CLI.
---

# ☕ Skill: CodMod App Modernization Assessment

You are executing the application modernization assessment workflow. Follow this step-by-step protocol meticulously.

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

## 2. Spawn Modernization Scout Subagent

To perform an intelligent, context-aware pre-scan without relying on rigid scripts, leverage the Antigravity agentic harness:

1. **Invoke the Subagent:**
   - Spawn a dedicated subagent using the `invoke_subagent` tool:
     *   **TypeName**: `research`
     *   **Role**: `Modernization Scout`
     *   **Prompt**:
         ```
         You are the Modernization Scout subagent. Your task is to perform a comprehensive, non-intrusive scan of the codebase directory: {{args}} (or current workspace if omitted).
         
         1. Walk the folders and count files by extension.
         2. Check for legacy Java indicators: Parse pom.xml or build.gradle files to check if the Java source compatibility version is 8 or older (e.g. sourceCompatibility = 1.8).
         3. Check for WildFly profiles: Look for XML structures like standalone.xml, wildfly-config.xml, or package descriptors with WildFly server references.
         4. Check for Microsoft workloads: Look for .sln, .csproj, or .vbproj files.
         5. Check for Arm VM candidates: Look for C/C++ source code targeting legacy VM structures.
         6. Check for cloud vendor libraries: Scan code for AWS (boto3, aws-sdk) or Azure imports.
         
         Return a structured findings list summarizing: file counts, Java source versions, detected application servers, cloud libraries, and overall codebase lines of code (LOC).
         ```
2. **Retrieve & Parse findings:**
   - Wait for the Scout subagent to report its findings, then extract its summarized metrics.

---

## 3. Map Findings to CodMod Intents

Based on the Scout subagent's findings, compute the optimal arguments for the CLI execution:

1. **Select Intent Flag (`--intent`):**
   - If WildFly configurations or profiles are detected: `--intent WILDFLY_LEGACY_TO_MODERN`
   - Else if Java source compatibility <= 8 is detected: `--intent JAVA_LEGACY_TO_MODERN`
   - Else if Microsoft solution/project files are detected: `--intent MICROSOFT_MODERNIZATION`
   - Else if C/C++ source code targeting legacy environments is detected: `--intent ARM_MIGRATION`
   - Else if AWS or Azure vendor libraries are detected: `--intent CLOUD_TO_CLOUD`
   - Default fallback: If no clear matches exist, print a message informing the user and ask for their target intent choice.

2. **Select Optional Sections (`--optional-sections`):**
   - If Java or C# is detected, set `--optional-sections classes,files`.
   - Otherwise, default to `--optional-sections files`.

---

## 4. Model Set & Region Workaround Routing

To leverage the latest Gemini 3.x capabilities while avoiding Vertex AI regional 404 errors, apply this custom model fallback:

1. **Parse Arguments & Detect Target Class:**
   - Scan the input string or `{{args}}` for flags specifying model tier overrides (e.g. `--pro`, `pro`, `--modelset=pro`, `--modelset=gemini-3.1-pro`):
   - **If "pro" is requested:**
     *   Set CLI Parameter: `--modelset=gemini-3.1-pro`
     *   Set Region: `--region=global` (Ensure global region is used to avoid regional availability limitations)
   - **Default (If no "pro" overrides are specified):**
     *   Set CLI Parameter: `--modelset=gemini-3.6-flash`
     *   Set Region: `--region=global` (Enforces 3.6 flash routing inside the global Vertex AI region)

2. **Console Warning:**
   - Display a warning advising the user that custom model fallbacks are active:
     ```
     ⚠️ WARNING: Custom modelset active. The system will attempt to interpret this as a Gemini model name.
     - Model: <selected-modelset>
     - Region: global
     ```

---

## 5. Interactive Cost Shield

1. **Calculate Estimates:**
   - Run the cost-estimation dry-run using Vertex AI Gemini pricing parameters:
     ```bash
     codmod create --estimate-cost --intent <intent> --optional-sections <optional-sections> --modelset <computed-modelset> --region global
     ```
2. **Gate Budgets:**
   - Print the calculated bill and codebase file count to the terminal.
   - If the codebase size exceeds 100,000 LOC or the estimated cost is substantial, halt execution and prompt the user for explicit confirmation (`y/N`) before launching the remote API.
   - If the user selects "No" or rejects, terminate gracefully, displaying the exact CLI command that would have run.

---

## 6. Execute Google Cloud CodMod Assessment

1. **Trigger Assessment:**
   - Run the main assessment command with computed parameters:
     ```bash
     codmod create --intent <intent> --optional-sections <optional-sections> --modelset <computed-modelset> --region global -o modernization_report.html
     ```
   - Ensure the command execution uses safe argument lists (`shell=False` equivalents) to shield the CLI from injection.

2. **Trap Failures (Self-Healing Log Collection):**
   - If the `codmod create` command fails or returns a non-zero exit code:
     *   Trigger the diagnostic collection tool:
         ```bash
         codmod collect-logs -o plans/feature/20260731-codmod-assessment/codmod_logs.zip
         ```
     *   Inform the developer of the failure and point them to the diagnostic zip path.

---

## 7. Report Mirroring & Telemetry

1. **Artifact Mirroring (Rule 5 compliance):**
   - Upon successful generation of `modernization_report.html`, immediately copy/mirror this report into your active chat session's system artifacts directory as `08_visual-recap.html` (e.g. using `python3 scripts/manage_dashboard.py mirror --plan-dir "." --target-filename "08_visual-recap.html"` or copying to `<appDataDir>/brain/<conversation-id>/08_visual-recap.html`).
   - Include valid `ArtifactMetadata` so that the interactive HTML opens directly inside the side-panel chat panel.

2. **Write Telemetry Logs:**
   - Append a single structured JSON line containing execution metadata to:
     `plans/feature/20260731-codmod-assessment/codmod_telemetry.log`
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
       "estimated_cost_usd": <cost>,
       "duration_ms": <duration>
     }
     ```
