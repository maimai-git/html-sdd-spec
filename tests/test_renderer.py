import base64
import gzip
import json
import re
import tempfile
import unittest
from pathlib import Path

from html_sdd.renderer import render_spec

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = json.loads((ROOT / "examples/asset-library/sdd.json").read_text())
TEMPLATE = ROOT / "templates" / "console.html"


class RendererTest(unittest.TestCase):
    def test_render_injects_spec_and_keeps_all_tabs(self):
        html = render_spec(EXAMPLE, TEMPLATE)
        for label in ("需求", "排期", "接口", "数据表", "架构设计", "上线需要配置"):
            self.assertIn(label, html)
        self.assertIn("const spec=await loadSpec().catch", html)

    def test_render_embeds_compressed_json_that_roundtrips(self):
        html = render_spec(EXAMPLE, TEMPLATE)
        match = re.search(r'const specGzipBase64="([A-Za-z0-9+/=]+)";', html)
        self.assertIsNotNone(match)
        decoded = gzip.decompress(base64.b64decode(match.group(1)))
        self.assertEqual(json.loads(decoded), EXAMPLE)
        self.assertIn("asset_library_resource", decoded.decode())
        source_size = len(json.dumps(EXAMPLE, ensure_ascii=False, separators=(",", ":")).encode())
        self.assertLess(len(match.group(1)), source_size // 2)

    def test_render_escapes_script_terminator(self):
        spec = json.loads(json.dumps(EXAMPLE))
        spec["metadata"]["summary"] = "</script><script>alert(1)</script>"
        html = render_spec(spec, TEMPLATE)
        self.assertNotIn("</script><script>", html)
        match = re.search(r'const specGzipBase64="([A-Za-z0-9+/=]+)";', html)
        decoded = gzip.decompress(base64.b64decode(match.group(1))).decode()
        self.assertIn("<\\/script>", decoded)

    def test_render_requires_template_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.html"
            path.write_text("<html>no placeholder</html>")
            with self.assertRaises(ValueError):
                render_spec(EXAMPLE, path)


if __name__ == "__main__":
    unittest.main()
