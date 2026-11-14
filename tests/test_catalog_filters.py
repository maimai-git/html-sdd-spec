import copy
import json
import shutil
import subprocess
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
        from html_sdd.statuses import registry
        source = (ROOT / "html_sdd/assets/console.html").read_text().replace("__HTML_SDD_STATUSES__",json.dumps(registry(),ensure_ascii=False))
        code = source[source.index("    const statusRegistry="):source.rindex("    render();")]
        prelude = """
const spec=SPEC;
const window={};
const nodes={};
const document={addEventListener(){},querySelectorAll:()=>[],getElementById:id=>(nodes[id]??={innerHTML:'',textContent:'',className:'',querySelectorAll:()=>[],classList:{add(){},remove(){},toggle(){}}})};
""".replace("SPEC", json.dumps(spec if spec is not None else fixture(), ensure_ascii=False))
        script = prelude + code + "\nconsole.log(JSON.stringify((()=>{" + expression + "})()));"
        result = subprocess.run(["node", "-"], input=script, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def test_development_status_is_explicit_and_missing_stays_unverified(self):
        self.assertEqual(["已完成", "部分完成", "未开发", "待核实"], self.run_js("return apis.map(developmentStatus);"))
        self.assertEqual("unknown", self.run_js('return changeKind({changeType:"未知"});'))

    def test_filters_combine_and_remain_independent_between_categories(self):
        result = self.run_js('catalogFilters.apis={status:"已完成",type:"new"};catalogFilters.tables={status:"部分完成",type:"existing"};return {apis:allItems("apis").map(x=>x.id),tables:allItems("tables").map(x=>x.id),existing:allItems("existingInterfaces").length};')
        self.assertEqual({"apis": ["API-1"], "tables": ["DATA-3"], "existing": 1}, result)
        self.assertEqual(["API-2", "API-3"], self.run_js('catalogFilters.apis.type="existing";return allItems("apis").map(x=>x.id);'))
        self.assertEqual(["API-4"], self.run_js('catalogFilters.apis.status="待核实";return allItems("apis").map(x=>x.id);'))

    def test_empty_results_clear_detail_and_selection(self):
        result = self.run_js('state.mode="apis";state.selectedId="API-1";render();catalogFilters.apis={status:"已完成",type:"reused"};render();return {selected:state.selectedId,html:nodes.detail.innerHTML,count:nodes.catalogCount.textContent};')
        self.assertIsNone(result["selected"])
        self.assertIn("没有匹配条目", result["html"])
        self.assertNotIn("API-1", result["html"])
        self.assertIn("0 / 4", result["count"])

    def test_api_and_table_heads_separate_development_and_deployment(self):
        result = self.run_js('return {api:renderApis(apis[1]),table:renderTables(tables[2])};')
        for html in result.values():
            self.assertIn("部分完成", html)
        self.assertIn("delivery-note", result["api"])
        self.assertIn("代码已实现，迁移待执行", result["api"])
        self.assertNotIn("执行情况待核实", result["table"])
        self.assertIn("待核实", self.run_js('return renderApis(apis[3]);'))

    def test_examples_and_ddl_are_open_but_other_details_stay_collapsible(self):
        result = self.run_js('return {api:renderApis(apis[0]),table:renderTables(tables[0])};')
        self.assertEqual(2, result["api"].count('<details open class="disclosure example-disclosure"'))
        self.assertIn('<details open class="disclosure text-disclosure"', result["table"])
        self.assertNotIn("结构差异", result["table"])

    def test_response_parameter_columns_include_required_heading(self):
        html = self.run_js('return fieldTable([{name:"items",type:"array",required:"是",description:"示意结果",example:[]}],false);')
        self.assertIn("<th>必填</th>", html)
        self.assertEqual(5, html.count("<th>"))
        self.assertEqual(5, html.count("<td"))

    def test_compact_snapshot_does_not_repeat_work_status(self):
        html = self.run_js('renderSnapshot();return nodes.snapshot.innerHTML;')
        self.assertNotIn("snapshot-summary", html)
        self.assertNotIn("测试中的真实阶段", html)
        self.assertIn("版本信息", html)
        self.assertIn("编码条件", html)

    def test_config_page_keeps_content_without_rejected_notice(self):
        html = self.run_js('return renderConfigs({id:"CFG-1",title:"发布配置",content:"DEMO_ENABLED=true"});')
        self.assertIn("DEMO_ENABLED=true", html)
        self.assertNotIn("只展示需要填写或执行的文本", html)


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
