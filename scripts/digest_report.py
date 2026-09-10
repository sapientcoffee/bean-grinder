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


def parse_markdown_table_rows(content: str) -> List[Dict[str, str]]:
    """Parse the first markdown table in content into a list of row dicts."""
    rows = []
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    headers: List[str] = []
    in_table = False

    for line in lines:
        if line.startswith("|") and line.endswith("|"):
            parts = [c.strip() for c in line[1:-1].split("|")]
            if not in_table:
                headers = parts
                in_table = True
            elif all(re.match(r"^:?-+:?$", p) for p in parts):
                continue
            else:
                row_dict = {}
                for idx, h in enumerate(headers):
                    val = parts[idx] if idx < len(parts) else ""
                    clean_h = re.sub(r"[^a-zA-Z0-9_]", "_", h.lower().strip("_"))
                    row_dict[clean_h] = val
                rows.append(row_dict)
        elif in_table and rows:
            break
    return rows


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
    graph_data: Dict[str, Any],
    seams_data: Optional[List[Dict[str, Any]]] = None,
    specs_data: Optional[List[Dict[str, Any]]] = None,
    migration_data: Optional[List[Dict[str, Any]]] = None,
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

    # Build 7 Rs portfolio rationalization matrix
    portfolio_7rs = []
    for cid, mod in modules.items():
        name = mod["name"]
        in_deg = mod.get("in_degree", 0)
        out_deg = mod.get("out_degree", 0)
        hubs_in_mod = mod.get("central_hubs", [])
        name_lower = name.lower()

        if in_deg == 0 and out_deg == 0 and len(mod.get("nodes", [])) <= 1:
            strategy = "Retire"
            rationale = "Zero inbound callers and outbound dependencies detected. Candidate dead code."
        elif any(k in name_lower for k in ["wrapper", "build", "ci", "env", "configuration"]):
            strategy = "Replatform"
            rationale = "Target runtime upgrade (e.g. Java 21 / .NET 9 containerization and CI modernization)."
        elif len(hubs_in_mod) > 0 or in_deg >= 10:
            strategy = "Refactor / Rearchitect"
            rationale = "High blast radius and coupling. Extract bounded context via Anti-Corruption Layer and Branch by Abstraction."
        else:
            strategy = "Refactor"
            rationale = "Standardize on modern idiomatic patterns, non-blocking I/O, and domain validation."

        portfolio_7rs.append({
            "module_id": cid,
            "module_name": name,
            "strategy": strategy,
            "inbound_callers": in_deg,
            "outbound_dependencies": out_deg,
            "central_hubs": hubs_in_mod,
            "rationale": rationale
        })

    # Build Feathers' Seams & Decoupling inventory
    # Build Feathers' Seams & Decoupling inventory
    if seams_data:
        empirical_seams = []
        for row in seams_data:
            target = row.get("target_class") or row.get("target") or row.get("target_component")
            if target:
                empirical_seams.append({
                    "target": target,
                    "type": row.get("seam_type", "Object Seam"),
                    "technique": row.get("decoupling_pattern") or row.get("technique", "Branch by Abstraction"),
                    "sprout_opportunity": row.get("sprout_opportunity") or row.get("intervention_opportunity", "Introduce Sprout Method/Class"),
                    "blast_radius": row.get("blast_radius", "Medium coupling")
                })
        seams_inventory = empirical_seams if empirical_seams else []
    else:
        seams_inventory = []
        for hub in central_hubs[:10]:
            seams_inventory.append({
                "target": hub["label"],
                "type": "Object Seam",
                "technique": "Branch by Abstraction / Interface Extraction",
                "sprout_opportunity": "Introduce Sprout Method/Class for new domain validation to prevent modifying legacy methods.",
                "blast_radius": f"{hub.get('total_connections', hub.get('degree', 0))} connections ({hub.get('inbound_callers', hub.get('in_degree', 0))} callers)"
            })
        for m in infra_modules[:3]:
            seams_inventory.append({
                "target": m["name"],
                "type": "Link Seam",
                "technique": "Build-Time Dependency Substitution / Compiler Target Upgrade",
                "sprout_opportunity": "Isolate toolchain plugins without altering production source files.",
                "blast_radius": f"{m.get('in_degree', 0)} callers"
            })

    if migration_data:
        empirical_7rs = []
        for row in migration_data:
            mod_name = row.get("subsystem___library") or row.get("subsystem") or row.get("component_module")
            if mod_name:
                empirical_7rs.append({
                    "module_name": mod_name,
                    "strategy": row.get("7_rs_strategy") or row.get("strategy", "Refactor"),
                    "inbound_callers": 0,
                    "outbound_dependencies": 0,
                    "central_hubs": [],
                    "rationale": row.get("rationale", ""),
                    "target_service": row.get("target_cloud_service", "Cloud Run"),
                })
        if empirical_7rs:
            portfolio_7rs = empirical_7rs

    # Build Data Modernization & Outbox CDC Architecture
    data_architecture = {
        "strategy": "Transactional Outbox Pattern with Log-Based Change Data Capture (CDC)",
        "forbidden_patterns": ["Application-level dual writes", "Two-Phase Commit (2PC) / XA distributed locks"],
        "cdc_engine": "Debezium log-tailing (WAL/binlog) streaming to Kafka",
        "coordination": "Distributed Sagas with idempotent receivers and semantic compensation",
        "cutover_phases": [
            {"phase": "Phase A", "name": "Initial Snapshot & WAL Tailing", "description": "Stream historical tables to modern data store while tailing live database changes."},
            {"phase": "Phase B", "name": "Monolith Authoritative with CDC Sync", "description": "Legacy system remains primary. CDC replicates mutations to modernized schema with lag monitoring."},
            {"phase": "Phase C", "name": "Target Authoritative with Reverse-CDC", "description": "Switch primary write traffic to modern microservice; reverse CDC streams updates back to legacy for instant rollback safety."},
            {"phase": "Phase D", "name": "Decommission Synchronization", "description": "Sever CDC pipelines and archive legacy datastore once stability KPIs are satisfied."}
        ]
    }

    # Build Mikado Dependency Tree
    mikado_tree = {
        "root_goal": f"Modernize {codmod_data.get('title', 'Application')} to Cloud Run Architecture",
        "refactoring_rule": "On compile/test breakages, immediately execute git reset --hard, log prerequisite, and solve leaf prerequisites first.",
        "prerequisites": [
            {"level": 0, "node": "Slice 0: Runtime Toolchain & CI Wrappers", "status": "Ready", "type": "Leaf"},
            {"level": 1, "node": "Slice 1: Leaf Domain Models & DTOs", "status": "Blocked by Slice 0", "type": "Leaf"},
            {"level": 2, "node": "Slice 2: Core Domain Repositories & Outbox CDC", "status": "Blocked by Slice 1", "type": "Branch"},
            {"level": 3, "node": "Slice 3: Central Dependency Hubs (ACLs & Abstractions)", "status": "Blocked by Slice 2", "type": "Branch"},
            {"level": 4, "node": "Slice 4: Ingress Controllers & Strangler Interception", "status": "Blocked by Slice 3", "type": "Branch"},
            {"level": 5, "node": "Slice 5: Cloud Run Hardening & Production SRE", "status": "Blocked by Slice 4", "type": "Root"}
        ]
    }

    result = {
        "application_title": codmod_data.get("title", "Modernized Application"),
        "total_component_modules": len(modules),
        "total_communities": len(modules),  # Backward-compatible alias
        "total_central_dependency_hubs": len(central_hubs),
        "total_god_nodes": len(central_hubs),  # Backward-compatible alias
        "total_connections": graph_data.get("total_edges", 0),
        "total_nodes": graph_data.get("total_nodes", 0),
        "component_modules": modules,
        "communities": modules,  # Backward-compatible alias
        "central_dependency_hubs": central_hubs,
        "god_nodes": central_hubs,  # Backward-compatible alias
        "slices": slices,
        "portfolio_7rs": portfolio_7rs,
        "seams_inventory": seams_inventory,
        "data_architecture": data_architecture,
        "mikado_tree": mikado_tree
    }

    if specs_data:
        ambiguous = [
            s for s in specs_data
            if "AMBIGUOUS" in s.get("review_status", "").upper()
            or "AMBIGUOUS" in s.get("domain_rule_summary", "").upper()
        ]
        result["recovered_invariants"] = specs_data
        result["ambiguous_specs_count"] = len(ambiguous)
        result["ambiguous_specs"] = ambiguous

    return result


