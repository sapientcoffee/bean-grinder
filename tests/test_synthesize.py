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

"""Unit tests for standalone synthesis and skills/synthesize/scripts/synthesize_runner.py."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.digest_report import (
    parse_codmod_report,
    parse_graphify_graph,
    parse_markdown_table_rows,
    synthesize_migration_slices,
)
from skills.synthesize.scripts.synthesize_runner import (
    resolve_run_dir,
    locate_discovery_artifacts,
    run_synthesis,
)
from scripts.run_manager import RunManager, STAGE_DIRS


class TestSynthesizeRunner(unittest.TestCase):
    """Test suite for standalone synthesis runner and scout reconciliation."""

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.test_dir.name)

        # Create mock run hierarchy
        self.run_mgr = RunManager(base_dir=self.tmp_path)
        self.run_dir = self.run_mgr.scaffold_run(app_name="PetClinicTest")

        # Discovery files
        disc_dir = self.run_dir / STAGE_DIRS["stage1_discovery"]
        self.mock_report = disc_dir / "codmod_assessment_report.html"
        self.mock_report.write_text("""
        <!DOCTYPE html>
        <html>
        <head><title>Spring PetClinic Modernization Assessment</title></head>
        <body>
            <h1>Assessment Overview</h1>
            <p>Migrating Spring PetClinic from Java 17 to Java 21 on Google Cloud.</p>
        </body>
        </html>
        """, encoding="utf-8")

        self.mock_graph = disc_dir / "graphify_ast_graph.json"
        graph_data = {
            "directed": True,
            "multigraph": False,
            "nodes": [
                {"id": "owner_entity", "label": "Owner", "community": 1, "community_name": "Domain Entities"},
                {"id": "owner_repo", "label": "OwnerRepository", "community": 2, "community_name": "Data JPA"},
            ],
            "links": [
                {"source": "owner_repo", "target": "owner_entity", "relation": "uses"}
            ]
        }
        self.mock_graph.write_text(json.dumps(graph_data), encoding="utf-8")

        # Mock seams report
        self.mock_seams = disc_dir / "seam_findings.md"
        self.mock_seams.write_text("""
        # Seam Findings
        | Component ID | Target Class | Seam Type | Decoupling Pattern | Blast Radius |
        | :--- | :--- | :--- | :--- | :--- |
        | `SEAM-01` | OwnerRepository | Object Seam | Branch by Abstraction | 5 connections |
        """, encoding="utf-8")

        # Mock specs report with ambiguous invariant
        self.mock_specs = disc_dir / "spec_invariants.md"
        self.mock_specs.write_text("""
        # Spec Invariants
        | Requirement ID | Domain Rule Summary | Source Code Location | Preconditions | Postconditions | Review Status |
        | :--- | :--- | :--- | :--- | :--- | :--- |
        | `RULE-VET-01` | Validate specialty assignment | `Vet.java:45-60` | Specialty exists | Add to vet | Verified |
        | `RULE-OWN-02` | Legacy grandfathered discount | `Billing.java:110` | Created < 2015 | 10% discount | [AMBIGUOUS_SPEC_REQUIRES_HUMAN_REVIEW] |
        """, encoding="utf-8")

    def tearDown(self):
        self.test_dir.cleanup()

    def test_parse_markdown_table_rows(self):
        content = """
        | Header One | Header Two |
        | :--- | :--- |
        | Val 1 | Val 2 |
        """
        rows = parse_markdown_table_rows(content)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["header_one"], "Val 1")
        self.assertEqual(rows[0]["header_two"], "Val 2")

    def test_resolve_run_dir(self):
        resolved = resolve_run_dir(self.tmp_path, "latest")
        self.assertEqual(resolved.resolve(), self.run_dir.resolve())

    def test_locate_discovery_artifacts(self):
        artifacts = locate_discovery_artifacts(self.run_dir)
        self.assertIsNotNone(artifacts["report"])
        self.assertIsNotNone(artifacts["graph"])
        self.assertIsNotNone(artifacts["seams"])
        self.assertIsNotNone(artifacts["specs"])

    def test_run_synthesis_end_to_end(self):
        matrix = run_synthesis(
            run_dir=self.run_dir,
            base_dir=self.tmp_path,
            no_dashboard=False,
            no_mirror=True
        )
        self.assertIn("slices", matrix)
        self.assertIn("ambiguous_specs", matrix)
        self.assertEqual(matrix["ambiguous_specs_count"], 1)
        self.assertEqual(matrix["seams_inventory"][0]["target"], "OwnerRepository")

        # Check emitted files
        stage2 = self.run_dir / STAGE_DIRS["stage2_synthesis"]
        stage4 = self.run_dir / STAGE_DIRS["stage4_migration_plan"]
        self.assertTrue((stage2 / "migration_matrix.json").exists())
        self.assertTrue((stage2 / "vertical_slices.json").exists())
        self.assertTrue((stage4 / "05_PLAN.md").exists())
        self.assertTrue((self.run_dir / "index.html").exists())

        plan_content = (stage4 / "05_PLAN.md").read_text(encoding="utf-8")
        self.assertIn("Ambiguous Specifications Requiring Human Approval", plan_content)
        self.assertIn("RULE-OWN-02", plan_content)

    def test_digest_report_from_run_cli(self):
        cmd = [
            sys.executable,
            "scripts/digest_report.py",
            "--from-run", str(self.run_dir),
            "--no-mirror"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd="/home/robedwards/workspace/bean-grinder")
        self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
        self.assertTrue((self.run_dir / "02_synthesis" / "migration_matrix.json").exists())


if __name__ == "__main__":
    unittest.main()
