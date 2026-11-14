import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExampleTest(unittest.TestCase):
    def test_example_check_passes(self):
        result = subprocess.run(
            [sys.executable, "-m", "html_sdd", "check", str(ROOT / "examples/asset-library/sdd.json")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main()
