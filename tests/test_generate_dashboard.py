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

import json
from pathlib import Path
import tempfile
import unittest

from scripts.generate_dashboard import (
    build_dashboard_html,
    generate_modernization_dashboard,
    mirror_dashboard,
)


class TestGenerateDashboard(unittest.TestCase):

    def setUp(self):
        self.matrix_data = {
            "application_title": "Pet Clinic Modernization",
            "total_component_modules": 4,
            "total_central_dependency_hubs": 2,
            "total_connections": 150,
            "total_nodes": 45,
            "central_dependency_hubs": [
                {
                    "node_id": "com.example.Owner",
                    "label": "Owner",
                    "degree": 32,
                    "total_connections": 32,
                    "in_degree": 20,
                    "inbound_callers": 20,
                    "out_degree": 12,
                    "outbound_dependencies": 12,
                    "community_id": 1,
                    "module_name": "Domain Entities",
                    "source_file": "src/main/java/org/springframework/samples/petclinic/owner/Owner.java"
                },
                {
                    "node_id": "com.example.Pet",
                    "label": "Pet",
                    "degree": 19,
                    "total_connections": 19,
                    "in_degree": 10,
                    "inbound_callers": 10,
                    "out_degree": 9,
                    "outbound_dependencies": 9,
                    "community_id": 1,
                    "module_name": "Domain Entities",
                    "source_file": "src/main/java/org/springframework/samples/petclinic/owner/Pet.java"
                }
            ],
            "slices": [
                {
                    "slice_id": "Slice 0",
                    "name": "Build & Runtime Foundation",
                    "execution_order": 0,
                    "nature": "[Serial]",
                    "description": "Baseline toolchain upgrade.",
                    "component_modules": ["Toolchain"],
                    "central_hubs_addressed": [],
                    "codmod_tasks": [
                        {"task": "Upgrade to Java 21", "complexity": "Low", "effort": "Small"}
                    ],
                    "verification_strategy": "./gradlew check"
                },
                {
                    "slice_id": "Slice 1",
                    "name": "Leaf Models",
                    "execution_order": 1,
                    "nature": "[Parallel]",
                    "description": "Migrate standalone models.",
                    "component_modules": ["Models"],
                    "central_hubs_addressed": ["Pet"],
                    "codmod_tasks": [
                        {"task": "Convert Pet to Record", "complexity": "Medium", "effort": "Small"}
                    ],
                    "verification_strategy": "./gradlew test"
                }
            ]
        }

        self.codmod_data = {
            "title": "Pet Clinic Modernization",
            "executive_summary": "Legacy Spring Boot 2 to Spring Boot 3 migration.",
            "key_findings": [
                "Tight coupling in domain entities.",
                "Eager relationship fetching."
            ],
            "strategic_recommendations": [
                "Upgrade to Java 21 and Spring Boot 3.",
                "Enable Virtual Threads."
            ],
            "roadmap_phases": [
                {
                    "phase": "Unit Tests",
                    "focus": "Domain verification",
                    "objectives": "ClinicServiceTests"
                }
            ],
            "work_plan_tasks": [
                "Upgrade Java version in pom.xml",
                "Migrate javax to jakarta imports"
            ],
            "flagged_files": [
                "src/main/java/Owner.java",
                "src/main/java/Pet.java"
            ]
        }

        self.graph_data = {
            "total_nodes": 45,
            "total_edges": 150,
            "component_modules": {
                "0": {
                    "name": "Test Harness",
                    "nodes": ["Test1", "Test2"],
                    "files": ["Test1.java", "Test2.java"],
                    "central_hubs": [],
                    "in_degree": 5,
                    "out_degree": 2
                },
                "1": {
                    "name": "Domain Entities",
                    "nodes": ["Owner", "Pet"],
                    "files": ["Owner.java", "Pet.java"],
                    "central_hubs": ["Owner", "Pet"],
                    "in_degree": 30,
                    "out_degree": 15
                }
            }
        }

    def test_build_dashboard_html_structure(self):
        html = build_dashboard_html(
            matrix_data=self.matrix_data,
            codmod_data=self.codmod_data,
            graph_data=self.graph_data,
            graph_report_content="# Graphify Architecture Report\n- 45 nodes\n- 150 edges",
            plan_markdown_content="# Modernization Plan\n## Slices\nExecute Slice 0 first."
        )

        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Pet Clinic Modernization", html)
        self.assertIn("tab-scorecard", html)
        self.assertIn("tab-slices", html)
        self.assertIn("tab-hubs", html)
        self.assertIn("tab-modules", html)
        self.assertIn("tab-codmod", html)
        self.assertIn("tab-graphify", html)
        self.assertIn("tab-plan", html)

        # Check KPIs
        self.assertIn("150", html)  # Connections
        self.assertIn("45", html)   # Nodes
        self.assertIn("Owner", html)
        self.assertIn("Critical", html) # Degree >= 30
        self.assertIn("High", html)     # Degree >= 18

        # Check Slices
        self.assertIn("Slice 0", html)
        self.assertIn("Slice 1", html)
        self.assertIn('data-nature="serial"', html)
        self.assertIn('data-nature="parallel"', html)

    def test_generate_modernization_dashboard_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            dash_file = generate_modernization_dashboard(
                matrix_data=self.matrix_data,
                codmod_data=self.codmod_data,
                graph_data=self.graph_data,
                output_dir=out_dir,
                mirror=False
            )

            self.assertTrue(dash_file.exists())
            self.assertEqual(dash_file.name, "modernization_dashboard.html")
            compat_file = out_dir / "visual-dashboard.html"
            self.assertTrue(compat_file.exists())
            self.assertGreater(dash_file.stat().st_size, 5000)

    def test_mirror_dashboard(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "plan"
            brain_dir = Path(tmpdir) / "brain"
            out_dir.mkdir(parents=True)
            brain_dir.mkdir(parents=True)

            dash_file = out_dir / "modernization_dashboard.html"
            dash_file.write_text("<html><body>Dashboard</body></html>", encoding="utf-8")

            mirrored = mirror_dashboard(
                dashboard_path=dash_file,
                target_filename="00_visual-dashboard.html",
                brain_dir=str(brain_dir)
            )

            self.assertTrue(len(mirrored) >= 1)
            target = brain_dir / "00_visual-dashboard.html"
            self.assertTrue(target.exists())
            self.assertEqual(target.read_text(encoding="utf-8"), "<html><body>Dashboard</body></html>")


if __name__ == "__main__":
    unittest.main()
