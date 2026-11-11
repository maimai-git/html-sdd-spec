try:
    import tomllib
except ModuleNotFoundError:  # Python 3.9 has no stdlib TOML parser.
    tomllib = None
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackagingTest(unittest.TestCase):
    def test_pyproject_declares_installable_cli(self):
        text = (ROOT / "pyproject.toml").read_text()
        if tomllib is not None:
            project = tomllib.loads(text)["project"]
            self.assertEqual("html-sdd-spec", project["name"])
            self.assertEqual("0.1.0", project["version"])
            self.assertEqual("html_sdd.cli:main", project["scripts"]["html-sdd"])
            self.assertGreaterEqual(len(project["requires-python"]), 4)
        else:
            self.assertRegex(text, r'(?m)^name = "html-sdd-spec"$')
            self.assertRegex(text, r'(?m)^version = "0\.1\.0"$')
            self.assertRegex(text, r'(?m)^html-sdd = "html_sdd\.cli:main"$')
            self.assertRegex(text, r'(?m)^requires-python = ">=3\.9"$')

    def test_package_contains_the_offline_console_asset(self):
        asset = ROOT / "html_sdd" / "assets" / "console.html"
        template = ROOT / "templates" / "console.html"
        self.assertTrue(asset.exists())
        self.assertEqual(template.read_text(), asset.read_text())

    def test_skeleton_has_a_readiness_gate(self):
        from html_sdd.scaffold import skeleton_spec

        readiness = skeleton_spec()["metadata"]["readiness"]
        self.assertFalse(readiness["codingReady"])
        self.assertIn("blockingItems", readiness)
        self.assertIn("exitCriteria", readiness)


if __name__ == "__main__":
    unittest.main()
