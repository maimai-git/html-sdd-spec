import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/asset-library/sdd.json"


class CliCheckerTest(unittest.TestCase):
    def test_check_command_returns_zero_for_valid_spec(self):
        result = subprocess.run(
            [sys.executable, "-m", "html_sdd", "check", str(EXAMPLE)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("OK", result.stdout)

    def test_check_command_returns_one_for_invalid_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            spec = json.loads(EXAMPLE.read_text())
            spec["requirements"][0]["related"].append("BROKEN-ID")
            path.write_text(json.dumps(spec, ensure_ascii=False))
            result = subprocess.run(
                [sys.executable, "-m", "html_sdd", "check", str(path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(1, result.returncode)
            self.assertIn("REF_MISSING", result.stdout)


if __name__ == "__main__":
    unittest.main()
