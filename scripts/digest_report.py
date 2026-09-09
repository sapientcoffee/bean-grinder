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
Digest CodMod Assessment Reports and Cross-Reference with Graphify Knowledge Graphs.

Synthesizes semantic modernization recommendations from Google Cloud codmod
with topological AST knowledge graphs from Graphify. Decomposes complex legacy
applications into low-risk, topologically ordered vertical migration slices.
"""

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


def parse_codmod_report(report_path: Path) -> Dict[str, Any]:
    """Parse a codmod HTML or JSON assessment report."""
    if not report_path.exists():
        raise FileNotFoundError(f"Report file not found: {report_path}")

    # If already JSON
    if report_path.suffix.lower() == ".json":
        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # HTML parsing
    content = report_path.read_text(encoding="utf-8", errors="replace")
    data: Dict[str, Any] = {
        "title": "Modernization Assessment",
        "executive_summary": "",
        "key_findings": [],
        "strategic_recommendations": [],
        "roadmap_phases": [],
        "work_plan_tasks": [],
        "complexity_matrix": [],
        "code_transformations": [],
        "data_layer_impacts": [],
        "flagged_files": [],
    }

    if HAS_BS4:
        soup = BeautifulSoup(content, "html.parser")
        if soup.title and soup.title.string:
            data["title"] = soup.title.string.strip()

        # Remove heavy script and style tags to make text extraction instantaneous
        for tag in soup(["script", "style"]):
            tag.decompose()

        # Extract Executive Summary & Sections
        for h in soup.find_all(["h1", "h2", "h3"]):
            text = h.get_text(strip=True).lower()
            if "executive summary" in text:
                p = h.find_next("p")
                if p:
                    data["executive_summary"] = p.get_text(strip=True)

            elif "key findings" in text:
                nxt = h.find_next(["ul", "ol", "p"])
                if nxt and nxt.name in ["ul", "ol"]:
                    data["key_findings"] = [
                        li.get_text(strip=True) for li in nxt.find_all("li")
                    ]
                elif nxt:
                    data["key_findings"] = [nxt.get_text(strip=True)]

            elif "strategic recommendations" in text:
                nxt = h.find_next(["ul", "ol", "p"])
                if nxt and nxt.name in ["ul", "ol"]:
                    data["strategic_recommendations"] = [
                        li.get_text(strip=True) for li in nxt.find_all("li")
                    ]

            elif "migration roadmap" in text:
                table = h.find_next("table")
                if table:
                    rows = table.find_all("tr")
                    for row in rows[1:]:
                        cols = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                        if len(cols) >= 3:
                            data["roadmap_phases"].append({
                                "phase": cols[0],
                                "focus": cols[1],
                                "objectives": cols[2]
                            })

            elif "prioritized work plan" in text:
                nxt = h.find_next(["ol", "ul"])
                if nxt:
                    data["work_plan_tasks"] = [
                        li.get_text(strip=True) for li in nxt.find_all("li")
                    ]

            elif "task complexity & effort" in text:
                table = h.find_next("table")
                if table:
                    rows = table.find_all("tr")
                    for row in rows[1:]:
                        cols = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                        if len(cols) >= 4:
                            data["complexity_matrix"].append({
                                "task": cols[0],
                                "category": cols[1],
                                "complexity": cols[2],
                                "effort": cols[3]
                            })

            elif "identified code transformations" in text:
                nxt = h.find_next(["ul", "ol", "table", "p"])
                if nxt and nxt.name in ["ul", "ol"]:
                    data["code_transformations"] = [
                        li.get_text(strip=True) for li in nxt.find_all("li")
                    ]

            elif "data layer code analysis" in text or "data layer changes" in text:
                nxt = h.find_next(["ul", "ol", "p"])
                if nxt and nxt.name in ["ul", "ol"]:
                    data["data_layer_impacts"] = [
                        li.get_text(strip=True) for li in nxt.find_all("li")
                    ]
                elif nxt:
                    data["data_layer_impacts"] = [nxt.get_text(strip=True)]

        body_text = soup.get_text(separator=" ")
        file_matches = set(re.findall(r'[a-zA-Z0-9_/-]+\.(?:java|cs|py|xml|gradle|properties|yml|yaml)', body_text))
        data["flagged_files"] = sorted(list(file_matches))
    else:
        title_m = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
        if title_m:
            data["title"] = title_m.group(1).strip()
        data["executive_summary"] = "Parsed via regex fallback."

    return data


def parse_graphify_graph(graph_path: Path) -> Dict[str, Any]:
    """Parse Graphify graph.json and calculate component modules and central dependency hubs."""
    if not graph_path.exists():
        raise FileNotFoundError(f"Graph file not found: {graph_path}")

    # If a directory was provided, resolve graphify-out/graph.json
    if graph_path.is_dir():
        cand = graph_path / "graphify-out" / "graph.json"
        if cand.exists():
            graph_path = cand
        else:
            cand2 = graph_path / "graph.json"
            if cand2.exists():
                graph_path = cand2
            else:
                raise FileNotFoundError(f"Could not find graph.json in {graph_path}")

    with open(graph_path, "r", encoding="utf-8") as f:
        raw_graph = json.load(f)

    nodes = raw_graph.get("nodes", [])
    links = raw_graph.get("links", [])

    node_by_id: Dict[str, Dict[str, Any]] = {n["id"]: n for n in nodes if "id" in n}

    # Connection and caller/dependency calculations
    in_degree: Dict[str, int] = defaultdict(int)
    out_degree: Dict[str, int] = defaultdict(int)
    total_degree: Dict[str, int] = defaultdict(int)

    # Component module grouping (functional subsystems)
    communities: Dict[int, Dict[str, Any]] = {}
    node_to_comm: Dict[str, int] = {}

    for n in nodes:
        nid = n["id"]
        comm_id = n.get("community", 0)
        comm_name = n.get("community_name", f"Module {comm_id}")
        node_to_comm[nid] = comm_id

        if comm_id not in communities:
            communities[comm_id] = {
                "id": comm_id,
                "name": comm_name,
                "nodes": [],
                "files": set(),
                "central_hubs": [],
                "god_nodes": [],  # Backward-compatible alias
                "in_degree": 0,
                "out_degree": 0,
            }
        communities[comm_id]["nodes"].append(n)
        if "source_file" in n and n["source_file"]:
            communities[comm_id]["files"].add(n["source_file"])

    # Connection analysis between modules
    inter_comm_edges: Dict[Tuple[int, int], int] = defaultdict(int)

    for link in links:
        src = link.get("source")
        tgt = link.get("target")
        if src in node_by_id and tgt in node_by_id:
            out_degree[src] += 1
            in_degree[tgt] += 1
            total_degree[src] += 1
            total_degree[tgt] += 1

            c_src = node_to_comm.get(src, -1)
            c_tgt = node_to_comm.get(tgt, -1)
            if c_src != -1 and c_tgt != -1 and c_src != c_tgt:
                inter_comm_edges[(c_src, c_tgt)] += 1
                communities[c_src]["out_degree"] += 1
                communities[c_tgt]["in_degree"] += 1

    # Central Dependency Hubs: classes with highest number of incoming/outgoing connections (high blast radius)
    sorted_nodes = sorted(
        nodes,
        key=lambda n: total_degree[n["id"]],
        reverse=True
    )
    central_hubs = [
        {
            "id": n["id"],
            "label": n.get("label", n["id"]),
            "community_id": n.get("community", 0),
            "community_name": n.get("community_name", "Unknown"),
            "module_name": n.get("community_name", "Unknown"),
            "source_file": n.get("source_file", ""),
            "degree": total_degree[n["id"]],
            "total_connections": total_degree[n["id"]],
            "in_degree": in_degree[n["id"]],
            "inbound_callers": in_degree[n["id"]],
            "out_degree": out_degree[n["id"]],
            "outbound_dependencies": out_degree[n["id"]],
        }
        for n in sorted_nodes[:15]
        if total_degree[n["id"]] > 5
    ]

    # Assign central hubs to their component modules
    for hub in central_hubs:
        cid = hub["community_id"]
        if cid in communities:
            communities[cid]["central_hubs"].append(hub["label"])
            communities[cid]["god_nodes"].append(hub["label"])

    # Convert sets to sorted lists for JSON serialization
    for c in communities.values():
        c["files"] = sorted(list(c["files"]))

    return {
        "total_nodes": len(nodes),
        "total_edges": len(links),
        "central_hubs": central_hubs,
        "god_nodes": central_hubs,  # Backward-compatible alias
        "component_modules": communities,
        "communities": communities,  # Backward-compatible alias
        "inter_module_edges": {f"{k[0]}->{k[1]}": v for k, v in inter_comm_edges.items()},
        "inter_comm_edges": {f"{k[0]}->{k[1]}": v for k, v in inter_comm_edges.items()}
    }


def synthesize_migration_slices(
    codmod_data: Dict[str, Any],
    graph_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Correlate CodMod recommendations with component modules and build dependency-ordered slices."""
    modules = graph_data.get("component_modules", graph_data.get("communities", {}))
    central_hubs = graph_data.get("central_hubs", graph_data.get("god_nodes", []))

    hub_labels = {h["label"] for h in central_hubs}

    # Partition modules into logical layers based on name, contents, and connection degree
    leaf_modules = []
    core_modules = []
    central_hub_modules = []
    ingress_modules = []
    infra_modules = []

    for cid, mod in modules.items():
        name_lower = mod["name"].lower()

        # Infrastructure / Build / DB schema
        if any(term in name_lower for term in ["wrapper", "schema", "environment", "ci/cd", "branding", "system configuration"]):
            infra_modules.append(mod)
        # Entry surfaces / MVC / Ingress / UI
        elif any(term in name_lower for term in ["controller", "mvc", "thymeleaf", "endpoint", "ui"]):
            ingress_modules.append(mod)
        # Monolith anchors / Central Hubs with high coupling
        elif len(mod["central_hubs"]) >= 2 or any(lbl in hub_labels for lbl in mod["central_hubs"]):
            central_hub_modules.append(mod)
        # Leaf vs Core based on outbound dependencies
        elif mod["out_degree"] <= 2:
            leaf_modules.append(mod)
        else:
            core_modules.append(mod)

    # If categories are empty, gracefully distribute
    if not core_modules and leaf_modules:
        core_modules = leaf_modules[len(leaf_modules)//2:]
        leaf_modules = leaf_modules[:len(leaf_modules)//2]

    # Build vertical slices
    slices = [
        {
            "slice_id": "Slice 0",
            "name": "Build & Runtime Foundation",
            "execution_order": 0,
            "nature": "[Serial]",
            "description": "Establish target runtime toolchains (JDK 21 / .NET 9), modernize build plugins, configure CI wrappers, and set up baseline test harnesses.",
            "component_modules": [m["name"] for m in infra_modules],
            "communities": [m["name"] for m in infra_modules],
            "module_ids": [m["id"] for m in infra_modules],
            "community_ids": [m["id"] for m in infra_modules],
            "codmod_tasks": [
                t for t in codmod_data.get("complexity_matrix", [])
                if any(w in t["task"].lower() or w in t["category"].lower() for w in ["build", "compiler", "wrapper", "target", "plugin"])
            ] or [
                {"task": "Toolchain Upgrade & Compiler Target Properties", "complexity": "Low", "effort": "Small"},
                {"task": "CI Pipeline & Build Wrapper Alignment", "complexity": "Low", "effort": "Small"}
            ],
            "central_hubs_addressed": [],
            "god_nodes_addressed": [],
            "verification_strategy": "Compile clean build and verify unit test harness passes on target runtime."
        },
        {
            "slice_id": "Slice 1",
            "name": "Standalone Leaf Modules & Lookup Models",
            "execution_order": 1,
            "nature": "[Parallel]",
            "description": "Modernize low-coupling leaf modules, domain enums, dictionary models, and standalone lookup entities that have zero or minimal external dependencies.",
            "component_modules": [m["name"] for m in leaf_modules],
            "communities": [m["name"] for m in leaf_modules],
            "module_ids": [m["id"] for m in leaf_modules],
            "community_ids": [m["id"] for m in leaf_modules],
            "codmod_tasks": [
                t for t in codmod_data.get("complexity_matrix", [])
                if any(w in t["task"].lower() for w in ["model", "entity", "annotation", "collection"])
            ] or [
                {"task": "Domain Model Modernization (Records, Value Objects)", "complexity": "Low", "effort": "Small"}
            ],
            "central_hubs_addressed": [],
            "god_nodes_addressed": [],
            "verification_strategy": "Unit tests for entity serialization, immutability, and validation constraints."
        },
        {
            "slice_id": "Slice 2",
            "name": "Core Domain Repositories & Data Layer",
            "execution_order": 2,
            "nature": "[Serial]",
            "description": "Migrate core transactional domain services, repositories, and ORM persistence mappings. Update JPA annotations (javax to jakarta) and database driver configurations.",
            "component_modules": [m["name"] for m in core_modules],
            "communities": [m["name"] for m in core_modules],
            "module_ids": [m["id"] for m in core_modules],
            "community_ids": [m["id"] for m in core_modules],
            "codmod_tasks": [
                t for t in codmod_data.get("complexity_matrix", [])
                if any(w in t["task"].lower() or w in t["category"].lower() for w in ["data", "database", "repository", "jpa", "driver"])
            ] or [
                {"task": "Jakarta Persistence & Spring Data Upgrade", "complexity": "Medium", "effort": "Medium"},
                {"task": "Database Connection Pool & Dialect Modernization", "complexity": "Medium", "effort": "Small"}
            ],
            "central_hubs_addressed": [h["label"] for h in central_hubs if h["community_id"] in [m["id"] for m in core_modules]],
            "god_nodes_addressed": [h["label"] for h in central_hubs if h["community_id"] in [m["id"] for m in core_modules]],
            "verification_strategy": "Integration tests executing real database queries and transaction boundaries."
        },
        {
            "slice_id": "Slice 3",
            "name": "Central Dependency Hubs & Monolith Decoupling",
            "execution_order": 3,
            "nature": "[Serial]",
            "description": "Encapsulate highly coupled central classes with interface facades or adapters to prevent changes from rippling across the codebase.",
            "component_modules": [m["name"] for m in central_hub_modules],
            "communities": [m["name"] for m in central_hub_modules],
            "module_ids": [m["id"] for m in central_hub_modules],
            "community_ids": [m["id"] for m in central_hub_modules],
            "codmod_tasks": [
                t for t in codmod_data.get("complexity_matrix", [])
                if any(w in t["task"].lower() for w in ["refactoring", "virtual threads", "service", "api remediation"])
            ] or [
                {"task": "Central Hub Decoupling & Interface Segregation", "complexity": "High", "effort": "Medium"}
            ],
            "central_hubs_addressed": [h["label"] for h in central_hubs if h["community_id"] in [m["id"] for m in central_hub_modules]],
            "god_nodes_addressed": [h["label"] for h in central_hubs if h["community_id"] in [m["id"] for m in central_hub_modules]],
            "verification_strategy": "Contract verification and synthetic traffic replay with @runtime-parity-verifier."
        },
        {
            "slice_id": "Slice 4",
            "name": "Ingress Controllers & Edge Adapters",
            "execution_order": 4,
            "nature": "[Parallel]",
            "description": "Modernize MVC controllers, REST endpoints, request formatters, and web templates. Upgrade web framework filters and validation binders.",
            "component_modules": [m["name"] for m in ingress_modules],
            "communities": [m["name"] for m in ingress_modules],
            "module_ids": [m["id"] for m in ingress_modules],
            "community_ids": [m["id"] for m in ingress_modules],
            "codmod_tasks": [
                t for t in codmod_data.get("complexity_matrix", [])
                if any(w in t["task"].lower() or w in t["category"].lower() for w in ["controller", "web", "template", "mvc", "endpoint"])
            ] or [
                {"task": "Spring MVC Controller & Validation Binder Modernization", "complexity": "Medium", "effort": "Medium"}
            ],
            "central_hubs_addressed": [h["label"] for h in central_hubs if h["community_id"] in [m["id"] for m in ingress_modules]],
            "god_nodes_addressed": [h["label"] for h in central_hubs if h["community_id"] in [m["id"] for m in ingress_modules]],
            "verification_strategy": "End-to-end HTTP endpoint tests verifying status codes and JSON/HTML payloads."
        },
        {
            "slice_id": "Slice 5",
            "name": "Target Cloud Hardening & Observability",
            "execution_order": 5,
            "nature": "[Serial]",
            "description": "Prepare the modernized service for Cloud Run / GKE deployment: container optimization, Cloud SQL pooling, Secret Manager, health probes, and OpenTelemetry.",
            "component_modules": ["Cloud Deployment & SRE"],
            "communities": ["Cloud Deployment & SRE"],
            "module_ids": [],
            "community_ids": [],
            "codmod_tasks": [
                {"task": "Containerfile Multi-Stage Build & Distroless Tuning", "complexity": "Low", "effort": "Small"},
                {"task": "Cloud Run Health Probes & Graceful Shutdown", "complexity": "Low", "effort": "Small"},
                {"task": "GCP Secret Manager & Cloud SQL Auth Proxy Integration", "complexity": "Medium", "effort": "Small"}
            ],
            "central_hubs_addressed": [],
            "god_nodes_addressed": [],
            "verification_strategy": "Container smoke run and simulated cloud environment health probe audit."
        }
    ]

    return {
        "application_title": codmod_data.get("title", "Modernized Application"),
        "total_component_modules": len(modules),
        "total_communities": len(modules),  # Backward-compatible alias
        "total_central_dependency_hubs": len(central_hubs),
        "total_god_nodes": len(central_hubs),  # Backward-compatible alias
        "central_dependency_hubs": central_hubs,
        "god_nodes": central_hubs,  # Backward-compatible alias
        "slices": slices
    }


def generate_plan_markdown(matrix: Dict[str, Any], output_path: Path) -> str:
    """Generate 05_PLAN.md content using clear, software-engineering focused terminology."""
    hubs = matrix.get("central_dependency_hubs", matrix.get("god_nodes", []))
    total_mods = matrix.get("total_component_modules", matrix.get("total_communities", 0))
    total_hubs = matrix.get("total_central_dependency_hubs", matrix.get("total_god_nodes", len(hubs)))

    lines = [
        f"# 🗺️ Modernization Implementation Plan: {matrix['application_title']}",
        "",
        "> **Generated by `bean-grinder` (CodMod + Graphify Modernization Engine)**",
        "",
        "## 📊 Architectural Structure Overview",
        f"- **Detected Component Modules / Subsystems:** {total_mods}",
        f"- **Central Dependency Hubs (High Blast Radius):** {total_hubs}",
        "",
        "> [!NOTE]",
        "> **Architecture Concepts Guide:**",
        "> - **Component Modules / Subsystems:** Cohesive groups of classes and configurations that work together as a functional unit (e.g., Domain Entities, JPA Repositories, MVC Controllers).",
        "> - **Central Dependency Hubs:** Highly coupled classes that many other parts of the application depend on. Modifying these has a wide blast radius, so they are encapsulated with interfaces/facades.",
        "> - **Dependency Order:** Migration slices are ordered so foundational tools come first, followed by independent leaf modules, then core data/domain, central hubs, and finally controllers.",
        "",
        "### ⚠️ Central Dependency Hubs (Highest Blast Radius)",
        "| Rank | Core Class / Component | Total Connections | Callers (Inbound) / Dependencies (Outbound) | Component Module | Modernization Action |",
        "| :---: | :--- | :---: | :---: | :--- | :--- |"
    ]

    for idx, hub in enumerate(hubs[:8], 1):
        deg = hub.get("total_connections", hub.get("degree", 0))
        in_deg = hub.get("inbound_callers", hub.get("in_degree", 0))
        out_deg = hub.get("outbound_dependencies", hub.get("out_degree", 0))
        mod_name = hub.get("module_name", hub.get("community_name", "Unknown"))
        lines.append(
            f"| {idx} | `{hub['label']}` | {deg} | {in_deg} callers / {out_deg} dependencies | {mod_name} | Encapsulate with Interface / Facade |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 🍰 Vertical Migration Slices (Ordered by Dependency Flow)",
        ""
    ])

    for s in matrix["slices"]:
        mods = s.get("component_modules", s.get("communities", []))
        hubs_addressed = s.get("central_hubs_addressed", s.get("god_nodes_addressed", []))

        lines.extend([
            f"### {s['slice_id']}: {s['name']} `{s['nature']}`",
            f"**Objective:** {s['description']}",
            "",
            "**Component Modules in Slice:**",
        ])
        for cname in mods[:6]:
            lines.append(f"- {cname}")
        if len(mods) > 6:
            lines.append(f"- *...and {len(mods) - 6} more*")

        if hubs_addressed:
            lines.append("")
            lines.append(f"**Central Hubs Decoupled in this Slice:** {', '.join(f'`{g}`' for g in hubs_addressed)}")

        lines.extend([
            "",
            "**Associated Modernization Tasks:**",
            "| Task Area | Complexity | Effort |",
            "| :--- | :---: | :---: |"
        ])
        for t in s["codmod_tasks"][:5]:
            lines.append(f"| {t.get('task', 'Modernize component')} | {t.get('complexity', 'Medium')} | {t.get('effort', 'Small')} |")

        lines.extend([
            "",
            f"**Verification:** {s['verification_strategy']}",
            "",
            "---",
            ""
        ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Digest CodMod assessment reports and Graphify knowledge graphs into vertical migration slices."
    )
    parser.add_argument(
        "--report",
        required=True,
        type=Path,
        help="Path to modernization_report.html or codmod assessment JSON."
    )
    parser.add_argument(
        "--graph",
        required=True,
        type=Path,
        help="Path to graphify-out/graph.json or directory containing it."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./migration_slices"),
        help="Target directory to emit migration_matrix.json and 05_PLAN.md."
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print summary scorecard to stdout without writing files."
    )

    args = parser.parse_args()

    # Parse inputs
    print(f"⚙️  Ingesting CodMod Report: {args.report}")
    codmod_data = parse_codmod_report(args.report)

    print(f"🕸️  Ingesting Graphify Knowledge Graph: {args.graph}")
    graph_data = parse_graphify_graph(args.graph)

    # Synthesize slices
    print("🔄 Synthesizing dependency-ordered vertical slices...")
    matrix = synthesize_migration_slices(codmod_data, graph_data)

    # Print summary scorecard
    total_mods = matrix.get("total_component_modules", matrix.get("total_communities", 0))
    total_hubs = matrix.get("total_central_dependency_hubs", matrix.get("total_god_nodes", 0))
    hubs = matrix.get("central_dependency_hubs", matrix.get("god_nodes", []))

    print("\n" + "=" * 60)
    print(f"📊 MODERNIZATION SCORECARD: {matrix['application_title']}")
    print("=" * 60)
    print(f"Component Modules Identified: {total_mods}")
    print(f"Central Dependency Hubs:      {total_hubs} (High blast-radius classes)")
    print("\nTop Central Dependency Hubs (Highest Coupling):")
    for hub in hubs[:5]:
        deg = hub.get("total_connections", hub.get("degree", 0))
        in_deg = hub.get("inbound_callers", hub.get("in_degree", 0))
        out_deg = hub.get("outbound_dependencies", hub.get("out_degree", 0))
        mod_name = hub.get("module_name", hub.get("community_name", "Unknown"))
        print(f"  • {hub['label']:<24} ({deg:>2} connections: {in_deg:>2} callers, {out_deg:>2} deps) - {mod_name}")

    print("\nPlanned Vertical Slices (Ordered by Dependency):")
    for s in matrix["slices"]:
        print(f"  [{s['execution_order']}] {s['slice_id']}: {s['name']} ({s['nature']})")
    print("=" * 60 + "\n")

    if not args.summary_only:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        matrix_path = args.output_dir / "migration_matrix.json"
        plan_path = args.output_dir / "05_PLAN.md"

        with open(matrix_path, "w", encoding="utf-8") as f:
            json.dump(matrix, f, indent=2, ensure_ascii=False)
        print(f"✅ Emitted matrix: {matrix_path}")

        plan_md = generate_plan_markdown(matrix, plan_path)
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(plan_md)
        print(f"✅ Emitted plan:   {plan_path}")


if __name__ == "__main__":
    main()

