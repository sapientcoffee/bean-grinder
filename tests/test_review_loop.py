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
Unit tests for scripts/review_loop.py:
- Consensus score calculation
- Reviewer payload parsing (JSON, Markdown codeblock, plain text)
- Conflict / trade-off reconciliation
- Round evaluation and convergence gating
- Circuit breaker tripping
- Full 3-round simulation and plan patching
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add repo root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.review_loop import (
    compute_consensus_score,
    parse_reviewer_payload,
    reconcile_trade_offs,
    evaluate_review_round,
    simulate_adversarial_round,
    generate_adversarial_review_md,
    patch_plan_hardening_log,
)


class TestReviewLoop(unittest.TestCase):

    def test_compute_consensus_score(self):
        # Perfect score
        self.assertEqual(compute_consensus_score(0, 0, 0, 0), 100.0)

        # 1 Critical (-25), 1 High (-10), 2 Med (-6), 3 Low (-3) -> 100 - 44 = 56.0
        self.assertEqual(compute_consensus_score(1, 1, 2, 3), 56.0)

        # Extreme count -> bounded at 0.0
        self.assertEqual(compute_consensus_score(10, 10, 10, 10), 0.0)

        # 1 Medium (-3) -> 97.0
        self.assertEqual(compute_consensus_score(0, 0, 1, 0), 97.0)

    def test_parse_reviewer_payload_json(self):
        raw_json = json.dumps({
            "persona": "reviewer-exec",
            "status": "CHANGES_REQUESTED",
            "risk_level": "HIGH",
            "findings": [
                {
                    "id": "EXEC-001",
                    "severity": "CRITICAL",
                    "title": "Unbudgeted Dual-Run",
                    "concrete_scenario": "Dual running both databases",
                    "actionable_remediation": "Cap dual run to 30 days"
                }
            ],
            "summary": "TCO violation detected."
        })

        parsed = parse_reviewer_payload(raw_json, "reviewer-exec")
        self.assertEqual(parsed["persona"], "reviewer-exec")
        self.assertEqual(parsed["status"], "CHANGES_REQUESTED")
        self.assertEqual(len(parsed["findings"]), 1)
        self.assertEqual(parsed["findings"][0]["severity"], "CRITICAL")
        self.assertEqual(parsed["summary"], "TCO violation detected.")

    def test_parse_reviewer_payload_markdown_codeblock(self):
        codeblock = """
Here is my review:
```json
{
  "persona": "reviewer-engineer",
  "status": "APPROVED_ROBUST",
  "risk_level": "LOW",
  "findings": [],
  "summary": "AST transformations are clean."
}
```
Thank you.
"""
        parsed = parse_reviewer_payload(codeblock, "reviewer-engineer")
        self.assertEqual(parsed["status"], "APPROVED_ROBUST")
        self.assertEqual(len(parsed["findings"]), 0)
        self.assertEqual(parsed["summary"], "AST transformations are clean.")

    def test_parse_reviewer_payload_markdown_fallback(self):
        plain_md = """
### Reflection breakage in UserSerializer
Scenario: Reflection breaks during serialization.
Remediation: Add dynamic serialization tests.

### Slow test builds
Scenario: Build exceeds 15 minutes.
Remediation: Parallelize slice tests.
"""
        parsed = parse_reviewer_payload(plain_md, "reviewer-pm")
        self.assertEqual(parsed["persona"], "reviewer-pm")
        self.assertGreaterEqual(len(parsed["findings"]), 2)
        severities = [f["severity"] for f in parsed["findings"]]
        self.assertIn("HIGH", severities)

    def test_reconcile_trade_offs(self):
        reviews = [
            {
                "persona": "reviewer-exec",
                "findings": [
                    {"category": "TCO / Cloud Spend", "title": "High Cloud Run Cost", "severity": "HIGH"}
                ]
            },
            {
                "persona": "reviewer-architect",
                "findings": [
                    {"category": "Distributed Architecture", "title": "Over-partitioned microservices", "severity": "HIGH"}
                ]
            },
            {
                "persona": "reviewer-pm",
                "findings": [
                    {"category": "Parity / Bug Equivalence", "title": "Legacy quirk missing", "severity": "MEDIUM"}
                ]
            },
            {
                "persona": "reviewer-engineer",
                "findings": [
                    {"category": "Testing & Fixtures", "title": "Harness complexity", "severity": "LOW"}
                ]
            },
        ]

        trade_offs = reconcile_trade_offs(reviews)
        self.assertGreaterEqual(len(trade_offs), 2)
        trade_off_ids = [to["id"] for to in trade_offs]
        self.assertIn("TRADE-01", trade_off_ids)
        self.assertIn("TRADE-02", trade_off_ids)

    def test_evaluate_review_round_convergence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir)
            # Round 1: has blockers
            persona_reviews = [
                {
                    "persona": "reviewer-exec",
                    "status": "CHANGES_REQUESTED",
                    "risk_level": "HIGH",
                    "summary": "Blocker",
                    "findings": [{"id": "F1", "severity": "CRITICAL", "title": "TCO", "concrete_scenario": "...", "actionable_remediation": "..."}]
                }
            ]
            round_1 = evaluate_review_round(plan_dir, 1, persona_reviews, max_rounds=3, threshold=90.0)
            self.assertEqual(round_1["verdict"], "NEEDS_REVISION")
            self.assertFalse(round_1["is_converged"])
            self.assertEqual(round_1["critical_count"], 1)
            self.assertLess(round_1["consensus_score"], 90.0)

            # Round 2: clean approved reviews
            clean_reviews = [
                {"persona": "reviewer-exec", "status": "APPROVED_ROBUST", "risk_level": "LOW", "findings": [], "summary": "Approved"},
                {"persona": "reviewer-engineer", "status": "APPROVED_ROBUST", "risk_level": "LOW", "findings": [], "summary": "Approved"},
                {"persona": "reviewer-architect", "status": "APPROVED_ROBUST", "risk_level": "LOW", "findings": [], "summary": "Approved"},
                {"persona": "reviewer-pm", "status": "APPROVED_ROBUST", "risk_level": "LOW", "findings": [], "summary": "Approved"},
            ]
            round_clean = evaluate_review_round(plan_dir, 2, clean_reviews, max_rounds=3, threshold=90.0)
            self.assertEqual(round_clean["verdict"], "CONVERGED_ROBUST")
            self.assertTrue(round_clean["is_converged"])
            self.assertEqual(round_clean["consensus_score"], 100.0)
            self.assertEqual(round_clean["critical_count"], 0)
            self.assertEqual(round_clean["high_count"], 0)

            # Circuit breaker test
            round_max = evaluate_review_round(plan_dir, 3, persona_reviews, max_rounds=3, threshold=90.0)
            self.assertEqual(round_max["verdict"], "CIRCUIT_BREAKER_TRIGGERED")
            self.assertFalse(round_max["is_converged"])

    def test_simulation_and_plan_patching(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir)
            plan_file = plan_dir / "05_PLAN.md"
            plan_file.write_text("# Initial Migration Plan\n\n## Tasks\n- Task 1\n", encoding="utf-8")

            # Simulate round 1
            reviews_r1 = simulate_adversarial_round(1)
            self.assertGreater(len(reviews_r1), 0)
            r1_eval = evaluate_review_round(plan_dir, 1, reviews_r1)
            self.assertEqual(r1_eval["verdict"], "NEEDS_REVISION")

            matrix = {
                "plan_slug": "test",
                "plan_dir": str(plan_dir),
                "current_round": 1,
                "max_rounds": 3,
                "convergence_threshold": 90.0,
                "is_converged": False,
                "circuit_breaker_tripped": False,
                "rounds": [r1_eval],
            }
            md_content = generate_adversarial_review_md(matrix)
            self.assertIn("Round 1", md_content)

            # Patch plan
            patch_plan_hardening_log(plan_file, r1_eval)
            plan_text_1 = plan_file.read_text(encoding="utf-8")
            self.assertIn("🛡️ Adversarial Review & Hardening Audit", plan_text_1)

            # Simulate round 3 -> should converge
            reviews_r3 = simulate_adversarial_round(3)
            r3_eval = evaluate_review_round(plan_dir, 3, reviews_r3)
            self.assertEqual(r3_eval["verdict"], "CONVERGED_ROBUST")
            self.assertTrue(r3_eval["is_converged"])
            self.assertEqual(r3_eval["critical_count"], 0)
            self.assertEqual(r3_eval["high_count"], 0)
            self.assertGreaterEqual(r3_eval["consensus_score"], 90.0)

            # Patch plan again to verify section replacement
            patch_plan_hardening_log(plan_file, r3_eval)
            plan_text_3 = plan_file.read_text(encoding="utf-8")
            self.assertIn("CONVERGED_ROBUST", plan_text_3)


if __name__ == "__main__":
    unittest.main()
