import tempfile
import unittest
from pathlib import Path
from src.generate_data import generate
from src.database import load
from src.investigation import execute_tool
from src.ai_assistant import demo_investigation

class InvestigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        root=Path(cls.tmp.name)
        cls.csv=root/'tickets.csv'
        cls.db=root/'tickets.db'
        generate(cls.csv)
        load(cls.csv,cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_category_totals_reconcile(self):
        rows=execute_tool('get_breakdown',{'dimension':'category'},self.db)
        self.assertEqual(sum(r['tickets'] for r in rows),2600)
        self.assertEqual(sum(r['breaches'] for r in rows),746)

    def test_period_totals_reconcile(self):
        rows=execute_tool('compare_periods',{},self.db)
        from src.analysis import query
        expected = query("SELECT COUNT(*) AS n FROM ticket_metrics WHERE date(created_at) BETWEEN date((SELECT MAX(created_at) FROM tickets), ?) AND date((SELECT MAX(created_at) FROM tickets))", ("-34 days",), self.db)[0]["n"]
        self.assertEqual(sum(r["tickets"] for r in rows), expected)

    def test_restrict_invalid_tool_and_args(self):
        with self.assertRaises(ValueError):
            execute_tool('run_sql',{'sql':'DROP TABLE tickets'},self.db)
        with self.assertRaises(ValueError):
            execute_tool('get_breakdown',{'dimension':'sql'},self.db)
        with self.assertRaises(ValueError):
            execute_tool('get_weekly_trend',{'sql':'DELETE FROM tickets'},self.db)

    def test_offline_evidence(self):
        evidence=demo_investigation(self.db)
        self.assertEqual(len(evidence),4)
        self.assertTrue(all(e['rows'] for e in evidence))
        self.assertEqual([e['id'] for e in evidence], ['E1','E2','E3','E4'])

if __name__ == '__main__': unittest.main()
