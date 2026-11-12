import copy
import unittest
from tests import test_catalog_filters as catalog
fixture, EXAMPLE = catalog.fixture, catalog.EXAMPLE
from html_sdd.checker import validate_spec


class ScheduleControlsTest(unittest.TestCase):
    run_js = catalog.CatalogFiltersTest.run_js

    def spec(self):
        spec = fixture()
        spec['plans'] = [dict(id=key,sequence=seq,module=module,priority=priority,status=status,requirementIds=[]) for key,seq,module,priority,status in (
            ('PLAN-A',1,'文件','P2','已完成'),('PLAN-B',2,'空间','P0','进行中'),('PLAN-C',5,'文件','P0','进行中'),('PLAN-D',8,'空间','P1','已完成'))]
        return spec

    def test_priority_sort_and_module_grouping(self):
        spec=self.spec()
        self.assertEqual(['PLAN-B','PLAN-D','PLAN-C','PLAN-A'],self.run_js('return scheduleRows().map(p=>p.id);',spec))
        self.assertEqual(['PLAN-B','PLAN-C','PLAN-D','PLAN-A'],self.run_js('scheduleState.group=false;return scheduleRows().map(p=>p.id);',spec))
        self.assertEqual(['PLAN-A','PLAN-B','PLAN-C','PLAN-D'],self.run_js('scheduleState.group=false;scheduleState.sort="sequence";return scheduleRows().map(p=>p.id);',spec))

    def test_filter_keeps_actual_sequence_and_colors(self):
        spec=self.spec()
        result=self.run_js('scheduleState.status="进行中";return scheduleRows().map(p=>p.sequence);',spec)
        self.assertEqual([2,5],result)
        html=self.run_js('return renderPlan();',spec)
        self.assertIn('<th>序号</th>',html)
        self.assertIn('data-plan-id="PLAN-A"',html)

    def test_legacy_numbers_do_not_collide_with_explicit_numbers(self):
        spec=self.spec();spec['plans'][0].pop('sequence');spec['plans'][1]['sequence']=1
        result=self.run_js('scheduleState.group=false;scheduleState.sort="sequence";return scheduleRows().map(p=>p.sequence);',spec)
        self.assertEqual([1,2,5,8],result)

    def test_sequence_validation(self):
        for value in (None,True,0,-1,1.5,'1',9007199254740992):
            with self.subTest(value=value):
                spec=copy.deepcopy(EXAMPLE);spec['plans'][0]['sequence']=value
                self.assertTrue(any(i.code=='PLAN_SEQUENCE_INVALID' for i in validate_spec(spec)))
        spec=copy.deepcopy(EXAMPLE)
        spec['plans'][0]['sequence']=1;spec['plans'][1]['sequence']=1
        self.assertTrue(any(i.code=='PLAN_SEQUENCE_DUPLICATE' for i in validate_spec(spec)))
