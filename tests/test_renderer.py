import json
import re
import tempfile
import unittest
from pathlib import Path

from html_sdd.renderer import render_spec
from tests.rendered_payload import decode_html_payload

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = json.loads((ROOT / "examples/asset-library/sdd.json").read_text())
TEMPLATE = ROOT / "templates" / "console.html"


class RendererTest(unittest.TestCase):
    def test_render_injects_spec_and_keeps_all_tabs(self):
        html = render_spec(EXAMPLE, TEMPLATE)
        for label in ("需求", "排期", "接口", "数据表", "架构设计", "上线需要配置"):
            self.assertIn(label, html)
        self.assertIn("JSON.parse", html)

    def test_render_embeds_plain_json_that_roundtrips(self):
        html = render_spec(EXAMPLE, TEMPLATE)
        self.assertEqual(decode_html_payload(html), EXAMPLE)
        self.assertIn("asset_library_resource", html)
        self.assertNotIn("DecompressionStream", html)
        self.assertNotIn("specGzipBase64", html)

    def test_render_escapes_script_terminator(self):
        spec = json.loads(json.dumps(EXAMPLE))
        spec["metadata"]["summary"] = "</script><SCRIPT>alert(1)</SCRIPT><!--&中文"
        html = render_spec(spec, TEMPLATE)
        self.assertNotIn("</script><SCRIPT>", html)
        self.assertEqual(decode_html_payload(html), spec)

    def test_render_requires_template_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.html"
            path.write_text("<html>no placeholder</html>")
            with self.assertRaises(ValueError):
                render_spec(EXAMPLE, path)


if __name__ == "__main__":
    unittest.main()
