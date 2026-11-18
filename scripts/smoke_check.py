"""Offline smoke check for the packaged analytics path (no Gemini calls)."""
from pathlib import Path

from src.evidence_guard import investigate_checked
from src.investigation import execute_tool


def main():
    db = Path("data/bankops.db")
    if not db.exists():
        raise SystemExit("Missing data/bankops.db. Run: python -m scripts.setup_demo")
    comparisons = {r["period"]: r for r in execute_tool("compare_periods")}
    if set(comparisons) != {"baseline", "recent"}:
        raise AssertionError("Expected recent and baseline cohorts")
    question = "Which teams and categories had the largest estimated excess SLA breaches?"
    outcome = investigate_checked(question)
    assert "Payment Investigation" in outcome["answer"]
    assert "Payments Operations" in outcome["answer"]
    assert outcome["evidence"]
    assert execute_tool("get_data_quality")
    print("PASS: SQL cohorts, comparison, data quality, and offline evidence-backed answer")
    print("Recent tickets:", comparisons["recent"]["tickets"])
    print("Baseline tickets:", comparisons["baseline"]["tickets"])
    print("Mode:", outcome["mode"])


if __name__ == "__main__":
    main()
