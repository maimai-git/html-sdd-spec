import copy
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from html_sdd.cli import main
from html_sdd.diffing import diff_specs
from html_sdd.references import expanded_spec
from tests.test_definitions import EXAMPLE


def source():
    spec = copy.deepcopy(EXAMPLE)
    row = {'field':'Authorization','type':'string','required':'是','where':'header','description':'可信登录身份，不能用 scope 覆盖。'*20,'example':'Bearer <token>'}
    for api in spec['apis'][:4]:
        api['request'] = [copy.deepcopy(row), {'field':'folder_id', 'example':None}]
        api['rules'] = ['保持原有权限、空间和不可见资源的错误语义。'*20]
    # Same name with different where, required and type must stay distinct.
    spec['apis'][1]['request'].append(dict(row, where='query', required='否', type='object'))
    spec['apis'][0]['responseExample'] = {'id':0, 'ok':False, 'folder_id':None}
    return spec


class ReuseTest(unittest.TestCase):
    def test_reuse_reduces_size_without_changing_contracts_or_input(self):
        from html_sdd.reuse import reuse_spec
        spec = source(); before = copy.deepcopy(spec)
        result = reuse_spec(spec)
        self.assertLess(len(json.dumps(result,ensure_ascii=False)),len(json.dumps(spec,ensure_ascii=False)))
        self.assertEqual(expanded_spec(spec,drop_definitions=True),expanded_spec(result,drop_definitions=True))
        self.assertEqual(spec,before)
        self.assertEqual(result,reuse_spec(result))
        self.assertEqual('query',result['apis'][1]['request'][-1]['where'])
        self.assertFalse([c for c in diff_specs(spec,result) if c.section!='definitions'])

    def test_preview_does_not_write_and_explicit_output_roundtrips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'方案事实源.json';path.write_text(json.dumps(source(),ensure_ascii=False))
            before=path.read_bytes(); stream=StringIO()
            with redirect_stdout(stream):code=main(['reuse',str(path)])
            self.assertEqual(0,code);self.assertEqual(before,path.read_bytes())
            output=Path(tmp)/'候选.json'
            with redirect_stdout(StringIO()):code=main(['reuse',str(path),'--output',str(output)])
            self.assertEqual(0,code)
            self.assertEqual(expanded_spec(source(),drop_definitions=True),expanded_spec(json.loads(output.read_text()),drop_definitions=True))

    def test_unused_small_definitions_are_not_added(self):
        from html_sdd.reuse import reuse_spec
        spec=copy.deepcopy(EXAMPLE)
        for api in spec['apis']:
            api['request']=[];api['response']=[];api['rules']=['短规则']
        self.assertNotIn('definitions',reuse_spec(spec))

    def test_compatible_with_existing_group_definitions(self):
        from html_sdd.reuse import reuse_spec
        spec=source();spec['definitions']={'rules':{'显式规则':['保留一','保留二']}}
        spec['apis'][0]['rules'].append({'$ref':'#/definitions/rules/显式规则'})
        result=reuse_spec(spec)
        self.assertEqual(spec['definitions']['rules']['显式规则'],result['definitions']['rules']['显式规则'])
        self.assertEqual(expanded_spec(spec,drop_definitions=True),expanded_spec(result,drop_definitions=True))

    def test_minified_source_candidate_does_not_grow(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.json';output=Path(tmp)/'candidate.json'
            path.write_text(json.dumps(source(),ensure_ascii=False,separators=(',',':')))
            with redirect_stdout(StringIO()):code=main(['reuse',str(path),'--output',str(output)])
            self.assertEqual(0,code)
            self.assertLess(output.stat().st_size,path.stat().st_size)

    def test_false_zero_absent_and_null_are_not_unified(self):
        from html_sdd.reuse import reuse_spec
        spec=source()
        for api in spec['apis'][:4]:
            api['response']=[{'field':'ok','example':False,'description':'布尔原值'*30},
                             {'field':'ok','example':0,'description':'布尔原值'*30},
                             {'field':'folder_id','example':None,'description':'显式根目录'*30},
                             {'field':'folder_id','description':'显式根目录'*30}]
        expanded=expanded_spec(reuse_spec(spec),drop_definitions=True)
        self.assertIs(expanded['apis'][0]['response'][0]['example'],False)
        self.assertIs(type(expanded['apis'][0]['response'][1]['example']),int)
        self.assertIn('example',expanded['apis'][0]['response'][2])
        self.assertNotIn('example',expanded['apis'][0]['response'][3])

    def test_existing_output_and_source_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.json';output=Path(tmp)/'candidate.json'
            path.write_text(json.dumps(source(),ensure_ascii=False));before=path.read_bytes()
            output.write_text('人工修改，请勿覆盖')
            for target in (output,path):
                with redirect_stdout(StringIO()):code=main(['reuse',str(path),'--output',str(target)])
                self.assertEqual(1,code)
            self.assertEqual('人工修改，请勿覆盖',output.read_text())
            self.assertEqual(before,path.read_bytes())

    def test_reuse_drops_only_new_field_markers_repeated_by_the_parent(self):
        from html_sdd.reuse import reuse_spec

        spec = {
            'apis': [
                {'id': 'API-NEW', 'changeType': '新增接口',
                 'request': [{'$ref': '#/definitions/fields/shared', 'changeStatus': '新增'}],
                 'response': [{'field': 'id', 'changeStatus': '新增'},
                              {'field': 'legacy', 'changeStatus': '删除'}],
                 'responseExample': {'changeStatus': '新增'}},
                {'id': 'API-OLD', 'changeType': '存量接口变更',
                 'request': [{'field': 'value', 'changeStatus': '新增'}]},
            ],
            'tables': [
                {'id': 'DATA-NEW', 'changeType': '新增数据表', 'ddl': 'CREATE TABLE sample (id bigint)',
                 'columns': [{'name': 'id', 'type': 'bigint', 'changeStatus': '新增'}]},
                {'id': 'DATA-OLD', 'changeType': '存量表变更',
                 'columns': [{'name': 'value', 'changeStatus': '新增'}]},
            ],
            'definitions': {'fields': {'shared': {'field': 'Authorization'}}},
        }
        original = copy.deepcopy(spec)
        compact = reuse_spec(spec)
        self.assertEqual([{'$ref': '#/definitions/fields/shared'}], compact['apis'][0]['request'])
        self.assertEqual([{'field': 'id'}, {'field': 'legacy', 'changeStatus': '删除'}],
                         compact['apis'][0]['response'])
        self.assertEqual({'changeStatus': '新增'}, compact['apis'][0]['responseExample'])
        self.assertEqual([{'name': 'id', 'type': 'bigint'}], compact['tables'][0]['columns'])
        self.assertEqual(spec['apis'][1], compact['apis'][1])
        self.assertEqual(spec['tables'][1], compact['tables'][1])
        self.assertEqual(original, spec)
        self.assertEqual(compact, reuse_spec(compact))

    def test_reuse_shares_interface_notes_without_turning_them_into_rules(self):
        from html_sdd.reuse import reuse_spec

        shared = "这段补充说明适用于多条接口。" * 20
        spec = {"apis": [{"notes": [shared, "本接口的例外"]}] * 2,
                "existingInterfaces": [{"notes": [shared], "rules": ["保持原规则"]}]}
        compact = reuse_spec(spec)
        self.assertIn("$ref", compact["apis"][0]["notes"][0])
        self.assertNotIn("rules", compact["apis"][0])
        self.assertEqual(spec, expanded_spec(compact, drop_definitions=True))
        self.assertEqual(compact, reuse_spec(compact))

    def test_format_command_compacts_json_without_changing_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.json"
            output = Path(tmp) / "compact.json"
            spec = {"apis": [{"id": "API-1", "request": [{"field": "状态", "example": False}]}]}
            original = json.dumps(spec, indent=4, ensure_ascii=False)
            path.write_text(original, encoding="utf-8")
            with redirect_stdout(StringIO()):
                self.assertEqual(0, main(["format", str(path), "--output", str(output)]))
            self.assertEqual(spec, json.loads(output.read_text(encoding="utf-8")))
            self.assertLess(output.stat().st_size, path.stat().st_size)
            self.assertEqual(original, path.read_text(encoding="utf-8"))
