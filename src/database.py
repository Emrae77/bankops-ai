"""Create and validate a small SQLite analytics store."""
import csv
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

ANALYSIS_AS_OF = '2026-11-13T00:00:00'

def load(csv_path=Path('data/bank_service_tickets.csv'), db_path=Path('data/bankops.db')):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with Path(csv_path).open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    ids = [r['ticket_id'] for r in rows]
    assert len(ids) == len(set(ids)), 'Duplicate ticket IDs'
    assert rows and all(r['created_at'] and r['due_at'] for r in rows)
    for r in rows:
        assert r['status'] in ('Open','Resolved')
        assert (r['status'] == 'Open') == (r['resolved_at'] == '')
        assert datetime.fromisoformat(r['due_at']) >= datetime.fromisoformat(r['created_at'])
        if r['resolved_at']:
            assert datetime.fromisoformat(r['resolved_at']) >= datetime.fromisoformat(r['created_at'])
    with closing(sqlite3.connect(db_path)) as db:
        db.executescript('''
        DROP VIEW IF EXISTS ticket_metrics;
        DROP TABLE IF EXISTS tickets;
        CREATE TABLE tickets (
            ticket_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            due_at TEXT NOT NULL,
            category TEXT NOT NULL,
            team TEXT NOT NULL,
            priority TEXT NOT NULL,
            channel TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Open','Resolved')),
            sla_target_hours REAL NOT NULL,
            synthetic_slowdown_flag INTEGER NOT NULL
        );
        ''')
        db.executemany('''INSERT INTO tickets VALUES (?,?,?,?,?,?,?,?,?,?,?)''', [
            (r['ticket_id'], r['created_at'], r['resolved_at'] or None, r['due_at'], r['category'], r['team'],r['priority'],r['channel'],r['status'],float(r['sla_target_hours']),int(r['synthetic_slowdown_flag'])) for r in rows
        ])
        # SLA breach is determined from completion time, or age of an open case at a FIXED as-of timestamp.
        # Open tickets not yet due are not counted as breached.
        db.execute(f'''CREATE VIEW ticket_metrics AS
        SELECT *,
        CASE WHEN status='Resolved' AND resolved_at>due_at THEN 1
             WHEN status='Open' AND due_at<'{ANALYSIS_AS_OF}' THEN 1 ELSE 0 END AS sla_breached,
        CASE WHEN status='Resolved' THEN (julianday(resolved_at)-julianday(created_at))*24 ELSE NULL END AS resolution_hours
        FROM tickets''')
        db.execute('CREATE INDEX idx_tickets_created ON tickets(created_at)')
        db.execute('CREATE INDEX idx_tickets_category ON tickets(category)')
        db.commit()
    return len(rows)

if __name__=='__main__':
    print('Imported',load(),'tickets')
