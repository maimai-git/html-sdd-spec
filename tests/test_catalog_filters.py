import copy
import json
import shutil
import unittest
from pathlib import Path

from html_sdd.checker import validate_spec
from html_sdd.scaffold import skeleton_spec

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = json.loads((ROOT / "examples/asset-library/sdd.json").read_text())


def fixture():
    spec = skeleton_spec()
    spec["metadata"]["status"] = "测试中的真实阶段"
    spec["metadata"]["statusPolicy"] = "legacy"
    for i, (kind, state) in enumerate((("新增接口", "已完成"), ("存量接口变更", "部分完成"), ("存量接口复用", "未开发"), ("新增接口", None)), 1):
        row = {"id": f"API-{i}", "group": "文件", "name": f"接口{i}", "path": f"/api/demo/{i}", "method": "GET", "changeType": kind, "status": "代码已实现，迁移待执行", "summary": "演示", "request": [], "response": [], "requestExample": {}, "responseExample": {}}
        if state is not None:
            row["developmentStatus"] = state
        spec["apis"].append(row)
    for i, (kind, state) in enumerate((("新增数据表", "已完成"), ("存量表变更", "未开发"), ("存量表复用", "部分完成")), 1):
        spec["tables"].append({"id": f"DATA-{i}", "group": "文件", "name": f"demo_{i}", "changeType": kind, "developmentStatus": state, "status": "执行情况待核实", "purpose": "示意", "ddl": "-- 演示 DDL"})
    spec["existingInterfaces"] = [copy.deepcopy(spec["apis"][0])]
    return spec


@unittest.skipUnless(shutil.which("node"), "模板运行回归需要 Node")
class CatalogFiltersTest(unittest.TestCase):
    def run_js(self, expression, spec=None):
        from tests.vue_runtime import run_vue
        return run_vue(expression, spec if spec is not None else fixture())

    def test_development_status_is_explicit_and_missing_stays_unverified(self):
        self.assertEqual(["已完成", "部分完成", "未开发", "待核实"], self.run_js('mode.value="apis";return records.value.map(itemStatus);'))

    def test_filters_combine_and_remain_independent_between_categories(self):
        result = self.run_js('''filters.apis={query:"",status:"已完成",change:"新增接口"};
filters.tables={query:"",status:"部分完成",change:"存量表复用"};
return Object.fromEntries(["apis","tables","existingInterfaces"].map(key=>{mode.value=key;return [key,visible.value.map(x=>x.id)]}));''')
        self.assertEqual({"apis": ["API-1"], "tables": ["DATA-3"], "existingInterfaces": ["API-1"]}, result)
        self.assertEqual(["API-2", "API-3"], self.run_js('mode.value="apis";filters.apis.status="未完成";return visible.value.map(x=>x.id);'))
        self.assertEqual(["API-4"], self.run_js('mode.value="apis";filters.apis.status="待核实";return visible.value.map(x=>x.id);'))

    def test_empty_results_have_no_selected_detail(self):
        result = self.run_js('mode.value="apis";selected.value="API-1";filters.apis={query:"",status:"已完成",change:"存量接口复用"};return {record:record.value||null,count:visible.value.length,total:records.value.length};')
        self.assertEqual({"record": None, "count": 0, "total": 4}, result)

    def test_development_and_deployment_status_are_independent(self):
        result = self.run_js('return ["apis","tables"].map(key=>{mode.value=key;const item=records.value.find(x=>x.developmentStatus==="部分完成");return [itemStatus(item),recordStatus(item),statusNote(item)]});')
        self.assertEqual(["部分完成", "待核实", "代码已实现，迁移待执行"], result[0])
        self.assertEqual(["部分完成", "待核实", "执行情况待核实"], result[1])

    def test_response_parameter_columns_include_required_heading(self):
        self.assertEqual(["字段", "类型", "必填", "说明", "示例"], self.run_js('return columns("response").map(caption);'))

    def test_config_content_is_preserved_in_primary_fields(self):
        spec=fixture()
        spec["configs"]=[{"id":"CFG-1","title":"发布配置","content":"DEMO_ENABLED=true"}]
        self.assertEqual([["content", "DEMO_ENABLED=true"]], self.run_js('mode.value="configs";return primary.value;', spec))


class DevelopmentStatusContractTest(unittest.TestCase):
    def test_optional_status_rejects_invalid_explicit_values(self):
        for section in ("apis", "tables"):
            for value in (None, [], {}, True, "差不多完成"):
                with self.subTest(section=section, value=value):
                    spec = copy.deepcopy(EXAMPLE)
                    spec[section][0]["developmentStatus"] = value
                    self.assertTrue(any(i.code == "DEVELOPMENT_STATUS_INVALID" for i in validate_spec(spec)))
            for value in ("已完成", "部分完成", "未开发"):
                spec = copy.deepcopy(EXAMPLE)
                spec[section][0]["developmentStatus"] = value
                self.assertFalse(any(i.code == "DEVELOPMENT_STATUS_INVALID" for i in validate_spec(spec)))

    def test_config_source_is_optional_but_explicit_value_must_be_string(self):
        for value in (None, [], {}, 1, True):
            with self.subTest(value=value):
                spec = copy.deepcopy(EXAMPLE)
                spec["configs"][0]["source"] = value
                self.assertTrue(any(i.code == "CONFIG_SOURCE_INVALID" for i in validate_spec(spec)))
        spec = copy.deepcopy(EXAMPLE)
        spec["configs"][0]["source"] = "发布配置/最终SQL.sql"
        self.assertFalse(any(i.code == "CONFIG_SOURCE_INVALID" for i in validate_spec(spec)))

    def test_schema_supports_optional_development_status_and_api_reuse(self):
        schema = json.loads((ROOT / "schema/html-sdd.schema.json").read_text())
        for kind in ("api", "table"):
            contract = schema["$defs"][kind]["allOf"][1]
            self.assertEqual(["已完成", "部分完成", "未开发"], contract["properties"]["developmentStatus"]["enum"])
            self.assertNotIn("developmentStatus", contract["required"])
        self.assertIn("存量接口复用", schema["$defs"]["api"]["allOf"][1]["properties"]["changeType"]["enum"])


if __name__ == "__main__":
    unittest.main()
