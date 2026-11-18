# Business case and user stories

## Scenario

A banking operations manager receives a service-performance update. The overall share of requests missing SLA deadlines is materially higher than the prior baseline. A summary dashboard makes the change visible, but the next question is more important: **where should operations investigate first?**

The manager needs an analyst to establish comparability, identify affected categories and teams, examine what the numbers actually measure, and communicate follow-up checks without prematurely claiming a root cause. BankOps AI is a deliberately synthetic, small-scale implementation of that workflow.

## Primary story

> As an **operations analyst**, I want to **compare a recent ticket cohort to an appropriate historical baseline and identify the segments with the most estimated excess SLA breaches**, so that **I can recommend targeted follow-up analyses backed by transparent calculations**.

### Acceptance criteria

1. Display the recent and baseline date boundaries and ticket denominators.
2. Show recent and baseline SLA breach rates, with the **difference expressed in percentage points**.
3. Rank category and team comparisons using a documented baseline-adjusted excess calculation.
4. Keep category and team views distinct; do not add their estimated excess values together.
5. Let a reviewer open the underlying comparison rows.
6. Recommend next checks, but do not equate a segment with an identified cause.

## Supporting stories

**Operations manager**
> As a manager, I want an overview of the most recent SLA change and leading affected category/team, so that I can decide which operational queue needs a closer review.

**Data analyst**
> As an analyst, I want reusable SQL tools for comparisons, breakdowns, trends, backlog, and data quality, so that I can inspect a question with consistent metric definitions.

**AI-assisted analyst**
> As an analyst, I want optional AI to select only approved analytical tools and cite retrieved evidence, so that I can gain a concise explanation without allowing model-authored SQL or unsupported numerical claims.

**Technical reviewer**
> As a reviewer, I want to see result tables and model-selected tool events, so that I can reconstruct which tools were called and whether the model answer passed the application's checks.

## Example investigation

**Question:** “Which teams and categories had the largest estimated excess SLA breaches in the recent period?”

**Observation:** The recent overall SLA breach rate in the deterministic demo is 47.64%, compared with 30.48% in the baseline, an increase of 17.16 percentage points. Payment Investigation has the largest estimated excess among categories (+25.03). Payments Operations has the largest estimated excess among teams (+34.10).

**Interpretation:** These figures identify two overlapping descriptions of concentrated deterioration. They do not establish which process, channel, staffing condition, or customer behaviour caused it.

**Next analytical questions:**

- Has the priority or channel mix changed within Payment Investigation?
- Are overdue open requests concentrated in particular priority groups?
- Is the weekly pattern consistent with a sustained issue or a single peak?
- Are data-quality problems distorting the numerator or denominator?

## Scope

**In scope:** local synthetic data, SQLite metrics, period/segment comparisons, descriptive investigation, optional Gemini SQL-tool selection, evidence checks, local audit traces, reproducible tests.

**Out of scope:** bank customer data, real-time integrations, predictive causality, compliance certification, automated staffing decisions, unsupervised SQL execution, authentication, production SLAs, and enterprise deployment.

## Value being demonstrated

This portfolio project demonstrates a disciplined analytical chain: **metric definition → segmentation → SQL evidence → appropriately qualified finding → operational next check**. Its value is in the quality and traceability of the reasoning workflow, not in claiming artificial intelligence has discovered a real banking problem.
