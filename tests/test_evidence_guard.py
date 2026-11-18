import unittest
from unittest.mock import patch
from src.evidence_guard import verify_answer, investigate_checked

class EvidenceGuardTests(unittest.TestCase):

    def test_supported_number(self):
        evidence = [{"id": "E1", "rows": [{"breach_pct": 20.0}]}]
        self.assertTrue(verify_answer("Rate was 20.0% [E1].", evidence))

    def test_fabricated_number(self):
        evidence = [{"id": "E1", "rows": [{"breach_pct": 20.0}]}]
        self.assertFalse(verify_answer("Rate was 99.9% [E1].", evidence))

    def test_offline_evidence(self):
        result = investigate_checked("Why did SLA breaches increase?")
        tools = {item["tool"] for item in result["evidence"]}
        self.assertEqual(result["mode"], "offline")
        self.assertEqual(tools, {"compare_periods", "compare_segments"})
        segments = [e for e in result["evidence"] if e["tool"] == "compare_segments"]
        self.assertEqual({e["args"]["dimension"] for e in segments}, {"category", "team"})
        self.assertIn("Payment Investigation", result["answer"])
        self.assertIn("Payments Operations", result["answer"])

    @patch("src.evidence_guard.investigate")
    def test_gemini_failure_fallback(self, mock_investigate):
        mock_investigate.side_effect = RuntimeError("503 UNAVAILABLE")
        result = investigate_checked("Investigate SLA changes", api_key="test")
        self.assertEqual(result["mode"], "fallback")
        self.assertTrue(result["evidence"])
        self.assertTrue(result["warnings"])

if __name__ == "__main__":
    unittest.main()
