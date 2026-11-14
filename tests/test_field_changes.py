import unittest
from pathlib import Path

from html_sdd.diffing import diff_specs
from html_sdd.renderer import render_spec

ROOT = Path(__file__).resolve().parents[1]


class FieldChangesTest(unittest.TestCase):
    def test_api_changes_match_by_position_and_name_after_expanding_refs(self):
        shared = {"$ref": "#/definitions/fields/shared"}
        query = {"field": "value", "location": "query", "type": "string"}
        header = {"field": "value", "location": "header", "type": "string"}
        before = {"apis": [{"id": "API-1", "request": [shared, query], "response": [{"name": "data.old"}]}],
                  "definitions": {"fields": {"shared": header}}}
        after = {"apis": [{"id": "API-1", "request": [query, shared], "response": [{"name": "data.new"}]}],
                 "definitions": {"fields": {"shared": dict(header, type="integer")}}}
        change = next(c.as_dict() for c in diff_specs(before, after) if c.section == "apis")
        self.assertEqual(
            [("request", "header", "value", "changed"), ("response", "", "data.new", "added"),
             ("response", "", "data.old", "removed")],
            [(r["area"], r["location"], r["name"], r["kind"]) for r in change["fieldChanges"]],
        )

    def test_table_columns_compare_by_name_and_legacy_ddl_is_indicated(self):
        before = {"tables": [{"id": "DATA-1", "columns": [{"name": "a", "type": "text"}]},
                             {"id": "DATA-2", "ddl": "old"}]}
        after = {"tables": [{"id": "DATA-1", "columns": [{"name": "a", "type": "integer"}]},
                            {"id": "DATA-2", "ddl": "new"}]}
        first, second = [c.as_dict() for c in diff_specs(before, after)]
        self.assertEqual("changed", first["fieldChanges"][0]["kind"])
        self.assertTrue(second["ddlChangedWithoutColumns"])
        self.assertNotIn("fieldChanges", second)

    def test_reordering_and_legacy_aliases_do_not_mark_fields_changed(self):
        before = {"apis": [{"id": "API-1", "request": [
            {"field": "a", "where": "query", "desc": "说明"},
            {"field": "b", "location": "query"},
        ]}]}
        after = {"apis": [{"id": "API-1", "request": [
            {"name": "b", "location": "query"},
            {"name": "a", "location": "query", "description": "说明"},
        ]}]}
        self.assertNotIn("fieldChanges", diff_specs(before, after)[0].as_dict())

    def test_generated_pages_contain_safe_field_data_only_with_baseline(self):
        before = {"apis": [{"id": "API-1", "request": []}]}
        after = {"apis": [{"id": "API-1", "request": [{"name": "</script>"}]}]}
        for name in ("console.html", "console-vue.html"):
            template = ROOT / "html_sdd" / "assets" / name
            html = render_spec(after, template, baseline=before)
            self.assertIn('"kind":"added"', html)
            self.assertIn(r"\u003c/script\u003e", html)
            self.assertNotIn('"kind":"added"', render_spec(after, template))

    def test_templates_use_a_table_for_column_diffs_without_a_standalone_api_diff(self):
        for name in ("console.html", "console-vue.html"):
            with self.subTest(template=name):
                template = (ROOT / "html_sdd" / "assets" / name).read_text()
                self.assertNotIn("查看字段详情", template)
                self.assertNotIn("field-change-list", template)
                self.assertIn("column-diff-table", template)
                for label in ("字段", "变更", "旧值", "新值"):
                    self.assertIn(f'scope="col">{label}</th>', template)

    def test_reference_status_is_local_and_does_not_change_the_contract_diff(self):
        from html_sdd.references import expand_api

        ref = {"$ref": "#/definitions/fields/shared"}
        field = {"field": "id", "type": "string"}
        base = {"definitions": {"fields": {"shared": field}},
                "apis": [{"id": "API-1", "request": [ref]}]}
        updated = {"definitions": base["definitions"], "apis": [
            {"id": "API-1", "request": [dict(ref, changeStatus="修改")]},
        ]}
        request = expand_api(updated, updated["apis"][0])["request"]
        self.assertEqual([dict(field, changeStatus="修改")], request)
        self.assertNotIn("changeStatus", field)
        changes = diff_specs(base, updated)
        self.assertFalse(any(change.fields for change in changes))

    def test_invalid_explicit_status_is_rejected_by_check_and_render(self):
        from html_sdd.checker import validate_spec
        from html_sdd.scaffold import skeleton_spec

        spec = skeleton_spec()
        spec["tables"] = [{"id": "DATA-1", "columns": [{"name": "id", "changeStatus": "待确认"}]}]
        self.assertTrue(any(issue.code == "FIELD_CHANGE_STATUS_INVALID" for issue in validate_spec(spec)))
        with self.assertRaisesRegex(ValueError, "changeStatus"):
            render_spec(spec, ROOT / "html_sdd/assets/console.html")
