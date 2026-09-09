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
| **`assess` (`skills/assess`)** | Skill | Full Google Cloud `codmod` driver: pre-scan with `@migration-scout`, intent mapping (`JAVA_LEGACY_TO_MODERN`, `WILDFLY_LEGACY_TO_MODERN`, `MICROSOFT_MODERNIZATION`, `ARM_MIGRATION`, `CLOUD_TO_CLOUD`), interactive dry-run cost shields, execution of `codmod create`, self-healing diagnostic collection (`codmod collect-logs`), and JSON telemetry. |
| **`rewrite` (`skills/rewrite`)** | Skill | Language-agnostic rewrite brew protocol: ingests assessment reports, maps source-to-target runtimes, establishes strict contract parity, and cuts vertical slices into `05_PLAN.md`. |
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
    end

    subgraph ScoutPhase["🔍 Phase 1: Pre-Scan (@migration-scout)"]
        Scout["@migration-scout Subagent"]
        DetectRuntimes["Detect Source Runtime & Deprecated Frameworks"]
        DetectClouds["Detect Cloud SDKs & Proprietary Locks"]
        EmitScoutSummary["Emit: Migration Intent Classification"]
    end

    subgraph AssessPhase["⚙️ Phase 2: Assessment & Cost Shield (skills/assess)"]
        IntentMapping["Map Codmod Intent<br/>(JAVA_LEGACY_TO_MODERN, WILDFLY, etc.)"]
        CostShield{"Interactive Dry-Run Cost Shield"}
        UserAbort["Abort: Avoid Unintended GCP Cost"]
        ExecCodmod["Run: codmod create & codmod collect-logs"]
        ModernReport["Emit: modernization_report.html & Telemetry JSON"]
    end

    subgraph RewritePhase["📐 Phase 3: Parity Specification (skills/rewrite)"]
        IngestReport["Ingest Assessment Insights"]
        RuntimeMapping["Source-to-Target Architecture Mapping"]
        ParityMatrix["Establish Strict Functional Parity Matrix"]
        VerticalSlicing["Cut Decoupled Migration Slices"]
        EmitArtifacts["Emit: 02_PRD.md & 05_PLAN.md"]
    end

    subgraph GrindingPass["🔄 Phase 4: AST Transformation (@ast-grinder & @msbuild)"]
        ASTTransform["@ast-grinder (Automated Syntax & Codemods)"]
        BuildCheck["@msbuild (Legacy Compilation Verification)"]
        ParityCheck["@runtime-parity-verifier<br/>(Synthetic Request Replay & Diffs)"]
        ParityVerdict{"Strict Parity Maintained?"}
    end

    subgraph Downstream["🚀 Downstream Delivery & Tracking"]
        HandoffBrewer["Hand off Slices to bean-brewer<br/>(@architect, @engineer, TDD, PR)"]
        TelemetryCup["Telemetry Sync to bean-cup<br/>(visual-dashboard.html)"]
    end

    LegacyCode & GCPAuth --> Scout
    Scout --> DetectRuntimes & DetectClouds --> EmitScoutSummary
    EmitScoutSummary --> IntentMapping --> CostShield
    CostShield -->|User Rejects Cost| UserAbort
    CostShield -->|User Confirms| ExecCodmod
    ExecCodmod --> ModernReport --> IngestReport
    IngestReport --> RuntimeMapping --> ParityMatrix --> VerticalSlicing --> EmitArtifacts
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
