# Dataset, definitions, and analytical methods

## Data provenance and reproducibility

All tickets are **synthetic and deterministically generated**, not collected from a bank. `src/generate_data.py` creates 2,600 records with seed `42`; `src/database.py` validates and loads them into SQLite. The generator intentionally changes the distribution and handling-time behaviour of selected payment categories near the end of the simulated period. This is scenario design, not a discovered cause.

**Regenerate the entire demo** from the repository root:

```bash
python -m scripts.setup_demo
```

Generated files (ignored by Git) are `data/bank_service_tickets.csv` and `data/bankops.db`. The generated summary report is `reports/segment_evaluation.json` (a reference snapshot is included in Git).

## Logical data model

**`tickets` table**: one row per synthetic service request, keyed by `ticket_id`.

| Column | Type | Meaning |
| --- | --- | --- |
| `ticket_id` | TEXT | Unique synthetic ticket identifier |
| `created_at` | TEXT (ISO timestamp) | Ticket creation timestamp; defines cohort membership |
| `resolved_at` | TEXT (ISO timestamp), nullable | Resolution timestamp for resolved requests |
| `due_at` | TEXT (ISO timestamp) | Synthetic SLA deadline |
| `category` | TEXT | Service-request category |
| `team` | TEXT | Associated operating team |
| `priority` | TEXT | Low, Medium, High, Critical |
| `channel` | TEXT | Request origination channel |
| `status` | TEXT | Open or Resolved |
| `sla_target_hours` | REAL | Target resolution window used in generation |
| `synthetic_slowdown_flag` | INTEGER | Scenario-design field; **not used as analytical evidence** |

**`ticket_metrics` view** adds:

| Calculated column | Meaning |
| --- | --- |
| `sla_breached` | `1` if a resolved ticket's `resolved_at` exceeds `due_at`; or an open ticket is past due as of the fixed synthetic observation timestamp; otherwise `0` |
| `resolution_hours` | Elapsed hours from creation to resolution; NULL for open tickets |

The open-ticket observation time is fixed in `src/database.py` as **`2026-11-13T00:00:00`**, making reruns reproducible. This is not a live clock, and the result should not be labeled a real-time SLA dashboard.

## Period selection

The main operational comparison is anchored to `MAX(date(created_at))` rather than the current calendar date.

| Cohort | SQL date span relative to latest ticket | Demo dates | Demo count |
| --- | --- | --- | ---: |
| Baseline | Latest date minus 34 through minus 7 days | 2026-10-03 through 2026-10-30 | 725 |
| Recent | Latest date minus 6 through latest date | 2026-10-31 through 2026-11-06 | 212 |

Both cohorts contain ticket-created records, so their SLA outcomes are evaluated for tickets **created** in those periods, not only for tickets resolved inside them. They are unequal windows (28 days versus 7 days); comparing **rates** and segment-adjusted counts avoids comparing the two raw breach totals as if their time exposures matched.

## KPI calculations

Let \(t_s\) denote tickets for segment \(s\), and \(b_s\) denote breaches.

**SLA breach rate**

```text
SLA breach rate (%) = 100 × breached tickets / tickets in cohort
```

**Percentage-point change**

```text
Change (pp) = recent breach rate (%) - baseline breach rate (%)
```

For the fixed demo: `47.64 - 30.48 = +17.16 pp`. This is a change in **percentage points**, not a 17.16% relative increase.

**Estimated excess SLA breaches by segment**

```text
Expected recent breaches at segment baseline rate
   = recent segment tickets × (baseline segment breaches / baseline segment tickets)

Estimated excess SLA breaches
   = observed recent segment breaches - expected recent breaches at baseline rate
```

For Payment Investigation:

```text
Baseline: 65 breaches / 154 tickets
Recent:   55 breaches / 71 tickets
Expected recent breaches at baseline rate = 71 × (65 / 154) ≈ 29.97
Estimated excess = 55 - 29.97 ≈ +25.03
```

For Payments Operations, estimated excess is `+34.10`. These numbers are rounded to two decimal places. A negative value means fewer recent breaches than the segment-specific historical rate would predict.

**Critical distinction:** Excess breach estimates for category and team are overlapping **cuts of the same tickets**. A category may map to a team; summing category and team estimates would double-count events. The estimate is a descriptive baseline comparison, *not a causal contribution* and not a statistical confidence interval.

## Metric-quality considerations

- The most recent and baseline windows have different sample sizes, so use rates and explain denominators.
- Small segments can have volatile rates; the current release does not show uncertainty intervals or minimum-volume thresholds.
- A fixed synthetic observation timestamp affects whether still-open tickets are considered overdue.
- The generator's category/team relationships are synthetic. They do not establish independence, resource allocation patterns, or real operational drivers.
- The `get_data_quality` tool checks selected missing or inconsistent dates/statuses. It is not comprehensive source-data validation.

## SQL reproducibility

`src/investigation.py` implements the authoritative period and segment calculations used by the UI. Run the following from the repository root after setup:

```bash
python -m scripts.evaluate_segments
python -m scripts.smoke_check
```

The saved report includes the overall period comparison, category/team comparison rows, top segments and limitations. It evaluates **SQL calculations**, not Gemini answer accuracy.
