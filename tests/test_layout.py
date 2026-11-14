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
            self.assertFalse((target / "使用说明.md").exists())
            for name in ("变更记录", "证据", "证据索引", "临时文件"):
                with self.subTest(directory=name):
                    self.assertFalse((target / name).exists())
            self.assertTrue((target / ".gitignore").exists())
            self.assertFalse((target / "sdd.json").exists())
            self.assertFalse((target / "rendered" / "index.html").exists())

    def test_local_archives_are_ignored_without_hiding_shared_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            subprocess.run(["git", "init", "-q", str(project)], check=True)
            target = project / "需求"
            subprocess.run([sys.executable, "-m", "html_sdd", "init", str(target)], cwd=ROOT, check=True, capture_output=True)
            for name in ("变更记录/变更记录.md", "证据/索引.md", "证据索引/历史回执.json", "证据/EVID-001-验收截图.png", "临时文件/对接草案.md"):
                result = subprocess.run(["git", "check-ignore", "-q", "需求/" + name], cwd=project)
                self.assertEqual(0, result.returncode)
            for name in ("方案事实源.json", "方案对齐.html", "使用说明.md", ".gitignore"):
                result = subprocess.run(["git", "check-ignore", "-q", "需求/" + name], cwd=project)
                self.assertEqual(1, result.returncode)

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