def generate_plan_markdown(matrix: Dict[str, Any], output_path: Path) -> str:
    """Generate 05_PLAN.md content using clear, software-engineering focused terminology."""
    hubs = matrix.get("central_dependency_hubs", matrix.get("god_nodes", []))
    total_mods = matrix.get("total_component_modules", matrix.get("total_communities", 0))
    total_hubs = matrix.get("total_central_dependency_hubs", matrix.get("total_god_nodes", len(hubs)))
    portfolio = matrix.get("portfolio_7rs", [])
    seams = matrix.get("seams_inventory", [])
    data_arch = matrix.get("data_architecture", {})
    mikado = matrix.get("mikado_tree", {})

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

    if portfolio:
        lines.extend([
            "",
            "---",
            "",
            "## 🏛️ 7 Rs Portfolio Rationalization Matrix",
            "| Component Module | Strategy | Inbound / Outbound | Rationale |",
            "| :--- | :---: | :---: | :--- |"
        ])
        for p in portfolio[:10]:
            lines.append(
                f"| **{p['module_name']}** | `{p['strategy']}` | {p['inbound_callers']} callers / {p['outbound_dependencies']} deps | {p['rationale']} |"
            )

    if seams:
        lines.extend([
            "",
            "---",
            "",
            "## ✂️ Michael Feathers' Seams & Decoupling Boundaries",
            "| Target Component | Seam Type | Decoupling Technique | Sprout / Wrap Intervention Opportunity |",
            "| :--- | :---: | :--- | :--- |"
        ])
        for sm in seams[:8]:
            lines.append(
                f"| `{sm['target']}` | **{sm['type']}** | {sm['technique']} | {sm['sprout_opportunity']} |"
            )

    ambiguous_specs = matrix.get("ambiguous_specs", [])
    if ambiguous_specs:
        lines.extend([
            "",
            "---",
            "",
            "## ⚠️ Ambiguous Specifications Requiring Human Approval (HITL Gate)",
            "> The following legacy business invariants require clarification before code refactoring:",
            "",
            "| Requirement ID | Domain Rule Summary | Source Code Location | Preconditions / Postconditions | Review Status |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ])
        for amb in ambiguous_specs[:8]:
            req_id = amb.get("requirement_id", "REQ-?")
            rule = amb.get("domain_rule_summary", "Unspecified rule")
            loc = amb.get("source_code_location", "Unknown")
            cond = f"{amb.get('preconditions', '')} -> {amb.get('postconditions', '')}".strip(" ->")
            stat = amb.get("review_status", "[AMBIGUOUS]")
            lines.append(f"| `{req_id}` | {rule} | `{loc}` | {cond} | **{stat}** |")

    if data_arch:
        lines.extend([
            "",
            "---",
            "",
            "## 🔄 Data Modernization & State Integrity (Transactional Outbox + CDC)",
            f"> **Strategy:** {data_arch.get('strategy')}",
            f"> **Forbidden Anti-Patterns:** {', '.join(data_arch.get('forbidden_patterns', []))}",
            f"> **CDC Engine:** {data_arch.get('cdc_engine')}",
            "",
            "### 4-Phase Data Cutover Protocol:",
            "| Phase | Name | Cutover Execution Protocol |",
            "| :---: | :--- | :--- |"
        ])
        for cp in data_arch.get("cutover_phases", []):
            lines.append(f"| **{cp['phase']}** | {cp['name']} | {cp['description']} |")

    if mikado and mikado.get("prerequisites"):
        lines.extend([
            "",
            "---",
            "",
            "## 🌳 Mikado Method Dependency Graph (Leaf-to-Root Execution Flow)",
            f"> **Root Modernization Objective:** {mikado.get('root_goal')}",
            f"> **Safety Constraint:** {mikado.get('refactoring_rule')}",
            "",
            "```mermaid",
            "graph BT",
            f"  R[\"{mikado.get('root_goal')}\"]"
        ])
        for idx, prereq in enumerate(mikado.get("prerequisites", [])):
            lines.append(f"  P{idx}[\"{prereq['node']}\"] --> R")
        lines.extend([
            "```",
            ""
        ])

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

    lines.extend([
        "## 🛡️ Adversarial Review & Hardening Audit",
        "- **Audit Status:** `PENDING_REVIEW`",
        "- **Reviewer Swarm:** `@reviewer-exec`, `@reviewer-engineer`, `@reviewer-architect`, `@reviewer-pm`",
        "- **Arbiter:** `@review-arbiter`",
        "- *(Execute review loop via `python3 scripts/review_loop.py --plan-dir <plan_dir>` or `rewrite` Step 5.5)*",
        ""
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Digest CodMod assessment reports and Graphify knowledge graphs into vertical migration slices."
    )
    parser.add_argument(
        "--from-run",
        type=str,
        help="Path or name of existing assessment run (e.g. 'latest' or 'assessments/runs/20260909_120000') to auto-discover reports from."
    )
    parser.add_argument(
        "--report",
        required=False,
        type=Path,
        help="Path to modernization_report.html or codmod assessment JSON."
    )
    parser.add_argument(
        "--graph",
        required=False,
        type=Path,
        help="Path to graphify-out/graph.json or directory containing it."
    )
    parser.add_argument(
        "--seams-report",
        type=Path,
        help="Path to seam scout markdown report (e.g. 01_discovery/seam_findings.md)."
    )
    parser.add_argument(
        "--specs-report",
        type=Path,
        help="Path to spec recovery markdown report (e.g. 01_discovery/spec_invariants.md)."
    )
    parser.add_argument(
        "--migration-report",
        type=Path,
        help="Path to migration scout markdown report (e.g. 01_discovery/migration_strategy.md)."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Target directory to emit migration_matrix.json, 05_PLAN.md, and modernization_dashboard.html."
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print summary scorecard to stdout without writing files."
    )
    parser.add_argument(
        "--graph-html",
        type=Path,
        help="Path to graphify-out/graph.html for interactive visualizer embedding."
    )
    parser.add_argument(
        "--graph-report",
        type=Path,
        help="Path to graphify-out/GRAPH_REPORT.md for topology breakdown embedding."
    )
    parser.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Disable automatic generation of modernization_dashboard.html."
    )
    parser.add_argument(
        "--no-mirror",
        action="store_true",
        help="Disable dual-write brain mirroring to 00_visual-dashboard.html."
    )
    parser.add_argument(
        "--brain-dir",
        type=str,
        help="Explicit conversation brain directory to mirror artifacts to."
    )

    args = parser.parse_args()

    # Handle --from-run resolution
    if args.from_run:
        target = args.from_run
        base_dir = Path("assessments")
        runs_dir = base_dir / "runs"
        run_dir = None

        if target == "latest":
            latest_link = base_dir / "latest"
            if latest_link.exists() and latest_link.is_symlink():
                run_dir = latest_link.resolve()
            elif runs_dir.exists():
                entries = [d for d in runs_dir.iterdir() if d.is_dir() and not d.name.startswith(".") and d.name != "latest"]
                if entries:
                    entries.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    run_dir = entries[0].resolve()
        else:
            p = Path(target).resolve()
            if p.exists() and p.is_dir():
                run_dir = p
            elif (runs_dir / target).exists():
                run_dir = (runs_dir / target).resolve()

        if not run_dir or not run_dir.exists():
            sys.stderr.write(f"❌ Could not resolve assessment run for: '{target}'\n")
            sys.exit(1)

        disc_dir = run_dir / "01_discovery"
        search_dirs = [disc_dir, run_dir]

        if not args.report:
            for d in search_dirs:
                for name in ["codmod_assessment_report.html", "modernization_report.html", "codmod_report.html", "codmod_assessment.json"]:
                    if (d / name).exists():
                        args.report = d / name
                        break
                if args.report:
                    break

        if not args.graph:
            for d in search_dirs:
                for name in ["graphify_ast_graph.json", "graph.json", "graphify-out/graph.json"]:
                    if (d / name).exists():
                        args.graph = d / name
                        break
                if args.graph:
                    break

        if not args.graph_html:
            for d in search_dirs:
                for name in ["graphify_ast_interactive.html", "graph.html", "graphify-out/graph.html"]:
                    if (d / name).exists():
                        args.graph_html = d / name
                        break
                if args.graph_html:
                    break

        if not args.graph_report:
            for d in search_dirs:
                for name in ["graphify_architecture_report.md", "GRAPH_REPORT.md", "graphify-out/GRAPH_REPORT.md"]:
                    if (d / name).exists():
                        args.graph_report = d / name
                        break
                if args.graph_report:
                    break

        if not args.seams_report:
            for d in search_dirs:
                for name in ["seam_findings.md", "seams.md"]:
                    if (d / name).exists():
                        args.seams_report = d / name
                        break
                if args.seams_report:
                    break

        if not args.specs_report:
            for d in search_dirs:
                for name in ["spec_invariants.md", "specs.md"]:
                    if (d / name).exists():
                        args.specs_report = d / name
                        break
                if args.specs_report:
                    break

        if not args.migration_report:
            for d in search_dirs:
                for name in ["migration_strategy.md"]:
                    if (d / name).exists():
                        args.migration_report = d / name
                        break
                if args.migration_report:
                    break

        if not args.output_dir:
            args.output_dir = run_dir

    if not args.report or not args.graph:
        parser.error("Both --report and --graph are required unless --from-run is specified with an existing run.")

    if not args.output_dir:
        args.output_dir = Path("./migration_slices")

    # Ingest scout reports if provided
    seams_data = None
    if args.seams_report and args.seams_report.exists():
        try:
            seams_data = parse_markdown_table_rows(args.seams_report.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Warning: Could not parse seams report: {e}")

    specs_data = None
    if args.specs_report and args.specs_report.exists():
        try:
            specs_data = parse_markdown_table_rows(args.specs_report.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Warning: Could not parse specs report: {e}")

    migration_data = None
    if args.migration_report and args.migration_report.exists():
        try:
            migration_data = parse_markdown_table_rows(args.migration_report.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Warning: Could not parse migration report: {e}")

    # Parse inputs
    print(f"⚙️  Ingesting CodMod Report: {args.report}")
    codmod_data = parse_codmod_report(args.report)

    print(f"🕸️  Ingesting Graphify Knowledge Graph: {args.graph}")
    graph_data = parse_graphify_graph(args.graph)

    # Synthesize slices
    print("🔄 Synthesizing dependency-ordered vertical slices...")
    matrix = synthesize_migration_slices(
        codmod_data,
        graph_data,
        seams_data=seams_data,
        specs_data=specs_data,
        migration_data=migration_data,
    )

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
        try:
            from scripts.run_manager import RunManager, STAGE_DIRS
        except ImportError:
            try:
                from run_manager import RunManager, STAGE_DIRS
            except ImportError:
                sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
                from scripts.run_manager import RunManager, STAGE_DIRS

        args.output_dir.mkdir(parents=True, exist_ok=True)
        for s_name in STAGE_DIRS.values():
            (args.output_dir / s_name).mkdir(parents=True, exist_ok=True)

        graph_html_path = args.graph_html
        if not graph_html_path:
            candidate_html = args.graph.parent / "graph.html"
            if candidate_html.exists():
                graph_html_path = candidate_html

        graph_report_path = args.graph_report
        if not graph_report_path:
            candidate_report = args.graph.parent / "GRAPH_REPORT.md"
            if candidate_report.exists():
                graph_report_path = candidate_report

        # Stage discovery artifacts with clear, human-friendly names
        base_dir = args.output_dir.parent.parent if args.output_dir.parent.name == "runs" else args.output_dir.parent
        run_mgr = RunManager(base_dir=base_dir)
        run_mgr.scaffold_run(custom_run_dir=args.output_dir, app_name=matrix.get("application_title", "application"))
        destinations = run_mgr.organize_discovery_artifacts(
            run_dir=args.output_dir,
            codmod_report_path=args.report,
            graph_json_path=args.graph,
            graph_html_path=graph_html_path,
            graph_report_path=graph_report_path,
            seams_report_path=args.seams_report,
            specs_report_path=args.specs_report,
            migration_report_path=args.migration_report,
        )

        effective_report = destinations.get("codmod_report", args.report)
        effective_graph_html = destinations.get("graph_html", graph_html_path)
        effective_graph_report = destinations.get("graph_report", graph_report_path)

        # Stage 2: Synthesis artifacts
        matrix_path = args.output_dir / "migration_matrix.json"
        stage_matrix_path = args.output_dir / STAGE_DIRS["stage2_synthesis"] / "migration_matrix.json"
        with open(matrix_path, "w", encoding="utf-8") as f:
            json.dump(matrix, f, indent=2, ensure_ascii=False)
        with open(stage_matrix_path, "w", encoding="utf-8") as f:
            json.dump(matrix, f, indent=2, ensure_ascii=False)
        print(f"✅ Emitted matrix: {stage_matrix_path}")

        slices_path = args.output_dir / STAGE_DIRS["stage2_synthesis"] / "vertical_slices.json"
        with open(slices_path, "w", encoding="utf-8") as f:
            json.dump(matrix.get("slices", []), f, indent=2, ensure_ascii=False)

        # Stage 4: Migration plan
        plan_path = args.output_dir / "05_PLAN.md"
        stage_plan_path = args.output_dir / STAGE_DIRS["stage4_migration_plan"] / "05_PLAN.md"
        plan_md = generate_plan_markdown(matrix, plan_path)
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(plan_md)
        with open(stage_plan_path, "w", encoding="utf-8") as f:
            f.write(plan_md)
        print(f"✅ Emitted plan:   {stage_plan_path}")

        # Update run manifest
        run_mgr.update_manifest(
            args.output_dir,
            status="SYNTHESIS_COMPLETE",
            scorecard={
                "component_modules": total_mods,
                "central_dependency_hubs": total_hubs,
                "slices": len(matrix.get("slices", [])),
            }
        )

        if not args.no_dashboard:
            try:
                from scripts.generate_dashboard import generate_modernization_dashboard
            except ImportError:
                try:
                    from generate_dashboard import generate_modernization_dashboard
                except ImportError:
                    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
                    from scripts.generate_dashboard import generate_modernization_dashboard
            generate_modernization_dashboard(
                matrix_data=matrix,
                codmod_data=codmod_data,
                graph_data=graph_data,
                output_dir=args.output_dir,
                codmod_report_path=effective_report,
                graph_html_path=effective_graph_html,
                graph_report_path=effective_graph_report,
                plan_path=stage_plan_path,
                brain_dir=args.brain_dir,
                mirror=not args.no_mirror,
            )


if __name__ == "__main__":
    main()

