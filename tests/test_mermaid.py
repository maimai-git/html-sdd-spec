import copy
import json
import unittest
from pathlib import Path

from html_sdd.checker import validate_spec
from html_sdd.renderer import render_spec


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = json.loads((ROOT / "examples/asset-library/sdd.json").read_text())
TEMPLATE = ROOT / "templates" / "console.html"


class MermaidContractTest(unittest.TestCase):
    def test_mermaid_engine_requires_source(self):
        spec = copy.deepcopy(EXAMPLE)
        diagram = next(item for item in spec["architecture"] if item["type"] == "diagram")
        diagram["diagramEngine"] = "mermaid"
        diagram.pop("diagramSource", None)
        issues = validate_spec(spec)
        self.assertTrue(any(issue.code == "ARCH_DIAGRAM_SOURCE_MISSING" for issue in issues))

    def test_unknown_diagram_engine_is_rejected(self):
        spec = copy.deepcopy(EXAMPLE)
        diagram = next(item for item in spec["architecture"] if item["type"] == "diagram")
        diagram["diagramEngine"] = "unknown"
        issues = validate_spec(spec)
        self.assertTrue(any(issue.code == "ARCH_DIAGRAM_ENGINE_INVALID" for issue in issues))

    def test_mermaid_template_contains_lazy_loader_and_fallback(self):
        html = render_spec(EXAMPLE, TEMPLATE)
        self.assertIn("cdn.jsdelivr.net/npm/mermaid@11.12.1/dist/mermaid.min.js", html)
        self.assertIn("loadMermaid", html)
        self.assertIn("diagram-view-mermaid", html)
        self.assertIn("Mermaid 加载失败", html)

    def test_skill_documents_mermaid_engine_and_fallback(self):
        text = (ROOT / "skills/html-sdd-spec/SKILL.md").read_text()
        self.assertIn("diagramEngine", text)
        self.assertIn("Mermaid", text)
        self.assertIn("图源", text)


if __name__ == "__main__":
    unittest.main()
