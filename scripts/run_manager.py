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
Run Manager for Bean-Grinder Modernization & Assessment Workflows.

Manages the lifecycle of a unified assessment directory:
- Scaffolds human-friendly, stage-based subdirectories (01_discovery to 05_parity_verification)
- Normalizes and organizes artifact filenames across stages
- Tracks run manifests and status metadata
- Maintains symlinks to the latest run
- Generates root-level index.html with interactive multi-run navigation
"""

from datetime import datetime
import json
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional


STAGE_DIRS = {
    "stage1_discovery": "01_discovery",
    "stage2_synthesis": "02_synthesis",
    "stage3_adversarial_review": "03_adversarial_review",
    "stage4_migration_plan": "04_migration_plan",
    "stage5_parity_verification": "05_parity_verification",
}

STAGE_DESCRIPTIONS = {
    "01_discovery": "Non-Invasive Discovery & Codebase Ingestion (CodMod + Graphify + AST)",
    "02_synthesis": "Architectural Synthesis & Digestion (7 Rs + Mikado Slices + Matrices)",
    "03_adversarial_review": "Multi-Persona Adversarial Review & Plan Hardening",
    "04_migration_plan": "Hardened Migration Plan & Downstream Architecture Contracts",
    "05_parity_verification": "Runtime Parity Verification & Golden Master Fixtures",
}


class RunManager:
    """Manages assessment runs and directory hierarchies."""

    def __init__(self, base_dir: Path = Path("assessments")):
        self.base_dir = Path(base_dir).resolve()
        self.runs_dir = self.base_dir / "runs"

    def scaffold_run(
        self,
        run_id: Optional[str] = None,
        app_name: str = "application",
        custom_run_dir: Optional[Path] = None,
    ) -> Path:
        """
        Scaffold a self-contained run directory with all stage folders.

        Returns the absolute Path to the newly created run directory.
        """
        if custom_run_dir:
            run_dir = Path(custom_run_dir).resolve()
        else:
            if not run_id:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                clean_app = "".join(c if c.isalnum() or c in "-_" else "_" for c in app_name.lower())
                run_id = f"{timestamp}_{clean_app}"
            run_dir = self.runs_dir / run_id

        run_dir.mkdir(parents=True, exist_ok=True)

        # Create stage folders
        for folder_name in STAGE_DIRS.values():
            stage_path = run_dir / folder_name
            stage_path.mkdir(parents=True, exist_ok=True)

        # Initialize run manifest
        manifest_path = run_dir / "run_manifest.json"
        if not manifest_path.exists():
            manifest_data = {
                "run_id": run_dir.name,
                "app_name": app_name,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "status": "INITIALIZED",
                "stages": {
                    stage_key: {
                        "dir": folder_name,
                        "status": "PENDING",
                        "artifacts": [],
                    }
                    for stage_key, folder_name in STAGE_DIRS.items()
                },
                "scorecard": {},
            }
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)

        # Update 'latest' symlink if inside standard runs_dir or base_dir
        if run_dir.parent == self.runs_dir:
            self._update_latest_symlink(run_dir)

        return run_dir

    def _update_latest_symlink(self, run_dir: Path):
        """Update assessments/latest symlink to point to the active run."""
        latest_link = self.base_dir / "latest"
        try:
            if latest_link.is_symlink() or latest_link.exists():
                latest_link.unlink()
            rel_target = os.path.relpath(run_dir, self.base_dir)
            latest_link.symlink_to(rel_target, target_is_directory=True)
        except Exception:
            # Fallback gracefully if symlinks not supported on filesystem
            pass

    def update_manifest(self, run_dir: Path, **kwargs) -> Dict[str, Any]:
        """Update manifest key-values in run_dir / run_manifest.json."""
        manifest_path = run_dir / "run_manifest.json"
        if not manifest_path.exists():
            manifest_data = {
                "run_id": run_dir.name,
                "created_at": datetime.now().isoformat(),
                "stages": {},
            }
        else:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)

        manifest_data["updated_at"] = datetime.now().isoformat()
        for k, v in kwargs.items():
            if isinstance(v, dict) and k in manifest_data and isinstance(manifest_data[k], dict):
                manifest_data[k].update(v)
            else:
                manifest_data[k] = v

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        return manifest_data

    def organize_discovery_artifacts(
        self,
        run_dir: Path,
        codmod_report_path: Optional[Path] = None,
        graph_json_path: Optional[Path] = None,
        graph_html_path: Optional[Path] = None,
        graph_report_path: Optional[Path] = None,
        telemetry_path: Optional[Path] = None,
    ) -> Dict[str, Path]:
        """
        Copy or relocate discovery artifacts into 01_discovery/ with descriptive names.
        """
        discovery_dir = run_dir / STAGE_DIRS["stage1_discovery"]
        discovery_dir.mkdir(parents=True, exist_ok=True)

        destinations: Dict[str, Path] = {}

        # 1. CodMod assessment report
        if codmod_report_path and codmod_report_path.exists():
            target = discovery_dir / "codmod_assessment_report.html"
            if codmod_report_path.resolve() != target.resolve():
                shutil.copy2(codmod_report_path, target)
            destinations["codmod_report"] = target

        # 2. Graphify AST JSON
        if graph_json_path and graph_json_path.exists():
            target = discovery_dir / "graphify_ast_graph.json"
            if graph_json_path.resolve() != target.resolve():
                shutil.copy2(graph_json_path, target)
            destinations["graph_json"] = target

        # 3. Graphify interactive HTML visualizer
        if graph_html_path and graph_html_path.exists():
            target = discovery_dir / "graphify_visualizer.html"
            if graph_html_path.resolve() != target.resolve():
                shutil.copy2(graph_html_path, target)
            destinations["graph_html"] = target

        # 4. Graphify architecture markdown report
        if graph_report_path and graph_report_path.exists():
            target = discovery_dir / "graphify_architecture_report.md"
            if graph_report_path.resolve() != target.resolve():
                shutil.copy2(graph_report_path, target)
            destinations["graph_report"] = target

        # 5. Telemetry log
        if telemetry_path and telemetry_path.exists():
            target = discovery_dir / "codmod_execution_telemetry.json"
            if telemetry_path.resolve() != target.resolve():
                shutil.copy2(telemetry_path, target)
            destinations["telemetry"] = target

        return destinations

    def list_runs(self) -> List[Dict[str, Any]]:
        """List all discovered assessment runs sorted by recency."""
        runs: List[Dict[str, Any]] = []
        if not self.runs_dir.exists():
            return runs

        for entry in sorted(self.runs_dir.iterdir(), reverse=True):
            if not entry.is_dir():
                continue
            manifest_file = entry / "run_manifest.json"
            if manifest_file.exists():
                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        data["path"] = str(entry)
                        runs.append(data)
                        continue
                except Exception:
                    pass

            # Fallback without manifest
            runs.append({
                "run_id": entry.name,
                "app_name": entry.name,
                "created_at": datetime.fromtimestamp(entry.stat().st_mtime).isoformat(),
                "path": str(entry),
                "status": "COMPLETED" if (entry / "index.html").exists() else "UNKNOWN",
            })

        return runs

    def update_root_index(self, active_run_dir: Optional[Path] = None) -> Optional[Path]:
        """
        Generate or refresh assessments/index.html with top-level run navigation.
        If an active_run_dir is supplied, root index copies/mirrors that dashboard
        while adding a sticky header run switcher.
        """
        if not self.base_dir.exists():
            self.base_dir.mkdir(parents=True, exist_ok=True)

        runs = self.list_runs()
        root_index = self.base_dir / "index.html"

        # If there's an active run or latest run, mirror its dashboard to root index.html
        target_run = active_run_dir
        if not target_run and (self.base_dir / "latest").exists():
            target_run = (self.base_dir / "latest").resolve()
        elif not target_run and runs:
            target_run = Path(runs[0]["path"])

        if target_run and (target_run / "index.html").exists():
            html_content = (target_run / "index.html").read_text(encoding="utf-8", errors="replace")

            # Rewrite relative paths from run_dir to root base_dir
            rel_prefix = os.path.relpath(target_run, self.base_dir)
            for stage_dir in STAGE_DIRS.values():
                html_content = html_content.replace(f'"{stage_dir}/', f'"{rel_prefix}/{stage_dir}/')
                html_content = html_content.replace(f"'{stage_dir}/", f"'{rel_prefix}/{stage_dir}/")

            # Inject Run Switcher Bar at the top of the body
            switcher_html = self._build_run_switcher_html(runs, current_run_id=target_run.name)
            if "<body" in html_content:
                body_idx = html_content.find(">", html_content.find("<body")) + 1
                html_content = html_content[:body_idx] + "\n" + switcher_html + "\n" + html_content[body_idx:]

            root_index.write_text(html_content, encoding="utf-8")
            return root_index

        # If no runs exist yet, create a welcoming placeholder
        placeholder_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Bean-Grinder Modernization Hub</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #1e1e2e; color: #cdd6f4; text-align: center; padding: 4rem; }
        .card { background: #181825; border: 1px solid #313244; border-radius: 12px; max-width: 600px; margin: 0 auto; padding: 2rem; }
        h1 { color: #89b4fa; }
        code { background: #313244; padding: 0.2rem 0.5rem; border-radius: 4px; color: #a6e3a1; }
    </style>
</head>
<body>
    <div class="card">
        <h1>⚙️ Bean-Grinder Modernization Hub</h1>
        <p>No assessment runs recorded yet.</p>
        <p>Run <code>agy -i "/assess"</code> or <code>python3 scripts/digest_report.py</code> to generate your first modernization dashboard.</p>
    </div>
</body>
</html>"""
        root_index.write_text(placeholder_html, encoding="utf-8")
        return root_index

    def _build_run_switcher_html(self, runs: List[Dict[str, Any]], current_run_id: str) -> str:
        """Construct a lightweight sticky run switcher toolbar."""
        options_html = ""
        for r in runs:
            rid = r.get("run_id", "unknown")
            app = r.get("app_name", "app")
            selected = "selected" if rid == current_run_id else ""
            options_html += f'<option value="runs/{rid}/index.html" {selected}>📅 {rid} ({app})</option>\n'

        return f"""
<!-- Bean-Grinder Multi-Run Navigation Bar -->
<div id="bean-grinder-run-nav" style="background:#11111b; border-bottom:1px solid #313244; padding:0.6rem 1.5rem; display:flex; justify-content:space-between; align-items:center; position:sticky; top:0; z-index:9999; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size:13px; color:#cdd6f4;">
    <div style="display:flex; align-items:center; gap:0.75rem;">
        <span style="font-size:16px;">⚙️</span>
        <strong style="color:#89b4fa; font-size:14px;">Bean-Grinder Modernization Runs</strong>
        <span style="background:#313244; color:#a6adc8; padding:2px 8px; border-radius:12px; font-size:11px;">{len(runs)} Run{'s' if len(runs) != 1 else ''}</span>
    </div>
    <div style="display:flex; align-items:center; gap:0.75rem;">
        <label for="run-select" style="color:#a6adc8;">Switch Run:</label>
        <select id="run-select" onchange="if(this.value) window.location.href=this.value;" style="background:#181825; color:#cdd6f4; border:1px solid #45475a; border-radius:6px; padding:4px 10px; font-size:12px; outline:none; cursor:pointer;">
            {options_html}
        </select>
        <a href="latest/index.html" style="background:#89b4fa; color:#11111b; text-decoration:none; padding:4px 10px; border-radius:6px; font-weight:600; font-size:12px;">View Latest</a>
    </div>
</div>
"""
