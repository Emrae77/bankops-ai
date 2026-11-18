import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from src.generate_data import generate
from src.database import load
from src.analysis import summary, category_breakdown, compare_periods

class PipelineTests(unittest.TestCase):
    def test_repeatable_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            a=generate(d/'a.csv',n=2600,seed=42)
            generate(d/'b.csv',n=2600,seed=42)
            self.assertEqual((d/'a.csv').read_bytes(),(d/'b.csv').read_bytes())
            self.assertEqual(len(a),2600)
            count=load(d/'a.csv',d/'demo.db')
            self.assertEqual(count,2600)
            s=summary(d/'demo.db')
            self.assertEqual(s['tickets'],2600)
            self.assertEqual(sum(x['tickets'] for x in category_breakdown(d/'demo.db')),2600)
            self.assertEqual(sum(x['tickets'] for x in compare_periods(d/'demo.db')),2600)
            with closing(sqlite3.connect(d/'demo.db')) as db:
                self.assertEqual(db.execute('SELECT COUNT(DISTINCT ticket_id) FROM tickets').fetchone()[0],2600)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM ticket_metrics WHERE sla_breached NOT IN (0,1)").fetchone()[0],0)
if __name__=='__main__': unittest.main()
