import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExampleTest(unittest.TestCase):
    def test_prompts_and_example_are_present(self):
        for role in ("owner", "reviewer", "executor"):
            path = ROOT / "prompts" / f"{role}.md"
            self.assertTrue(path.exists(), path)
            text = path.read_text()
            self.assertIn("方案事实源", text)
            self.assertIn("ID", text)

    def test_owner_prompt_keeps_user_reports_short_and_plain(self):
        text = (ROOT / "prompts" / "owner.md").read_text()
        self.assertIn("300 字以内", text)
        self.assertIn("言简意赅", text)
        self.assertIn("阶段目标", text)
        self.assertIn("存在问题", text)

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
