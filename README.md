<p align="center">
  <img src="assets/banner.png" alt="Bean-Grinder Banner" width="100%" />
</p>

# ⚙️ Bean-Grinder

> **Code Modernization, AST Transformations, and Migration Forge for Antigravity SDLC pipelines.**

---

## ☕ Why "The Grinder"? (The Metaphor Explained)

<p align="center">
  <img src="assets/sketch.png" alt="Bean-Grinder Fun Sketch" width="480px" />
</p>

In specialty coffee brewing, whole roasted beans cannot simply be dropped directly into boiling water—they must first pass through precision-calibrated burrs to be milled into uniform, structured particle sizes before optimal extraction can occur.

In software engineering, legacy monoliths and aging codebases are the coarse, uneven roasted beans: full of tightly coupled modules, deprecated APIs, outdated runtimes, and accumulated technical debt. 

**`bean-grinder`** is the mechanical burr mill of our autonomous barista swarm:
1. **Deconstruction:** It takes coarse legacy repositories (Java 8, WildFly, .NET Framework, monolithic SQL) and breaks them down into Abstract Syntax Trees (ASTs).
2. **Chaff Removal:** It strips away obsolete frameworks, dead vendor dependencies, and legacy boilerplate.
3. **Calibrated Modernization:** It runs Google Cloud **`codmod`** assessments and automated AST transformations to mill the legacy system into clean, uniform, decoupled vertical slices ready for implementation by **`bean-brewer`**.

---

## 🏛️ Origin & Architectural Rationale

