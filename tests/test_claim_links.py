import copy
import json
import unittest
from pathlib import Path

from html_sdd.checker import validate_spec


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = json.loads((ROOT / "examples/asset-library/sdd.json").read_text(encoding="utf-8"))


class ClaimAndLinksTest(unittest.TestCase):
    def test_optional_claim_state_evidence_and_links_are_valid(self):
        spec = copy.deepcopy(EXAMPLE)
        requirement = spec["requirements"][0]
        evidence_id = spec["evidence"][0]["id"]
        requirement.update(
            {
                "state": "observed",
                "claim": {"kind": "fact", "confidence": "high"},
                "evidenceIds": [evidence_id],
                "links": {
                    "plans": [spec["plans"][0]["id"]],
                    "evidence": [evidence_id],
                },
            }
        )

        issues = validate_spec(spec)

        self.assertEqual([], [issue for issue in issues if issue.level == "error"], issues)

    def test_invalid_claim_kind_has_a_human_readable_error(self):
        spec = copy.deepcopy(EXAMPLE)
        spec["requirements"][0]["claim"] = {"kind": "事实", "confidence": "high"}

        issues = validate_spec(spec)

        issue = next(issue for issue in issues if issue.code == "CLAIM_KIND_INVALID")
        self.assertIn("fact", issue.message)

    def test_malformed_optional_values_report_issues_instead_of_raising(self):
        spec = copy.deepcopy(EXAMPLE)
        requirement = spec["requirements"][0]
        requirement.update(
            {
                "state": [],
                "claim": {"kind": [], "confidence": {}},
                "evidenceIds": [[]],
                "links": {"apis": [[]]},
            }
        )

        issues = validate_spec(spec)

        codes = {issue.code for issue in issues}
        self.assertTrue({"STATE_INVALID", "CLAIM_KIND_INVALID", "CLAIM_CONFIDENCE_INVALID", "REF_MISSING", "LINK_TARGET_MISSING"} <= codes)

    def test_claim_statement_is_validated_and_missing_statement_is_only_a_warning(self):
        spec = copy.deepcopy(EXAMPLE)
        requirement = spec["requirements"][0]
        requirement["claim"] = {"kind": "fact", "confidence": "high"}

        issues = validate_spec(spec)

        self.assertTrue(any(issue.code == "CLAIM_STATEMENT_MISSING" and issue.level == "warning" for issue in issues))
        self.assertFalse(any(issue.level == "error" and issue.path.endswith(".claim") for issue in issues))
        requirement["claim"]["statement"] = "文件资产库服务代码已落地。"
        self.assertFalse(any(issue.code == "CLAIM_STATEMENT_MISSING" for issue in validate_spec(spec)))

    def test_legacy_state_values_are_accepted_with_deprecation_warning(self):
        spec = copy.deepcopy(EXAMPLE)
        spec["requirements"][0]["state"] = "observed"

        issues = validate_spec(spec)

        self.assertTrue(any(issue.code == "STATE_DEPRECATED" and issue.level == "warning" for issue in issues))
        self.assertFalse(any(issue.level == "error" and issue.path.endswith(".state") for issue in issues))

    def test_explicit_null_statement_is_invalid_instead_of_missing(self):
        spec = copy.deepcopy(EXAMPLE)
        spec["requirements"][0]["claim"]["statement"] = None

        issues = validate_spec(spec)

        self.assertTrue(any(issue.code == "CLAIM_STATEMENT_INVALID" and issue.level == "error" for issue in issues))
        self.assertFalse(any(issue.code == "CLAIM_STATEMENT_MISSING" for issue in issues))

    def test_optional_fields_reject_explicit_null_but_allow_omission(self):
        for field in ("state", "claim", "evidenceIds", "links"):
            with self.subTest(field=field):
                spec = copy.deepcopy(EXAMPLE)
                spec["requirements"][0][field] = None
                errors = [i for i in validate_spec(spec) if i.level == "error"]
                self.assertTrue(any(i.path == f"requirements[0].{field}" for i in errors), errors)
        spec = copy.deepcopy(EXAMPLE)
        spec["requirements"][0]["claim"]["confidence"] = None
        self.assertTrue(any(i.code == "CLAIM_CONFIDENCE_INVALID" for i in validate_spec(spec)))

    def test_evidence_metadata_matches_schema_types_and_enums(self):
        for field, value in (("locator", None), ("capturedAt", []), ("commit", 42),
                             ("checkedBy", "invalid id"), ("checkedBy", None),
                             ("confidence", "certain"), ("confidence", None)):
            with self.subTest(field=field, value=value):
                spec = copy.deepcopy(EXAMPLE)
                spec["evidence"][0][field] = value
                errors = [i for i in validate_spec(spec) if i.level == "error"]
                self.assertTrue(any(i.path == f"evidence[0].{field}" for i in errors), errors)

    def test_evidence_ids_must_reference_existing_evidence(self):
        spec = copy.deepcopy(EXAMPLE)
        spec["requirements"][0]["evidenceIds"] = ["EVID-NOT-FOUND"]

        issues = validate_spec(spec)

        self.assertTrue(
            any(
                issue.code == "REF_MISSING"
                and issue.path.endswith("evidenceIds[0]")
                and "证据" in issue.message
                for issue in issues
            )
        )

    def test_links_must_point_to_the_declared_section(self):
        spec = copy.deepcopy(EXAMPLE)
        table_id = next(item["id"] for item in spec["tables"])
        spec["requirements"][0]["links"] = {"apis": [table_id]}

        issues = validate_spec(spec)

        issue = next(issue for issue in issues if issue.code == "LINK_TARGET_MISMATCH")
        self.assertIn("apis", issue.message)
        self.assertIn("tables", issue.message)

    def test_evidence_metadata_is_optional_and_accepted(self):
        spec = copy.deepcopy(EXAMPLE)
        spec["evidence"][0].update(
            {
                "locator": "tests/example.py:12",
                "capturedAt": "2026-11-11T10:00:00+08:00",
                "checkedBy": "AGENT-REVIEWER",
                "commit": "f319a11",
                "confidence": "medium",
            }
        )

        issues = validate_spec(spec)

        self.assertEqual([], [issue for issue in issues if issue.level == "error"], issues)


if __name__ == "__main__":
    unittest.main()
