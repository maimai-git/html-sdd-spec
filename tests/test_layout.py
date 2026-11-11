import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StandardLayoutTest(unittest.TestCase):
    def test_init_uses_chinese_sdd_artifact_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            result = subprocess.run(
                [sys.executable, "-m", "html_sdd", "init"],
                cwd=project_root,
                env={**os.environ, "PYTHONPATH": str(ROOT)},
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            target = project_root / "html-sdd-spec" / "新开发需求"
            self.assertTrue((target / "方案事实源.json").exists())
            self.assertTrue((target / "方案对齐.html").exists())
            self.assertTrue((target / "使用说明.md").exists())
            self.assertTrue((target / "变更记录" / "说明.md").exists())
            self.assertTrue((target / "证据索引" / "说明.md").exists())
            self.assertIn("子需求", (target / "使用说明.md").read_text())
            self.assertFalse((target / "sdd.json").exists())
            self.assertFalse((target / "rendered" / "index.html").exists())

    def test_custom_artifact_directory_keeps_the_same_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "html-sdd-spec" / "订单履约"
            result = subprocess.run(
                [sys.executable, "-m", "html_sdd", "init", str(target)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue((target / "方案事实源.json").exists())
            self.assertTrue((target / "方案对齐.html").exists())


if __name__ == "__main__":
    unittest.main()
