"""BankOps AI | Banking operations analytics dashboard.

Uses the project's existing SQL reporting and Gemini investigation modules.
Compatible with Python 3.9.
"""

import json
import os
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.analysis import query
from src.investigation import execute_tool
from src.evidence_guard import investigate_checked

load_dotenv()


st.set_page_config(
    page_title="BankOps AI | Operations Intelligence",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
<style>
.block-container {max-width: 1280px; padding-top: 1.5rem; padding-bottom: 3rem;}
h1 {letter-spacing: -.035em;}
[data-testid="stMetric"] {background: #F5F7FA; border: 1px solid #E5E8EC; padding: 16px; border-radius: 12px;}
[data-testid="stMetricLabel"] {font-weight: 550;}
</style>
""",
    unsafe_allow_html=True,
)

st.title("BankOps AI")
st.caption("Banking Operations Intelligence")
# Load comparable recent and baseline cohorts from the existing reporting tools.
try:
    period_rows = execute_tool("compare_periods")
    period_map = {r["period"]: r for r in period_rows}
    current = period_map.get("recent")
    baseline = period_map.get("baseline")
    category_rows = execute_tool("compare_segments", {"dimension": "category"})
    team_rows = execute_tool("compare_segments", {"dimension": "team"})
except Exception as exc:
    st.error("The SQL reporting engine could not load: {}".format(type(exc).__name__))
    st.stop()

if not current or not baseline:
    st.warning("Not enough historical records for a comparable overview.")
    st.stop()

change = round(current["breach_pct"] - baseline["breach_pct"], 2)


def positive_top(rows):
    """Return the segment with the greatest positive baseline-adjusted excess."""
    positive = [r for r in rows if (r.get("excess_breaches") or 0) > 0]
    return max(positive, key=lambda r: r["excess_breaches"]) if positive else None


main_category = positive_top(category_rows)
main_team = positive_top(team_rows)

# Dates are anchored to the most recent record, not the current calendar date.
window_rows = query(
    """
SELECT date(MAX(created_at), '-34 days') AS baseline_start,
       date(MAX(created_at), '-7 days') AS baseline_end,
       date(MAX(created_at), '-6 days') AS current_start,
       date(MAX(created_at)) AS current_end
FROM tickets
"""
)
w = window_rows[0]

page_overview, page_investigation, page_audit = st.tabs(
    ["Overview", "AI Investigation", "Data Quality & Audit"]
)

with page_overview:
    st.subheader("Operations Overview")
    st.caption(
        "Recent (7 days): {} to {}  |  Baseline (28 day): {} to {}".format(
            w["current_start"],
            w["current_end"],
            w["baseline_start"],
            w["baseline_end"],
        )
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tickets received", "{:,}".format(current["tickets"]))
    m2.metric("Current SLA breach rate", "{:.2f}%".format(current["breach_pct"]))
    m3.metric("Baseline SLA breach rate", "{:.2f}%".format(baseline["breach_pct"]))
    m4.metric("SLA breach rate change", "{:+.2f} pp".format(change))

    st.write("")
    if main_category and main_team:
        st.markdown(
            "**Key finding:** Highest estimated excess SLA breaches: "
            "**{}** ({:+.2f}) by category; **{}** ({:+.2f}) by team.".format(
                main_category["segment"],
                main_category["excess_breaches"],
                main_team["segment"],
                main_team["excess_breaches"],
            )
        )

    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown("**Estimated Excess SLA Breaches by Category**")
        if category_rows:
            chart_data = pd.DataFrame(category_rows)[["segment", "excess_breaches"]]
            chart = (
                alt.Chart(chart_data)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "excess_breaches:Q",
                        title="Estimated excess breaches",
                    ),
                    y=alt.Y(
                        "segment:N",
                        title=None,
                        sort="-x",
                        axis=alt.Axis(labelLimit=230),
                    ),
                    tooltip=[
                        alt.Tooltip("segment:N", title="Category"),
                        alt.Tooltip(
                            "excess_breaches:Q",
                            title="Estimated excess breaches",
                            format=".2f",
                        ),
                    ],
                )
                .properties(height=280)
            )
            st.altair_chart(chart, use_container_width=True)

    with right:
        st.markdown("**Recommended Actions**")
        category_name = main_category["segment"] if main_category else "the priority category"
        team_name = main_team["segment"] if main_team else "the priority team"
        st.markdown(
            "1. Review the priority and channel mix for {}.\n\n"
            "2. Compare {} with its baseline period.\n\n"
            "3. Review overdue queues and exceptions before changing capacity.".format(
                category_name, team_name
            )
        )

    with st.expander("Comparison details and definitions"):
        dim = st.radio(
            "Breakdown", ["Category", "Team"], horizontal=True, key="overview_dimension"
        )
        rows = category_rows if dim == "Category" else team_rows
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption(
            "The recent period covers 7 days; the baseline covers the preceding "
            "28 days. Estimated excess breaches compare each segment's recent "
            "breaches with the number expected at its baseline breach rate. "
            "Negative values indicate fewer breaches than that benchmark. "
            "Category and team views overlap and should not be added together."
        )

with page_investigation:
    st.subheader("AI Investigation")
    question = st.text_input(
        "Question",
        value=(
            "Which teams and categories had the largest estimated excess "
            "SLA breaches in the recent period?"
        ),
    )
    use_ai = st.toggle("AI-assisted analysis", value=False)
    supplied_key = ""
    if use_ai:
        supplied_key = st.text_input(
            "Gemini API key (if not configured in the environment)",
            type="password",
        )

    if st.button("Analyze", type="primary"):
        key = (os.getenv("GEMINI_API_KEY") or supplied_key) if use_ai else None
        if use_ai and not key:
            st.warning("Set GEMINI_API_KEY or provide a key in the password field.")
        else:
            with st.spinner("Analyzing..."):
                try:
                    outcome = investigate_checked(question, api_key=key)
                    st.session_state["bankops_latest_investigation"] = outcome
                except Exception as exc:
                    st.error("Investigation failed: {}".format(type(exc).__name__))

    outcome = st.session_state.get("bankops_latest_investigation")
    if outcome:
        st.markdown("**Investigation Findings**")
        st.write(outcome.get("answer", ""))
        if outcome.get("warnings"):
            st.warning("; ".join(outcome["warnings"]))

        evidence = outcome.get("evidence") or []
        with st.expander("Evidence and run details ({} SQL results)".format(len(evidence))):
            st.caption(
                "Execution mode: {} | AI response check passed: {}".format(
                    outcome.get("mode", "unknown"),
                    "Yes" if outcome.get("model_answer_verified", False) else "No",
                )
            )
            for item in evidence:
                st.markdown("**[{}] {}**".format(item.get("id", "?"), item.get("tool", "?")))
                st.caption("Arguments: {}".format(item.get("args", {})))
                st.dataframe(
                    pd.DataFrame(item.get("rows") or []),
                    hide_index=True,
                    use_container_width=True,
                )

        st.download_button(
            "Download investigation evidence",
            data=json.dumps(outcome, indent=2, default=str),
            file_name="bankops_investigation.json",
            mime="application/json",
        )

with page_audit:
    st.subheader("Data Quality & Audit")
    sub_sql, sub_calls, sub_quality = st.tabs(
        ["Period Comparison", "Gemini Tool Calls", "Data Quality"]
    )

    with sub_sql:
        for label, rows in [("Category", category_rows), ("Team", team_rows)]:
            with st.expander(
                "{} comparisons".format(label), expanded=(label == "Category")
            ):
                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

        report_path = Path("reports/segment_evaluation.json")
        if report_path.exists():
            st.download_button(
                "Download saved SQL evaluation",
                report_path.read_text(),
                file_name="bankops_segment_evaluation.json",
                mime="application/json",
            )

    with sub_calls:
        trace_file = Path("logs/gemini_tool_calls.jsonl")
        if trace_file.exists():
            events = []
            for line in trace_file.read_text().splitlines():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            ids = list(
                dict.fromkeys(
                    x.get("run_id")
                    for x in events
                    if x.get("event") == "start" and x.get("run_id")
                )
            )
            if ids:
                selected_id = st.selectbox("Investigation", ids[::-1])
                run = [e for e in events if e.get("run_id") == selected_id]
                req = sum(e.get("event") == "tool_requested" for e in run)
                ok = sum(e.get("event") == "tool_success" for e in run)
                err = sum(e.get("event") in ("tool_error", "api_error") for e in run)
                t1, t2, t3 = st.columns(3)
                t1.metric("AI-selected calls", req)
                t2.metric("Successful calls", ok)
                t3.metric("Errors", err)
                for e in run:
                    with st.expander(
                        "{} | {}".format(e.get("event", "unknown"), e.get("tool", ""))
                    ):
                        st.json(e)
            else:
                st.info("No Gemini investigation runs logged yet.")
        else:
            st.info("No Gemini audit log found.")

    with sub_quality:
        st.markdown("**Data Quality Checks**")
        try:
            results = execute_tool("get_data_quality")
            st.dataframe(pd.DataFrame(results), hide_index=True, use_container_width=True)
        except Exception as exc:
            st.warning("Data-quality tool unavailable: {}".format(type(exc).__name__))

    with st.expander("About the Data"):
        st.caption(
            "This application uses synthetic banking service-request data for "
            "demonstration and analysis. No real customer records are used."
        )
