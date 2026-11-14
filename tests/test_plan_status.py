import copy
import json
import unittest
from pathlib import Path

from html_sdd.checker import validate_spec

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = json.loads((ROOT / "examples/asset-library/sdd.json").read_text())
TEMPLATE = ROOT / "html_sdd" / "assets" / "console.html"
PLAN_STATUS = {
    "待拆分", "待确认", "编码 READY", "待开始", "进行中", "待接入",
    "待执行", "待复核", "待验收", "阻塞", "已完成", "已取消",
}


class PlanStatusTest(unittest.TestCase):
    def test_example_uses_only_canonical_plan_statuses(self):
        self.assertTrue({plan["status"] for plan in EXAMPLE["plans"]} <= PLAN_STATUS)

    def test_unknown_plan_status_is_rejected(self):
        spec = copy.deepcopy(EXAMPLE)
        spec["plans"][0]["status"] = "代码差不多完成"
        issues = validate_spec(spec)
        self.assertTrue(any(issue.code == "PLAN_STATUS_INVALID" for issue in issues))

    def test_schedule_template_has_note_column_and_status_renderer(self):
        html = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("<th>进展与备注</th>", html)
        self.assertIn("planStatus(p.status)", html)
        self.assertIn("planStatusClass", html)


if __name__ == "__main__":
    unittest.main()
