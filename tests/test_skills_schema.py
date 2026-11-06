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
Skill Schema and Frontmatter Test Suite.
Validates all SKILL.md files in skills/ for required YAML frontmatter fields
and script file path references.
"""

import os
import sys
import unittest
import yaml


def find_repo_root():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(script_dir, ".."))


class TestSkillsSchema(unittest.TestCase):

    def setUp(self):
        self.repo_root = find_repo_root()
        self.skills_dir = os.path.join(self.repo_root, "skills")

    def test_skills_directory_exists(self):
        self.assertTrue(os.path.exists(self.skills_dir), f"Skills directory not found at {self.skills_dir}")

    def test_all_skills_have_skill_md_and_valid_frontmatter(self):
        skill_folders = [
            d for d in os.listdir(self.skills_dir)
            if os.path.isdir(os.path.join(self.skills_dir, d)) and not d.startswith(".")
        ]
        self.assertGreater(len(skill_folders), 0, "No skill directories found under skills/")

        for skill_name in sorted(skill_folders):
            skill_folder_path = os.path.join(self.skills_dir, skill_name)
            skill_md_path = os.path.join(skill_folder_path, "SKILL.md")

            with self.subTest(skill=skill_name):
                self.assertTrue(
                    os.path.exists(skill_md_path),
                    f"Missing SKILL.md in skill directory: {skill_folder_path}"
                )

                with open(skill_md_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Frontmatter parsing
                self.assertTrue(
                    content.startswith("---"),
                    f"{skill_md_path} does not start with YAML frontmatter delimiter '---'"
                )

                parts = content.split("---", 2)
                self.assertGreaterEqual(
                    len(parts), 3,
                    f"{skill_md_path} frontmatter delimiter '---' is invalid or not closed"
                )

                frontmatter_raw = parts[1]
                try:
                    data = yaml.safe_load(frontmatter_raw)
                except Exception as e:
                    self.fail(f"YAML parsing error in {skill_md_path}: {e}")

                self.assertIsInstance(
                    data, dict,
                    f"Frontmatter in {skill_md_path} must be a dictionary"
                )
                self.assertIn(
                    "name", data,
                    f"Frontmatter in {skill_md_path} missing required 'name' field"
                )
                self.assertIn(
                    "description", data,
                    f"Frontmatter in {skill_md_path} missing required 'description' field"
                )
                self.assertTrue(
                    data["name"],
                    f"'name' field in {skill_md_path} cannot be empty"
                )
                self.assertTrue(
                    data["description"],
                    f"'description' field in {skill_md_path} cannot be empty"
                )

    def test_adversarial_review_skill_supports_enterprise_teamwork_mode(self):
        adv_skill_path = os.path.join(self.skills_dir, "adversarial-review", "SKILL.md")
        with open(adv_skill_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Mode A: Hub-and-Spoke Concurrent Dispatch (`invoke_subagent`)", content)
        self.assertIn("Mode B: Antigravity Enterprise `/teamwork` Autonomous Stakeholder Council", content)
        self.assertIn("@synthesis-agent", content)
        self.assertIn("@reviewer-exec", content)
        self.assertIn("@reviewer-architect", content)
        self.assertIn("@reviewer-pm", content)
        self.assertIn("@reviewer-engineer", content)
        self.assertIn("@review-arbiter", content)
        self.assertIn("send_message", content)
        self.assertIn("In-Process Modular Monolith Facade", content)
        self.assertIn("Legacy Quirk Adapter Envelope", content)
        self.assertIn("Phased Criticality Slicing", content)

    def test_rewrite_and_assess_skills_enforce_subagent_delegation_and_teamwork_guidance(self):
        rewrite_skill_path = os.path.join(self.skills_dir, "rewrite", "SKILL.md")
        with open(rewrite_skill_path, "r", encoding="utf-8") as f:
            rewrite_content = f.read()

        for agent in [
            "@spec-recovery-agent",
            "@seam-scout",
            "@synthesis-agent",
            "@ast-grinder",
            "@runtime-parity-verifier",
        ]:
            self.assertIn(agent, rewrite_content, f"Expected {agent} delegation in rewrite/SKILL.md")

        self.assertIn("/teamwork", rewrite_content)
        self.assertIn("Smart Zone", rewrite_content)

        assess_skill_path = os.path.join(self.skills_dir, "assess", "SKILL.md")
        with open(assess_skill_path, "r", encoding="utf-8") as f:
            assess_content = f.read()

        self.assertIn("/teamwork", assess_content)
        self.assertIn("unbiased", assess_content)


if __name__ == "__main__":
    unittest.main()
