#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Adversarial Review Loop Engine for Bean-Grinder Modernization Plans.

Orchestrates multi-persona adversarial reviews across:
- @reviewer-exec (TCO, cloud run-rate, licensing, timeline, rollback)
- @reviewer-engineer (AST safety, DX, build times, testability, error handling)
- @reviewer-architect (central dependency hubs, ACLs, statefulness, scalability)
- @reviewer-pm (parity, undocumented quirks, Gherkin criteria, scope control)
- @review-arbiter (trade-off resolution, consensus scoring, patch directives)

Tracks iterative review rounds, enforces convergence criteria and circuit breakers,
emits 05_ADVERSARIAL_REVIEW.md, and maintains adversarial_review_matrix.json.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

PERSONAS = [
    "reviewer-exec",
    "reviewer-engineer",
    "reviewer-architect",
    "reviewer-pm",
]

DEFAULT_MAX_ROUNDS = 3
DEFAULT_CONVERGENCE_THRESHOLD = 90.0


def compute_consensus_score(critical: int, high: int, medium: int, low: int) -> float:
    """Calculate consensus score from 0.0 to 100.0 based on severity penalties."""
    penalty = (critical * 25.0) + (high * 10.0) + (medium * 3.0) + (low * 1.0)
    return max(0.0, min(100.0, round(100.0 - penalty, 1)))


def parse_reviewer_payload(raw_content: str, default_persona: str) -> Dict[str, Any]:
    """
    Robustly parse reviewer output from raw JSON, markdown-wrapped JSON code blocks,
    or structured markdown fallback.
    """
    cleaned = raw_content.strip()

    # 1. Try markdown fenced json block
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # 2. Try raw JSON parse
    if (cleaned.startswith("{") and cleaned.endswith("}")) or (
        cleaned.startswith("[") and cleaned.endswith("]")
    ):
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
            elif isinstance(parsed, list):
                return {
                    "persona": default_persona,
                    "status": "CHANGES_REQUESTED",
                    "risk_level": "HIGH",
                    "summary": "Imported findings list",
                    "findings": parsed,
                }
        except json.JSONDecodeError:
            pass

    # 3. Fallback: Parse structured markdown headers and lists
    findings = []
    current_finding: Dict[str, Any] = {}
    finding_counter = 1

    lines = cleaned.splitlines()
    summary_lines = []
    status = "APPROVED_ROBUST"
    risk_level = "LOW"

    for line in lines:
        line_s = line.strip()
        if "critical" in line_s.lower():
            status = "CHANGES_REQUESTED"
            risk_level = "CRITICAL"
        elif "high" in line_s.lower() and risk_level != "CRITICAL":
            status = "CHANGES_REQUESTED"
            risk_level = "HIGH"

        # Check for finding header
        if re.match(r"^#{2,4}\s+.*", line_s):
            if current_finding.get("title"):
                findings.append(current_finding)
            title = re.sub(r"^#{2,4}\s+", "", line_s)
            sev = "HIGH" if "critical" not in title.lower() else "CRITICAL"
            current_finding = {
                "id": f"{default_persona.upper()[:4]}-{finding_counter:02d}",
                "severity": sev,
                "category": "GENERAL_AUDIT",
                "title": title,
                "concrete_scenario": "",
                "actionable_remediation": "",
            }
            finding_counter += 1
        elif current_finding:
            if "scenario" in line_s.lower() or "failure" in line_s.lower():
                current_finding["concrete_scenario"] = line_s
            elif "remediation" in line_s.lower() or "recommendation" in line_s.lower():
                current_finding["actionable_remediation"] = line_s
            elif line_s:
                if not current_finding.get("concrete_scenario"):
                    current_finding["concrete_scenario"] = line_s
        elif line_s and not line_s.startswith("#"):
            summary_lines.append(line_s)

    if current_finding.get("title"):
        findings.append(current_finding)

    return {
        "persona": default_persona,
        "status": status if findings else "APPROVED_ROBUST",
        "risk_level": risk_level if findings else "LOW",
        "summary": " ".join(summary_lines[:3]) or f"Audited by {default_persona}",
        "findings": findings,
    }


