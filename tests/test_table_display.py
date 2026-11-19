import copy
import unittest
from tests import test_catalog_filters as catalog
from html_sdd.checker import validate_spec

class TableDisplayTest(unittest.TestCase):
    run_js=catalog.CatalogFiltersTest.run_js

    def test_chinese_name_follows_physical_name_and_ddl_is_primary(self):
        spec=catalog.fixture();spec['tables'][0]['displayName']='文件记录'
        result=self.run_js('mode.value="tables";return {title:label(record.value),primary:primary.value};',spec)
        self.assertEqual('demo_1（文件记录）',result['title'])
        self.assertEqual([['ddl','-- 演示 DDL']],result['primary'])

    def test_missing_display_name_preserves_old_title_and_invalid_values_are_rejected(self):
        self.assertEqual('demo_1',self.run_js('mode.value="tables";return label(record.value);',catalog.fixture()))
        for value in (None,True,[],{},'', '  '):
            spec=copy.deepcopy(catalog.EXAMPLE);spec['tables'][0]['displayName']=value
            self.assertTrue(any(i.code=='TABLE_DISPLAY_NAME_INVALID' for i in validate_spec(spec)))

    def test_display_name_preserves_special_characters_for_vue_text_binding(self):
        spec=catalog.fixture();spec['tables'][0]['displayName']='<文件&图>'
        self.assertEqual('demo_1（<文件&图>）',self.run_js('mode.value="tables";return label(record.value);',spec))
