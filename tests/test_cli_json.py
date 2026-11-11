import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from html_sdd.cli import check_command


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/asset-library/sdd.json"


class CliJsonOutputTest(unittest.TestCase):
    def test_check_json_emits_machine_readable_json_only(self):
        output = StringIO()
        with redirect_stdout(output):
            code = check_command(EXAMPLE, as_json=True)
        self.assertEqual(0, code)
        payload = json.loads(output.getvalue())
        self.assertEqual([], payload)

    def test_check_json_reports_errors_as_machine_readable_json(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            spec = json.loads(EXAMPLE.read_text())
            spec["requirements"][0]["related"].append("BROKEN-ID")
            path.write_text(json.dumps(spec, ensure_ascii=False))
            output = StringIO()
            with redirect_stdout(output):
                code = check_command(path, as_json=True)
            self.assertEqual(1, code)
            payload = json.loads(output.getvalue())
            self.assertTrue(any(item["code"] == "REF_MISSING" for item in payload))

    def test_check_json_reports_input_errors_as_machine_readable_json(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "malformed.json"
            path.write_text("{broken", encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                code = check_command(path, as_json=True)
            self.assertEqual(1, code)
            payload = json.loads(output.getvalue())
            self.assertEqual("INPUT_ERROR", payload[0]["code"])


if __name__ == "__main__":
    unittest.main()
