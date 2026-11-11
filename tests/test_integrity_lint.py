import copy
import json
import unittest
from pathlib import Path

from html_sdd.checker import validate_spec


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = json.loads((ROOT / "examples/asset-library/sdd.json").read_text())


class IntegrityLintTest(unittest.TestCase):
    def test_solution_architecture_requires_renderer_contract_fields(self):
        spec = copy.deepcopy(EXAMPLE)
        solution = next(item for item in spec["architecture"] if item["type"] == "solution")
        solution.pop("risks", None)
        solution["risk"] = "旧字段"
        issues = validate_spec(spec)
        self.assertTrue(any(issue.code == "ARCH_FIELD_MISSING" and issue.path.endswith(".risks") for issue in issues))

    def test_diagram_architecture_requires_source_or_fallback(self):
        spec = copy.deepcopy(EXAMPLE)
        diagram = next(item for item in spec["architecture"] if item["type"] == "diagram")
        diagram.pop("diagramSource", None)
        diagram.pop("fallback", None)
        diagram.pop("diagramSvg", None)
        issues = validate_spec(spec)
        self.assertTrue(any(issue.code == "ARCH_FIELD_MISSING" and "diagramSource" in issue.message for issue in issues))

    def test_stable_acceptance_evidence_id_must_exist(self):
        spec = copy.deepcopy(EXAMPLE)
        spec["requirements"][0]["acceptance"][0]["evidence"] = "EVID-NOT-FOUND"
        issues = validate_spec(spec)
        self.assertTrue(any(issue.code == "REF_MISSING" and issue.path.endswith("acceptance[0].evidence") for issue in issues))

    def test_requirement_without_plan_is_reported_as_warning(self):
        spec = copy.deepcopy(EXAMPLE)
        spec["plans"] = []
        issues = validate_spec(spec)
        self.assertTrue(any(issue.level == "warning" and issue.code == "LINT_PLAN_LINK_MISSING" for issue in issues))

    def test_parallel_executors_require_owner_paths(self):
        spec = copy.deepcopy(EXAMPLE)
        plan = spec["plans"][0]
        plan["executorIds"] = [plan["executor"], "AGENT-REVIEWER"]
        plan.pop("ownerPaths", None)
        issues = validate_spec(spec)
        self.assertTrue(any(issue.code == "LINT_OWNER_PATHS_MISSING" for issue in issues))

    def test_overlapping_owner_paths_are_reported(self):
        spec = copy.deepcopy(EXAMPLE)
        spec["plans"][0]["ownerPaths"] = ["src/assets"]
        spec["plans"][1]["ownerPaths"] = ["src/assets/styles"]
        spec["plans"][1]["deps"] = []
        issues = validate_spec(spec)
        self.assertTrue(any(issue.code == "LINT_OWNER_PATH_OVERLAP" for issue in issues))

    def test_ready_requirement_requires_plan_and_acceptance_evidence(self):
        spec = copy.deepcopy(EXAMPLE)
        requirement = spec["requirements"][0]
        requirement["status"] = "编码 READY"
        requirement["acceptance"][0]["evidence"] = "EVID-REQ"
        for plan in spec["plans"]:
            plan["requirementIds"] = [item for item in plan["requirementIds"] if item != requirement["id"]]
        requirement["acceptance"][1].pop("evidence", None)
        issues = validate_spec(spec)
        ready_issues = [issue for issue in issues if issue.code == "READY_INCOMPLETE"]
        self.assertGreaterEqual(len(ready_issues), 2)

    def test_plan_dependency_cycle_is_reported(self):
        spec = copy.deepcopy(EXAMPLE)
        spec["plans"][0]["deps"] = [spec["plans"][1]["id"]]
        spec["plans"][1]["deps"] = [spec["plans"][0]["id"]]
        issues = validate_spec(spec)
        self.assertTrue(any(issue.code == "LINT_DEPENDENCY_CYCLE" for issue in issues))


if __name__ == "__main__":
    unittest.main()
