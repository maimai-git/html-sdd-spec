import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from html_sdd.scaffold import skeleton_spec

ROOT = Path(__file__).resolve().parents[1]
PROPERTIES = """# ===== Orders / Apollo / application =====
# 目标环境：测试
# AppId：orders
# Namespace：application

# 订单功能开关｜控制订单功能。默认值为 false。
# 本地生效值，来自 testlocal。
orders.enabled=true
"""
SQL = """-- ===== 01 Orders / orders =====
-- 目标环境：测试
-- 数据库类型：PostgreSQL
-- 目标实例（Archery）：test-orders
-- 数据库：orders
-- Schema：public
-- 前置条件：核对已部署结构。
-- 跨库依赖：无。
CREATE TABLE public.orders (id bigint PRIMARY KEY);
-- ===== 历史数据补充 =====
ALTER TABLE public.orders ADD COLUMN status text;
"""


class ReleaseCheckTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        self.directory = self.repo / "html-sdd-spec" / "订单"
        self.directory.mkdir(parents=True)
        self.source = self.directory / "方案事实源.json"
        self.spec = skeleton_spec()
        self.config = self.add_file("上线配置清单/上线配置.properties", "Apollo", PROPERTIES)
        self.sql = self.add_file("上线SQL清单/上线SQL.sql", "DDL", SQL)

    def add_file(self, relative_path, kind, body):
        file = self.directory / relative_path
        file.parent.mkdir()
        file.write_text(body, encoding="utf-8")
        self.spec["configs"].append({
            "id": f"CFG-{len(self.spec['configs']) + 1}",
            "group": "订单", "kind": kind, "title": kind, "environment": "测试",
            "status": "待验证", "content": body.rstrip("\n"),
            "source": file.relative_to(self.repo).as_posix(),
        })
        return file

    def replace_file(self, file, body):
        file.write_text(body, encoding="utf-8")
        record = next(item for item in self.spec["configs"] if item["source"].endswith(file.name))
        record["content"] = body.rstrip("\n")

    def check(self, *args, exit_code=0):
        self.source.write_text(json.dumps(self.spec, ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "html_sdd", "check", str(self.source), "--json", *args],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(exit_code, result.returncode, result.stdout + result.stderr)
        return {issue["code"] for issue in json.loads(result.stdout)}

    def test_valid_release_with_sql_subheading(self):
        self.assertEqual(set(), self.check("--release"))

    def test_missing_file_and_stale_snapshot_are_release_only(self):
        self.sql.unlink()
        self.config.write_text(PROPERTIES.replace("true", "false"), encoding="utf-8")
        self.assertEqual(set(), self.check())
        self.assertEqual(
            {"RELEASE_FILE_MISSING", "RELEASE_CONTENT_STALE"}, self.check("--release", exit_code=1)
        )

    def test_properties_comment_and_sql_section_requirements(self):
        self.replace_file(self.config, PROPERTIES.replace("# 订单功能开关｜控制订单功能。默认值为 false。\n", ""))
        self.replace_file(self.sql, SQL.replace("-- Schema：public\n", ""))
        self.assertEqual(
            {"RELEASE_CONFIG_COMMENT", "RELEASE_SECTION_FIELD"}, self.check("--release", exit_code=1)
        )

    def test_unresolved_targets_and_example_values(self):
        self.replace_file(self.config, PROPERTIES.replace("AppId：orders", "AppId：待核对。").replace("本地生效值", "示例值"))
        self.replace_file(self.sql, SQL.replace("test-orders", "<在 Archery 核对>"))
        self.assertEqual(
            {"RELEASE_TARGET_UNCONFIRMED", "RELEASE_CONFIG_EXAMPLE"}, self.check("--release", exit_code=1)
        )

    def test_release_check_rejects_source_outside_the_demand(self):
        self.spec["configs"][0]["source"] = "../上线配置清单/上线配置.properties"
        self.assertIn("RELEASE_SOURCE_INVALID", self.check("--release", exit_code=1))


    def test_multiple_configuration_sections_are_checked_independently(self):
        second = """# ===== Worker / 环境变量 / Deployment =====
# 目标环境：生产
# 部署位置：订单 worker Deployment

# 订单功能开关｜控制异步处理。无默认值。
# 目标环境确认值，来自发布工单。
orders.enabled=false
"""
        self.replace_file(self.config, PROPERTIES + "\n" + second)
        self.assertEqual(set(), self.check("--release"))
        self.replace_file(self.config, PROPERTIES + "\n" + second.replace("# 部署位置：订单 worker Deployment\n", ""))
        self.assertEqual({"RELEASE_SECTION_FIELD"}, self.check("--release", exit_code=1))

    def test_each_target_database_requires_its_own_header_fields(self):
        second = SQL.replace("01 Orders / orders", "02 Reports / reports").replace(
            "-- 数据库：orders", "-- 数据库：reports"
        ).replace("-- 目标实例（Archery）：test-orders\n", "")
        self.replace_file(self.sql, SQL + "\n" + second)
        self.assertEqual({"RELEASE_SECTION_FIELD"}, self.check("--release", exit_code=1))

    def test_release_file_without_config_record_is_reported(self):
        self.spec["configs"].pop(0)
        self.assertEqual({"RELEASE_FILE_UNLINKED"}, self.check("--release", exit_code=1))
