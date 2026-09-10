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
Standalone Synthesis Runner for Bean-Grinder Modernization Workflows.

Executes architectural synthesis against existing discovery artifacts without
re-running resource-heavy discovery scouts (CodMod, Graphify, etc.).
Can be invoked repeatedly to iterate on vertical slicing, runtime targets,
or incorporate domain invariants and Feathers' seams.
"""

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

# Locate repo root and import core bean-grinder scripts
def _find_repo_root() -> Path:
    # 1. Check relative to this script
    script_path = Path(__file__).resolve()
    for p in [script_path.parents[3], script_path.parents[2], script_path.parents[1], Path.cwd()]:
        if (p / "scripts" / "digest_report.py").exists():
            return p
    # 2. Check installed plugin directory
    home = Path.home()
    plugin_dir = home / ".gemini" / "config" / "plugins" / "bean-grinder"
    if (plugin_dir / "scripts" / "digest_report.py").exists():
        return plugin_dir
    return Path.cwd()

REPO_ROOT = _find_repo_root()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from scripts.digest_report import (
        parse_codmod_report,
        parse_graphify_graph,
        synthesize_migration_slices,
        generate_plan_markdown,
    )
    from scripts.run_manager import RunManager, STAGE_DIRS
    from scripts.generate_dashboard import generate_modernization_dashboard
except ImportError as e:
    sys.stderr.write(f"❌ Failed to import bean-grinder engines from {REPO_ROOT}: {e}\n")
    sys.exit(1)


def resolve_run_dir(base_dir: Path, target_run: Optional[str] = None) -> Path:
    """Resolve an assessment run directory (explicit path, run ID, or 'latest')."""
    runs_dir = base_dir / "runs" if base_dir.name != "runs" else base_dir

    if target_run and target_run != "latest":
        direct = Path(target_run).resolve()
        if direct.exists() and direct.is_dir():
            return direct
        cand = runs_dir / target_run
        if cand.exists() and cand.is_dir():
            return cand
        raise FileNotFoundError(f"Run directory not found for: '{target_run}' (checked {direct} and {cand})")

    # Resolve latest
    latest_link = base_dir / "latest"
    if latest_link.exists() and latest_link.is_symlink():
        return latest_link.resolve()

    runs_latest = runs_dir / "latest"
    if runs_latest.exists() and runs_latest.is_symlink():
        return runs_latest.resolve()

    # Search for most recent folder in runs_dir
    if runs_dir.exists():
        entries = [
            d for d in runs_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".") and d.name != "latest"
        ]
        if entries:
            entries.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return entries[0].resolve()

    raise FileNotFoundError(f"No previous assessment runs found under: {base_dir}")


def locate_discovery_artifacts(run_dir: Path) -> Dict[str, Optional[Path]]:
    """Scan 01_discovery/ and run root for existing discovery outputs."""
    disc_dir = run_dir / STAGE_DIRS.get("stage1_discovery", "01_discovery")
    search_dirs = [disc_dir, run_dir, REPO_ROOT]

    def _find_file(candidates: List[str]) -> Optional[Path]:
        for d in search_dirs:
            if not d.exists():
                continue
            for name in candidates:
                p = d / name
                if p.exists() and p.is_file():
                    return p
        return None

    report = _find_file([
        "codmod_assessment_report.html",
        "modernization_report.html",
        "codmod_report.html",
        "codmod_assessment.json",
        "modernization_report.json"
    ])

    graph_json = _find_file([
        "graphify_ast_graph.json",
        "graph.json",
        "graphify-out/graph.json"
    ])

    graph_html = _find_file([
        "graphify_ast_interactive.html",
        "graph.html",
        "graphify-out/graph.html"
    ])

    graph_report = _find_file([
        "graphify_architecture_report.md",
        "GRAPH_REPORT.md",
        "graphify-out/GRAPH_REPORT.md"
    ])

    seams_report = _find_file([
        "seam_findings.md",
        "seams.md",
        "seam_scout_report.md"
    ])

    specs_report = _find_file([
        "spec_invariants.md",
        "specs.md",
        "business_rules.md",
        "spec_recovery_report.md"
    ])

    migration_report = _find_file([
        "migration_strategy.md",
        "7rs_matrix.md",
        "migration_scout_report.md"
    ])

    return {
        "report": report,
        "graph": graph_json,
        "graph_html": graph_html,
        "graph_report": graph_report,
        "seams": seams_report,
        "specs": specs_report,
        "migration": migration_report,
    }


def parse_markdown_table_rows(content: str) -> List[Dict[str, str]]:
    """Simple parser to extract rows from the first markdown table in content."""
    import re
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


def run_synthesis(
    run_dir: Path,
    base_dir: Path,
    no_dashboard: bool = False,
    no_mirror: bool = False,
    brain_dir: Optional[str] = None,
    custom_slices: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Execute the synthesis workflow for the specified run directory."""
    artifacts = locate_discovery_artifacts(run_dir)

    if not artifacts["report"] or not artifacts["graph"]:
        missing = []
        if not artifacts["report"]:
            missing.append("CodMod report (codmod_assessment_report.html / modernization_report.html)")
        if not artifacts["graph"]:
            missing.append("Graphify AST graph (graphify_ast_graph.json / graph.json)")
        raise FileNotFoundError(
            f"❌ Missing required discovery artifacts in {run_dir}:\n" +
            "\n".join(f"  • {m}" for m in missing) +
            "\nPlease run '/assess' first to collect discovery reports before running synthesis."
        )

    print(f"📁 Ingesting discovery from run: {run_dir}")
    print(f"  • CodMod:   {artifacts['report']}")
    print(f"  • Graphify: {artifacts['graph']}")

    # Ingest baseline reports
    codmod_data = parse_codmod_report(artifacts["report"])
    graph_data = parse_graphify_graph(artifacts["graph"])

    # Ingest optional scout reports if present
    seams_data = None
    if artifacts["seams"]:
        print(f"  • Seam Scout: {artifacts['seams']}")
        try:
            seams_data = parse_markdown_table_rows(artifacts["seams"].read_text(encoding="utf-8"))
        except Exception as e:
            print(f"    (Warning: Could not parse {artifacts['seams']}: {e})")

    specs_data = None
    if artifacts["specs"]:
        print(f"  • Spec Recovery: {artifacts['specs']}")
        try:
            specs_data = parse_markdown_table_rows(artifacts["specs"].read_text(encoding="utf-8"))
        except Exception as e:
            print(f"    (Warning: Could not parse {artifacts['specs']}: {e})")

    migration_data = None
    if artifacts["migration"]:
        print(f"  • Migration Scout: {artifacts['migration']}")
        try:
            migration_data = parse_markdown_table_rows(artifacts["migration"].read_text(encoding="utf-8"))
        except Exception as e:
            print(f"    (Warning: Could not parse {artifacts['migration']}: {e})")

    # Synthesize migration slices and matrix
    print("🔄 Synthesizing dependency-ordered vertical slices...")
    matrix = synthesize_migration_slices(codmod_data, graph_data)

    # Enrich matrix with empirical scout data if available
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
        if empirical_seams:
            matrix["seams_inventory"] = empirical_seams
            matrix["seams_source"] = "empirical_seam_scout"

    if specs_data:
        ambiguous = [s for s in specs_data if "AMBIGUOUS" in s.get("review_status", "").upper() or "AMBIGUOUS" in s.get("domain_rule_summary", "").upper()]
        matrix["recovered_invariants"] = specs_data
        matrix["ambiguous_specs_count"] = len(ambiguous)
        matrix["ambiguous_specs"] = ambiguous

    if migration_data:
        empirical_7rs = []
        for row in migration_data:
            mod_name = row.get("subsystem___library") or row.get("subsystem") or row.get("component_module")
            if mod_name:
                empirical_7rs.append({
                    "module_name": mod_name,
                    "strategy": row.get("7_rs_strategy") or row.get("strategy", "Refactor"),
                    "rationale": row.get("rationale", ""),
                    "target_service": row.get("target_cloud_service", "Cloud Run"),
                })
        if empirical_7rs:
            matrix["portfolio_7rs"] = empirical_7rs
            matrix["portfolio_source"] = "empirical_migration_scout"

    if custom_slices:
        matrix["slices"] = custom_slices

    # Ensure stage directories exist
    stage2_dir = run_dir / STAGE_DIRS["stage2_synthesis"]
    stage4_dir = run_dir / STAGE_DIRS["stage4_migration_plan"]
    stage2_dir.mkdir(parents=True, exist_ok=True)
    stage4_dir.mkdir(parents=True, exist_ok=True)

    # Emit synthesis artifacts
    matrix_path = stage2_dir / "migration_matrix.json"
    root_matrix_path = run_dir / "migration_matrix.json"
    with open(matrix_path, "w", encoding="utf-8") as f:
        json.dump(matrix, f, indent=2, ensure_ascii=False)
    with open(root_matrix_path, "w", encoding="utf-8") as f:
        json.dump(matrix, f, indent=2, ensure_ascii=False)

    slices_path = stage2_dir / "vertical_slices.json"
    with open(slices_path, "w", encoding="utf-8") as f:
        json.dump(matrix.get("slices", []), f, indent=2, ensure_ascii=False)

    plan_path = stage4_dir / "05_PLAN.md"
    root_plan_path = run_dir / "05_PLAN.md"
    plan_md = generate_plan_markdown(matrix, plan_path)
    with open(plan_path, "w", encoding="utf-8") as f:
        f.write(plan_md)
    with open(root_plan_path, "w", encoding="utf-8") as f:
        f.write(plan_md)

    print(f"✅ Emitted matrix: {matrix_path}")
    print(f"✅ Emitted plan:   {plan_path}")

    # Update manifest
    run_mgr = RunManager(base_dir=base_dir)
    run_mgr.update_manifest(
        run_dir,
        status="SYNTHESIS_COMPLETE",
        scorecard={
            "component_modules": matrix.get("total_component_modules", 0),
            "central_dependency_hubs": matrix.get("total_central_dependency_hubs", 0),
            "slices": len(matrix.get("slices", [])),
            "ambiguous_specs": matrix.get("ambiguous_specs_count", 0),
        }
    )

    # Generate / refresh dashboard
    if not no_dashboard:
        generate_modernization_dashboard(
            matrix_data=matrix,
            codmod_data=codmod_data,
            graph_data=graph_data,
            output_dir=run_dir,
            codmod_report_path=artifacts["report"],
            graph_html_path=artifacts["graph_html"],
            graph_report_path=artifacts["graph_report"],
            plan_path=plan_path,
            brain_dir=brain_dir,
            mirror=not no_mirror,
        )

    return matrix


