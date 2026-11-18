import json
from datetime import datetime, timezone
from pathlib import Path
from src.investigation import execute_tool

def evaluate():
    categories = execute_tool("compare_segments", {"dimension": "category"})
    teams = execute_tool("compare_segments", {"dimension": "team"})
    periods = execute_tool("compare_periods")
    period_map = {r["period"]: r for r in periods}
    baseline = period_map.get("baseline")
    recent = period_map.get("recent")
    if not baseline or not recent:
        raise ValueError("Missing comparable reporting periods")
    def top_positive(rows):
        return next((r for r in rows if r["excess_breaches"] > 0), None)
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "Synthetic BankOps service tickets",
        "baseline": baseline,
        "recent": recent,
        "overall_change_pp": round(
            recent["breach_pct"] - baseline["breach_pct"], 2),
        "top_category": top_positive(categories),
        "top_team": top_positive(teams),
        "category_comparisons": categories,
        "team_comparisons": teams,
        "limitations": [
            "Associations do not establish causal root causes.",
            "Excess breaches use each segment historical rate.",
            "Different cohort sizes require careful interpretation.",
            "This report evaluates SQL findings, not Gemini accuracy."
        ]
    }
    Path("reports").mkdir(exist_ok=True)
    Path("reports/segment_evaluation.json").write_text(
        json.dumps(result, indent=2))
    print("Overall SLA change:", result["overall_change_pp"], "pp")
    print("Top category:", result["top_category"]["segment"] if result["top_category"] else "None")
    print("Top team:", result["top_team"]["segment"] if result["top_team"] else "None")
    print("Report saved: reports/segment_evaluation.json")

if __name__ == "__main__":
    evaluate()
