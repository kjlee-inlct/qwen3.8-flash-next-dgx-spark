from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate-runtime.py"
SPEC = importlib.util.spec_from_file_location("validate_runtime", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class RuntimeValidationTests(unittest.TestCase):
    def test_parses_only_sse_data_fields(self) -> None:
        lines = [b": heartbeat\n", b"data: {\"choices\": []}\n", b"\n", b"data: [DONE]\n"]
        self.assertEqual(list(MODULE.iter_sse_data(lines)), ['{"choices": []}', "[DONE]"])

    def test_accepts_text_chat_response(self) -> None:
        MODULE.validate_chat_response({"choices": [{"message": {"content": "READY"}}]})

    def test_rejects_empty_chat_response(self) -> None:
        with self.assertRaises(MODULE.ValidationError):
            MODULE.validate_chat_response({"choices": [{"message": {"content": ""}}]})


if __name__ == "__main__":
    unittest.main()
