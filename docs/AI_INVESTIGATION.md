# AI investigation: workflow and safety boundaries

## Goal

The optional Gemini layer turns an analyst's question into a *selection of known analysis operations*, then drafts a response citing tool results. It does **not** accept model-authored raw SQL, autonomously modify data, or assert root cause.

The AI layer is intentionally optional. A deterministic, SQL-backed fallback supports the project even when the network, account, or model is unavailable.

## Example question

> Which teams and categories had the largest estimated excess SLA breaches in the recent period?

The intended logic is to run `compare_segments(dimension="team")` and `compare_segments(dimension="category")`, identify the leading positive excess within each result, and cite the corresponding evidence IDs. A model may also request other tools if it determines they help answer the question.

## Tool contracts

| Tool | Returns | Permitted key arguments |
| --- | --- | --- |
| `compare_periods` | Baseline and recent ticket/breach counts and rates | Optional `category` |
| `compare_segments` | Baseline/recent counts, breach rates, change in pp, estimated excess by segment | `dimension` (category/team/priority/channel), optional `category` |
| `get_breakdown` | Counts, breaches, rates, average resolution hours | `dimension`, optional `category` |
| `get_weekly_trend` | Ticket-created cohorts grouped by week | Optional `category` |
| `get_open_backlog` | Open and overdue counts grouped by priority | Optional `category` |
| `get_data_quality` | Selected date/status consistency checks | Optional `category` |

**Tool limitations matter:** `get_weekly_trend` does not accept a `team` parameter. A model suggestion to filter weekly trends directly by team is **not supported by this interface**. The answer's follow-up instructions should be treated as suggestions for a human analyst to review, not executable plans.

## Operational sequence

1. `app.py` reads the question and optional Gemini key; `.env` is loaded locally if present.
2. `investigate_checked(...)` delegates to `ai_assistant.investigate(...)` only when a key is supplied.
3. Gemini receives descriptions and schemas for approved functions and can select tool calls.
4. The application validates each tool name and argument structure and runs the **prewritten SQLite queries** itself.
5. SQL results become evidence records with IDs such as `E1` and `E2`, attached to function responses.
6. Gemini can produce a concise explanation with references to those evidence IDs.
7. `evidence_guard.verify_answer` checks cited record IDs and supported numeric tokens; `_answers_question` adds an explicit leading-segment check for certain comparative questions.
8. On an insufficient model response, API interruption, or missing key, the application can produce deterministic SQL findings. The UI exposes the mode, references, warning(s), and result tables.

## What is checked versus what is not

**Checked:** Presence of supporting evidence, citations referencing returned records, numeric-token consistency (including basic derived differences), and leading-segment relevance for questions recognized by the comparison heuristics.

**Not guaranteed:** Correct interpretation of every metric, completeness of a complex analytical answer, semantic validity of every nonnumeric statement, causal reasoning, tool recommendation feasibility, adversarial prompt resistance, or protection against all data leakage. A generated answer passing these rules is **not independently verified analysis**.

## Failure paths and modes

| Mode | Meaning |
| --- | --- |
| `offline` | Gemini not requested; deterministic SQL explanation |
| `gemini` | AI response returned and passed the application's consistency/relevance checks |
| `gemini_fallback` | AI response returned but did not pass checks; SQL fallback displayed |
| `partial_fallback` | Gemini generation was interrupted; available SQL evidence retained when possible |
| `fallback` | Gemini call raised an exception; SQL fallback displayed |

For a question outside the fallback's supported patterns, the program may return only general period context and explicitly say it does not fully answer the question. It should not pretend that generic SQL information resolves all possible requests.

## Trace logs and reproducibility

`src/tool_trace.py` appends JSONL events to `logs/gemini_tool_calls.jsonl`, including run ID, timestamps, requested tools, successful calls and truncated result payloads. The Data Quality & Audit page displays the selected run. Logs are **not stored in Git** because they can contain user questions and results. The traces aid investigation but are not immutable, access-controlled or a production-grade audit trail.

## Privacy and operational constraints

Only synthetic records are intended. Do not load real banking data or private customer identifiers into the current application without implementing identity, authorization, minimization, redaction, log retention, secret management, secure hosting, and testing for prompt injection/data disclosure.
