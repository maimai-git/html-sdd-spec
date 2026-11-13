import copy
import unittest
from tests import test_catalog_filters as catalog
from html_sdd.checker import validate_spec

class TableDisplayTest(unittest.TestCase):
    run_js=catalog.CatalogFiltersTest.run_js

    def test_chinese_name_follows_physical_name_and_only_ddl_is_presented(self):
        spec=catalog.fixture();spec['tables'][0]['displayName']='文件记录'
        result=self.run_js('return {title:tableTitle(tables[0]),html:renderTables(tables[0])};',spec)
        self.assertEqual('demo_1（文件记录）',result['title'])
        self.assertIn('demo_1（文件记录）',result['html'])
        self.assertIn('-- 演示 DDL',result['html'])
        for label in ['表作用','当前状态','结构差异','范围/部署说明','执行情况待核实']:
            self.assertNotIn(label,result['html'])

    def test_missing_display_name_preserves_old_title_and_invalid_values_are_rejected(self):
        self.assertEqual('demo_1',self.run_js('return tableTitle(tables[0]);',catalog.fixture()))
        for value in (None,True,[],{},'', '  '):
            spec=copy.deepcopy(catalog.EXAMPLE);spec['tables'][0]['displayName']=value
            self.assertTrue(any(i.code=='TABLE_DISPLAY_NAME_INVALID' for i in validate_spec(spec)))

    def test_display_name_is_escaped_in_html(self):
        spec=catalog.fixture();spec['tables'][0]['displayName']='<文件&图>'
        html=self.run_js('return renderTables(tables[0]);',spec)
        self.assertIn('（&lt;文件&amp;图&gt;）',html)
        self.assertNotIn('<文件&图>',html)
