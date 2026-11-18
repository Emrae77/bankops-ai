"""Auditable, read-only operational investigations. No model-generated SQL."""
from datetime import datetime
from pathlib import Path
from .analysis import DB, query

MAX_ROWS = 25
ALLOWED_DIMENSIONS = {'category', 'team', 'priority', 'channel'}


def _validate_dimension(dimension):
    if dimension not in ALLOWED_DIMENSIONS:
        raise ValueError('Invalid dimension: choose category, team, priority, or channel')
    return dimension


def breakdown(dimension='category', category=None, db_path=DB):
    """Return ticket and SLA breach counts by an approved dimension."""
    dimension = _validate_dimension(dimension)
    sql = f'''SELECT {dimension} AS segment, COUNT(*) AS tickets,
       SUM(sla_breached) AS breaches,
       ROUND(100.0*SUM(sla_breached)/COUNT(*),2) AS breach_pct,
       ROUND(AVG(resolution_hours),2) AS avg_resolution_hours
       FROM ticket_metrics WHERE (? IS NULL OR category=?)
       GROUP BY {dimension} ORDER BY breaches DESC LIMIT {MAX_ROWS}'''
    return query(sql, (category, category), db_path)


def period_comparison(category=None, db_path=DB):
    """Compare baseline vs recent, grouped by created date and fixed cutoff."""
    sql = '''SELECT CASE WHEN date(created_at) >= date((SELECT MAX(created_at) FROM tickets), '-6 days') THEN 'recent'
       ELSE 'baseline' END AS period, COUNT(*) AS tickets,
       SUM(sla_breached) AS breaches,
       ROUND(100.0*SUM(sla_breached)/COUNT(*),2) AS breach_pct,
       ROUND(AVG(resolution_hours),2) AS avg_resolution_hours
       FROM ticket_metrics WHERE date(created_at) BETWEEN date((SELECT MAX(created_at) FROM tickets), '-34 days') AND date((SELECT MAX(created_at) FROM tickets)) AND (? IS NULL OR category=?)
       GROUP BY period ORDER BY period'''
    return query(sql, (category, category), db_path)


def weekly(category=None, db_path=DB):
    """Weekly service-ticket creation cohort with SLA rates."""
    return query('''SELECT strftime('%Y-%W',created_at) AS week, COUNT(*) AS tickets,
       SUM(sla_breached) AS breaches,
       ROUND(100.0*SUM(sla_breached)/COUNT(*),2) AS breach_pct
       FROM ticket_metrics WHERE (? IS NULL OR category=?)
       GROUP BY week ORDER BY week''', (category,category), db_path)


def open_backlog(category=None, db_path=DB):
    """Current open-ticket counts and currently overdue counts by priority."""
    return query('''SELECT priority, COUNT(*) AS open_tickets, SUM(sla_breached) AS overdue_tickets
      FROM ticket_metrics WHERE status='Open' AND (? IS NULL OR category=?)
      GROUP BY priority ORDER BY open_tickets DESC''', (category,category), db_path)


TOOL_FUNCTIONS = {
    'get_breakdown': breakdown,
    'compare_periods': period_comparison,
    'get_weekly_trend': weekly,
    'get_open_backlog': open_backlog,
}


def execute_tool(name, args=None, db_path=DB):
    """Allowlist dispatcher. Never accepts SQL or file paths from the model."""
    args = dict(args or {})
    if name not in TOOL_FUNCTIONS:
        raise ValueError('Tool not allowed')
    accepted = ({'dimension','category'} if name in ('get_breakdown', 'compare_segments') else {'category'})
    if set(args) - accepted:
        raise ValueError('Unexpected tool parameters')
    if 'category' in args and args['category'] is not None:
        if not isinstance(args['category'],str) or len(args['category']) > 100:
            raise ValueError('Invalid category')
    return TOOL_FUNCTIONS[name](**args, db_path=db_path)


def evidence_label(name,args):
    args=args or {}
    return f"{name}({', '.join(f'{k}={v!r}' for k,v in args.items())})"

def data_quality(category=None, db_path=DB):
    """Check ticket data quality without changing records."""
    sql = """
    SELECT
        COUNT(*) AS total_tickets,
        SUM(CASE WHEN due_at IS NULL THEN 1 ELSE 0 END) AS missing_deadlines,
        SUM(CASE WHEN status=? AND resolved_at IS NOT NULL THEN 1 ELSE 0 END) AS open_with_resolution,
        SUM(CASE WHEN status=? AND resolved_at IS NULL THEN 1 ELSE 0 END) AS resolved_without_date,
        SUM(CASE WHEN resolved_at IS NOT NULL AND julianday(resolved_at)<julianday(created_at) THEN 1 ELSE 0 END) AS negative_resolution_time,
        SUM(CASE WHEN due_at IS NOT NULL AND julianday(due_at)<julianday(created_at) THEN 1 ELSE 0 END) AS deadline_before_creation
    FROM tickets
    WHERE (? IS NULL OR category=?)
    """
    return query(sql, ("Open", "Resolved", category, category), db_path)

TOOL_FUNCTIONS["get_data_quality"] = data_quality

def compare_segments(dimension="category", category=None, db_path=DB):
    """Compare recent 7 days against the preceding 28 by segment."""
    dimension = _validate_dimension(dimension)
    sql = f"""
    WITH bounds AS (
        SELECT date(MAX(created_at)) AS latest FROM tickets
    ), grouped AS (
        SELECT
            {dimension} AS segment,
            CASE WHEN date(created_at) >= date(latest, "-6 days")
                THEN "recent" ELSE "baseline" END AS period,
            COUNT(*) AS tickets,
            SUM(sla_breached) AS breaches
        FROM ticket_metrics CROSS JOIN bounds
        WHERE date(created_at) BETWEEN date(latest, "-34 days")
            AND latest
            AND (? IS NULL OR category=?)
        GROUP BY segment, period
    )
    SELECT segment, period, tickets, breaches,
        ROUND(100.0 * breaches / NULLIF(tickets, 0), 2) AS breach_pct
    FROM grouped ORDER BY segment, period
    """
    import sqlite3
    from contextlib import closing

    uri = "file:" + str(Path(db_path).resolve()) + "?mode=ro"

    with closing(sqlite3.connect(uri, uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        rows = [
            dict(row)
            for row in conn.execute(sql, (category, category))
        ]
    segments = {}
    for row in rows:
        segments.setdefault(row["segment"], {})[row["period"]] = row
    results = []
    for segment, periods in segments.items():
        recent = periods.get("recent")
        baseline = periods.get("baseline")
        if not recent or not baseline:
            continue
        change = round(recent["breach_pct"] - baseline["breach_pct"], 2)
        excess = round(recent["breaches"] - recent["tickets"] * baseline["breaches"] / baseline["tickets"], 2)
        results.append({
            "segment": segment,
            "baseline_tickets": baseline["tickets"],
            "baseline_breaches": baseline["breaches"],
            "baseline_rate": baseline["breach_pct"],
            "recent_tickets": recent["tickets"],
            "recent_breaches": recent["breaches"],
            "recent_rate": recent["breach_pct"],
            "change_pp": change,
            "excess_breaches": excess,
        })
    return sorted(results, key=lambda r: r["excess_breaches"], reverse=True)

TOOL_FUNCTIONS["compare_segments"] = compare_segments
