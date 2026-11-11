import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "__pycache__", ".playwright-cli", "tests"}
TEXT_SUFFIXES = {".md", ".json", ".py", ".toml", ".yml", ".yaml", ".html", ".txt"}


class PublicHygieneTest(unittest.TestCase):
    def test_repository_has_no_local_machine_paths_or_credential_values(self):
        suspicious = []
        patterns = [
            re.compile(r"/Users/maimai/"),
            re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{16,}"),
            re.compile(r"(?i)(?:password|passwd|secret|api[_-]?key)\s*[:=]\s*[^<\[\s#][^\s#]*"),
            re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
        ]
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES or any(part in SKIP_DIRS for part in path.parts):
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in patterns:
                if pattern.search(text):
                    suspicious.append(f"{path.relative_to(ROOT)}: {pattern.pattern}")
        self.assertEqual([], suspicious)

    def test_repository_has_public_release_basics(self):
        self.assertTrue((ROOT / "LICENSE").exists())
        self.assertTrue((ROOT / "CONTRIBUTING.md").exists())
        self.assertTrue((ROOT / ".github" / "workflows" / "validate.yml").exists())
        self.assertTrue((ROOT / "examples" / "asset-library" / "README.md").exists())


if __name__ == "__main__":
    unittest.main()
