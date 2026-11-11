import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "html-sdd.schema.json"
EXAMPLE_PATH = ROOT / "examples" / "asset-library" / "sdd.json"

REQUIRED_TOP_LEVEL = {
    "specVersion",
    "metadata",
    "baseline",
    "agents",
    "requirements",
    "plans",
    "apis",
    "tables",
    "architecture",
    "configs",
    "evidence",
    "questions",
}


class SchemaShapeTest(unittest.TestCase):
    def test_schema_declares_required_top_level_sections(self):
        schema = json.loads(SCHEMA_PATH.read_text())
        self.assertEqual(schema["type"], "object")
        self.assertTrue(REQUIRED_TOP_LEVEL.issubset(schema["required"]))

    def test_asset_library_example_matches_required_shape(self):
        spec = json.loads(EXAMPLE_PATH.read_text())
        self.assertTrue(REQUIRED_TOP_LEVEL.issubset(spec))
        self.assertEqual(spec["specVersion"], "0.1")
        self.assertTrue(spec["requirements"])
        self.assertTrue(spec["plans"])
        self.assertTrue(spec["apis"])
        self.assertTrue(spec["tables"])
        self.assertTrue(spec["architecture"])
        self.assertTrue(spec["configs"])

    def test_schema_describes_the_coding_readiness_gate(self):
        schema = json.loads(SCHEMA_PATH.read_text())
        readiness = schema["properties"]["metadata"]["properties"]["readiness"]
        self.assertEqual(readiness["type"], "object")
        self.assertTrue({"overall", "codingReady", "blockingItems", "exitCriteria"}.issubset(readiness["required"]))

    def test_schema_freezes_schedule_status_enum_and_note(self):
        schema = json.loads(SCHEMA_PATH.read_text())
        plan = schema["$defs"]["plan"]["allOf"][1]["properties"]
        self.assertIn("待验收", plan["status"]["enum"])
        self.assertIn("阻塞", plan["status"]["enum"])
        self.assertEqual("string", plan["note"]["type"])


if __name__ == "__main__":
    unittest.main()
