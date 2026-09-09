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
Unified Modernization HTML Dashboard Generator.

Generates a responsive, self-contained HTML dashboard combining:
1. Executive Modernization Scorecard
2. Interactive Vertical Slices (Kanban)
3. Central Dependency Hubs Matrix (Callers vs Dependencies, Blast Radius)
4. Component Modules & Subsystems Breakdown
5. Integrated Google Cloud CodMod Tab (Iframe + Extracted Digest)
6. Integrated Graphify Tab (Vis-network AST Graph Iframe + Markdown Report)
7. Migration Plan View (05_PLAN.md)
8. Dual-Write UI Mirroring to 00_visual-dashboard.html
"""

import argparse
from datetime import datetime
import html
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Any, Dict, List, Optional, Tuple

try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False


def render_markdown_safe(text: str) -> str:
    """Render markdown safely to HTML with table and code block support."""
    if not text:
        return ""
    if HAS_MARKDOWN:
        return markdown.markdown(text, extensions=["tables", "fenced_code"])
    return f"<pre style='white-space: pre-wrap; font-family: monospace;'>{html.escape(text)}</pre>"


def find_brain_dirs(explicit_brain_dir: Optional[str] = None) -> List[str]:
    """
    Locate active Antigravity (AGY) conversation brain directories.
    Searches ~/.gemini/antigravity/brain and ~/.gemini/antigravity-cli/brain.
    """
    dirs = []
    if explicit_brain_dir and os.path.exists(explicit_brain_dir):
        dirs.append(explicit_brain_dir)

    home_dir = os.path.expanduser("~")
    conv_id = os.environ.get("AGY_CONVERSATION_ID") or os.environ.get("CONVERSATION_ID")
    explicit_env = os.environ.get("AGY_BRAIN_DIR")
    if explicit_env and os.path.exists(explicit_env) and explicit_env not in dirs:
        dirs.append(explicit_env)

    parents = [
        os.path.join(home_dir, ".gemini", "antigravity", "brain"),
        os.path.join(home_dir, ".gemini", "antigravity-cli", "brain"),
    ]

    for parent in parents:
        if conv_id:
            conv_path = os.path.join(parent, conv_id)
            if os.path.exists(os.path.dirname(conv_path)):
                os.makedirs(conv_path, exist_ok=True)
                if conv_path not in dirs:
                    dirs.append(conv_path)

        if os.path.exists(parent):
            try:
                entries = [
                    os.path.join(parent, d)
                    for d in os.listdir(parent)
                    if os.path.isdir(os.path.join(parent, d)) and not d.startswith(".")
                ]
                if entries:
                    entries.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                    for e in entries[:2]:
                        if e not in dirs:
                            dirs.append(e)
            except Exception:
                pass

    return dirs


def mirror_dashboard(
    dashboard_path: Path,
    target_filename: str = "00_visual-dashboard.html",
    brain_dir: Optional[str] = None,
    aux_files: Optional[List[Tuple[Path, str]]] = None,
) -> List[str]:
    """
    Dual-writes the modernization dashboard to active conversation brain directories.
    Also mirrors auxiliary files (e.g. 05_PLAN.md -> 05_plan.md, migration_matrix.json).
    """
    if not dashboard_path.exists():
        return []

    destinations = []
    target_dirs = find_brain_dirs(brain_dir)

    for b_dir in target_dirs:
        try:
            os.makedirs(b_dir, exist_ok=True)
            target_dest = Path(b_dir) / target_filename
            shutil.copy2(dashboard_path, target_dest)
            destinations.append(str(target_dest))

            # Emit ArtifactMetadata for the chat UI
            try:
                meta_file = Path(b_dir) / f"{target_filename}.metadata.json"
                meta_content = {
                    "summary": "Unified Modernization Dashboard combining Executive Modernization Scorecard, Interactive Vertical Slices (Kanban), Central Dependency Hubs Matrix, Component Modules, Integrated Google Cloud CodMod assessment report, and Graphify AST Knowledge Graph visualizer.",
                    "updatedAt": datetime.now().isoformat() + "Z",
                    "requestFeedback": False,
                    "userFacing": True
                }
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(meta_content, f, indent=2)
            except Exception:
                pass

            if aux_files:
                for src_file, dest_name in aux_files:
                    if src_file.exists():
                        aux_dest = Path(b_dir) / dest_name
                        shutil.copy2(src_file, aux_dest)
                        try:
                            aux_meta = Path(b_dir) / f"{dest_name}.metadata.json"
                            aux_meta_content = {
                                "summary": f"Modernization artifact: {dest_name}",
                                "updatedAt": datetime.now().isoformat() + "Z",
                                "requestFeedback": False,
                                "userFacing": True
                            }
                            with open(aux_meta, "w", encoding="utf-8") as f:
                                json.dump(aux_meta_content, f, indent=2)
                        except Exception:
                            pass
        except Exception as e:
            print(f"⚠️  Warning: Could not mirror dashboard to {b_dir}: {e}", file=sys.stderr)

    return destinations


def render_slice_card_html(s: Dict[str, Any]) -> str:
    """Helper to render a vertical slice card for the Kanban tab."""
    slice_id = s.get("slice_id", "Slice")
    name = s.get("name", "Migration Slice")
    nature = s.get("nature", "[Serial]")
    is_serial = "serial" in nature.lower()
    nature_badge_class = "badge-serial" if is_serial else "badge-parallel"
    nature_key = "serial" if is_serial else "parallel"

    desc = s.get("description", "")
    modules = s.get("component_modules", [])
    hubs = s.get("central_hubs_addressed", [])
    tasks = s.get("codmod_tasks", [])
    verify = s.get("verification_strategy", "Automated verification test.")

    tasks_html = ""
    if tasks:
        tasks_html = """
        <table class="task-table">
          <thead>
            <tr><th>Task Area</th><th>Complexity</th><th>Effort</th></tr>
          </thead>
          <tbody>
        """
        for t in tasks[:4]:
            t_name = html.escape(t.get("task", ""))
            t_comp = html.escape(t.get("complexity", "Medium"))
            t_eff = html.escape(t.get("effort", "Small"))
            tasks_html += f"<tr><td>{t_name}</td><td><span class='badge badge-warning'>{t_comp}</span></td><td>{t_eff}</td></tr>"
        tasks_html += "</tbody></table>"

    hubs_html = ""
    if hubs:
        hubs_badges = "".join(f"<span class='chip chip-hub'>{html.escape(h)}</span>" for h in hubs)
        hubs_html = f"""
        <div style="font-size: 11px; margin-top: 4px;">
          <strong style="color: var(--warning);">Decouples Hubs:</strong>
          <div class="chips-group" style="margin-top: 4px;">
            {hubs_badges}
          </div>
        </div>
        """

    modules_html = ""
    if modules:
        mod_chips = "".join(f"<span class='chip'>{html.escape(m)}</span>" for m in modules[:5])
        more_badge = f"<span class='chip'>+{len(modules)-5} more</span>" if len(modules) > 5 else ""
        modules_html = f"""
        <div style="font-size: 11px;">
          <span style="color: var(--muted);">Impacted Modules:</span>
          <div class="chips-group" style="margin-top: 4px;">
            {mod_chips}{more_badge}
          </div>
        </div>
        """

    return f"""
    <div class="slice-card" data-nature="{nature_key}">
      <div class="slice-header">
        <div>
          <span class="badge {nature_badge_class}">{html.escape(nature)}</span>
          <div class="slice-title" style="margin-top: 4px;">{html.escape(slice_id)}: {html.escape(name)}</div>
        </div>
        <span class="badge badge-accent">#{s.get("execution_order", 0)}</span>
      </div>

      <p class="slice-desc">{html.escape(desc)}</p>

      {modules_html}
      {hubs_html}
      {tasks_html}

      <div class="verification-box">
        <strong>Gate:</strong> {html.escape(verify)}
      </div>
    </div>
    """


def render_hub_row_html(idx: int, hub: Dict[str, Any], max_degree: int) -> str:
    """Helper to render a table row in the Central Dependency Hubs matrix."""
    label = hub.get("label", "Unknown")
    mod_name = hub.get("module_name", hub.get("community_name", "Unknown"))
    deg = hub.get("total_connections", hub.get("degree", 0))
    in_deg = hub.get("inbound_callers", hub.get("in_degree", 0))
    out_deg = hub.get("outbound_dependencies", hub.get("out_degree", 0))

    pct = min(100, int((deg / max(1, max_degree)) * 100))

    if deg >= 30:
        risk_badge = '<span class="badge badge-danger">Critical</span>'
        action = "Encapsulate with Interface / Anti-Corruption Facade"
    elif deg >= 18:
        risk_badge = '<span class="badge badge-warning">High</span>'
        action = "Extract DTO / Value Object / Decouple JPA Entity"
    else:
        risk_badge = '<span class="badge badge-accent">Moderate</span>'
        action = "Standard Interface Segregation & Unit Test Shield"

    src_info = f'<div style="font-size: 11px; color: var(--muted);">{html.escape(hub.get("source_file", ""))}</div>' if hub.get("source_file") else ""

    return f"""
    <tr>
      <td style="text-align: center; font-weight: 700;">{idx}</td>
      <td>
        <span class="mono" style="font-weight: 600; color: var(--fg);">{html.escape(label)}</span>
        {src_info}
      </td>
      <td><span class="chip">{html.escape(mod_name)}</span></td>
      <td>
        <strong>{deg}</strong>
        <div class="meter-bar"><div class="meter-fill" style="width: {pct}%;"></div></div>
      </td>
      <td>
        <span style="color: var(--accent); font-weight: 600;">{in_deg} callers</span> / 
        <span style="color: var(--muted);">{out_deg} deps</span>
      </td>
      <td>{risk_badge}</td>
      <td style="font-size: 12px;">{html.escape(action)}</td>
    </tr>
    """


def render_module_card_html(cid: Any, mod: Dict[str, Any]) -> str:
    """Helper to render a single component module card."""
    name = mod.get("name", f"Module {cid}")
    nodes = mod.get("nodes", [])
    files = mod.get("files", [])
    hubs = mod.get("central_hubs", [])
    in_deg = mod.get("in_degree", 0)
    out_deg = mod.get("out_degree", 0)

    hubs_badge = ""
    if hubs:
        hub_labels = ", ".join(html.escape(h) for h in hubs[:2])
        hubs_badge = f'<div style="margin-bottom: 6px;"><span class="badge badge-warning">{len(hubs)} Hubs: {hub_labels}</span></div>'

    files_list_html = ""
    if files:
        file_lines = "<br>".join(html.escape(f) for f in files[:8])
        more_files = f"<br><em>...and {len(files)-8} more files</em>" if len(files) > 8 else ""
        files_list_html = f"""
        <div class="module-file-list">
          {file_lines}{more_files}
        </div>
        """

    return f"""
    <div class="module-card">
      <h4>
        <span>{html.escape(name)}</span>
        <span class="badge badge-accent">ID {cid}</span>
      </h4>
      <div class="module-stats">
        <span>📦 {len(nodes)} Nodes</span>
        <span>📄 {len(files)} Files</span>
        <span>🔗 {in_deg} in / {out_deg} out</span>
      </div>
      {hubs_badge}
      {files_list_html}
    </div>
    """


def build_dashboard_html(
    matrix_data: Dict[str, Any],
    codmod_data: Dict[str, Any],
    graph_data: Dict[str, Any],
    graph_report_content: Optional[str] = None,
    plan_markdown_content: Optional[str] = None,
    codmod_rel_url: Optional[str] = None,
    graph_rel_url: Optional[str] = None,
    codmod_file_url: Optional[str] = None,
    graph_file_url: Optional[str] = None,
    timestamp_str: Optional[str] = None,
) -> str:
    """Constructs the complete, responsive modernization_dashboard.html."""
    app_title = matrix_data.get("application_title", "Application Modernization")
    now_str = timestamp_str or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total_mods = matrix_data.get("total_component_modules", len(matrix_data.get("component_modules", {})))
    if total_mods == 0 and "communities" in graph_data:
        total_mods = len(graph_data["communities"])
    total_hubs = matrix_data.get("total_central_dependency_hubs", len(matrix_data.get("central_dependency_hubs", [])))
    total_conns = matrix_data.get("total_connections", graph_data.get("total_edges", 0))
    total_nodes = matrix_data.get("total_nodes", graph_data.get("total_nodes", 0))
    slices = matrix_data.get("slices", [])
    total_slices = len(slices)

    target_frameworks = "Java 21 LTS · Spring Boot 3.x · Cloud Run"
    if "dotnet" in str(codmod_data).lower() or "c#" in str(codmod_data).lower():
        target_frameworks = ".NET 9 · C# 13 · Cloud Run"
    elif "python" in str(codmod_data).lower():
        target_frameworks = "Python 3.12 · FastAPI / Cloud Run"

    central_hubs = matrix_data.get("central_dependency_hubs", [])
    component_modules = graph_data.get("component_modules", matrix_data.get("component_modules", {}))

    codmod_iframe_src = codmod_rel_url or "codmod_report_latest.html"
    graph_iframe_src = graph_rel_url or "graphify-out/graph.html"
    codmod_open_href = codmod_file_url or codmod_iframe_src
    graph_open_href = graph_file_url or graph_iframe_src

    exec_summary = codmod_data.get("executive_summary", "")
    key_findings = codmod_data.get("key_findings", [])
    strategic_recs = codmod_data.get("strategic_recommendations", [])
    roadmap_phases = codmod_data.get("roadmap_phases", [])
    work_plan = codmod_data.get("work_plan_tasks", [])
    flagged_files = codmod_data.get("flagged_files", [])

    graph_report_html = ""
    if graph_report_content:
        graph_report_html = render_markdown_safe(graph_report_content)
    else:
        graph_report_html = "<p><em>No GRAPH_REPORT.md available. Run <code>graphify . --directed</code> to generate.</em></p>"

    plan_html = ""
    if plan_markdown_content:
        plan_html = render_markdown_safe(plan_markdown_content)
    else:
        plan_html = "<p><em>Plan markdown will appear here once generated.</em></p>"

    max_deg = max((h.get("total_connections", h.get("degree", 1)) for h in central_hubs), default=1)

    findings_items = "".join(f'<li style="padding: 10px 14px; background: var(--faint); border-left: 3px solid var(--warning); border-radius: 0 8px 8px 0; font-size: 13px; line-height: 1.5;">{html.escape(f)}</li>' for f in key_findings) or '<li style="color: var(--muted);">No specific findings extracted.</li>'
    recs_items = "".join(f'<li style="padding: 10px 14px; background: var(--faint); border-left: 3px solid var(--success); border-radius: 0 8px 8px 0; font-size: 13px; line-height: 1.5;">{html.escape(r)}</li>' for r in strategic_recs) or '<li style="color: var(--muted);">No recommendations extracted.</li>'

    roadmap_rows = "".join(f'<tr><td><strong>{html.escape(p.get("phase", ""))}</strong></td><td>{html.escape(p.get("focus", ""))}</td><td><code>{html.escape(p.get("objectives", ""))}</code></td></tr>' for p in roadmap_phases)
    roadmap_panel = ""
    if roadmap_phases:
        roadmap_panel = f"""
        <div class="panel">
          <div class="panel-header">
            <div class="panel-title">🗺️ Phased Verification Roadmap</div>
            <span class="badge badge-accent">{len(roadmap_phases)} Phases</span>
          </div>
          <table class="data-table">
            <thead>
              <tr>
                <th style="width: 20%;">Phase</th>
                <th style="width: 40%;">Focus Area</th>
                <th style="width: 40%;">High-Level Objectives</th>
              </tr>
            </thead>
            <tbody>
              {roadmap_rows}
            </tbody>
          </table>
        </div>
        """

    slices_rendered = "".join(render_slice_card_html(s) for s in slices)
    hubs_rendered = "".join(render_hub_row_html(idx, hub, max_deg) for idx, hub in enumerate(central_hubs, 1))
    modules_rendered = "".join(render_module_card_html(cid, mod) for cid, mod in component_modules.items())

    work_plan_items = "".join(f"<li>{html.escape(t)}</li>" for t in work_plan) or "<li>No work plan tasks.</li>"
    flagged_files_rendered = "<br>".join(html.escape(f) for f in flagged_files)

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>☕ Unified Modernization Dashboard — {html.escape(app_title)}</title>
  
  <style>
    /* ================= Universal Modernization Theme Tokens ================= */
    :root, [data-theme="light"] {{
      color-scheme: light;
      --bg: #f8fafc;
      --fg: #0f172a;
      --card: #ffffff;
      --card-border: #e2e8f0;
      --card-hover: #f1f5f9;
      --muted: #64748b;
      --faint: #f1f5f9;
      --accent: #0284c7;
      --accent-soft: #e0f2fe;
      --accent-hover: #0369a1;
      --success: #16a34a;
      --success-soft: #dcfce7;
      --warning: #d97706;
      --warning-soft: #fef3c7;
      --danger: #dc2626;
      --danger-soft: #fee2e2;
      --serial-badge: #d97706;
      --serial-bg: #fffbeb;
      --parallel-badge: #059669;
      --parallel-bg: #ecfdf5;
      --header-bg: #ffffff;
      --nav-bg: #f8fafc;
      --code-bg: #f1f5f9;
      --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
      --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
      --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
    }}

    [data-theme="dark"] {{
      color-scheme: dark;
      --bg: #0b0f19;
      --fg: #f1f5f9;
      --card: #151b2b;
      --card-border: #232d42;
      --card-hover: #1b2337;
      --muted: #94a3b8;
      --faint: #1e273a;
      --accent: #38bdf8;
      --accent-soft: #0c2744;
      --accent-hover: #7dd3fc;
      --success: #22c55e;
      --success-soft: #052e16;
      --warning: #f59e0b;
      --warning-soft: #451a03;
      --danger: #ef4444;
      --danger-soft: #450a0a;
      --serial-badge: #fbbf24;
      --serial-bg: #2d1c07;
      --parallel-badge: #34d399;
      --parallel-bg: #063122;
      --header-bg: #111726;
      --nav-bg: #0b0f19;
      --code-bg: #0f1422;
      --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.5);
      --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.4);
      --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.5);
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--fg);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
      overflow-x: hidden;
    }}

    /* Header Bar */
    header.top-header {{
      background: var(--header-bg);
      border-bottom: 1px solid var(--card-border);
      padding: 14px 24px;
      position: sticky;
      top: 0;
      z-index: 100;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: var(--shadow-sm);
    }}
    .brand-group {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .brand-icon {{
      font-size: 26px;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 44px;
      height: 44px;
      background: var(--accent-soft);
      border-radius: 10px;
    }}
    .brand-titles h1 {{
      font-size: 18px;
      font-weight: 700;
      color: var(--fg);
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .brand-titles .meta {{
      font-size: 12px;
      color: var(--muted);
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .header-actions {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.03em;
      text-transform: uppercase;
    }}
    .badge-accent {{ background: var(--accent-soft); color: var(--accent); border: 1px solid var(--accent); }}
    .badge-serial {{ background: var(--serial-bg); color: var(--serial-badge); border: 1px solid var(--serial-badge); }}
    .badge-parallel {{ background: var(--parallel-bg); color: var(--parallel-badge); border: 1px solid var(--parallel-badge); }}
    .badge-danger {{ background: var(--danger-soft); color: var(--danger); border: 1px solid var(--danger); }}
    .badge-warning {{ background: var(--warning-soft); color: var(--warning); border: 1px solid var(--warning); }}
    .badge-success {{ background: var(--success-soft); color: var(--success); border: 1px solid var(--success); }}

    button.btn, a.btn {{
      background: var(--card);
      color: var(--fg);
      border: 1px solid var(--card-border);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      text-decoration: none;
      transition: all 0.2s ease;
    }}
    button.btn:hover, a.btn:hover {{
      background: var(--card-hover);
      border-color: var(--accent);
      color: var(--accent);
    }}
    button.btn-primary {{
      background: var(--accent);
      color: #ffffff;
      border-color: var(--accent);
    }}
    button.btn-primary:hover {{
      background: var(--accent-hover);
      color: #ffffff;
    }}

    /* Tab Navigation */
    nav.tab-nav {{
      background: var(--header-bg);
      border-bottom: 1px solid var(--card-border);
      padding: 0 24px;
      display: flex;
      gap: 4px;
      overflow-x: auto;
    }}
    .tab-button {{
      background: none;
      border: none;
      color: var(--muted);
      padding: 12px 16px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      border-bottom: 3px solid transparent;
      white-space: nowrap;
      transition: all 0.15s ease;
    }}
    .tab-button:hover {{
      color: var(--fg);
    }}
    .tab-button.active {{
      color: var(--accent);
      border-bottom-color: var(--accent);
    }}

    /* Main Container & Sections */
    main.main-content {{
      padding: 24px;
      max-width: 1600px;
      margin: 0 auto;
    }}
    .tab-pane {{
      display: none;
    }}
    .tab-pane.active {{
      display: block;
      animation: fadeIn 0.2s ease-in-out;
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(4px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* Scorecard Grid */
    .scorecard-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}
    .kpi-card {{
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .kpi-card:hover {{
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
      border-color: var(--accent);
    }}
    .kpi-card .kpi-label {{
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    .kpi-card .kpi-value {{
      font-size: 32px;
      font-weight: 700;
      color: var(--fg);
      line-height: 1.1;
    }}
    .kpi-card .kpi-subtitle {{
      font-size: 12px;
      color: var(--muted);
      margin-top: 8px;
    }}

    /* Card Panels */
    .panel {{
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
      box-shadow: var(--shadow-sm);
    }}
    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--card-border);
    }}
    .panel-title {{
      font-size: 17px;
      font-weight: 700;
      color: var(--fg);
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    /* Kanban Slices Board */
    .kanban-toolbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      gap: 16px;
      flex-wrap: wrap;
    }}
    .search-box {{
      position: relative;
      flex: 1;
      max-width: 400px;
    }}
    .search-box input {{
      width: 100%;
      background: var(--card);
      border: 1px solid var(--card-border);
      color: var(--fg);
      padding: 8px 12px 8px 34px;
      border-radius: 8px;
      font-size: 13px;
      outline: none;
    }}
    .search-box input:focus {{
      border-color: var(--accent);
    }}
    .search-icon {{
      position: absolute;
      left: 10px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--muted);
      pointer-events: none;
    }}
    .filter-btn-group {{
      display: flex;
      gap: 6px;
    }}

    .kanban-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 20px;
    }}
    .slice-card {{
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      gap: 14px;
      transition: all 0.2s ease;
    }}
    .slice-card:hover {{
      box-shadow: var(--shadow-md);
      border-color: var(--accent);
    }}
    .slice-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 10px;
    }}
    .slice-title {{
      font-size: 16px;
      font-weight: 700;
      color: var(--fg);
    }}
    .slice-desc {{
      font-size: 13px;
      color: var(--muted);
      line-height: 1.4;
    }}
    .chips-group {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .chip {{
      background: var(--faint);
      color: var(--fg);
      border: 1px solid var(--card-border);
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 500;
    }}
    .chip-hub {{
      background: var(--warning-soft);
      color: var(--warning);
      border-color: var(--warning);
      font-weight: 600;
    }}

    .task-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      margin-top: 6px;
    }}
    .task-table th, .task-table td {{
      padding: 6px 8px;
      text-align: left;
      border-bottom: 1px solid var(--card-border);
    }}
    .task-table th {{
      color: var(--muted);
      font-weight: 600;
      text-transform: uppercase;
      font-size: 10px;
    }}

    .verification-box {{
      background: var(--faint);
      border-left: 3px solid var(--accent);
      padding: 8px 12px;
      border-radius: 0 6px 6px 0;
      font-size: 12px;
      color: var(--fg);
    }}

    /* Central Hubs Table */
    .data-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      margin-top: 8px;
    }}
    .data-table th, .data-table td {{
      padding: 12px 14px;
      text-align: left;
      border-bottom: 1px solid var(--card-border);
    }}
    .data-table th {{
      background: var(--faint);
      color: var(--muted);
      font-weight: 600;
      text-transform: uppercase;
      font-size: 11px;
      letter-spacing: 0.05em;
    }}
    .data-table tr:hover td {{
      background: var(--card-hover);
    }}
    .mono {{
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
      font-size: 12px;
    }}
    .meter-bar {{
      height: 6px;
      background: var(--card-border);
      border-radius: 3px;
      overflow: hidden;
      margin-top: 4px;
      width: 100px;
    }}
    .meter-fill {{
      height: 100%;
      background: var(--accent);
      border-radius: 3px;
    }}

    /* Component Modules Grid */
    .module-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
    }}
    .module-card {{
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 16px;
      box-shadow: var(--shadow-sm);
    }}
    .module-card h4 {{
      font-size: 14px;
      font-weight: 700;
      margin-bottom: 6px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .module-stats {{
      display: flex;
      gap: 12px;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 10px;
    }}
    .module-file-list {{
      max-height: 140px;
      overflow-y: auto;
      background: var(--code-bg);
      border-radius: 6px;
      padding: 8px;
      font-size: 11px;
      font-family: monospace;
    }}

    /* Integrated Iframe Views */
    .embedded-container {{
      border: 1px solid var(--card-border);
      border-radius: 12px;
      overflow: hidden;
      background: var(--card);
      box-shadow: var(--shadow-sm);
      height: calc(100vh - 200px);
      min-height: 700px;
      display: flex;
      flex-direction: column;
    }}
    .embedded-header {{
      padding: 12px 18px;
      background: var(--faint);
      border-bottom: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .embedded-iframe {{
      flex: 1;
      width: 100%;
      height: 100%;
      border: none;
      background: #ffffff;
    }}
    .view-switch-group {{
      display: flex;
      gap: 6px;
    }}

    /* Markdown Styling */
    .markdown-body {{
      font-size: 14px;
      line-height: 1.6;
      color: var(--fg);
    }}
    .markdown-body h1, .markdown-body h2, .markdown-body h3 {{
      margin-top: 24px;
      margin-bottom: 12px;
      font-weight: 700;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 6px;
    }}
    .markdown-body ul, .markdown-body ol {{
      padding-left: 24px;
      margin-bottom: 16px;
    }}
    .markdown-body table {{
      width: 100%;
      border-collapse: collapse;
      margin: 16px 0;
    }}
    .markdown-body th, .markdown-body td {{
      padding: 8px 12px;
      border: 1px solid var(--card-border);
    }}
    .markdown-body th {{
      background: var(--faint);
    }}
    .markdown-body pre {{
      background: var(--code-bg);
      padding: 12px;
      border-radius: 8px;
      overflow-x: auto;
      border: 1px solid var(--card-border);
    }}
    .markdown-body code {{
      background: var(--code-bg);
      padding: 2px 6px;
      border-radius: 4px;
      font-family: monospace;
      font-size: 12px;
    }}

    /* Footer */
    footer.dash-footer {{
      margin-top: 40px;
      padding: 20px 24px;
      text-align: center;
      border-top: 1px solid var(--card-border);
      font-size: 12px;
      color: var(--muted);
    }}
  </style>
</head>
<body>

  <!-- Top Header -->
  <header class="top-header">
    <div class="brand-group">
      <div class="brand-icon">☕</div>
      <div class="brand-titles">
        <h1>{html.escape(app_title)} <span class="badge badge-accent">Unified Modernization</span></h1>
        <div class="meta">
          <span>Target: <strong>{html.escape(target_frameworks)}</strong></span>
          <span>•</span>
          <span>Generated: {html.escape(now_str)}</span>
          <span>•</span>
          <span>Engine: <strong>Bean-Grinder (CodMod + Graphify)</strong></span>
        </div>
      </div>
    </div>
    <div class="header-actions">
      <button class="btn" id="theme-toggle" onclick="toggleTheme()" title="Toggle Light/Dark Theme">
        <span id="theme-icon">☀️</span> <span id="theme-text">Light Mode</span>
      </button>
      <a href="{html.escape(codmod_open_href)}" target="_blank" class="btn" title="Open raw CodMod HTML report in new tab">
        📋 CodMod (3.9 MB) ↗
      </a>
      <a href="{html.escape(graph_open_href)}" target="_blank" class="btn" title="Open raw Graphify AST interactive visualizer in new tab">
        🕸️ Graphify ↗
      </a>
    </div>
  </header>

  <!-- Navigation Tabs -->
  <nav class="tab-nav">
    <button class="tab-button active" onclick="showTab('scorecard')">📊 Executive Scorecard</button>
    <button class="tab-button" onclick="showTab('slices')">⚡ Vertical Slices (Kanban)</button>
    <button class="tab-button" onclick="showTab('hubs')">⚠️ Central Dependency Hubs ({total_hubs})</button>
    <button class="tab-button" onclick="showTab('modules')">🧩 Component Modules ({total_mods})</button>
    <button class="tab-button" onclick="showTab('codmod')">📋 Google Cloud CodMod Report</button>
    <button class="tab-button" onclick="showTab('graphify')">🕸️ Graphify AST Visualizer</button>
    <button class="tab-button" onclick="showTab('plan')">🗺️ Migration Plan (05_PLAN.md)</button>
  </nav>

  <!-- Main Content Area -->
  <main class="main-content">

    <!-- ================= TAB 1: EXECUTIVE SCORECARD ================= -->
    <div id="tab-scorecard" class="tab-pane active">
      
      <!-- Top Metric Cards -->
      <div class="scorecard-grid">
        <div class="kpi-card">
          <div class="kpi-label">Component Modules <span>🧩</span></div>
          <div class="kpi-value">{total_mods}</div>
          <div class="kpi-subtitle">Functional domain clusters detected</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Central Dependency Hubs <span>⚠️</span></div>
          <div class="kpi-value" style="color: var(--warning);">{total_hubs}</div>
          <div class="kpi-subtitle">High-blast-radius coupling classes</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Total AST Connections <span>🔗</span></div>
          <div class="kpi-value" style="color: var(--accent);">{total_conns:,}</div>
          <div class="kpi-subtitle">Direct method calls, imports &amp; mappings</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Total Codebase Nodes <span>📦</span></div>
          <div class="kpi-value">{total_nodes}</div>
          <div class="kpi-subtitle">Classes, endpoints &amp; database schemas</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Planned Vertical Slices <span>🍰</span></div>
          <div class="kpi-value" style="color: var(--success);">{total_slices}</div>
          <div class="kpi-subtitle">Dependency-ordered execution slices</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Target Architecture <span>☁️</span></div>
          <div class="kpi-value" style="font-size: 16px; font-weight: 600; margin-top: 8px;">{html.escape(target_frameworks)}</div>
          <div class="kpi-subtitle">Serverless &amp; managed cloud data tier</div>
        </div>
      </div>

      <!-- Executive Summary Panel -->
      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">📝 Executive Modernization Summary</div>
          <span class="badge badge-accent">CodMod Synthesized</span>
        </div>
        <p style="font-size: 15px; line-height: 1.7; color: var(--fg);">{html.escape(exec_summary or 'Assessment underway. Dual-lens CodMod semantic scan and Graphify AST topology synthesis active.')}</p>
      </div>

      <!-- Dual Column: Key Findings & Strategic Recommendations -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 24px; margin-bottom: 24px;">
        <!-- Key Findings -->
        <div class="panel" style="margin-bottom: 0;">
          <div class="panel-header">
            <div class="panel-title">🔍 Key Architectural Findings</div>
            <span class="badge badge-warning">{len(key_findings)} Items</span>
          </div>
          <ul style="list-style: none; display: flex; flex-direction: column; gap: 12px;">
            {findings_items}
          </ul>
        </div>

        <!-- Strategic Recommendations -->
        <div class="panel" style="margin-bottom: 0;">
          <div class="panel-header">
            <div class="panel-title">💡 Strategic Architecture Recommendations</div>
            <span class="badge badge-success">{len(strategic_recs)} Recommendations</span>
          </div>
          <ul style="list-style: none; display: flex; flex-direction: column; gap: 12px;">
            {recs_items}
          </ul>
        </div>
      </div>

      <!-- Phased Migration Roadmap -->
      {roadmap_panel}

    </div>

    <!-- ================= TAB 2: VERTICAL SLICES (KANBAN) ================= -->
    <div id="tab-slices" class="tab-pane">
      <div class="kanban-toolbar">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input type="text" id="slice-search" placeholder="Search slices, tasks, or modules..." oninput="filterSlices()" />
        </div>
        <div class="filter-btn-group">
          <button class="btn btn-primary" onclick="filterSliceNature('all', this)">All Slices</button>
          <button class="btn" onclick="filterSliceNature('serial', this)">[Serial] Only</button>
          <button class="btn" onclick="filterSliceNature('parallel', this)">[Parallel] Only</button>
        </div>
      </div>

      <div class="kanban-grid" id="kanban-container">
        {slices_rendered}
      </div>
    </div>

    <!-- ================= TAB 3: CENTRAL DEPENDENCY HUBS ================= -->
    <div id="tab-hubs" class="tab-pane">
      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">⚠️ Central Dependency Hubs Matrix (Highest Blast Radius)</div>
          <span class="badge badge-warning">{len(central_hubs)} Load-Bearing Classes</span>
        </div>
        <p style="font-size: 13px; color: var(--muted); margin-bottom: 16px;">
          Central Dependency Hubs are classes with the highest number of incoming callers and outgoing dependencies.
          Modifying these classes carries severe risk of regression cascading across the system. Apply Anti-Corruption Layers (ACLs) or Facade interfaces.
        </p>

        <div style="margin-bottom: 14px;">
          <input type="text" id="hub-search" placeholder="Filter central hubs by class name or module..." oninput="filterHubsTable()" style="width: 100%; max-width: 400px; background: var(--card); border: 1px solid var(--card-border); color: var(--fg); padding: 8px 12px; border-radius: 6px; font-size: 13px;" />
        </div>

        <div style="overflow-x: auto;">
          <table class="data-table" id="hubs-table">
            <thead>
              <tr>
                <th style="width: 60px; text-align: center;">Rank</th>
                <th>Core Class / Component</th>
                <th>Component Module</th>
                <th>Total Connections</th>
                <th>Callers (Inbound) / Dependencies (Outbound)</th>
                <th>Blast Radius</th>
                <th>Recommended Decoupling Action</th>
              </tr>
            </thead>
            <tbody>
              {hubs_rendered}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ================= TAB 4: COMPONENT MODULES & SUBSYSTEMS ================= -->
    <div id="tab-modules" class="tab-pane">
      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">🧩 Component Modules &amp; Subsystems ({total_mods})</div>
          <span class="badge badge-accent">Graphify AST Communities</span>
        </div>
        <p style="font-size: 13px; color: var(--muted); margin-bottom: 16px;">
          Detected cohesive functional clusters. Each module represents an architectural subsystem (e.g., Domain Models, JPA Repositories, MVC Web Controllers, Test Harnesses).
        </p>

        <div style="margin-bottom: 16px;">
          <input type="text" id="module-search" placeholder="Search modules or member files..." oninput="filterModules()" style="width: 100%; max-width: 400px; background: var(--card); border: 1px solid var(--card-border); color: var(--fg); padding: 8px 12px; border-radius: 6px; font-size: 13px;" />
        </div>

        <div class="module-grid" id="module-container">
          {modules_rendered}
        </div>
      </div>
    </div>

    <!-- ================= TAB 5: CODMOD ASSESSMENT REPORT ================= -->
    <div id="tab-codmod" class="tab-pane">
      <div class="embedded-container">
        <div class="embedded-header">
          <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-weight: 700; font-size: 14px;">Google Cloud CodMod Report (3.9 MB)</span>
            <div class="view-switch-group">
              <button class="btn btn-primary btn-sm" id="btn-codmod-iframe" onclick="switchCodmodView('iframe')">Embedded Full View</button>
              <button class="btn btn-sm" id="btn-codmod-digest" onclick="switchCodmodView('digest')">Synthesized Digest</button>
            </div>
          </div>
          <a href="{html.escape(codmod_open_href)}" target="_blank" class="btn btn-sm">Open in New Tab ↗</a>
        </div>

        <iframe id="codmod-iframe" class="embedded-iframe" src="{html.escape(codmod_iframe_src)}"></iframe>

        <div id="codmod-digest-view" style="display: none; padding: 24px; overflow-y: auto; height: 100%;">
          <div class="panel">
            <h3 style="margin-bottom: 12px;">📋 CodMod Key Findings &amp; Transformations</h3>
            <p style="font-size: 14px; margin-bottom: 16px;">{html.escape(exec_summary)}</p>
            
            <h4 style="margin: 16px 0 8px;">Work Plan Tasks ({len(work_plan)})</h4>
            <ol style="padding-left: 20px; font-size: 13px; line-height: 1.6;">
              {work_plan_items}
            </ol>

            <h4 style="margin: 16px 0 8px;">Flagged Codebase Files ({len(flagged_files)})</h4>
            <div style="max-height: 250px; overflow-y: auto; background: var(--code-bg); padding: 12px; border-radius: 8px; font-family: monospace; font-size: 12px;">
              {flagged_files_rendered}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ================= TAB 6: GRAPHIFY AST GRAPH ================= -->
    <div id="tab-graphify" class="tab-pane">
      <div class="embedded-container">
        <div class="embedded-header">
          <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-weight: 700; font-size: 14px;">Graphify AST Knowledge Graph</span>
            <div class="view-switch-group">
              <button class="btn btn-primary btn-sm" id="btn-graph-iframe" onclick="switchGraphView('iframe')">Interactive Graph</button>
              <button class="btn btn-sm" id="btn-graph-report" onclick="switchGraphView('report')">Topology Report</button>
            </div>
          </div>
          <a href="{html.escape(graph_open_href)}" target="_blank" class="btn btn-sm">Open in New Tab ↗</a>
        </div>

        <iframe id="graph-iframe" class="embedded-iframe" src="{html.escape(graph_iframe_src)}"></iframe>

        <div id="graph-report-view" style="display: none; padding: 24px; overflow-y: auto; height: 100%;">
          <div class="markdown-body">
            {graph_report_html}
          </div>
        </div>
      </div>
    </div>

    <!-- ================= TAB 7: MIGRATION PLAN ================= -->
    <div id="tab-plan" class="tab-pane">
      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">🗺️ Dependency-Ordered Migration Plan (05_PLAN.md)</div>
          <span class="badge badge-accent">Interactive Spec</span>
        </div>
        <div class="markdown-body">
          {plan_html}
        </div>
      </div>
    </div>

  </main>

  <!-- Footer -->
  <footer class="dash-footer">
    <p>⚡ Google Cloud CodMod + Graphify Modernization Dashboard • Emitted by <strong>Bean-Grinder</strong> • Dual-Write UI Sync Active</p>
  </footer>

  <script>
    function showTab(tabId) {{
      document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

      const targetPane = document.getElementById('tab-' + tabId);
      if (targetPane) {{
        targetPane.classList.add('active');
      }}

      const buttons = document.querySelectorAll('.tab-button');
      buttons.forEach(btn => {{
        if (btn.getAttribute('onclick') && btn.getAttribute('onclick').includes(tabId)) {{
          btn.classList.add('active');
        }}
      }});
    }}

    function toggleTheme() {{
      const htmlEl = document.documentElement;
      const current = htmlEl.getAttribute('data-theme') || 'dark';
      const next = current === 'dark' ? 'light' : 'dark';
      htmlEl.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);

      document.getElementById('theme-icon').textContent = next === 'dark' ? '☀️' : '🌙';
      document.getElementById('theme-text').textContent = next === 'dark' ? 'Light Mode' : 'Dark Mode';
    }}

    (function initTheme() {{
      const saved = localStorage.getItem('theme') || 'dark';
      document.documentElement.setAttribute('data-theme', saved);
      if (document.getElementById('theme-icon')) {{
        document.getElementById('theme-icon').textContent = saved === 'dark' ? '☀️' : '🌙';
        document.getElementById('theme-text').textContent = saved === 'dark' ? 'Light Mode' : 'Dark Mode';
      }}
    }})();

    function switchCodmodView(mode) {{
      const iframe = document.getElementById('codmod-iframe');
      const digest = document.getElementById('codmod-digest-view');
      const btnIframe = document.getElementById('btn-codmod-iframe');
      const btnDigest = document.getElementById('btn-codmod-digest');

      if (mode === 'iframe') {{
        iframe.style.display = 'block';
        digest.style.display = 'none';
        btnIframe.classList.add('btn-primary');
        btnDigest.classList.remove('btn-primary');
      }} else {{
        iframe.style.display = 'none';
        digest.style.display = 'block';
        btnIframe.classList.remove('btn-primary');
        btnDigest.classList.add('btn-primary');
      }}
    }}

    function switchGraphView(mode) {{
      const iframe = document.getElementById('graph-iframe');
      const report = document.getElementById('graph-report-view');
      const btnIframe = document.getElementById('btn-graph-iframe');
      const btnReport = document.getElementById('btn-graph-report');

      if (mode === 'iframe') {{
        iframe.style.display = 'block';
        report.style.display = 'none';
        btnIframe.classList.add('btn-primary');
        btnReport.classList.remove('btn-primary');
      }} else {{
        iframe.style.display = 'none';
        report.style.display = 'block';
        btnIframe.classList.remove('btn-primary');
        btnReport.classList.add('btn-primary');
      }}
    }}

    let currentNatureFilter = 'all';
    function filterSliceNature(nature, btn) {{
      currentNatureFilter = nature;
      document.querySelectorAll('.filter-btn-group button').forEach(b => b.classList.remove('btn-primary'));
      btn.classList.add('btn-primary');
      filterSlices();
    }}

    function filterSlices() {{
      const query = (document.getElementById('slice-search').value || '').toLowerCase();
      const cards = document.querySelectorAll('.slice-card');

      cards.forEach(card => {{
        const nature = card.getAttribute('data-nature') || '';
        const text = card.textContent.toLowerCase();

        const matchesNature = (currentNatureFilter === 'all') || (nature === currentNatureFilter);
        const matchesQuery = !query || text.includes(query);

        if (matchesNature && matchesQuery) {{
          card.style.display = 'flex';
        }} else {{
          card.style.display = 'none';
        }}
      }});
    }}

    function filterHubsTable() {{
      const query = (document.getElementById('hub-search').value || '').toLowerCase();
      const rows = document.querySelectorAll('#hubs-table tbody tr');

      rows.forEach(row => {{
        const text = row.textContent.toLowerCase();
        row.style.display = (!query || text.includes(query)) ? '' : 'none';
      }});
    }}

    function filterModules() {{
      const query = (document.getElementById('module-search').value || '').toLowerCase();
      const cards = document.querySelectorAll('.module-card');

      cards.forEach(card => {{
        const text = card.textContent.toLowerCase();
        card.style.display = (!query || text.includes(query)) ? 'block' : 'none';
      }});
    }}
  </script>
</body>
</html>
"""


