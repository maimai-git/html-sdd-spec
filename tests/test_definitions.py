import copy
import json
import unittest
from pathlib import Path

from html_sdd.checker import validate_spec
from html_sdd.context import build_context
from html_sdd.diffing import diff_specs
from html_sdd.renderer import render_spec
from tests.rendered_payload import decode_html_payload
from html_sdd.references import expanded_spec

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = expanded_spec(json.loads((ROOT/'examples/asset-library/sdd.json').read_text()), drop_definitions=True)


def fixture():
    spec = copy.deepcopy(EXAMPLE)
    spec['definitions'] = {
        'fields': {'身份/~': {'field': 'Authorization', 'where': 'header', 'required': '是', 'type': 'string', 'description': '登录身份', 'example': 'Bearer <token>'},
                   '分页': [{'field': 'page', 'type': 'integer', 'example': 0}, {'field': 'limit', 'type': 'integer', 'example': 20}]},
        'rules': {'隔离': ['只读本人数据', '企业须校验当前成员']},
    }
    spec['apis'][0]['request'] = [{'$ref': '#/definitions/fields/身份~1~0'}, {'field': 'folder_id', 'example': None}, {'$ref': '#/definitions/fields/分页'}]
    spec['apis'][0]['rules'] = [{'$ref': '#/definitions/rules/隔离'}, '接口自身约束']
    spec['apis'][0]['requestExample'] = {'$ref': 'business data, do not resolve'}
    return spec