### Spawned from `bean-to-cup`
**`bean-grinder`** was extracted from the monolithic [`bean-to-cup`](https://github.com/sapientcoffee/bean-to-cup) repository as part of a modular decomposition of the Antigravity barista swarm.

### Why Decompose?
1. **Dedicated Migration Specialization:** Enterprise codebase modernization, AST transformations, and Google Cloud `codmod` executions are specialized operations with unique prerequisites (GCP authorization, dry-run cost estimation, AST parsers). Isolating them prevents cluttering day-to-day feature development.
2. **Clean Separation from Day 2 SRE (`bean-descale`):** While `bean-descale` focuses on runtime health, incident triage, and operational resilience, `bean-grinder` focuses purely on static codebase transformation, language upgrades, and architectural rewrites.
3. **Parity-Preserving Handoffs:** `bean-grinder` generates assessment reports (`modernization_report.html`) and parity contracts (`02_PRD.md`) that hand off directly to `bean-brewer` for implementation and to `bean-cup` for visual tracking.
4. **Independent Evolution:** Support for new `codmod` intents, AST transformation rules, and migration language targets can be added without modifying core feature delivery plugins.

---

## 🚀 Capabilities & Skills Reference

| Feature | Type | Description |
| :--- | :---: | :--- |
| **`assess` (`skills/assess`)** | Skill | Parallel orchestrator: validates GCP credentials, manages optional pre-flight cost shield, and concurrently dispatches `@codmod-assessor` and `@graphify-scout` to generate `modernization_report.html` and `graphify-out/` without context bloat, feeding directly into `digest_report.py`. |
| **`rewrite` (`skills/rewrite`)** | Skill | Language-agnostic rewrite brew protocol: ingests assessment reports, digests semantic findings with Graphify architecture analysis (`scripts/digest_report.py`), maps source-to-target runtimes, establishes strict contract parity, and cuts vertical slices into `05_PLAN.md`. |
| **`digest_report.py` (`scripts/`)** | Tool | Dual-lens synthesis engine: extracts semantic tasks from `codmod` reports, maps codebase component modules and central dependency hubs from `graphify`, and emits `migration_matrix.json`, dependency-ordered `05_PLAN.md`, and the unified `modernization_dashboard.html`. |
| **`@codmod-assessor`** | Agent | Dedicated subagent running Google Cloud `codmod create`, intent auto-mapping, failure logging, and concise blocker synthesis in an isolated sandbox. |
| **`@graphify-scout`** | Agent | Dedicated subagent executing `graphify . --directed`, verifying knowledge graph artifacts, and extracting central dependency hubs and component clusters. |
| **`@migration-scout`** | Agent | Autonomous codebase scanner detecting source language levels, application servers, and cloud SDK lock-in. |
| **`@ast-grinder`** | Agent | AST transformation engine executing automated codemods, syntax modernization, and deprecated API replacements. |
| **`@runtime-parity-verifier`** | Agent | Evaluates functional, behavioral, and schema parity via active synthetic request replay in an execution sandbox, writing detailed diffs into `docs/parity_discrepancies.md`. |
| **`@msbuild`** | Agent | Manages verbose legacy .NET and C++ builds during modernization passes without overflowing LLM context. |

---

## 🔄 Detailed Code Modernization & Migration Workflow

```mermaid
flowchart TD
    subgraph Intake["📥 Monolith Ingestion"]
        LegacyCode["Legacy Monolithic Codebase<br/>(Java 8, WildFly, .NET 4.8, Monolithic DB)"]
        GCPAuth["GCP Authentication & Project Context"]
        CostCheck{"Optional Pre-Flight Cost Shield<br/>(--estimate-cost)"}
    end

    subgraph ParallelAssess["⚡ Phase 1: Parallel Assessment Subagents (skills/assess)"]
        direction TB
        Orchestrator["Parallel Orchestrator (skills/assess)"]
        AssessorSubagent["@codmod-assessor Subagent<br/>(codmod create & collect-logs)"]
        GraphifySubagent["@graphify-scout Subagent<br/>(graphify . --directed)"]
        ModernReport["Emit: modernization_report.html"]
        GraphifyOut["Emit: graph.json, graph.html, GRAPH_REPORT.md"]
        
        Orchestrator -->|invoke_subagent [Parallel]| AssessorSubagent
        Orchestrator -->|invoke_subagent [Parallel]| GraphifySubagent
        AssessorSubagent --> ModernReport
        GraphifySubagent --> GraphifyOut
    end

    subgraph RewritePhase["📐 Phase 2: Digest & Parity Specification (skills/rewrite)"]
        DigestTool["scripts/digest_report.py & generate_dashboard.py<br/>(Combine Semantic Tasks + Component Modules)"]
        RuntimeMapping["Source-to-Target Architecture Mapping"]
        ParityMatrix["Establish Strict Functional Parity Matrix"]
        VerticalSlicing["Dependency-Ordered Slices (Foundation, Leaf, Core, Central Hubs, Ingress)"]
        EmitArtifacts["Emit: 02_PRD.md, 05_PLAN.md, migration_matrix.json<br/>& modernization_dashboard.html (00_visual-dashboard.html)"]
    end

    subgraph GrindingPass["🔄 Phase 3: AST Transformation (@ast-grinder & @msbuild)"]
        ASTTransform["@ast-grinder (Automated Syntax & Codemods)"]
        BuildCheck["@msbuild (Legacy Compilation Verification)"]
        ParityCheck["@runtime-parity-verifier<br/>(Synthetic Request Replay & Diffs)"]
        ParityVerdict{"Strict Parity Maintained?"}
    end

    subgraph Downstream["🚀 Downstream Delivery & Tracking"]
        HandoffBrewer["Hand off Slices to bean-brewer<br/>(@architect, @engineer, TDD, PR)"]
        TelemetryCup["Telemetry Sync to bean-cup<br/>(visual-dashboard.html)"]
    end

    LegacyCode & GCPAuth --> CostCheck
    CostCheck --> Orchestrator
    ModernReport & GraphifyOut --> DigestTool
    DigestTool --> RuntimeMapping --> ParityMatrix --> VerticalSlicing --> EmitArtifacts
    EmitArtifacts --> ASTTransform
    ASTTransform --> BuildCheck --> ParityCheck --> ParityVerdict
    ParityVerdict -->|Discrepancy Found| ASTTransform
    ParityVerdict -->|Parity Verified| HandoffBrewer
    ModernReport & EmitArtifacts -.-> TelemetryCup
```

---

## 📦 Installation

```bash
# Local workspace
./install.sh

# Or global agy install
agy plugin install .
```

---

## 📜 License
Apache-2.0 - Copyright 2026 Google LLC.
