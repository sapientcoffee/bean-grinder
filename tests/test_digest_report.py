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

"""Unit tests for scripts/digest_report.py."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

from scripts.digest_report import (
    parse_codmod_report,
    parse_graphify_graph,
    synthesize_migration_slices,
    generate_plan_markdown,
)


class TestDigestReport(unittest.TestCase):
    """Test suite for CodMod and Graphify report digestion and slicing."""

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.test_dir.name)

        # Create mock HTML report
        self.mock_html = self.tmp_path / "mock_report.html"
        self.mock_html.write_text("""
        <!DOCTYPE html>
        <html>
        <head><title>Spring PetClinic Modernization Assessment</title></head>
        <body>
            <h1>Assessment Overview</h1>
            <h2>Executive Summary</h2>
            <p>Migrating Spring PetClinic from Java 17 to Java 21 on Google Cloud.</p>
            <h2>Key Findings</h2>
            <ul>
                <li>Spring Boot 3.x upgrade target</li>
                <li>Jakarta namespace migrations</li>
            </ul>
            <h2>Migration Roadmap (Phased Approach)</h2>
            <table>
                <tr><th>Phase</th><th>Focus Area</th><th>High-Level Objectives</th></tr>
                <tr><td>Phase 1</td><td>Environment</td><td>JDK 21 Setup</td></tr>
                <tr><td>Phase 2</td><td>Dependencies</td><td>Spring Boot 3 bump</td></tr>
            </table>
            <h2>Task Complexity & Effort Matrix</h2>
            <table>
                <tr><th>Task</th><th>Category</th><th>Complexity</th><th>Estimated Effort</th></tr>
                <tr><td>JDK 21 Compiler Target</td><td>Build</td><td>Low</td><td>Small</td></tr>
                <tr><td>JPA Eager to Lazy</td><td>Data Layer</td><td>Medium</td><td>Medium</td></tr>
            </table>
        </body>
        </html>
        """, encoding="utf-8")

        # Create mock graph.json
        self.mock_graph = self.tmp_path / "graph.json"
        graph_data = {
            "directed": True,
            "multigraph": False,
            "nodes": [
                {
                    "id": "owner_entity",
                    "label": "Owner",
                    "community": 1,
                    "community_name": "Domain Entities & Models",
                    "source_file": "src/main/java/Owner.java"
                },
                {
                    "id": "pet_entity",
                    "label": "Pet",
                    "community": 1,
                    "community_name": "Domain Entities & Models",
                    "source_file": "src/main/java/Pet.java"
                },
                {
                    "id": "owner_repo",
                    "label": "OwnerRepository",
                    "community": 2,
                    "community_name": "Spring Data JPA Repositories",
                    "source_file": "src/main/java/OwnerRepository.java"
                },
                {
                    "id": "owner_controller",
                    "label": "OwnerController",
                    "community": 3,
                    "community_name": "Spring MVC Controllers",
                    "source_file": "src/main/java/OwnerController.java"
                },
                {
                    "id": "maven_wrapper",
                    "label": "Maven Wrapper",
                    "community": 4,
                    "community_name": "Maven Wrapper & Environment",
                    "source_file": ".mvn/wrapper/maven-wrapper.properties"
                }
            ],
            "links": [
                {"source": "owner_controller", "target": "owner_repo", "relation": "calls"},
                {"source": "owner_repo", "target": "owner_entity", "relation": "uses"},
                {"source": "owner_entity", "target": "pet_entity", "relation": "references"},
                {"source": "owner_controller", "target": "owner_entity", "relation": "binds"},
                {"source": "owner_repo", "target": "pet_entity", "relation": "queries"}
            ]
        }
        self.mock_graph.write_text(json.dumps(graph_data), encoding="utf-8")

    def tearDown(self):
        self.test_dir.cleanup()

    def test_parse_codmod_report(self):
        data = parse_codmod_report(self.mock_html)
        self.assertIn("Spring PetClinic", data["title"])
        self.assertIn("Java 21", data["executive_summary"])
        self.assertEqual(len(data["roadmap_phases"]), 2)
        self.assertEqual(len(data["complexity_matrix"]), 2)
        self.assertEqual(data["complexity_matrix"][0]["task"], "JDK 21 Compiler Target")

    def test_parse_graphify_graph(self):
        graph_data = parse_graphify_graph(self.mock_graph)
        self.assertEqual(graph_data["total_nodes"], 5)
        self.assertEqual(graph_data["total_edges"], 5)
        self.assertIn("component_modules", graph_data)
        self.assertIn("central_hubs", graph_data)
        self.assertIn(1, graph_data["component_modules"])
        self.assertIn(2, graph_data["component_modules"])
        self.assertIn(3, graph_data["component_modules"])

    def test_synthesize_migration_slices(self):
        codmod_data = parse_codmod_report(self.mock_html)
        graph_data = parse_graphify_graph(self.mock_graph)
        matrix = synthesize_migration_slices(codmod_data, graph_data)

        self.assertIn("slices", matrix)
        self.assertEqual(len(matrix["slices"]), 6)
        self.assertIn("total_component_modules", matrix)
        self.assertIn("total_central_dependency_hubs", matrix)
        slice_names = [s["name"] for s in matrix["slices"]]
        self.assertIn("Build & Runtime Foundation", slice_names)
        self.assertIn("Standalone Leaf Modules & Lookup Models", slice_names)
        self.assertIn("Core Domain Repositories & Data Layer", slice_names)
        self.assertIn("Central Dependency Hubs & Monolith Decoupling", slice_names)
        self.assertIn("Ingress Controllers & Edge Adapters", slice_names)

    def test_generate_plan_markdown(self):
        codmod_data = parse_codmod_report(self.mock_html)
        graph_data = parse_graphify_graph(self.mock_graph)
        matrix = synthesize_migration_slices(codmod_data, graph_data)

        plan_md = generate_plan_markdown(matrix, self.tmp_path / "05_PLAN.md")
        self.assertIn("# 🗺️ Modernization Implementation Plan", plan_md)
        self.assertIn("Component Modules / Subsystems", plan_md)
        self.assertIn("Central Dependency Hubs", plan_md)
        self.assertIn("Slice 0: Build & Runtime Foundation", plan_md)
        self.assertIn("Slice 3: Central Dependency Hubs & Monolith Decoupling", plan_md)
        self.assertIn("Verification", plan_md)

    def test_real_petclinic_data_if_available(self):
        real_html = Path("/home/robedwards/workspace/spring-petclinic/petclinic-standard-report-3.6.html")
        real_graph = Path("/home/robedwards/workspace/spring-petclinic/graphify-out/graph.json")

        if real_html.exists() and real_graph.exists():
            codmod_data = parse_codmod_report(real_html)
            graph_data = parse_graphify_graph(real_graph)
            matrix = synthesize_migration_slices(codmod_data, graph_data)

    def test_main_emits_dashboard(self):
        import subprocess
        out_dir = self.tmp_path / "out_slices"
        cmd = [
            sys.executable,
            "scripts/digest_report.py",
            "--report", str(self.mock_html),
            "--graph", str(self.mock_graph),
            "--output-dir", str(out_dir),
            "--no-mirror"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd="/home/robedwards/workspace/bean-grinder")
        self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
        self.assertTrue((out_dir / "migration_matrix.json").exists())
        self.assertTrue((out_dir / "05_PLAN.md").exists())
        self.assertTrue((out_dir / "modernization_dashboard.html").exists())
        self.assertTrue((out_dir / "visual-dashboard.html").exists())
        dash_content = (out_dir / "modernization_dashboard.html").read_text(encoding="utf-8")
        self.assertIn("Unified Modernization Dashboard", dash_content)
        self.assertIn("tab-scorecard", dash_content)


if __name__ == "__main__":
    unittest.main()