class DefinitionTest(unittest.TestCase):
    def test_expand_preserves_order_null_and_examples_without_mutating_input(self):
        from html_sdd.references import expand_api
        spec = fixture(); before = copy.deepcopy(spec)
        api = expand_api(spec, spec['apis'][0])
        self.assertEqual(['Authorization', 'folder_id', 'page', 'limit'], [r['field'] for r in api['request']])
        self.assertIsNone(api['request'][1]['example'])
        self.assertEqual(['只读本人数据', '企业须校验当前成员', '接口自身约束'], api['rules'])
        self.assertEqual(spec['apis'][0]['requestExample'], api['requestExample'])
        api['request'][0]['description'] = 'changed locally'
        self.assertEqual(before, spec)

    def test_checker_and_renderer_reject_invalid_definitions(self):
        cases = [
            {'$ref': '#/definitions/fields/不存在'},
            {'$ref': 'https://example.org/field.json'},
            {'$ref': '#/definitions/rules/隔离'},
            {'$ref': '#/definitions/fields/身份~1~0', 'required': '否'},
            {'$ref': '#/definitions/fields/身份~2'},
        ]
        for ref in cases:
            with self.subTest(ref=ref):
                spec = fixture(); spec['apis'][0]['request'] = [ref]
                issues = validate_spec(spec)
                self.assertTrue(any(i.level == 'error' and i.code == 'DEFINITION_ERROR' for i in issues), issues)
                with self.assertRaises(ValueError):
                    render_spec(spec, ROOT/'html_sdd/assets/console.html')

    def test_definitions_are_not_recursive_and_validate_unused_values(self):
        for bad in ({'$ref': '#/definitions/fields/分页'}, [], None, 3):
            with self.subTest(value=bad):
                spec = fixture(); spec['definitions']['fields']['未使用'] = bad
                self.assertTrue(any(i.code == 'DEFINITION_ERROR' for i in validate_spec(spec)))

    def test_html_stores_refs_and_full_context_expands_only_target(self):
        spec = fixture()
        html = render_spec(spec, ROOT/'html_sdd/assets/console.html')
        self.assertEqual(spec, decode_html_payload(html))
        context = build_context(spec, spec['apis'][0]['id'], 'executor', full=True)
        self.assertEqual('Authorization', context['record']['request'][0]['field'])
        self.assertNotIn('definitions', context)
        self.assertNotIn('definitions', context['record'])
        self.assertIn('rules', context['record'])

    def test_definition_change_reports_impacted_api(self):
        before = fixture(); after = copy.deepcopy(before)
        after['definitions']['fields']['身份/~']['description'] = '最新登录约束'
        changes = diff_specs(before, after)
        self.assertTrue(any(c.section == 'definitions' for c in changes))
        api = next(c for c in changes if c.section == 'apis' and c.record_id == before['apis'][0]['id'])
        self.assertEqual('最新登录约束', api.after['request'][0]['description'])

    def test_inline_legacy_documents_still_work(self):
        from html_sdd.references import expand_api
        self.assertEqual(EXAMPLE['apis'][0], expand_api(EXAMPLE, EXAMPLE['apis'][0]))
        self.assertFalse([i for i in validate_spec(EXAMPLE) if i.level == 'error'])

    def test_schema_declares_the_same_local_reference_shapes(self):
        import re
        schema = json.loads((ROOT/'schema/html-sdd.schema.json').read_text())
        for category, ref_kind in (('fields','fieldReference'),('rules','ruleReference')):
            ref = schema['$defs'][ref_kind]
            self.assertFalse(ref['additionalProperties'])
            pattern=ref['properties']['$ref']['pattern']
            self.assertTrue(re.fullmatch(pattern,'#/definitions/'+category+'/名称~1~0'))
            self.assertFalse(re.fullmatch(pattern,'https://example.org/field'))
            self.assertFalse(re.fullmatch(pattern,'#/definitions/'+category+'/名称~2'))

    def test_ref_in_field_example_is_opaque_and_unused_sensitive_values_rejected(self):
        from html_sdd.references import expand_api
        spec=fixture()
        spec['definitions']['fields']['身份/~']['example']={'$ref':'business only'}
        self.assertEqual({'$ref':'business only'},expand_api(spec,spec['apis'][0])['request'][0]['example'])
        spec['definitions']['rules']['未使用']='DATABASE_PASSWORD=real-secret-value'
        self.assertTrue(any(i.code=='SENSITIVE_VALUE' for i in validate_spec(spec)))

    def test_context_budget_applies_after_expansion_and_diff_sees_removed_refs(self):
        from html_sdd.context import serialize_context, ContextError
        spec=fixture(); spec['definitions']['fields']['身份/~']['description']='完整约束'*4000
        context=build_context(spec,spec['apis'][0]['id'],'executor',full=True)
        with self.assertRaises(ContextError):serialize_context(context,as_json=True,full=True,max_chars=3000)
        after=copy.deepcopy(spec); after['apis'][0]['request']=[];after['definitions']['fields'].pop('身份/~')
        changes=diff_specs(spec,after)
        self.assertTrue(any(c.kind=='removed' and c.section=='definitions' for c in changes))
        self.assertTrue(any(c.section=='apis' for c in changes))

    def test_invalid_containers_are_never_treated_as_empty_contracts(self):
        from html_sdd.references import expand_api
        for key in ('request','response','rules'):
            spec=fixture(); spec['apis'][0][key]={'$ref':'#/definitions/rules/隔离'}
            with self.subTest(slot=key):
                self.assertTrue(any(i.code=='DEFINITION_ERROR' for i in validate_spec(spec)))
                with self.assertRaises(ValueError):build_context(spec,spec['apis'][0]['id'],full=True)
                with self.assertRaises(ValueError):expand_api(spec,spec['apis'][0])

    def test_diff_distinguishes_false_zero_and_absent_null(self):
        before=fixture();after=copy.deepcopy(before)
        before['definitions']['fields']['身份/~']['example']=False
        after['definitions']['fields']['身份/~']['example']=0
        changes=diff_specs(before,after)
        self.assertTrue(any(c.section=='definitions' for c in changes))
        self.assertTrue(any(c.section=='apis' for c in changes))
        after=copy.deepcopy(before);after['apis'][0]['optional_marker']=None
        changes=diff_specs(before,after)
        self.assertIn('optional_marker', next(c.summary for c in changes if c.section=='apis'))

    def test_diff_rejects_broken_interface_sections_or_records(self):
        for broken in ({}, [None]):
            spec=fixture();after=copy.deepcopy(spec);after['apis']=broken
            with self.subTest(value=broken),self.assertRaises(ValueError):
                diff_specs(spec,after)
