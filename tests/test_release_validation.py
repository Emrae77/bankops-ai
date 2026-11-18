"""Regression tests for the documented SQL analysis and evidence fallback."""
import tempfile
import unittest
from pathlib import Path

from src.database import load
from src.evidence_guard import investigate_checked, verify_answer
from src.generate_data import generate
from src.investigation import execute_tool


class ReleaseValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name)
        csv_path, cls.db = root / "tickets.csv", root / "bankops.db"
        generate(csv_path, n=2600, seed=42)
        load(csv_path, cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_sql_only_answer_matches_requested_segments(self):
        question = "Which teams and categories had the largest estimated excess SLA breaches?"
        outcome = investigate_checked(question, db_path=self.db)
        self.assertEqual(outcome["mode"], "offline")
        self.assertIn("Payment Investigation", outcome["answer"])
        self.assertIn("Payments Operations", outcome["answer"])
        self.assertIn("25.03", outcome["answer"])
        self.assertIn("34.10", outcome["answer"])
        self.assertGreaterEqual(len(outcome["evidence"]), 3)

    def test_period_denominators_and_excess_formula(self):
        rows = execute_tool("compare_periods", db_path=self.db)
        p = {r["period"]: r for r in rows}
        self.assertEqual(p["recent"]["tickets"], 212)
        self.assertEqual(p["baseline"]["tickets"], 725)
        categories = execute_tool("compare_segments", {"dimension": "category"}, self.db)
        top = categories[0]
        expected = top["recent_breaches"] - (
            top["recent_tickets"] * top["baseline_breaches"] / top["baseline_tickets"]
        )
        self.assertAlmostEqual(expected, top["excess_breaches"], delta=0.01)

    def test_data_quality_tool_available(self):
        rows = execute_tool("get_data_quality", db_path=self.db)
        self.assertEqual(rows[0]["total_tickets"], 2600)

    def test_unsupported_numeric_claim_rejected(self):
        self.assertFalse(verify_answer(
            "The rate was 99.99% [E1].", [{"id": "E1", "rows": [{"breach_pct": 47.64}]}]
        ))


if __name__ == "__main__":
    unittest.main()
