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
