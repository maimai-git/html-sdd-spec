import unittest
from pathlib import Path

from html_sdd.checker import load_spec
from html_sdd.renderer import render_spec
from tests.rendered_payload import decode_html_payload


ROOT = Path(__file__).resolve().parents[1]


class ReadinessRenderTest(unittest.TestCase):
    def test_readiness_gate_is_visible_in_the_requirements_page(self):
        spec = load_spec(str(ROOT / "examples" / "asset-library" / "sdd.json"))
        html = render_spec(spec, str(ROOT / "templates" / "console.html"))
        self.assertIn("编码条件", html)
        self.assertIn("BLOCK-CHAT-001", str(decode_html_payload(html)))


if __name__ == "__main__":
    unittest.main()
