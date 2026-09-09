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

"""Unit tests for RunManager and stage-based assessment directory structure."""

import json
from pathlib import Path
import tempfile
import unittest

from scripts.run_manager import RunManager, STAGE_DIRS


class TestRunManager(unittest.TestCase):
    """Test suite for RunManager directory scaffolding and multi-run navigation."""

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.test_dir.name)
        self.mgr = RunManager(base_dir=self.base_dir)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_scaffold_run(self):
        run_dir = self.mgr.scaffold_run(run_id="20260909_140000_petclinic", app_name="PetClinic")
        self.assertTrue(run_dir.exists())

        # Check all 5 stage directories exist
        for stage_folder in STAGE_DIRS.values():
            self.assertTrue((run_dir / stage_folder).is_dir(), f"Missing stage folder: {stage_folder}")

        # Check manifest
        manifest_file = run_dir / "run_manifest.json"
        self.assertTrue(manifest_file.exists())
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        self.assertEqual(manifest["run_id"], "20260909_140000_petclinic")
        self.assertEqual(manifest["app_name"], "PetClinic")
        self.assertEqual(manifest["status"], "INITIALIZED")

        # Check latest symlink
        latest_link = self.base_dir / "latest"
        self.assertTrue(latest_link.exists())
        self.assertEqual(latest_link.resolve(), run_dir.resolve())

    def test_organize_discovery_artifacts(self):
        run_dir = self.mgr.scaffold_run(run_id="run_artifacts_test")

        # Create dummy discovery files
        dummy_report = self.base_dir / "raw_report.html"
        dummy_report.write_text("<html>CodMod Report</html>", encoding="utf-8")

        dummy_graph_json = self.base_dir / "graph.json"
        dummy_graph_json.write_text('{"nodes": []}', encoding="utf-8")

        dummy_graph_html = self.base_dir / "graph.html"
        dummy_graph_html.write_text("<html>Graph Visualizer</html>", encoding="utf-8")

        dummy_graph_report = self.base_dir / "GRAPH_REPORT.md"
        dummy_graph_report.write_text("# Graph Report", encoding="utf-8")

        dummy_telemetry = self.base_dir / "telemetry.json"
        dummy_telemetry.write_text('{"time_sec": 12.5}', encoding="utf-8")

        destinations = self.mgr.organize_discovery_artifacts(
            run_dir=run_dir,
            codmod_report_path=dummy_report,
            graph_json_path=dummy_graph_json,
            graph_html_path=dummy_graph_html,
            graph_report_path=dummy_graph_report,
            telemetry_path=dummy_telemetry,
        )

        disc_dir = run_dir / "01_discovery"
        self.assertTrue((disc_dir / "codmod_assessment_report.html").exists())
        self.assertTrue((disc_dir / "graphify_ast_graph.json").exists())
        self.assertTrue((disc_dir / "graphify_visualizer.html").exists())
        self.assertTrue((disc_dir / "graphify_architecture_report.md").exists())
        self.assertTrue((disc_dir / "codmod_execution_telemetry.json").exists())

        self.assertEqual(destinations["codmod_report"].name, "codmod_assessment_report.html")

    def test_update_manifest(self):
        run_dir = self.mgr.scaffold_run(run_id="run_manifest_test")
        updated = self.mgr.update_manifest(
            run_dir,
            status="SYNTHESIS_COMPLETE",
            scorecard={"modules": 4, "hubs": 2}
        )
        self.assertEqual(updated["status"], "SYNTHESIS_COMPLETE")
        self.assertEqual(updated["scorecard"]["modules"], 4)

    def test_list_runs_and_root_index(self):
        run1 = self.mgr.scaffold_run(run_id="20260909_100000_app1", app_name="AppOne")
        run2 = self.mgr.scaffold_run(run_id="20260909_110000_app2", app_name="AppTwo")

        # Mock an index.html in run2
        (run2 / "index.html").write_text("<!DOCTYPE html><html><body><h1>Modernization</h1></body></html>", encoding="utf-8")

        runs = self.mgr.list_runs()
        self.assertEqual(len(runs), 2)

        root_index = self.mgr.update_root_index(active_run_dir=run2)
        self.assertTrue(root_index.exists())
        content = root_index.read_text(encoding="utf-8")

        self.assertIn("bean-grinder-run-nav", content)
        self.assertIn("20260909_100000_app1", content)
        self.assertIn("20260909_110000_app2", content)
        self.assertIn("Modernization", content)


if __name__ == "__main__":
    unittest.main()
