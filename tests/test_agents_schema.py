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
Agent Schema and Frontmatter Test Suite.
Validates all 13 agent markdown files in agents/ for required YAML frontmatter fields,
normalized tool names, and non-empty markdown definitions.
"""

import os
import unittest
import yaml


def find_repo_root():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(script_dir, ".."))


class TestAgentsSchema(unittest.TestCase):

    def setUp(self):
        self.repo_root = find_repo_root()
        self.agents_dir = os.path.join(self.repo_root, "agents")

    def test_agents_directory_exists(self):
        self.assertTrue(os.path.exists(self.agents_dir), f"Agents directory not found at {self.agents_dir}")

    def test_all_agents_have_valid_frontmatter_and_normalized_tools(self):
        agent_files = [
            f for f in os.listdir(self.agents_dir)
            if f.endswith(".md") and not f.startswith(".")
        ]
        self.assertEqual(len(agent_files), 13, "Expected exactly 13 agents in agents/")

        required_fields = ["name", "description", "kind", "tools", "model"]
        allowed_tools = {"read_file", "write_file", "edit_file", "run_command"}
        forbidden_tools = {"view_file", "write_to_file", "replace_file_content", "grep_search", "find_by_name", "list_dir"}

        for agent_file in sorted(agent_files):
            agent_path = os.path.join(self.agents_dir, agent_file)
            with self.subTest(agent=agent_file):
                with open(agent_path, "r", encoding="utf-8") as f:
                    content = f.read()

                self.assertTrue(
                    content.startswith("---"),
                    f"{agent_path} does not start with YAML frontmatter delimiter '---'"
                )

                parts = content.split("---", 2)
                self.assertGreaterEqual(
                    len(parts), 3,
                    f"{agent_path} frontmatter delimiter '---' is invalid or not closed"
                )

                frontmatter_raw = parts[1]
                body = parts[2].strip()

                try:
                    data = yaml.safe_load(frontmatter_raw)
                except Exception as e:
                    self.fail(f"YAML parsing error in {agent_path}: {e}")

                self.assertIsInstance(data, dict, f"Frontmatter in {agent_path} must be a dictionary")

                for field in required_fields:
                    self.assertIn(field, data, f"Frontmatter in {agent_path} missing required field '{field}'")
                    self.assertTrue(data[field], f"Field '{field}' in {agent_path} cannot be empty")

                self.assertIs(data.get("subagent"), True)
                self.assertIs(data.get("mainAgent"), False)
                self.assertEqual(data.get("model"), "inherit")

                tools = data["tools"]
                self.assertIsInstance(tools, list, f"'tools' in {agent_path} must be a list")
                self.assertGreater(len(tools), 0, f"'tools' in {agent_path} cannot be empty")
                for t in tools:
                    self.assertNotIn(t, forbidden_tools, f"Legacy tool '{t}' found in {agent_file}")
                    self.assertIn(t, allowed_tools, f"Unexpected tool '{t}' in {agent_file}")

                self.assertGreater(len(body), 50, f"Markdown body in {agent_path} is too short")

    def test_expected_13_agents_present_and_removed_absent(self):
        expected = {
            "ast-grinder.md",
            "codmod-assessor.md",
            "graphify-scout.md",
            "migration-scout.md",
            "msbuild.md",
            "reviewer-architect.md",
            "reviewer-engineer.md",
            "reviewer-exec.md",
            "reviewer-pm.md",
            "runtime-parity-verifier.md",
            "seam-scout.md",
            "spec-recovery-agent.md",
            "synthesis-agent.md",
        }
        present = {f for f in os.listdir(self.agents_dir) if f.endswith(".md")}
        self.assertEqual(present, expected)
        self.assertNotIn("review-arbiter.md", present)
        self.assertFalse(os.path.exists(os.path.join(self.repo_root, "scripts", "generate_dashboard.py")))
        self.assertFalse(os.path.exists(os.path.join(self.repo_root, "gemini-extension.json")))


if __name__ == "__main__":
    unittest.main()
