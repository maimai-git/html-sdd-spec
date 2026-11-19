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
        self.assertEqual(['PLAN-B','PLAN-D','PLAN-C','PLAN-A'],self.run_js('return schedule.value.flatMap(([,rows])=>rows).map(p=>p.id);',spec))
        self.assertEqual(['PLAN-B','PLAN-C','PLAN-D','PLAN-A'],self.run_js('groupPlans.value=false;return schedule.value.flatMap(([,rows])=>rows).map(p=>p.id);',spec))
        self.assertEqual(['PLAN-A','PLAN-B','PLAN-C','PLAN-D'],self.run_js('groupPlans.value=false;sort.value="sequence";return schedule.value.flatMap(([,rows])=>rows).map(p=>p.id);',spec))

    def test_filter_keeps_actual_sequence(self):
        spec=self.spec()
        result=self.run_js('planStatus.value="进行中";return planRows.value.map(p=>p.sequence);',spec)
        self.assertEqual([2,5],result)

    def test_legacy_numbers_do_not_collide_with_explicit_numbers(self):
        spec=self.spec();spec['plans'][0].pop('sequence');spec['plans'][1]['sequence']=1
        result=self.run_js('groupPlans.value=false;sort.value="sequence";return planRows.value.map(p=>p.sequence);',spec)
        self.assertEqual([1,2,5,8],result)

    def test_sequence_validation(self):
        for value in (None,True,0,-1,1.5,'1',9007199254740992):
            with self.subTest(value=value):
                spec=copy.deepcopy(EXAMPLE);spec['plans'][0]['sequence']=value
                self.assertTrue(any(i.code=='PLAN_SEQUENCE_INVALID' for i in validate_spec(spec)))
        spec=copy.deepcopy(EXAMPLE)
        spec['plans'][0]['sequence']=1;spec['plans'][1]['sequence']=1
        self.assertTrue(any(i.code=='PLAN_SEQUENCE_DUPLICATE' for i in validate_spec(spec)))

    def test_compact_table_has_seven_columns(self):
        self.assertEqual(['序号','优先级','模块 / 任务','关联需求','执行人','状态','进展与备注'],self.run_js('return planColumns;',self.spec()))

    def test_notes_merge_deduplicate_and_prioritize_blocker(self):
        result=self.run_js('return [taskNote({blocker:"等待数据库",progress:"接口完成",note:"接口完成"}),taskNote({}),taskNote({status:"阻塞"})];',self.spec())
        self.assertEqual(['阻塞说明：等待数据库；接口完成','—','阻塞原因待补充'],result)

    def test_details_preserve_dates_and_original_values(self):
        spec=self.spec();p=spec['plans'][0]
        p.update(main='历史文件查询',sub='核对分页',start='2026-11-01',end='2026-11-05',progress='查询已完成',note='需要验收',blocker='等待数据库',ownerPaths=['src/files'],deps='PLAN-B')
        details=dict(self.run_js('return planDetails(planRows.value.find(x=>x.id==="PLAN-A"));',spec))
        self.assertEqual('阻塞说明：等待数据库；查询已完成；需要验收',details['进展与备注'])
        for key in ('progress','note','blocker','statusNote'):
            self.assertNotIn(key,details)
        for key in ('sub','start','end','ownerPaths','deps'):
            self.assertEqual(p[key],details[key])
        p.pop('end')
        self.assertNotIn('end',dict(self.run_js('return planDetails(planRows.value.find(x=>x.id==="PLAN-A"));',spec)))

    def test_requirement_names_and_notes_preserve_original_text_for_vue(self):
        spec=self.spec();spec['requirements']=[dict(id='REQ-A',title='上传 <文件>')]
        spec['plans'][0].update(requirementIds=['REQ-A','REQ-MISSING'],note='<script>alert(1)</script>')
        result=self.run_js('return {names:["REQ-A","REQ-MISSING"].map(nameFor),note:taskNote(planRows.value.find(x=>x.id==="PLAN-A"))};',spec)
        self.assertEqual(['上传 <文件>','REQ-MISSING'],result['names'])
        self.assertEqual('<script>alert(1)</script>',result['note'])

    def test_non_date_end_stays_in_details(self):
        for value in ['验收后再确认','2026-02-30','',None]:
            spec=self.spec();spec['plans'][0]['end']=value
            details=dict(self.run_js('return planDetails(planRows.value.find(x=>x.id==="PLAN-A"));',spec))
            self.assertEqual(value or None,details.get('end'))
