import json
import unittest
from pathlib import Path

from html_sdd.checker import load_spec, validate_spec


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "examples" / "asset-library" / "sdd.json"


class AssetLibraryCompletenessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = load_spec(str(SPEC_PATH))

    def test_spec_is_checkable_and_has_current_readiness_gate(self):
        self.assertEqual([], validate_spec(self.spec))
        readiness = self.spec["metadata"]["readiness"]
        self.assertIn(readiness["overall"], {"待验收", "编码 READY"})
        self.assertIn("blockingItems", readiness)

    def test_requirement_modules_cover_the_full_asset_library_scope(self):
        groups = {row["group"] for row in self.spec["requirements"]}
        self.assertTrue({"文件资产库", "风格", "模特", "Chat 引用", "空间与同步"} <= groups)

    def test_routes_are_grouped_and_distinguish_current_code_from_pending_chat(self):
        paths = {row["path"] for row in self.spec["apis"]}
        self.assertIn("/api/library/history", paths)
        self.assertIn("/api/library/styles", paths)
        self.assertIn("/api/library/models/generations", paths)
        self.assertIn("/api/library/references/validate", paths)
        turn = next(row for row in self.spec["apis"] if "/api/v1/chats/" in row["path"])
        self.assertEqual("存量接口变更", turn["changeType"])
        self.assertIn("待接入", turn["status"])

    def test_tables_cover_both_migrations_and_existing_authorities(self):
        names = {row["name"] for row in self.spec["tables"]}
        expected_new = {
            "asset_library_resource",
            "asset_library_folder",
            "asset_library_space_item",
            "asset_library_trash",
            "asset_library_operation",
            "file_retention_claim",
            "asset_library_download_bundle",
            "asset_library_style",
            "asset_library_style_reference",
            "asset_library_model",
            "asset_library_model_image",
            "asset_library_model_generation",
            "asset_library_style_trash",
            "asset_library_model_trash",
        }
        self.assertTrue(expected_new <= names)
        self.assertIn("public.file_record", names)
        self.assertIn("public.asset", names)
        self.assertTrue(all(row["ddl"].strip() for row in self.spec["tables"]))

    def test_spec_does_not_claim_unverified_integrations(self):
        self.assertTrue(any("进程内" in row.get("current", "") for row in self.spec["architecture"]))
        self.assertTrue(any("未接入" in row.get("current", "") for row in self.spec["apis"]))
        self.assertTrue(any("手工" in row.get("current", "") for row in self.spec["configs"]))


if __name__ == "__main__":
    unittest.main()
