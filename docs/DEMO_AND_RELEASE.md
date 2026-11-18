# Demo plan and GitHub release checklist

## Thirty-second project introduction

> I built BankOps AI to demonstrate how a banking operations analyst can go beyond an overall SLA breach rate. It compares recent service requests with a historical baseline, identifies the categories and teams that need investigation, and uses approved SQL tools to support the findings. I also added an optional Gemini workflow that retrieves SQL evidence and keeps the results auditable. The dataset is synthetic; the focus is reliable operational analysis and traceable AI-assisted explanation.

## Two-minute walkthrough

**0:00–0:35 · Signal.** Show **Overview**. Point to 47.64% recent versus 30.48% baseline (+17.16 percentage points), and clearly state that the recent cohort covers seven days versus a 28-day baseline.

**0:35–1:05 · Segmentation.** Show the estimated-excess chart. Payment Investigation is the leading category (+25.03); Payments Operations is the leading team (+34.10). Note that the category and team views overlap and are not causal attribution.

**1:05–1:40 · Investigation.** Open **AI Investigation**. Use the prepared question about which teams and categories experienced the greatest estimated excess. Show the answer's `[E1]`/`[E2]` references and open the result tables. For a no-network demonstration, use SQL-only mode; for a live model call, check the mode after generation.

**1:40–2:00 · Traceability.** Open **Data Quality & Audit** and point out the SQL comparisons, optional logged tool calls, and selected data-quality checks.

**Finish with the decision:** The project helps an analyst identify *what to investigate next*; it does not invent a root cause or automate a staffing decision.

## Questions worth preparing for

- **Why 7 days vs 28?** A recent monitoring cohort against a broader preceding rate baseline; the counts are not directly compared as equal exposure windows.
- **What's an excess breach?** Recent observed breaches minus the estimated number at that segment's earlier breach rate.
- **Why use SQL with AI?** Business calculations remain deterministic and inspectable; Gemini helps choose preapproved queries and explain returned evidence.
- **How do you stop hallucinations?** Tool allowlists, input validation, evidence references, numeric consistency checks, and SQL fallback. These are safeguards, not absolute guarantees.
- **How was it evaluated?** Repeatable synthetic fixtures, tests for KPI calculations and tool restrictions, local logs, and manual inspection of model responses.
- **What would you improve in production?** Proper authentication, access controls, data contracts, monitoring, deployment, stronger evaluation of narrative accuracy, privacy-safe audit logs, and explicit metrics governance.

## Safe GitHub release process

1. Run the setup, tests and smoke check locally using the commands in `README.md`.
2. Verify `assets/` screenshots contain no visible tokens or sensitive browser content. The bundled screenshots were cropped to focus on the application.
3. Verify `.env` contains real credentials **only locally**, and `.gitignore` excludes `.env`, local DB/CSV, and logs.
4. Check `git status`, `git diff --cached --name-only`, and `git ls-files`. If any secret was previously committed, simply ignoring it now is insufficient; rotate the credential and clean history before publishing.
5. Create a new empty GitHub repository named `bankops-ai`, without generating another README or `.gitignore` in GitHub.
6. From your checked repository folder, initialize/push with the commands below.
7. Confirm README images render, GitHub Actions tests pass, and the repository opens without credentials or large local artifacts.

```bash
# After copying the reviewed release files to your intended project directory:
git init
git branch -M main
git add .
git status --short
git diff --cached --name-only
# Inspect staged file list before proceeding
git commit -m "Document and validate BankOps AI portfolio release"
git remote add origin https://github.com/YOUR-USERNAME/bankops-ai.git
git push -u origin main
```

**If the project already has a `.git` history**, do not blindly re-initialize or overwrite a configured remote. Inspect `git status` and `git remote -v`; use the existing repository history, commit only reviewed changes, and push to the correct origin. Do not use force-push as a quick fix.

## Release gate

- [ ] Documented business problem, user stories and architecture
- [ ] Reproducible demo dataset and saved evaluation report
- [ ] Dashboard runs; all three top-level pages checked
- [ ] AI off provides correct SQL-specific answer
- [ ] AI on either produces checked cited findings or discloses fallback
- [ ] Selected data quality checks work whether a Gemini trace exists or not
- [ ] Offline test suite and smoke checks pass
- [ ] No real API keys, local database or logs in `git status --short`
- [ ] README and screenshots render on GitHub
- [ ] GitHub Actions workflow passes after publishing

## Portfolio description

**BankOps AI** | Python, SQL, SQLite, Streamlit, Gemini
Built a banking operations analytics prototype that compares service-request SLA performance against historical baselines, ranks estimated excess breaches across categories and teams, and supports evidence-backed investigation through approved SQL tools and optional Gemini tool calling. Implemented cited evidence checks, deterministic SQL fallback, data-quality reporting, and an auditable investigation workflow using reproducible synthetic data.