def generate_modernization_dashboard(
    matrix_data: Dict[str, Any],
    codmod_data: Dict[str, Any],
    graph_data: Dict[str, Any],
    output_dir: Path,
    codmod_report_path: Optional[Path] = None,
    graph_html_path: Optional[Path] = None,
    graph_report_path: Optional[Path] = None,
    plan_path: Optional[Path] = None,
    brain_dir: Optional[str] = None,
    mirror: bool = True,
) -> Path:
    """
    Main orchestration entrypoint to generate modernization_dashboard.html,
    save it to output_dir, update visual-dashboard.html, and optionally mirror.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    dashboard_path = output_dir / "modernization_dashboard.html"

    codmod_rel_url = None
    codmod_file_url = None
    if codmod_report_path and codmod_report_path.exists():
        try:
            codmod_rel_url = os.path.relpath(codmod_report_path, output_dir)
        except ValueError:
            codmod_rel_url = codmod_report_path.name
        codmod_file_url = codmod_report_path.resolve().as_uri()

    graph_rel_url = None
    graph_file_url = None
    if graph_html_path and graph_html_path.exists():
        try:
            graph_rel_url = os.path.relpath(graph_html_path, output_dir)
        except ValueError:
            graph_rel_url = graph_html_path.name
        graph_file_url = graph_html_path.resolve().as_uri()

    graph_report_content = None
    if graph_report_path and graph_report_path.exists():
        graph_report_content = graph_report_path.read_text(encoding="utf-8", errors="replace")

    plan_content = None
    if plan_path and plan_path.exists():
        plan_content = plan_path.read_text(encoding="utf-8", errors="replace")

    html_content = build_dashboard_html(
        matrix_data=matrix_data,
        codmod_data=codmod_data,
        graph_data=graph_data,
        graph_report_content=graph_report_content,
        plan_markdown_content=plan_content,
        codmod_rel_url=codmod_rel_url,
        graph_rel_url=graph_rel_url,
        codmod_file_url=codmod_file_url,
        graph_file_url=graph_file_url,
    )

    dashboard_path.write_text(html_content, encoding="utf-8")
    print(f"✅ Emitted dashboard: {dashboard_path} ({len(html_content):,} bytes)")

    compat_path = output_dir / "visual-dashboard.html"
    compat_path.write_text(html_content, encoding="utf-8")

    if mirror:
        aux_files = []
        matrix_file = output_dir / "migration_matrix.json"
        if matrix_file.exists():
            aux_files.append((matrix_file, "migration_matrix.json"))
        if plan_path and plan_path.exists():
            aux_files.append((plan_path, "05_plan.md"))

        mirrored = mirror_dashboard(
            dashboard_path=dashboard_path,
            target_filename="00_visual-dashboard.html",
            brain_dir=brain_dir,
            aux_files=aux_files,
        )
        if mirrored:
            for m in mirrored:
                print(f"🪞 Mirrored UI dashboard: {m}")

    return dashboard_path


def main():
    parser = argparse.ArgumentParser(description="Generate unified modernization HTML dashboard.")
    parser.add_argument("--matrix", required=True, type=Path, help="Path to migration_matrix.json")
    parser.add_argument("--report", required=True, type=Path, help="Path to codmod HTML report")
    parser.add_argument("--graph", required=True, type=Path, help="Path to graphify-out/graph.json")
    parser.add_argument("--graph-html", type=Path, help="Path to graphify-out/graph.html")
    parser.add_argument("--graph-report", type=Path, help="Path to graphify-out/GRAPH_REPORT.md")
    parser.add_argument("--plan", type=Path, help="Path to 05_PLAN.md")
    parser.add_argument("--output-dir", type=Path, default=Path("."), help="Output directory")
    parser.add_argument("--brain-dir", type=str, help="Explicit brain artifact directory")
    parser.add_argument("--no-mirror", action="store_true", help="Disable dual-write brain mirroring")

    args = parser.parse_args()

    with open(args.matrix, "r", encoding="utf-8") as f:
        matrix_data = json.load(f)

    with open(args.graph, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    try:
        try:
            from scripts.digest_report import parse_codmod_report
        except ImportError:
            try:
                from digest_report import parse_codmod_report
            except ImportError:
                sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
                from scripts.digest_report import parse_codmod_report
        codmod_data = parse_codmod_report(args.report)
    except Exception:
        codmod_data = {"title": "Application Modernization", "executive_summary": "Parsed report."}

    generate_modernization_dashboard(
        matrix_data=matrix_data,
        codmod_data=codmod_data,
        graph_data=graph_data,
        output_dir=args.output_dir,
        codmod_report_path=args.report,
        graph_html_path=args.graph_html,
        graph_report_path=args.graph_report,
        plan_path=args.plan,
        brain_dir=args.brain_dir,
        mirror=not args.no_mirror,
    )


if __name__ == "__main__":
    main()
