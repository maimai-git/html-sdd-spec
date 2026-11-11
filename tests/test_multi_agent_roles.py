import unittest
from pathlib import Path

from html_sdd.checker import validate_spec
from html_sdd.renderer import render_spec
from html_sdd.scaffold import skeleton_spec


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "console.html"


class MultiAgentRolesTest(unittest.TestCase):
    def _spec_with_collaborators(self):
        spec = skeleton_spec()
        spec["agents"] = [
            {"id": "AG-OWNER", "name": "负责人", "role": "owner"},
            {"id": "AG-REVIEWER", "name": "主审核人", "role": "reviewer"},
            {"id": "AG-REVIEWER-DATA", "name": "数据审核人", "role": "reviewer"},
            {"id": "AG-EXECUTOR", "name": "主执行人", "role": "executor"},
            {"id": "AG-EXECUTOR-DATA", "name": "数据执行人", "role": "executor"},
        ]
        spec["requirements"] = [{
            "id": "REQ-001",
            "group": "订单",
            "title": "批量发货",
            "summary": "支持批量发货",
            "status": "待确认",
            "acceptance": [{"id": "AC-001", "text": "批量发货成功", "status": "待验证"}],
        }]
        spec["plans"] = [{
            "id": "PLAN-001",
            "priority": "P1",
            "module": "订单",
            "requirementIds": ["REQ-001"],
            "main": "批量发货",
            "sub": "接口和数据实现",
            "owner": "AG-OWNER",
            "reviewer": "AG-REVIEWER",
            "reviewerIds": ["AG-REVIEWER", "AG-REVIEWER-DATA"],
            "executor": "AG-EXECUTOR",
            "executorIds": ["AG-EXECUTOR", "AG-EXECUTOR-DATA"],
            "status": "进行中",
        }]
        return spec

    def test_plan_validates_multiple_reviewers_and_executors(self):
        spec = self._spec_with_collaborators()
        issues = validate_spec(spec)
        self.assertEqual([], [issue for issue in issues if issue.code == "REF_MISSING"])

    def test_missing_collaborator_id_is_reported(self):
        spec = self._spec_with_collaborators()
        spec["plans"][0]["executorIds"].append("AG-MISSING")
        issues = validate_spec(spec)
        self.assertTrue(any(issue.path.endswith("executorIds[2]") for issue in issues if issue.code == "REF_MISSING"))

    def test_primary_and_collaborator_roles_must_match_agent_role(self):
        spec = self._spec_with_collaborators()
        spec["plans"][0]["reviewerIds"] = ["AG-EXECUTOR-DATA"]
        spec["plans"][0]["executor"] = "AG-REVIEWER-DATA"
        issues = validate_spec(spec)
        mismatches = [issue for issue in issues if issue.code == "AGENT_ROLE_MISMATCH"]
        self.assertGreaterEqual(len(mismatches), 2)

    def test_schedule_template_has_primary_and_collaborator_role_renderer(self):
        html = render_spec(self._spec_with_collaborators(), TEMPLATE)
        self.assertIn("roleNames", html)
        self.assertIn("reviewerIds", html)
        self.assertIn("executorIds", html)


if __name__ == "__main__":
    unittest.main()
