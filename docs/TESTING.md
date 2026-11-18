# Testing, evaluation, and troubleshooting

## Reproduce the dataset

From the repository root in an active Python virtual environment:

```bash
python -m scripts.setup_demo
```

This regenerates a synthetic CSV (seed 42, 2,600 tickets), builds the local SQLite tables/view, and refreshes `reports/segment_evaluation.json`.

## Run the checks

```bash
python -m py_compile app.py
python -m unittest discover -s tests -v
python -m scripts.smoke_check
python -m scripts.evaluate_segments
```

Tests cover synthetic-data repeatability, row totals and SLA reconciliation, parameter validation and blocking unapproved tools, period/segment comparison math, numeric evidence checks, SQL-only fallback output, selected data-quality checks, and mocked Gemini event tracing.

**CI:** `.github/workflows/tests.yml` installs dependencies, regenerates data, compiles source, runs the test suite and performs an offline smoke check on pushes and pull requests. No real Gemini API key is required for CI. The tool-trace test uses the SDK but mocks the client; it is skipped if `google-genai` is not installed.

**Execution status of this release:** Offline tests and smoke checks were run in the packaging environment. A live SDK call and interactive browser walkthrough were **not run from this package**. Earlier screenshots supplied by the project author show an actual Gemini-assisted result, but that does not replace repeatable automated live integration testing.

## Manual UI validation checklist

- [ ] Start with `python -m streamlit run app.py` after setting up synthetic data.
- [ ] Overview: dates, denominators, 47.64% current rate and 30.48% baseline agree with the report.
- [ ] Overview: horizontal category labels are readable; category/team top metrics match SQL.
- [ ] AI Investigation OFF: answer mentions the leading category and team with references.
- [ ] AI Investigation ON (optional): inspect outcome mode, output, references and warnings.
- [ ] Evidence expander: each `[E#]` points to an actual returned tool record.
- [ ] Data Quality & Audit → Period Comparison: category and team tables display.
- [ ] Data Quality & Audit → Gemini Tool Calls: audit entries display after a live run (or an appropriate empty state displays).
- [ ] Data Quality & Audit → Data Quality: selected checks display **even if a Gemini trace file exists**.
- [ ] About the Data: explicitly states synthetic data.
- [ ] Confirm no `.env`, logs, `.venv`, `data/*.db`, or local data exports are staged in Git.

## Expected numeric baselines (seed 42)

| Check | Expected value |
| --- | ---: |
| All-time synthetic tickets | 2,600 |
| Recent cohort tickets | 212 |
| Baseline cohort tickets | 725 |
| Recent breach rate | 47.64% |
| Baseline breach rate | 30.48% |
| Difference | 17.16 pp |
| Highest category excess | Payment Investigation +25.03 |
| Highest team excess | Payments Operations +34.10 |

These are fixture assertions for reproducibility, not performance KPIs from a real bank.

## Frequent problems

**`No module named streamlit`**: Activate `.venv`, then install requirements using the same interpreter: `python -m pip install -r requirements.txt`. Run via `python -m streamlit run app.py` rather than an unrelated system Python.

**SQLite database not found / the reporting engine cannot load**: Run `python -m scripts.setup_demo` from the repository root. Commands assume relative paths beginning with `data/` and `reports/`.

**Gemini API timeout or unavailable model**: The SQL-only investigation remains available. Confirm a key is present and choose an accessible `GEMINI_MODEL` through `.env`; run `python -m scripts.diagnose_gemini` if troubleshooting a live SDK connection. Never paste keys or complete log files containing secrets into issues.

**No Gemini log**: This is expected until a live AI-assisted investigation is executed. The SQL-only mode does not invoke Gemini.

**Different port, such as 8502**: Another Streamlit process may be using port 8501. Stop existing servers with `Control+C` where appropriate and use the URL printed by the active command.

**AI result fails checks**: Inspect the query evidence and warnings. Do not disable verification merely to suppress the warning; correct missing evidence, unsupported numeric claims, or tool-contract errors.