def main():
    parser = argparse.ArgumentParser(
        description="Standalone synthesis runner for bean-grinder modernization."
    )
    parser.add_argument(
        "--run-dir",
        type=str,
        help="Path or ID of run directory. If omitted, uses 'latest'."
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("assessments"),
        help="Assessments root directory (default: ./assessments)."
    )
    parser.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Skip generating or refreshing the HTML dashboard."
    )
    parser.add_argument(
        "--no-mirror",
        action="store_true",
        help="Skip dual-write mirroring to conversation brain."
    )
    parser.add_argument(
        "--brain-dir",
        type=str,
        help="Explicit conversation brain directory to mirror artifacts to."
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print summary scorecard to stdout without writing files."
    )

    args = parser.parse_args()

    try:
        run_dir = resolve_run_dir(args.base_dir, args.run_dir)
    except FileNotFoundError as e:
        sys.stderr.write(f"❌ {e}\n")
        sys.exit(1)

    try:
        matrix = run_synthesis(
            run_dir=run_dir,
            base_dir=args.base_dir,
            no_dashboard=args.no_dashboard or args.summary_only,
            no_mirror=args.no_mirror,
            brain_dir=args.brain_dir,
        )
    except FileNotFoundError as e:
        sys.stderr.write(f"{e}\n")
        sys.exit(1)

    total_mods = matrix.get("total_component_modules", 0)
    total_hubs = matrix.get("total_central_dependency_hubs", 0)
    slices = matrix.get("slices", [])

    print("\n" + "=" * 60)
    print(f"📊 STANDALONE SYNTHESIS COMPLETE: {matrix.get('application_title', 'Application')}")
    print("=" * 60)
    print(f"Run Directory:             {run_dir}")
    print(f"Component Modules:         {total_mods}")
    print(f"Central Dependency Hubs:   {total_hubs}")
    print(f"Vertical Slices:           {len(slices)}")
    if matrix.get("ambiguous_specs_count"):
        print(f"Ambiguous Specs Detected:  {matrix['ambiguous_specs_count']} (governed by HITL gates)")
    print("\nNext Action:")
    print("  • Inspect [05_PLAN.md] in 04_migration_plan/")
    print("  • Run '@synthesis-agent' to further customize domain slices")
    print("  • Run '/adversarial-review' to stress-test the implementation plan")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
