---
name: rewrite
description: Stage 1/2 - Orchestrate a legacy application rewrite workflow by analyzing modernization assessments and coordinating specialized skills.
---

# ☕ Skill: Application Rewrite Brew Protocol

You are executing the **Application Rewrite Brew Protocol**. Rewriting a legacy application requires a structured, risk-mitigated, and language-agnostic approach that guarantees functional parity, resolves architectural technical debt, and maintains compliance with the perfect brew state machine (Stages 0 to 9).

This skill provides a generic orchestrator that walks through analyzing legacy assessment reports (regardless of language or framework), extracting domain details, establishing parity requirements, slicing the monolith, and coordinating implementation using existing specialized repository skills.

---

## 🛠️ Unified Workspace Skills Mapping
An application rewrite leverages the repository's suite of specialized autonomous barista swarm skills:
1. **Assessment & Scanning (Phase 1):** Use the `assess` skill to run codebase pre-scans, check active credentials, select `codmod` intents, and execute the remote assessment.
2. **Requirements & Discovery (Phase 2):** Use the `feature` / `write-prd` skill to initialize directories, draft `02_PRD.md`, and compile the master `visual-dashboard.html`.
3. **Parity Extraction (Phase 3):** Use the `research` skill to do blind, factual extraction of legacy models, endpoints, and business rules to build `docs/glossary.md` and `docs/visual-glossary.html`.
4. **Domain Architecture (Phase 4):** Use the `domain-modeling` skill to define target bounded contexts and architectural decisions.
5. **Socratic Alignment (Phase 4):** Use the `grill` / `grilling` skill to stress-test your rewrite specification and implementation plan.
6. **Execution & Kanban Planning (Phase 5):** Use the `kanban` skill to cut vertical slices, conduct dependency mapping, and generate interactive Kanban tracking boards.
7. **TDD Code Generation (Phase 7):** Use `generate-code` to write backend/frontend codebase slices and `audit-code` for QA compliance.
8. **Testing & Dev Hosting (Phase 7):** Use `dev` to run local backend/frontend servers, and `test-api` to execute local verification suites.
9. **Walkthrough & Recording (Phase 8):** Use the `record` skill to capture high-fidelity terminal playbacks and walkthroughs.
10. **Delivery & Branching (Phase 9):** Use the `worktree` skill and `github-workflow` to manage isolated branches and open clean pull requests.

---

## 🧭 Generic & Flexible Step-by-Step Protocol

### Step 1: Ingest Assessment Report & Architectural Dependencies (Dual-Lens Engine)
1. **Locate or Generate Assessment & Dependency Map:**
   - Look for a pre-generated assessment report (e.g., `modernization_report.html`, `petclinic-standard-report-3.6.html`, or a JSON metadata export). If none exists, run the `assess` skill using `codmod create` to generate one.
   - Run or locate **Graphify** codebase analysis (`graphify <path> --directed`). If `graphify-out/graph.json` exists, utilize it to map dependencies and subsystem boundaries.
   - Run the automated digest tool to cross-reference recommendations with codebase architecture and build the unified dashboard:
     ```bash
     python3 scripts/digest_report.py \
       --report <path-to-report.html> \
       --graph <path-to-graphify-out/graph.json> \
       --output-dir plans/<slug>/<timestamp>
     ```
     This automatically emits `modernization_dashboard.html`, `migration_matrix.json`, and `05_PLAN.md`, while mirroring `00_visual-dashboard.html` to conversation system artifacts for instant inspection.
