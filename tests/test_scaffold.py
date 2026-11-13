import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ScaffoldTest(unittest.TestCase):
    def test_init_creates_valid_project_skeleton(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "new-sdd"
            result = subprocess.run(
                [sys.executable, "-m", "html_sdd", "init", str(target)],
                cwd=root,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue((target / "方案事实源.json").exists())
            self.assertTrue((target / "使用说明.md").exists())
            self.assertTrue((target / "方案对齐.html").exists())
            spec = json.loads((target / "方案事实源.json").read_text())
            self.assertEqual("0.1", spec["specVersion"])
            html = (target / "方案对齐.html").read_text(encoding="utf-8")
            self.assertIn("上线配置", html)
            self.assertIn("vue.global.prod.js", html)


if __name__ == "__main__":
    unittest.main()
