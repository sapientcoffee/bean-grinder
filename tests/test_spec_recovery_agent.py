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
Unit tests for spec-recovery-agent and seam-scout agent definitions.
Ensures Human-in-the-Loop review tokens and Feathers' seam taxonomies are present.
"""

import os
import unittest
import yaml


def find_repo_root():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(script_dir, ".."))


class TestSpecRecoveryAndSeamScout(unittest.TestCase):

    def setUp(self):
        self.repo_root = find_repo_root()
        self.agents_dir = os.path.join(self.repo_root, "agents")

    def test_spec_recovery_agent_hitl_directives(self):
        agent_path = os.path.join(self.agents_dir, "spec-recovery-agent.md")
        self.assertTrue(os.path.exists(agent_path), f"Missing {agent_path}")

        with open(agent_path, "r", encoding="utf-8") as f:
            content = f.read()

        parts = content.split("---", 2)
        self.assertGreaterEqual(len(parts), 3)
        fm = yaml.safe_load(parts[1])
        body = parts[2]

        self.assertEqual(fm.get("name"), "spec-recovery-agent")
        self.assertIn("[AMBIGUOUS_SPEC_REQUIRES_HUMAN_REVIEW]", body)
        self.assertIn("Human-in-the-Loop", body)
        self.assertIn("Bounded Contexts", body)

    def test_seam_scout_taxonomies(self):
        agent_path = os.path.join(self.agents_dir, "seam-scout.md")
        self.assertTrue(os.path.exists(agent_path), f"Missing {agent_path}")

        with open(agent_path, "r", encoding="utf-8") as f:
            content = f.read()

        parts = content.split("---", 2)
        self.assertGreaterEqual(len(parts), 3)
        fm = yaml.safe_load(parts[1])
        body = parts[2]

        self.assertEqual(fm.get("name"), "seam-scout")
        self.assertIn("Object Seams", body)
        self.assertIn("Link Seams", body)
        self.assertIn("Preprocessor Seams", body)
        self.assertIn("Branch by Abstraction", body)
        self.assertIn("Sprout Method", body)


if __name__ == "__main__":
    unittest.main()