2. **Determine Source Stack & Target Runtime:**
   - Identify the source language and frameworks (e.g., legacy Java/Spring, .NET Framework / C#, C/C++, COBOL, mainframe, or modern monolith).
   - Identify the target modernized platform (e.g., Java 21/Spring Boot 3.x, .NET Core/8/9, Go, Node.js/TypeScript).
   - Identify the target compute environment (e.g., Cloud Run, Google Kubernetes Engine (GKE), App Engine) and data tier (e.g., Google Cloud SQL, Cloud Spanner, Cloud Memorystore).
3. **Extract Architectural Structure & Component Modules:**
   - Note codebase scale (Lines of Code (LOC) and file counts).
   - Inspect the codebase breakdown for discovered **Component Modules** (functional subsystems like Repositories, Entities, Controllers) and **Central Dependency Hubs** (load-bearing classes that have the most incoming callers and outgoing dependencies, meaning high blast radius).
   - Map external dependencies, runtime frameworks, and build engines (e.g., Maven, Gradle, MSBuild, dotnet CLI, npm).
4. **Identify Architectural Technical Debt & Strategic Drivers:**
   - **Coupling & Cohesion:** Are business rules, data access, and UI tightly coupled? Are there cross-subsystem dependency leaks?
   - **Central Dependency Hubs:** Which core classes act as bottlenecks that require Anti-Corruption Layers (ACLs) or Facade isolation to prevent changes from rippling across the system?
   - **State & Scalability:** Is the application limited by single-node in-memory state or local sessions that prevent horizontal scalability?
   - **Security Posture:** Are there hardcoded secrets, plain-text connection strings, or unrestricted actuator/metrics endpoints?
   - **Concurrency & Performance:** Are blocking I/O calls limiting throughput? (e.g., synchronous database queries or single-threaded loops).

### Step 2: Initialize Plan & Parity Requirements (Stage 2 - PRD)
1. **Initialize Versioned Directory:**
   - Determine a target slug name (e.g., `rewrite-<app-slug>`).
   - Create the versioned path: `plans/<slug>/<YYYY-MM-DD_HHMM>/`.
2. **Draft the PRD (`02_PRD.md` & `visual-dashboard.html`):**
   - Incorporate the report findings and strategic recommendations directly.
   - Mandate strict API, input validation, and layout/view parity for existing screens and routes.
   - Specify **Non-Goals** (e.g., "We are NOT adding new user features in this pass; this is a strict rewrite for technical modernization, security, and performance").
   - Follow the **Dual-Write Requirement** (Rule 5) via `python3 scripts/manage_dashboard.py mirror --plan-dir "plans/<slug>/<timestamp>"` to mirror `visual-dashboard.html` and `02_PRD.md` to system artifacts as `00_visual-dashboard.html` and `02_prd.md` respectively.

### Step 3: Domain Extraction & Ubiquitous Glossary (Stage 3 - Extraction)
1. **Launch Research Subagent:** Run the `research` skill to scan the legacy code and extract factual specifications:
   - **Legacy Models & Schemas:** Map database schemas, table layouts, core entity relationships, and value objects.
   - **Legacy API & Entry Surfaces:** Extract the full catalog of entry points (HTTP routes, SOAP/WSDL endpoints, MVC controllers, file ingestion jobs, or CLI interfaces).
2. **Publish the Ubiquitous Glossary:**
   - Create `docs/glossary.md` and `docs/visual-glossary.html` documenting domain terms, business rules, validations, and API contracts.
   - Mirror these to the system artifacts folder as `01_visual-glossary.html` (Rule 5).

### Step 4: Target Domain Modeling & Socratic Alignment (Stage 4 - Spec)
1. **Architect Target Models:** Use the `domain-modeling` skill to design target entity classes, repositories, and services aligned with your modern target runtime's idioms (e.g., adopting Java Records, .NET primary constructors, asynchronous/non-blocking patterns, or lightweight serverless handlers).
2. **Decouple Business Logic:** Introduce explicit service boundaries or domain services to completely isolate core business rules from Web/HTTP handlers or database persistence classes.
3. **Draft `04_SPEC.md` & `04_visual-spec.html`:** Document the target system design, data architecture, security hardening (e.g., Secret Manager, identity providers), and SRE/observability integrations. Mirror to system artifacts.
4. **Conduct Socratic Grill:** Execute the `grill` / `grilling` skill to stress-test your design and ensure all edge cases are answered before writing code.

### Step 5: Decompose Monolith into Logical Vertical Slices (Stage 5 - Execution Plan)
1. **Vertical Slicing Rules:** Do NOT plan a monolithic rewrite. Cut the application into logical, independent vertical slices sequenced by dependency order (foundation first, leaf models, core services, central hubs, then ingress controllers).
2. **Draft the Slice-Based Execution Plan (`05_PLAN.md`):**
   - Establish physical contract signatures first.
   - Categorize tasks into `[Serial]` and parallelizable (`[Parallel]`) chunks.
   - Leverage `scripts/digest_report.py` to auto-generate the preliminary `05_PLAN.md` and `migration_matrix.json`.
   - **Dependency-Ordered Slicing Pattern:**
     - **Slice 0 (Common Foundation & Infrastructure):** Target build system configuration (JDK 21, .NET 9), runtime properties, compiler plugins, schema migrations, and CI wrappers.
     - **Slice 1 (Standalone Leaf Modules & Lookup Models):** Low-coupling modules with minimal external dependencies (e.g., lookups, dictionary models, enums). Serves to validate pipeline compilation, data access, and routing.
     - **Slice 2 (Core Domain Repositories & Data Layer):** Main domain services and repositories handling state mutations, validation rules, and heavy transactions. Apply `codmod`'s data layer recommendations (e.g., `javax.*` to `jakarta.*`).
     - **Slice 3 (Central Dependency Hubs & Monolith Decoupling):** High-blast-radius core classes with the most incoming callers and outgoing dependencies. Encapsulate with Anti-Corruption Layers (ACLs) or Facade interfaces to isolate changes.
     - **Slice 4 (Ingress Controllers & Edge Adapters):** MVC controllers, REST endpoints, request formatters, and web templates.
     - **Slice 5 (Target Cloud Hardening & Observability):** Cloud Run configuration, Cloud SQL pooling, GCP Secret Manager, health probes, and OpenTelemetry exporters.
3. **Generate Kanban Visuals:** Use the `kanban` skill to generate an interactive board and Mermaid diagram to map slices and track progress. Mirror `05_PLAN.md` to system artifacts.

### Step 6: Human Gate & Execution (Stages 6 to 9)
1. **Halt for Approval:** Present the PRD, Spec, and Slice Execution Plan to the user. Require explicit "approve" verification.
2. **Slice-by-Slice Implementation:** Execute using TDD via `/tdd` (silent on success) utilizing the `generate-code` and `audit-code` skills to build and verify each slice.
3. **Walkthrough Proof:** Capture terminal playbacks or page tests with the `record` command.
4. **Isolated Branch Delivery:** Build production packages, isolate branch slices using the `worktree` command, and create elegant PRs using `gh` via the `github-workflow` skill.
