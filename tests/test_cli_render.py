import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.rendered_payload import decode_html_payload

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/asset-library/sdd.json"


class CliRenderTest(unittest.TestCase):
    def test_removed_template_option_is_rejected_without_creating_output(self):
        for template in ("classic", "vue"):
            with self.subTest(template=template), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "index.html"
                result = subprocess.run(
                    [sys.executable, "-m", "html_sdd", "render", str(EXAMPLE),
                     "--template", template, "--output", str(output)],
                    cwd=ROOT, capture_output=True, text=True,
                )
                self.assertEqual(2, result.returncode, result.stderr)
                self.assertIn(f"unrecognized arguments: --template {template}", result.stderr)
                self.assertFalse(output.exists())


    def test_default_render_preserves_all_source_records_with_vue(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "方案对齐.html"
            spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
            spec["existingInterfaces"] = [
                {**spec["apis"][0], "id": "BASE-API-01"},
            ]
            source = Path(tmp) / "方案事实源.json"
            source.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "html_sdd", "render", str(source),
                 "--output", str(output)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            html = output.read_text(encoding="utf-8")
            self.assertIn("https://cdn.jsdelivr.net/npm/vue@3.5.24/dist/vue.global.prod.js", html)
            self.assertEqual(spec, decode_html_payload(html))


if __name__ == "__main__":
    unittest.main()
