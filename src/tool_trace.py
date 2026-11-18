import json
from datetime import datetime, timezone
from pathlib import Path

TRACE_PATH = Path("logs/gemini_tool_calls.jsonl")

def write_trace(run_id, event, **details):
    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "event": event,
        **details,
    }
    with TRACE_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, default=str) + "\n")
