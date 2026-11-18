import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
try:
    from google.genai import types
except ImportError:
    types = None
from src.ai_assistant import investigate

class FakeModels:
    def __init__(self):
        self.count = 0

    def generate_content(self, **kwargs):
        self.count += 1
        if self.count <= 2:
            name = "get_breakdown" if self.count == 1 else "get_weekly_trend"
            args = {"dimension": "category"} if self.count == 1 else {}
            content = types.Content(role="model", parts=[
                types.Part.from_text(text="Investigating")
            ])
            return SimpleNamespace(
                function_calls=[SimpleNamespace(name=name, args=args)],
                candidates=[SimpleNamespace(content=content)],
            )
        return SimpleNamespace(
            function_calls=[],
            text="Category and weekly evidence reviewed [E1][E2].",
        )

@unittest.skipIf(types is None, "Install google-genai to exercise SDK trace test")
class TraceTests(unittest.TestCase):
    def test_gemini_selected_tools_are_logged(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "trace.jsonl"
            fake = SimpleNamespace(models=FakeModels())
            with patch("src.tool_trace.TRACE_PATH", path), patch("google.genai.Client", return_value=fake), patch("src.ai_assistant.execute_tool", return_value=[{"tickets":10}]):
                answer, evidence = investigate("Investigate SLA", "fake-key")
            events = [json.loads(line) for line in path.read_text().splitlines()]
            requested = [e for e in events if e["event"] == "tool_requested"]
            success = [e for e in events if e["event"] == "tool_success"]
            self.assertEqual(len(requested), 2)
            self.assertEqual(len(success), 2)
            self.assertEqual([e["tool"] for e in requested],
                             ["get_breakdown", "get_weekly_trend"])
            self.assertEqual(len(evidence), 2)
            self.assertTrue(any(e["event"] == "finished" for e in events))
            self.assertEqual(len({e["run_id"] for e in events}), 1)

if __name__ == "__main__":
    unittest.main()
