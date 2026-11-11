import copy
import json
import unittest
from pathlib import Path

from html_sdd.checker import validate_spec

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = json.loads((ROOT / "examples/asset-library/sdd.json").read_text())


class CheckerTest(unittest.TestCase):
    def test_asset_library_example_has_no_errors(self):
        issues = validate_spec(EXAMPLE)
        self.assertEqual([], [i for i in issues if i.level == "error"], issues)

    def test_missing_related_id_is_reported(self):
        spec = copy.deepcopy(EXAMPLE)
        spec["requirements"][0]["related"].append("API-NOT-FOUND")
        issues = validate_spec(spec)
        self.assertTrue(any(i.code == "REF_MISSING" and "API-NOT-FOUND" in i.message for i in issues))

    def test_ready_requirement_requires_acceptance_and_delivery_fields(self):
        spec = copy.deepcopy(EXAMPLE)
        requirement = spec["requirements"][0]
        requirement["status"] = "编码 READY"
        requirement["acceptance"] = []
        requirement["related"] = []
        issues = validate_spec(spec)
        codes = {i.code for i in issues}
        self.assertIn("READY_INCOMPLETE", codes)

    def test_sensitive_value_is_rejected(self):
        spec = copy.deepcopy(EXAMPLE)
        spec["configs"][0]["content"] = "DATABASE_PASSWORD=real-secret-value"
        issues = validate_spec(spec)
        self.assertTrue(any(i.code == "SENSITIVE_VALUE" for i in issues))

    def test_ready_gate_requires_each_required_section_to_be_linked_to_requirement(self):
        spec = copy.deepcopy(EXAMPLE)
        requirement = spec["requirements"][0]
        requirement["status"] = "编码 READY"
        requirement["impact"] = {
            "apis": "required",
            "tables": "required",
            "architecture": "required",
            "configs": "required",
        }
        requirement["related"] = ["PLAN-001", "EVID-001"]
        for item in requirement["acceptance"]:
            item["evidence"] = "EVID-001"
        issues = validate_spec(spec)
        missing = [issue for issue in issues if issue.code == "READY_IMPACT_MISSING"]
        self.assertEqual(
            {"apis", "tables", "architecture", "configs"},
            {issue.path.rsplit(".", 1)[-1] for issue in missing},
        )

    def test_ready_acceptance_evidence_must_reference_evidence_record(self):
        spec = copy.deepcopy(EXAMPLE)
        requirement = spec["requirements"][0]
        requirement["status"] = "编码 READY"
        requirement["related"] = ["PLAN-001", "API-F-001", "DATA-F-001", "ARCH-001", "CFG-001"]
        requirement["impact"] = {
            "apis": "required",
            "tables": "required",
            "architecture": "required",
            "configs": "required",
        }
        for item in requirement["acceptance"]:
            item["evidence"] = "tests/acceptance.py"
        issues = validate_spec(spec)
        self.assertTrue(any(issue.code == "READY_EVIDENCE_UNLINKED" for issue in issues))


if __name__ == "__main__":
    unittest.main()
