import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/asset-library/sdd.json"


class CliDiffTest(unittest.TestCase):
    def test_diff_json_is_machine_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            after = Path(tmp) / "after.json"
            data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
            data["metadata"]["title"] += "（调整）"
            after.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "html_sdd", "diff", str(EXAMPLE), str(after), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload)
        self.assertIn("before", payload[0])
        self.assertIn("after", payload[0])


if __name__ == "__main__":
    unittest.main()
