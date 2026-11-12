import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from html_sdd.context import ContextError, build_context, format_context


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = json.loads((ROOT / "examples/asset-library/sdd.json").read_text(encoding="utf-8"))


class ContextTest(unittest.TestCase):
    def test_context_resolves_links_dependencies_blockers_and_evidence(self):
        spec = copy.deepcopy(EXAMPLE)
        requirement = spec["requirements"][0]
        plan = spec["plans"][0]
        evidence_id = spec["evidence"][0]["id"]
        requirement["state"] = "observed"
        requirement["evidenceIds"] = [evidence_id]
        requirement["links"] = {
            "plans": [plan["id"]],
            "evidence": [evidence_id],
        }
        plan["state"] = "blocked"
        plan["blocker"] = "等待数据库验收"

        context = build_context(spec, requirement["id"], role="reviewer")

        self.assertEqual(requirement["id"], context["recordId"])
        self.assertEqual("requirements", context["section"])
        self.assertEqual("reviewer", context["role"])
        related_ids = {item["id"] for item in context["relatedRecords"]}
        self.assertIn(plan["id"], related_ids)
        self.assertIn(plan["id"], {item["id"] for item in context["blockers"]})
        self.assertIn(evidence_id, {item["id"] for item in context["evidence"]})
        self.assertIn("apis", context["focusSections"])

    def test_context_includes_plan_dependencies(self):
        spec = copy.deepcopy(EXAMPLE)
        plan = spec["plans"][1]

        context = build_context(spec, plan["id"], role="executor")

        self.assertEqual(plan["deps"], [item["id"] for item in context["dependencies"]])
        self.assertIn("apis", context["focusSections"])

    def test_context_rejects_unknown_record_id(self):
        with self.assertRaises(ContextError) as raised:
            build_context(EXAMPLE, "REQ-NOT-FOUND")

        self.assertIn("记录 ID 不存在", str(raised.exception))

    def test_text_context_has_stable_human_sections(self):
        context = build_context(EXAMPLE, EXAMPLE["requirements"][0]["id"], role="owner")

        output = format_context(context)

        self.assertIn("记录：REQ-001", output)
        self.assertIn("关联记录：", output)
        self.assertIn("阻塞：", output)
        self.assertIn("依赖：", output)
        self.assertIn("证据：", output)

    def test_context_cli_json_is_machine_readable(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "html_sdd",
                "context",
                str(ROOT / "examples/asset-library/sdd.json"),
                "REQ-001",
                "--role",
                "reviewer",
                "--json",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("REQ-001", payload["recordId"])
        self.assertEqual("reviewer", payload["role"])

    def test_context_cli_text_is_human_readable(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "html_sdd",
                "context",
                str(ROOT / "examples/asset-library/sdd.json"),
                "REQ-001",
                "--role",
                "owner",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("记录：REQ-001", result.stdout)
        self.assertIn("关联记录：", result.stdout)

    def test_role_filters_related_records_and_returns_compact_entries(self):
        outputs = {}
        for role in ("owner", "reviewer", "executor"):
            context = build_context(EXAMPLE, "REQ-001", role=role)
            outputs[role] = context
            self.assertEqual(context["totalCount"], context["includedCount"] + context["omittedCount"])
            self.assertEqual(context["includedCount"], len(context["relatedRecords"]))
            self.assertTrue(all("relation" in item for item in context["relatedRecords"]))
            self.assertTrue(all("record" not in item for item in context["relatedRecords"]))
            sections = {item["section"] for item in context["relatedRecords"]}
            self.assertTrue(sections <= set(context["focusSections"]))

        owner_sections = {item["section"] for item in outputs["owner"]["relatedRecords"]}
        reviewer_sections = {item["section"] for item in outputs["reviewer"]["relatedRecords"]}
        executor_sections = {item["section"] for item in outputs["executor"]["relatedRecords"]}
        self.assertIn("questions", owner_sections)
        self.assertIn("apis", reviewer_sections)
        self.assertNotIn("questions", executor_sections)
        self.assertIn("Q-001", {item["id"] for item in outputs["executor"]["blockers"]})
        self.assertGreater(len(outputs["reviewer"]["relatedRecords"]), len(outputs["owner"]["relatedRecords"]))

    def test_related_only_legacy_records_remain_usable(self):
        spec = copy.deepcopy(EXAMPLE)
        for section in ("agents", "requirements", "plans", "apis", "tables", "architecture", "configs", "evidence", "questions"):
            for record in spec.get(section, []):
                record.pop("links", None)

        context = build_context(spec, "REQ-001", role="owner")

        self.assertIn("PLAN-001", {item["id"] for item in context["relatedRecords"]})
        self.assertEqual(context["totalCount"], context["includedCount"] + context["omittedCount"])

    def test_full_expands_only_the_requested_record(self):
        context = build_context(EXAMPLE, "REQ-001", role="owner", full=True)

        self.assertIn("acceptance", context["record"])
        self.assertTrue(all("record" not in item for item in context["relatedRecords"]))

    def test_evidence_is_output_once_with_all_direct_relation_sources(self):
        spec = copy.deepcopy(EXAMPLE)
        requirement = spec["requirements"][0]
        evidence_id = spec["evidence"][0]["id"]
        requirement["related"].append(evidence_id)

        context = build_context(spec, requirement["id"], role="reviewer")

        self.assertFalse(any(item["section"] == "evidence" for item in context["relatedRecords"]))
        evidence = [item for item in context["evidence"] if item["id"] == evidence_id]
        self.assertEqual(1, len(evidence))
        self.assertTrue({"related", "links.evidence", "evidenceIds"} <= set(evidence[0]["relation"]))

    def test_related_only_evidence_is_collected_in_evidence_list(self):
        spec = {"requirements": [{"id": "REQ-LEGACY", "related": ["EVID-LEGACY"]}],
                "evidence": [{"id": "EVID-LEGACY", "label": "旧证据"}]}

        context = build_context(spec, "REQ-LEGACY", role="owner")

        self.assertEqual([], context["relatedRecords"])
        self.assertEqual(["EVID-LEGACY"], [item["id"] for item in context["evidence"]])
        self.assertIn("related", context["evidence"][0]["relation"])

    def test_context_limits_blockers_and_evidence(self):
        spec = copy.deepcopy(EXAMPLE)
        requirement = spec["requirements"][0]
        requirement["related"] = []
        requirement["evidenceIds"] = []
        for index in range(20):
            question_id = "Q-LIMIT-{:02d}".format(index)
            evidence_id = "EVID-LIMIT-{:02d}".format(index)
            spec["questions"].append({"id": question_id, "question": "pending", "status": "待确认"})
            spec["evidence"].append({"id": evidence_id, "kind": "source", "label": "source", "source": "src", "status": "ok"})
            requirement["related"].extend([question_id, evidence_id])

        context = build_context(spec, requirement["id"], role="owner")

        self.assertLessEqual(len(context["blockers"]), 8)
        self.assertEqual(8, len(context["evidence"]))
        self.assertEqual(22, context["evidenceCounts"]["totalCount"])
        self.assertEqual(14, context["evidenceCounts"]["omittedCount"])
        self.assertIn("证据：共 22，返回 8，省略 14", format_context(context))

    def test_cli_full_and_role_outputs_report_related_count_and_are_smaller_than_full(self):
        sizes = {}
        counts = {}
        raw_records = {
            record["id"]: record
            for section in ("agents", "requirements", "plans", "apis", "tables", "architecture", "configs", "evidence", "questions")
            for record in EXAMPLE.get(section, [])
        }
        for role in ("owner", "reviewer", "executor"):
            result = subprocess.run(
                [sys.executable, "-m", "html_sdd", "context", str(ROOT / "examples/asset-library/sdd.json"), "REQ-001", "--role", role, "--json"],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            payload = json.loads(result.stdout)
            counts[role] = payload["totalCount"]
            sizes[role] = len(result.stdout.encode("utf-8"))
            legacy_payload = copy.deepcopy(payload)
            for related in legacy_payload["relatedRecords"]:
                related["record"] = raw_records[related["id"]]
            legacy_bytes = len(json.dumps(legacy_payload, ensure_ascii=False, indent=2).encode("utf-8"))
            self.assertLess(sizes[role], legacy_bytes)

        self.assertNotEqual(counts["owner"], counts["reviewer"])
        self.assertNotEqual(counts["reviewer"], counts["executor"])
        self.assertGreater(sizes["reviewer"], sizes["owner"])

    def test_text_context_includes_target_summary_and_full_details(self):
        compact = format_context(build_context(EXAMPLE, "REQ-001", role="owner"))
        self.assertIn(EXAMPLE["requirements"][0]["summary"], compact)

        result = subprocess.run(
            [sys.executable, "-m", "html_sdd", "context", str(ROOT / "examples/asset-library/sdd.json"), "REQ-001", "--role", "owner", "--full"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('"acceptance"', result.stdout)
        self.assertIn('"AC-001"', result.stdout)
        self.assertNotIn('"requestParams"', result.stdout)

    def test_context_cli_supports_full_for_target_record(self):
        result = subprocess.run(
            [sys.executable, "-m", "html_sdd", "context", str(ROOT / "examples/asset-library/sdd.json"), "REQ-001", "--full", "--json"],
            cwd=ROOT, capture_output=True, text=True,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("acceptance", payload["record"])
        self.assertTrue(all("record" not in item for item in payload["relatedRecords"]))


if __name__ == "__main__":
    unittest.main()
