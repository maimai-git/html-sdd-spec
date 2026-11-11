import json
import unittest
from pathlib import Path

from html_sdd.checker import validate_spec
from html_sdd.renderer import render_spec
from html_sdd.scaffold import skeleton_spec
from tests.rendered_payload import decode_html_payload


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "console.html"


class OptionalSectionsTest(unittest.TestCase):
    def test_coding_ready_allows_explicitly_not_applicable_api_and_data_sections(self):
        spec = skeleton_spec()
        spec["agents"] = [
            {"id": "AG-OWNER", "name": "负责人", "role": "owner"},
            {"id": "AG-REVIEWER", "name": "审核人", "role": "reviewer"},
            {"id": "AG-EXECUTOR", "name": "执行人", "role": "executor"},
        ]
        spec["requirements"] = [{
            "id": "REQ-001",
            "group": "日志",
            "title": "统一日志格式",
            "summary": "调整日志输出格式",
            "status": "编码 READY",
            "acceptance": [{"id": "AC-001", "text": "日志格式符合约定", "status": "待验证", "evidence": "测试用例已列出"}],
            "related": ["PLAN-001"],
            "impact": {"apis": "not_applicable", "tables": "not_applicable"},
        }]
        spec["plans"] = [{
            "id": "PLAN-001",
            "priority": "P1",
            "module": "日志",
            "requirementIds": ["REQ-001"],
            "main": "调整日志输出",
            "sub": "补充测试",
            "owner": "AG-OWNER",
            "reviewer": "AG-REVIEWER",
            "executor": "AG-EXECUTOR",
            "status": "待开始",
        }]
        issues = validate_spec(spec)
        self.assertEqual([], [issue for issue in issues if issue.code == "READY_INCOMPLETE"])

    def test_empty_section_renders_coverage_reason(self):
        spec = skeleton_spec()
        spec["metadata"]["sectionCoverage"] = {
            "apis": {"status": "not_applicable", "reason": "本次只调整日志，不改业务接口"},
        }
        html = render_spec(spec, TEMPLATE)
        coverage = decode_html_payload(html)["metadata"]["sectionCoverage"]["apis"]
        self.assertEqual("not_applicable", coverage["status"])
        self.assertEqual("本次只调整日志，不改业务接口", coverage["reason"])


if __name__ == "__main__":
    unittest.main()