def reconcile_trade_offs(reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Identify and synthesize cross-functional tensions between personas.
    Applies Bean-Grinder Arbiter heuristics:
    1. Exec (Cost/Speed) vs Architect (Modular Purity/ACLs)
    2. PM (100% Bug-for-Bug Parity) vs Engineer (Clean Refactor/Standards)
    3. Exec (Minimum Scope) vs PM (Comprehensive Batch Coverage)
    """
    persona_map = {r.get("persona"): r for r in reviews}
    trade_offs = []

    has_exec_finding = bool(persona_map.get("reviewer-exec", {}).get("findings"))
    has_arch_finding = bool(persona_map.get("reviewer-architect", {}).get("findings"))
    has_eng_finding = bool(persona_map.get("reviewer-engineer", {}).get("findings"))
    has_pm_finding = bool(persona_map.get("reviewer-pm", {}).get("findings"))

    if has_exec_finding and has_arch_finding:
        trade_offs.append({
            "id": "TRADE-01",
            "personas_involved": ["reviewer-exec", "reviewer-architect"],
            "conflict_summary": "Tension between rapid delivery / cloud cost limits and deep architectural decoupling of Central Dependency Hubs.",
            "arbiter_decision": "Pragmatic In-Process Facade: Encapsulate Central Hubs with lightweight internal interfaces in Slice 1 rather than full microservice extraction.",
            "plan_directive": "Introduce an Anti-Corruption Facade in Slice 1 to protect caller contracts without deploying independent microservices.",
        })

    if has_pm_finding and has_eng_finding:
        trade_offs.append({
            "id": "TRADE-02",
            "personas_involved": ["reviewer-pm", "reviewer-engineer"],
            "conflict_summary": "Tension between strict legacy bug-for-bug error payload parity and clean standard HTTP exception handling.",
            "arbiter_decision": "Boundary Compatibility Envelope: Retain legacy JSON error formats on public edge controllers, but use idiomatic domain exceptions internally.",
            "plan_directive": "Retain legacy payload response adapters in Slice 4 while modernizing internal service exceptions in Slice 2.",
        })

    if has_exec_finding and has_pm_finding:
        trade_offs.append({
            "id": "TRADE-03",
            "personas_involved": ["reviewer-exec", "reviewer-pm"],
            "conflict_summary": "Tension between migration timeline constraints and exhaustive coverage of legacy batch export jobs.",
            "arbiter_decision": "Phased Criticality Slicing: Core transactional paths migrate in Primary Slices; non-critical offline batch jobs are sequenced into an explicit follow-on Slice 5.",
            "plan_directive": "Categorize batch jobs into Slice 5 (Target Cloud Hardening) and verify primary user transactions first.",
        })

    return trade_offs


def evaluate_review_round(
    plan_dir: Path,
    round_number: int,
    persona_reviews: List[Dict[str, Any]],
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    threshold: float = DEFAULT_CONVERGENCE_THRESHOLD,
) -> Dict[str, Any]:
    """
    Execute Arbiter synthesis for a single round of adversarial reviews.
    """
    critical_count = 0
    high_count = 0
    medium_count = 0
    low_count = 0

    normalized_reviews = {}
    all_findings = []

    for r in persona_reviews:
        p_name = r.get("persona", "unknown")
        normalized_reviews[p_name] = r
        for f in r.get("findings", []):
            sev = f.get("severity", "MEDIUM").upper()
            if sev == "CRITICAL":
                critical_count += 1
            elif sev == "HIGH":
                high_count += 1
            elif sev == "MEDIUM":
                medium_count += 1
            else:
                low_count += 1
            f["persona"] = p_name
            all_findings.append(f)

    consensus_score = compute_consensus_score(
        critical_count, high_count, medium_count, low_count
    )

    trade_offs = reconcile_trade_offs(persona_reviews)

    # Determine verdict
    is_converged = (
        critical_count == 0
        and high_count == 0
        and consensus_score >= threshold
    )
    circuit_breaker = (not is_converged) and (round_number >= max_rounds)

    if is_converged:
        verdict = "CONVERGED_ROBUST"
    elif circuit_breaker:
        verdict = "CIRCUIT_BREAKER_TRIGGERED"
    else:
        verdict = "NEEDS_REVISION"

    # Compile directives
    directives = []
    for to in trade_offs:
        directives.append(to["plan_directive"])

    for f in all_findings:
        if f.get("severity") in ["CRITICAL", "HIGH"]:
            rem = f.get("actionable_remediation")
            if rem:
                directives.append(f"[{f.get('id', 'BLOCKER')}]: {rem}")

    round_data = {
        "round_number": round_number,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "is_converged": is_converged,
        "circuit_breaker_tripped": circuit_breaker,
        "consensus_score": consensus_score,
        "critical_count": critical_count,
        "high_count": high_count,
        "medium_count": medium_count,
        "low_count": low_count,
        "persona_reviews": normalized_reviews,
        "trade_offs": trade_offs,
        "directives": directives,
        "findings": all_findings,
    }

    return round_data


def generate_adversarial_review_md(matrix: Dict[str, Any]) -> str:
    """Generate the definitive 05_ADVERSARIAL_REVIEW.md report."""
    current_round = matrix.get("current_round", 1)
    rounds = matrix.get("rounds", [])
    latest_round = rounds[-1] if rounds else {}

    verdict = latest_round.get("verdict", "PENDING")
    score = latest_round.get("consensus_score", 0.0)
    crit = latest_round.get("critical_count", 0)
    high = latest_round.get("high_count", 0)
    med = latest_round.get("medium_count", 0)
    low = latest_round.get("low_count", 0)

    # Status Badge
    if verdict == "CONVERGED_ROBUST":
        status_badge = "🟢 **CONVERGED: ROBUST & APPROVED**"
    elif verdict == "CIRCUIT_BREAKER_TRIGGERED":
        status_badge = "🔴 **CIRCUIT BREAKER: HUMAN ARBITRATION REQUIRED**"
    else:
        status_badge = "🟡 **IN PROGRESS: HARDENING REVISIONS REQUIRED**"

    lines = [
        "# 🛡️ Adversarial Review & Hardening Audit Report",
        "",
        f"> **Modernization Plan:** `{matrix.get('plan_slug', 'Application Rewrite')}`  ",
        f"> **Review Loop Progress:** Round {current_round} of {matrix.get('max_rounds', DEFAULT_MAX_ROUNDS)}  ",
        f"> **Status:** {status_badge}  ",
        f"> **Consensus Score:** **{score:.1f}%** (Threshold: {matrix.get('convergence_threshold', DEFAULT_CONVERGENCE_THRESHOLD)}%)  ",
        "",
        "---",
        "",
        "## 📊 Multi-Persona Review Scorecard",
        "",
        "| Stakeholder Persona | Status | Risk Level | Critical | High | Medium | Primary Audit Focus |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]

    persona_meta = {
        "reviewer-exec": ("💼 Executive", "TCO, Cloud Run-Rate, Licensing & Rollback"),
        "reviewer-engineer": ("💻 Engineering", "AST Safety, DX, Build Times & Testability"),
        "reviewer-architect": ("🏛️ Architecture", "Central Hubs, ACLs, Scalability & State"),
        "reviewer-pm": ("📋 Product & Parity", "Parity, Undocumented Quirks & Gherkin AC"),
    }

    p_reviews = latest_round.get("persona_reviews", {})
    for p_id in PERSONAS:
        p_label, p_focus = persona_meta.get(p_id, (p_id, "Specialized Audit"))
        p_data = p_reviews.get(p_id, {})
        status = p_data.get("status", "NOT_REVIEWED")
        risk = p_data.get("risk_level", "N/A")
        f_list = p_data.get("findings", [])
        c_p = sum(1 for f in f_list if f.get("severity") == "CRITICAL")
        h_p = sum(1 for f in f_list if f.get("severity") == "HIGH")
        m_p = sum(1 for f in f_list if f.get("severity") == "MEDIUM")

        status_icon = "✅ APPROVED" if status == "APPROVED_ROBUST" else "⚠️ REVISION"
        lines.append(
            f"| **{p_label}** | `{status_icon}` | `{risk}` | `{c_p}` | `{h_p}` | `{m_p}` | {p_focus} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## ⚖️ Cross-Functional Trade-Off Resolutions (@review-arbiter)",
        "",
    ])

    trade_offs = latest_round.get("trade_offs", [])
    if trade_offs:
        for to in trade_offs:
            involved = ", ".join(f"`@{p}`" for p in to.get("personas_involved", []))
            lines.extend([
                f"### {to.get('id')}: {to.get('conflict_summary')}",
                f"- **Stakeholders Involved:** {involved}",
                f"- **Arbiter Consensus Rationale:** {to.get('arbiter_decision')}",
                f"- **Hardening Directive for `05_PLAN.md`:** `{to.get('plan_directive')}`",
                "",
            ])
    else:
        lines.append("*(No unresolved cross-functional trade-offs identified in this round)*\n")

    lines.extend([
        "---",
        "",
        "## 🚨 Active Flaws & Remediation Directives",
        "",
    ])

    findings = latest_round.get("findings", [])
    if findings:
        for idx, f in enumerate(findings, 1):
            sev = f.get("severity", "MEDIUM")
            sev_icon = "🔴" if sev == "CRITICAL" else ("🟠" if sev == "HIGH" else "🟡")
            lines.extend([
                f"#### {sev_icon} [{f.get('id', f'FLAW-{idx}')}] {f.get('title')}",
                f"- **Stakeholder:** `@{f.get('persona')}` | **Severity:** `{sev}` | **Category:** `{f.get('category', 'GENERAL')}`",
                f"- **Concrete Failure Scenario:** {f.get('concrete_scenario', 'N/A')}",
            ])
            if f.get("blast_radius"):
                lines.append(f"- **Blast Radius / Impact:** {f.get('blast_radius')}")
            if f.get("financial_blast_radius"):
                lines.append(f"- **Financial Impact:** {f.get('financial_blast_radius')}")
            if f.get("customer_blast_radius"):
                lines.append(f"- **Customer Impact:** {f.get('customer_blast_radius')}")
            lines.extend([
                f"- **Required Plan Remediation:** {f.get('actionable_remediation', 'Address finding in execution plan.')}",
                "",
            ])
    else:
        lines.append("*(Zero active blockers. All stakeholder criteria satisfied!)*\n")

    lines.extend([
        "---",
        "",
        "## 🔄 Review Loop History Across Rounds",
        "",
        "| Round | Timestamp | Verdict | Consensus Score | Critical | High | Medium |",
        "| :---: | :--- | :---: | :---: | :---: | :---: | :---: |",
    ])

    for r in rounds:
        r_num = r.get("round_number")
        ts = r.get("timestamp", "")[:19].replace("T", " ")
        r_verdict = r.get("verdict")
        r_score = r.get("consensus_score", 0.0)
        lines.append(
            f"| **Round {r_num}** | {ts} | `{r_verdict}` | **{r_score:.1f}%** | {r.get('critical_count', 0)} | {r.get('high_count', 0)} | {r.get('medium_count', 0)} |"
        )

    lines.extend([
        "",
        "---",
        "*(Generated automatically by Bean-Grinder Adversarial Review Engine)*",
    ])

    return "\n".join(lines)


def patch_plan_hardening_log(plan_path: Path, round_data: Dict[str, Any]) -> bool:
    """
    Append or replace the ## 🛡️ Adversarial Hardening Log section inside 05_PLAN.md.
    """
    if not plan_path.exists():
        return False

    content = plan_path.read_text(encoding="utf-8", errors="replace")

    r_num = round_data.get("round_number", 1)
    verdict = round_data.get("verdict", "PENDING")
    score = round_data.get("consensus_score", 0.0)
    crit = round_data.get("critical_count", 0)
    high = round_data.get("high_count", 0)

    log_section = [
        "## 🛡️ Adversarial Review & Hardening Audit",
        f"- **Audit Status:** `{verdict}` (Consensus Score: **{score:.1f}%**)",
        f"- **Iteration:** Round {r_num} (Critical Blockers: `{crit}`, High Risks: `{high}`)",
        "- **Sign-Off Matrix:**",
    ]

    p_reviews = round_data.get("persona_reviews", {})
    for p_id in PERSONAS:
        p_name = p_id.replace("reviewer-", "").capitalize()
        p_data = p_reviews.get(p_id, {})
        status = p_data.get("status", "CHANGES_REQUESTED")
        icon = "✅ Approved" if status == "APPROVED_ROBUST" else "⚠️ Changes Requested"
        log_section.append(f"  - **@{p_id} ({p_name}):** {icon}")

    directives = round_data.get("directives", [])
    if directives:
        log_section.append("- **Incorporated Directives & Mitigations:**")
        for d in directives[:6]:
            log_section.append(f"  - {d}")

    log_text = "\n".join(log_section) + "\n"

    # If section already exists, replace it
    if "## 🛡️ Adversarial Review & Hardening Audit" in content:
        pattern = r"## 🛡️ Adversarial Review & Hardening Audit[\s\S]*?(?=\n## |\Z)"
        new_content = re.sub(pattern, log_text.strip(), content)
    else:
        new_content = content.rstrip() + "\n\n" + log_text

    plan_path.write_text(new_content, encoding="utf-8")
    return True


def simulate_adversarial_round(round_number: int) -> List[Dict[str, Any]]:
    """
    Generate realistic multi-persona review findings for testing and simulation.
    Round 1: Discovers realistic critical/high issues.
    Round 2+: Shows hardening progress with resolved flaws.
    """
    if round_number == 1:
        return [
            {
                "persona": "reviewer-exec",
                "status": "CHANGES_REQUESTED",
                "risk_level": "CRITICAL",
                "summary": "Dual-run database costs and unmetered Cloud SQL IOPS will exceed migration budget.",
                "findings": [
                    {
                        "id": "EXEC-01",
                        "severity": "CRITICAL",
                        "category": "TCO_AND_CLOUD_COST",
                        "title": "Unmetered Cloud SQL Read Replicas During Dual-Run",
                        "concrete_scenario": "Running the legacy monolith in parallel with Cloud SQL without instance auto-scaling caps will double database licensing costs for 6 months.",
                        "financial_blast_radius": "Estimated +$15,000/month overrun during transition period.",
                        "actionable_remediation": "Cap dual-run window to 60 days and configure auto-scaling upper bounds in Slice 0.",
                    }
                ],
            },
            {
                "persona": "reviewer-engineer",
                "status": "CHANGES_REQUESTED",
                "risk_level": "HIGH",
                "summary": "Automated codemod breaks runtime reflection in legacy persistence layer.",
                "findings": [
                    {
                        "id": "ENG-01",
                        "severity": "HIGH",
                        "category": "AST_SAFETY",
                        "title": "Dynamic Reflection in Custom Entity Serialization",
                        "concrete_scenario": "Rewriting javax.persistence to jakarta.persistence breaks custom reflection serializer at runtime without compiler warnings.",
                        "blast_radius": "Silent data corruption or NPE during runtime entity persistence.",
                        "actionable_remediation": "Add an explicit contract test exercising dynamic cloning before running AST transforms.",
                    }
                ],
            },
            {
                "persona": "reviewer-architect",
                "status": "CHANGES_REQUESTED",
                "risk_level": "CRITICAL",
                "summary": "Central Dependency Hub SessionManager modified without Anti-Corruption Layer.",
                "findings": [
                    {
                        "id": "ARCH-01",
                        "severity": "CRITICAL",
                        "category": "CENTRAL_DEPENDENCY_HUB",
                        "title": "Central Hub SessionManager Modified Without Anti-Corruption Layer",
                        "concrete_scenario": "SessionManager has 38 incoming callers across 5 subsystems. Modifying its signatures in Slice 2 will trigger cascade breakages.",
                        "blast_radius": "High (38 caller classes across core domain repositories).",
                        "actionable_remediation": "Wrap SessionManager in an Anti-Corruption Layer interface and introduce an adapter in Slice 1 before refactoring internals.",
                    }
                ],
            },
            {
                "persona": "reviewer-pm",
                "status": "CHANGES_REQUESTED",
                "risk_level": "HIGH",
                "summary": "Modernized REST endpoints alter legacy error envelope structure.",
                "findings": [
                    {
                        "id": "PM-01",
                        "severity": "HIGH",
                        "category": "API_PARITY",
                        "title": "Legacy Error Envelope Altered in Modernized Endpoints",
                        "concrete_scenario": "Legacy API returned custom error codes on HTTP 400. Modernized plan proposes standard RFC 7807 ProblemDetails which breaks the mobile app.",
                        "customer_blast_radius": "Mobile app crashes on validation errors for ~150k daily active users.",
                        "actionable_remediation": "Retain legacy error payload adapter on public routes or introduce a versioned v2 route namespace.",
                    }
                ],
            },
        ]
    else:
        # Hardened Round 2 / 3: All critical and high flaws mitigated!
        return [
            {
                "persona": "reviewer-exec",
                "status": "APPROVED_ROBUST",
                "risk_level": "LOW",
                "summary": "Dual-run cost cap of 60 days incorporated into Slice 0. TCO within acceptable bounds.",
                "findings": [],
            },
            {
                "persona": "reviewer-engineer",
                "status": "APPROVED_ROBUST",
                "risk_level": "LOW",
                "summary": "Entity cloning contract test fixture added to Slice 1. AST transforms validated safe.",
                "findings": [],
            },
            {
                "persona": "reviewer-architect",
                "status": "APPROVED_ROBUST",
                "risk_level": "LOW",
                "summary": "SessionManager ACL facade introduced in Slice 1. Central hub blast radius mitigated.",
                "findings": [],
            },
            {
                "persona": "reviewer-pm",
                "status": "APPROVED_ROBUST",
                "risk_level": "LOW",
                "summary": "Legacy error envelope adapter preserved on public ingress routes. 100% parity verified.",
                "findings": [],
            },
        ]


def main():
    parser = argparse.ArgumentParser(
        description="Bean-Grinder Multi-Persona Adversarial Review Engine"
    )
    parser.add_argument(
        "--plan-dir",
        type=str,
        required=True,
        help="Target plan directory containing 05_PLAN.md",
    )
    parser.add_argument(
        "--simulate-round",
        type=int,
        choices=[1, 2, 3],
        help="Simulate a realistic review round (1 = initial critiques, 2 = hardened resolution)",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=DEFAULT_MAX_ROUNDS,
        help="Maximum review iterations before circuit breaker trip",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_CONVERGENCE_THRESHOLD,
        help="Consensus score threshold for convergence (default: 90.0)",
    )
    parser.add_argument(
        "--ingest-review",
        type=str,
        help="Path to reviewer JSON or Markdown payload file to ingest",
    )
    parser.add_argument(
        "--persona",
        type=str,
        choices=PERSONAS,
        help="Reviewer persona name for ingested payload",
    )

    args = parser.parse_args()
    plan_dir = Path(args.plan_dir)
    plan_dir.mkdir(parents=True, exist_ok=True)

    rev_stage_dir = plan_dir / "03_adversarial_review"
    plan_stage_dir = plan_dir / "04_migration_plan"
    rev_stage_dir.mkdir(parents=True, exist_ok=True)

    # Locate matrix file (check stage dir first, then root)
    matrix_file = plan_dir / "adversarial_review_matrix.json"
    if (rev_stage_dir / "adversarial_review_matrix.json").exists():
        matrix_file = rev_stage_dir / "adversarial_review_matrix.json"

    # Locate plan file (check stage dir first, then root)
    plan_file = plan_dir / "05_PLAN.md"
    if (plan_stage_dir / "05_PLAN.md").exists():
        plan_file = plan_stage_dir / "05_PLAN.md"

    review_report_file = plan_dir / "05_ADVERSARIAL_REVIEW.md"
    stage_report_file = rev_stage_dir / "adversarial_audit_report.md"

    # Load or initialize matrix
    if matrix_file.exists():
        with open(matrix_file, "r", encoding="utf-8") as f:
            matrix = json.load(f)
    else:
        matrix = {
            "plan_slug": plan_dir.parent.name if plan_dir.parent else "modernization",
            "plan_dir": str(plan_dir.resolve()),
            "current_round": 1,
            "max_rounds": args.max_rounds,
            "convergence_threshold": args.threshold,
            "is_converged": False,
            "circuit_breaker_tripped": False,
            "rounds": [],
        }

    # Simulation Mode
    if args.simulate_round:
        round_num = args.simulate_round
        reviews = simulate_adversarial_round(round_num)
        round_data = evaluate_review_round(
            plan_dir=plan_dir,
            round_number=round_num,
            persona_reviews=reviews,
            max_rounds=args.max_rounds,
            threshold=args.threshold,
        )

        matrix["current_round"] = round_num
        matrix["rounds"].append(round_data)
        matrix["is_converged"] = (round_data["verdict"] == "CONVERGED_ROBUST")
        matrix["circuit_breaker_tripped"] = (round_data["verdict"] == "CIRCUIT_BREAKER_TRIGGERED")

        # Write matrix json to stage and root
        with open(rev_stage_dir / "adversarial_review_matrix.json", "w", encoding="utf-8") as f:
            json.dump(matrix, f, indent=2)
        with open(plan_dir / "adversarial_review_matrix.json", "w", encoding="utf-8") as f:
            json.dump(matrix, f, indent=2)

        # Write plan directives
        directives = round_data.get("directives", [])
        with open(rev_stage_dir / "plan_hardening_directives.json", "w", encoding="utf-8") as f:
            json.dump({"round": round_num, "directives": directives}, f, indent=2)

        # Generate markdown report in stage and root
        md_content = generate_adversarial_review_md(matrix)
        stage_report_file.write_text(md_content, encoding="utf-8")
        review_report_file.write_text(md_content, encoding="utf-8")

        # Patch plan in stage and root if present
        if (plan_stage_dir / "05_PLAN.md").exists():
            patch_plan_hardening_log(plan_stage_dir / "05_PLAN.md", round_data)
        if (plan_dir / "05_PLAN.md").exists() and (plan_stage_dir / "05_PLAN.md") != (plan_dir / "05_PLAN.md"):
            patch_plan_hardening_log(plan_dir / "05_PLAN.md", round_data)

        # Update manifest if run_manifest.json exists
        try:
            from scripts.run_manager import RunManager
            mgr = RunManager(base_dir=plan_dir.parent.parent if plan_dir.parent.name == "runs" else plan_dir.parent)
            mgr.update_manifest(
                plan_dir,
                status="REVIEW_CONVERGED" if matrix["is_converged"] else "IN_REVIEW",
                review_verdict=round_data["verdict"],
                consensus_score=round_data["consensus_score"],
            )
        except Exception:
            pass

        print(f"✅ Round {round_num} evaluated: Verdict = {round_data['verdict']}, Score = {round_data['consensus_score']}%")
        print(f"   Matrix: {rev_stage_dir / 'adversarial_review_matrix.json'}")
        print(f"   Report: {stage_report_file}")
        return

    # Ingestion Mode
    if args.ingest_review:
        if not args.persona:
            print("Error: --persona required when ingesting review payload", file=sys.stderr)
            sys.exit(1)
        in_path = Path(args.ingest_review)
        if not in_path.exists():
            print(f"Error: Ingest file not found: {in_path}", file=sys.stderr)
            sys.exit(1)

        payload_text = in_path.read_text(encoding="utf-8")
        parsed = parse_reviewer_payload(payload_text, args.persona)
        print(f"✅ Ingested review for @{args.persona}: {parsed.get('status')} ({len(parsed.get('findings', []))} findings)")


if __name__ == "__main__":
    main()
