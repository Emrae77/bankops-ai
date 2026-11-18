import unittest
from src.investigation import execute_tool

class SegmentComparisonTests(unittest.TestCase):

    def test_category_comparison(self):
        rows = execute_tool("compare_segments", {"dimension": "category"})
        self.assertGreater(len(rows), 0)
        for r in rows:
            self.assertGreater(r["baseline_tickets"], 0)
            self.assertGreater(r["recent_tickets"], 0)
            self.assertAlmostEqual(
                r["recent_rate"] - r["baseline_rate"],
                r["change_pp"], delta=0.02)

    def test_excess_breach_calculation(self):
        rows = execute_tool("compare_segments", {"dimension": "category"})
        for r in rows:
            expected = (
                r["recent_breaches"]
                - r["recent_tickets"]
                * r["baseline_breaches"] / r["baseline_tickets"]
            )
            self.assertAlmostEqual(
                r["excess_breaches"], expected, delta=0.01)

    def test_team_comparison(self):
        rows = execute_tool("compare_segments", {"dimension": "team"})
        self.assertGreater(len(rows), 0)
        self.assertTrue(all("segment" in r for r in rows))

    def test_invalid_dimension_rejected(self):
        with self.assertRaises(ValueError):
            execute_tool("compare_segments", {"dimension": "fake_column"})

if __name__ == "__main__":
    unittest.main()
