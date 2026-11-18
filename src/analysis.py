"""Read-only SQL KPI analysis. No LLM required."""
import sqlite3
from contextlib import closing
from pathlib import Path

DB = Path('data/bankops.db')

def query(sql, params=(), db_path=DB):
    if not sql.lstrip().lower().startswith('select'):
        raise ValueError('Only SELECT queries are permitted')
    with closing(sqlite3.connect(f'file:{Path(db_path).resolve()}?mode=ro', uri=True)) as db:
        db.row_factory=sqlite3.Row
        return [dict(r) for r in db.execute(sql, params).fetchall()]

def summary(db_path=DB):
    return query('''SELECT COUNT(*) tickets,
     SUM(status='Open') open_tickets,
     SUM(sla_breached) sla_breaches,
     ROUND(100.0*SUM(sla_breached)/COUNT(*),2) breach_pct,
     ROUND(AVG(resolution_hours),2) avg_resolution_hours
     FROM ticket_metrics''',db_path=db_path)[0]

def category_breakdown(db_path=DB):
    return query('''SELECT category, COUNT(*) tickets, SUM(sla_breached) breaches,
     ROUND(100.0*SUM(sla_breached)/COUNT(*),2) breach_pct
     FROM ticket_metrics GROUP BY category ORDER BY breaches DESC''',db_path=db_path)

def weekly_trend(db_path=DB):
    return query('''SELECT strftime('%Y-%W',created_at) week, COUNT(*) tickets,
     SUM(sla_breached) breaches,
     ROUND(100.0*SUM(sla_breached)/COUNT(*),2) breach_pct
     FROM ticket_metrics GROUP BY week ORDER BY week''',db_path=db_path)

def compare_periods(db_path=DB):
    """Legacy full-history category split, not the main 7-day / 28-day view."""
    return query('''SELECT CASE WHEN created_at >= '2026-10-24' THEN 'recent'
      ELSE 'baseline' END period, category, COUNT(*) tickets,
      SUM(sla_breached) breaches,
      ROUND(100.0*SUM(sla_breached)/COUNT(*),2) breach_pct
      FROM ticket_metrics GROUP BY period, category ORDER BY category,period''',db_path=db_path)

if __name__=='__main__':
    import json
    print(json.dumps({'summary':summary(),'categories':category_breakdown(),'period_comparison':compare_periods()},indent=2))
