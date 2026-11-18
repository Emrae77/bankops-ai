"""Evidence checks and safe SQL fallback for BankOps AI (Python 3.9)."""

import re

from .ai_assistant import investigate
from .investigation import execute_tool


_CITATION = re.compile(r"\[(E\d+)\]")
_NUMBER = re.compile(r"(?<![A-Za-z0-9])[-+]?\d+(?:\.\d+)?")


def _numeric_values(value):
    """Return two-decimal numeric representations of database result values."""
    if isinstance(value, dict):
        for item in value.values():
            yield from _numeric_values(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _numeric_values(item)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield round(float(value), 2)
    elif isinstance(value, str):
        try:
            yield round(float(value.strip().rstrip("%")), 2)
        except ValueError:
            pass


def _allowed_numbers(record):
    numbers = set(_numeric_values(record.get("rows", [])))
    if record.get("tool") == "compare_periods":
        periods = {r.get("period"): r for r in record.get("rows", [])}
        baseline, recent = periods.get("baseline"), periods.get("recent")
        if baseline and recent:
            a, b = baseline.get("breach_pct"), recent.get("breach_pct")
            if a is not None and b is not None:
                numbers.add(round(float(b) - float(a), 2))
    if record.get("tool") == "compare_segments":
        # The tool's fixed periods are seven recent days and 28 baseline days.
        numbers.update((7.0, 28.0))
    return numbers


def verify_answer(answer, evidence):
    """Conservative reference/number check, not a proof of semantic correctness."""
    # Normalize grouped evidence citations:
    # [E1, E2] becomes [E1] [E2].
    answer = re.sub(
        r"\[((?:E\d+\s*,\s*)+E\d+)\]",
        lambda match: " ".join(
            "[{}]".format(ref.strip())
            for ref in match.group(1).split(",")
        ),
        answer,
    )
    if not isinstance(answer, str) or not answer.strip() or not evidence:
        return False
    known = {e["id"]: e for e in evidence if e.get("id")}
    references = _CITATION.findall(answer)
    if not references or any(ref not in known for ref in references):
        return False

    for sentence in re.split(r"(?<=[.!?])\s+|\n+", answer):
        cited = _CITATION.findall(sentence)
        text = _CITATION.sub("", sentence)
        numbers = [round(float(n), 2) for n in _NUMBER.findall(text)]
        if not numbers:
            continue
        if not cited:
            return False
        supported = set()
        for ref in cited:
            supported.update(_allowed_numbers(known[ref]))
        if any(number not in supported for number in numbers):
            return False
    return True


def _dimensions(question):
    """Identify requests for a baseline-adjusted segment comparison."""
    text = (question or "").lower()
    comparative = ("excess", "contribut", "deteriorat", "baseline", "compared", "worsen", "increas", "rising", "spike", "surge")
    if not any(word in text for word in comparative):
        return []
    dimensions = []
    if "categor" in text:
        dimensions.append("category")
    if "team" in text:
        dimensions.append("team")
    if not dimensions:
        dimensions = ["category", "team"]
    return dimensions


def _find(evidence, name, args):
    return next(
        (e for e in evidence if e.get("tool") == name and e.get("args", {}) == args),
        None,
    )


def _ensure(evidence, name, args, kwargs):
    item = _find(evidence, name, args)
    if item is not None:
        return item
    rows = execute_tool(name, args, **kwargs)
    item = {
        "id": "E{}".format(len(evidence) + 1),
        "tool": name,
        "args": args,
        "rows": rows,
    }
    evidence.append(item)
    return item


def _top_positive(record):
    rows = record.get("rows") or []
    candidates = [r for r in rows if r.get("excess_breaches") is not None]
    if not candidates:
        return None
    top = max(candidates, key=lambda r: float(r["excess_breaches"]))
    return top if float(top["excess_breaches"]) > 0 else None


def _answers_question(question, answer, evidence):
    """For category/team questions, ensure the top segments are actually named."""
    for dimension in _dimensions(question):
        record = _find(evidence, "compare_segments", {"dimension": dimension})
        if record is None:
            return False
        top = _top_positive(record)
        if top is None:
            return False
        if top["segment"].casefold() not in answer.casefold():
            return False
        if "[{}]".format(record["id"]) not in answer:
            return False
    return True


def _period_summary(record):
    periods = {r.get("period"): r for r in record.get("rows", [])}
    base, recent = periods.get("baseline"), periods.get("recent")
    if not base or not recent:
        return "Comparable baseline and recent SLA data are unavailable [{}].".format(record["id"])
    a, b = base.get("breach_pct"), recent.get("breach_pct")
    if a is None or b is None:
        return "Comparable baseline and recent SLA rates are unavailable [{}].".format(record["id"])
    return (
        "Recent SLA breach rate: {:.2f}% versus a {:.2f}% baseline "
        "({:+.2f} percentage points) [{}]."
    ).format(float(b), float(a), float(b) - float(a), record["id"])


def _sql_fallback(question, evidence, kwargs):
    # A question-specific, deterministic answer. Never manufacture model output.
    periods = _ensure(evidence, "compare_periods", {}, kwargs)
    statements = [_period_summary(periods)]
    dimensions = _dimensions(question)

    for dimension in dimensions:
        record = _ensure(evidence, "compare_segments", {"dimension": dimension}, kwargs)
        top = _top_positive(record)
        label = "category" if dimension == "category" else "team"
        if top:
            statements.append(
                "Highest estimated excess SLA breaches by {}: {} "
                "({:+.2f} relative to its baseline breach rate) [{}].".format(
                    label, top["segment"], float(top["excess_breaches"]), record["id"]
                )
            )
        else:
            statements.append(
                "No {} has a positive estimated excess breach count in this comparison [{}].".format(
                    label, record["id"]
                )
            )

    if dimensions:
        statements.append(
            "Category and team results are overlapping views, not additive or proof of causation. "
            "Next, review priority, channel, and overdue queues for the affected segments."
        )
    elif not any(word in (question or "").lower() for word in ("breach rate", "sla rate", "period", "baseline", "rate change")):
        statements.append(
            "This SQL fallback provides period context only; it does not fully resolve the question."
        )
    else:
        statements.append("The difference is descriptive and does not establish its cause.")
    return " ".join(statements)


def investigate_checked(question, api_key=None, db_path=None):
    kwargs = {"db_path": db_path} if db_path is not None else {}
    evidence, warnings = [], []
    answer, mode = "", "offline"

    if api_key:
        try:
            answer, evidence = investigate(question, api_key, **kwargs)
            mode = "gemini"
            if answer.startswith("PARTIAL_INVESTIGATION:"):
                mode = "partial_fallback"
                warnings.append("Gemini was interrupted; available SQL evidence was retained.")
        except Exception as exc:
            mode = "fallback"
            warnings.append("Gemini unavailable: {}".format(type(exc).__name__))

    # Do not weaken validation merely to make a model response appear successful.
    valid = (
        mode == "gemini"
        and verify_answer(answer, evidence)
        and _answers_question(question, answer, evidence)
    )

    if not valid:
        if mode == "gemini":
            mode = "gemini_fallback"
            warnings.append("AI answer did not pass evidence/relevance checks; showing SQL findings.")
        answer = _sql_fallback(question, evidence, kwargs)

    return {
        "answer": answer,
        "mode": mode,
        "evidence": evidence,
        "warnings": warnings,
        "model_answer_verified": valid,
    }
