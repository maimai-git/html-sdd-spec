import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from html_sdd.scaffold import skeleton_spec

ROOT = Path(__file__).resolve().parents[1]


class SummaryTest(unittest.TestCase):
    def run_summary(self, spec):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sdd.json"
            source.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            before = source.read_bytes()
            result = subprocess.run(
                [sys.executable, "-m", "html_sdd", "summary", str(source), "--json"],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(source.read_bytes(), before)
            return json.loads(result.stdout)

    def test_completed_plan_does_not_close_delivery_or_unverified_acceptance(self):
        spec = skeleton_spec()
        spec["plans"] = [
            {"id": "PLAN-001", "module": "订单", "status": "已完成"},
            {"id": "PLAN-002", "module": "订单", "status": "已取消"},
            {"id": "PLAN-003", "module": "订单", "status": "阻塞", "blocker": "等待联调"},
        ]
        spec["requirements"] = [
            {"id": "REQ-001", "status": "已完成", "acceptance": [
                {"id": "AC-001", "status": "已通过", "evidence": "EVID-001"},
                {"id": "AC-002", "status": "已通过", "evidence": "EVID-MISSING"},
                {"id": "AC-003", "status": "待验收"},
            ]},
            {"id": "REQ-002", "status": "已取消", "acceptance": [
                {"id": "AC-004", "status": "待验收"},
            ]},
        ]
        spec["evidence"] = [{"id": "EVID-001", "status": "已验证"}]
        spec["apis"] = [{"id": "API-001", "status": "待部署", "developmentStatus": "已完成"}]
        spec["tables"] = [{"id": "DATA-001", "status": "待部署"}]
        spec["metadata"]["readiness"]["blockingItems"] = ["PLAN-003", "等待测试库", "等待测试库"]
        spec["questions"] = [{"id": "Q-001", "status": "已解决"}, {"id": "Q-002", "status": "待确认"}]
        result = self.run_summary(spec)
        self.assertEqual(["PLAN-003"], [x["id"] for x in result["pendingPlans"]])
        self.assertEqual(["PLAN-002"], [x["id"] for x in result["cancelledPlans"]])
        self.assertEqual(["AC-003"], [x["id"] for x in result["acceptanceGaps"]])
        self.assertEqual(["API-001", "DATA-001"], [x["id"] for x in result["deliveryGaps"]])
        self.assertEqual(["AC-002"], [x["id"] for x in result["unverified"]])
        self.assertEqual(["等待测试库"], result["blockingItems"])
        self.assertEqual(["Q-002"], [x["id"] for x in result["openQuestions"]])

    def test_empty_skeleton_reports_missing_coverage(self):
        result = self.run_summary(skeleton_spec())
        self.assertEqual(
            ["requirements", "plans", "apis", "tables", "configs", "architecture"],
            result["missingCoverage"],
        )
        self.assertFalse(result["codingReady"])

    def test_summary_uses_same_pending_items_as_vue(self):
        import re

        from html_sdd.renderer import render_spec

        spec = skeleton_spec()
        spec["metadata"]["sectionCoverage"].pop("apis")
        spec["metadata"]["sectionCoverage"]["tables"] = {
            "status": "not_applicable", "reason": "沿用当前表",
        }
        spec["questions"] = [
            {"id": "Q-USER", "question": "决定业务边界", "status": "待确认", "requiresUserDecision": True},
            {"id": "Q-AI", "question": "查测试环境", "status": "待确认", "requiresUserDecision": False},
            {"id": "Q-LEGACY", "question": "未分类", "status": "待确认"},
            {"id": "Q-CLOSED", "question": "已关闭", "status": "已解决"},
            {"id": "Q-CANCEL", "question": "已撤销", "status": "待确认", "state": "cancelled"},
        ]
        result = self.run_summary(spec)
        self.assertEqual(["Q-USER", "Q-AI", "Q-LEGACY"], [item["id"] for item in result["openQuestions"]])
        self.assertEqual([True, False, None], [item.get("requiresUserDecision") for item in result["openQuestions"]])
        self.assertIn("apis", result["missingCoverage"])
        self.assertNotIn("tables", result["missingCoverage"])
        spec["requirements"] = [{
            "id": "REQ-001", "status": "待验收", "acceptance": [
                {"id": "AC-001", "text": "这段验收条件只存一份", "status": "已通过"},
            ],
        }]
        spec["plans"] = [{"id": "PLAN-001", "status": "阻塞", "note": "这段备注只存一份"}]
        result = self.run_summary(spec)
        html = render_spec(spec, ROOT / "html_sdd" / "assets" / "console-vue.html")
        payload = re.search(r'<script id="html-sdd-summary" type="application/json">(.*?)</script>', html, re.S)
        self.assertIsNotNone(payload)
        embedded = json.loads(payload[1])
        for key in ("openQuestions", "pendingPlans", "deliveryGaps", "missingCoverage", "blockingItems", "acceptanceGaps", "unverified"):
            expected_ids = [item["id"] if isinstance(item, dict) else item for item in result[key]]
            rendered_ids = [item["id"] if isinstance(item, dict) else item for item in embedded[key]]
            self.assertEqual(expected_ids, rendered_ids)
        self.assertEqual(["Q-USER", "Q-AI", "Q-LEGACY"], embedded["openQuestions"])
        self.assertEqual(["PLAN-001"], embedded["pendingPlans"])
        self.assertEqual({
            "id": "AC-001", "status": "待核实", "reason": result["unverified"][0]["reason"],
        }, embedded["unverified"][0])
        self.assertNotIn("这段备注只存一份", payload[1])
        self.assertNotIn("这段验收条件只存一份", payload[1])

    def test_invalid_ready_flag_does_not_make_summary_ready(self):
        spec = skeleton_spec()
        spec["metadata"]["readiness"]["codingReady"] = True
        result = self.run_summary(spec)
        self.assertFalse(result["codingReady"])
        self.assertIn("READY_PROJECT_INCOMPLETE", [item["code"] for item in result["readinessIssues"]])
