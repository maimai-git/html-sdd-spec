import copy
import re
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

    def test_compact_table_has_seven_columns_and_task_expansion(self):
        html=self.run_js('return renderPlan();',self.spec())
        self.assertEqual(['序号','优先级','模块 / 任务','关联需求','执行人','状态','进展与备注'],re.findall(r'<th>(.*?)</th>',html))
        self.assertIn('colspan="7"',html)
        self.assertRegex(html,r'<button[^>]*data-plan-toggle')
        self.assertNotIn('>详情</button>',html)

    def test_notes_merge_deduplicate_and_prioritize_blocker(self):
        result=self.run_js('return [planNote({blocker:"等待数据库",progress:"接口完成",note:"接口完成"}),planNote({}),planNote({status:"阻塞"})];',self.spec())
        self.assertEqual(['阻塞说明：等待数据库；接口完成','—','阻塞原因待补充'],result)

    def test_main_row_omits_dates_and_details_preserve_original_values(self):
        spec=self.spec();p=spec['plans'][0]
        p.update(main='历史文件查询',sub='核对分页',start='2026-11-01',end='2026-11-05',progress='查询已完成',note='需要验收',blocker='等待数据库',ownerPaths=['src/files'],deps='PLAN-B')
        html=self.run_js('return renderPlan();',spec)
        row=re.search(r'<tr data-plan-id="PLAN-A".*?</tr>',html).group()
        self.assertNotIn('2026-11-05',row);self.assertNotIn('2026-11-01',row)
        details=re.search(r'<tr id="plan-details-1".*?</tr>',html).group()
        self.assertIn('<b>进展与备注</b><span>阻塞说明：等待数据库；查询已完成；需要验收</span>',details)
        for label in ('最新进度','备注','状态说明','阻塞原因'):
            self.assertNotIn(f'<b>{label}</b>',details)
        for text in ['核对分页','2026-11-01','2026-11-05','查询已完成','需要验收','等待数据库','src/files','PLAN-B']:
            self.assertIn(text,html)
        self.assertNotIn('<b>批次</b>',html);self.assertNotIn('<b>预估</b>',html)
        p.pop('end')
        row=re.search(r'<tr data-plan-id="PLAN-A".*?</tr>',self.run_js('return renderPlan();',spec)).group()
        self.assertNotIn('待定',row);self.assertNotIn('2026-11-01',row)

    def test_requirement_names_and_notes_are_escaped(self):
        spec=self.spec();spec['requirements']=[dict(id='REQ-A',title='上传 <文件>')]
        spec['plans'][0].update(requirementIds=['REQ-A','REQ-MISSING'],main='查询 <文件>',note='<script>alert(1)</script>')
        html=self.run_js('return renderPlan();',spec)
        self.assertIn('data-plan-requirement="REQ-A"',html)
        self.assertIn('上传 &lt;文件&gt;',html)
        self.assertIn('REQ-MISSING',html)
        self.assertIn('&lt;script&gt;',html);self.assertNotIn('<script>',html)
        self.assertNotIn('&amp;lt;',html)

    def test_non_date_end_stays_in_details(self):
        for value in ['验收后再确认','2026-02-30','',None]:
            spec=self.spec();spec['plans'][0]['end']=value
            html=self.run_js('return renderPlan();',spec)
            row=re.search(r'<tr data-plan-id="PLAN-A".*?</tr>',html).group()
            self.assertNotIn('<td>待定</td>',row)
            if value:self.assertIn(value,html)
