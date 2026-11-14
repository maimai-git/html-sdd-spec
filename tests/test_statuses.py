import copy
import unittest
from html_sdd.checker import validate_spec
from tests.test_definitions import EXAMPLE
from tests import test_catalog_filters as catalog

class StatusTest(unittest.TestCase):
    run_js=catalog.CatalogFiltersTest.run_js

    def test_registry_is_the_source_for_validators_and_colors(self):
        from html_sdd.statuses import registry, status_info
        from html_sdd.checker import PLAN_STATUSES
        data=registry()
        self.assertEqual(set(data['sections']['plans']),set(PLAN_STATUSES))
        for section,labels in data['sections'].items():
            for label in labels:
                self.assertEqual(data['statuses'][label],status_info(label,section)['tone'])
        self.assertEqual('neutral',status_info('代码已实现，迁移待执行','apis')['tone'])
        self.assertEqual('待核实',status_info('代码已实现，迁移待执行','apis')['label'])

    def test_strict_rejects_wrong_section_status_and_bad_notes(self):
        for section in ('requirements','apis','tables','architecture','configs','evidence','questions'):
            spec=copy.deepcopy(EXAMPLE);spec['metadata']['statusPolicy']='strict'
            spec[section][0]['status']='随便写一个状态'
            self.assertTrue(any(i.code=='STATUS_INVALID' and i.path.startswith(section+'[0]') for i in validate_spec(spec)))
        spec=copy.deepcopy(EXAMPLE);spec['apis'][0]['statusNote']=[]
        self.assertTrue(any(i.code=='STATUS_NOTE_INVALID' for i in validate_spec(spec)))

    def test_migration_keeps_text_does_not_guess_and_is_idempotent(self):
        from html_sdd.statuses import normalize_statuses
        spec=copy.deepcopy(EXAMPLE);spec['apis'][0]['status']='代码已实现，迁移待执行'
        result=normalize_statuses(spec)
        self.assertEqual('待核实',result['apis'][0]['status'])
        self.assertIn(spec['apis'][0]['status'],result['apis'][0]['statusNote'])
        self.assertEqual(result,normalize_statuses(result))
        self.assertFalse([i for i in validate_spec(result) if i.level=='error'])

    def test_browser_uses_exact_mapping_and_preserves_legacy_note(self):
        result=self.run_js('return {label:statusInfo("已实现但迁移待执行","apis").label,tone:statusClass("已实现但迁移待执行","apis"),badge:status("已完成","plans")};')
        self.assertEqual('待核实',result['label']);self.assertEqual('neutral',result['tone'])
        self.assertIn('done',result['badge'])

    def test_generated_artifacts_and_packaging_cover_registry(self):
        import subprocess,sys
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        result=subprocess.run([sys.executable,'tools/sync_statuses.py','--check'],cwd=root,capture_output=True,text=True)
        self.assertEqual(0,result.returncode,result.stdout)
        from html_sdd.context import build_context
        spec=copy.deepcopy(EXAMPLE);spec['apis'][0]['statusNote']='迁移尚未执行'
        self.assertEqual('迁移尚未执行',build_context(spec,spec['apis'][0]['id'])['record']['statusNote'])
        for filename in ('setup.py','pyproject.toml'):
            self.assertIn('assets/*.json',(root/filename).read_text())

    def test_acceptance_has_an_independent_subset(self):
        from html_sdd.statuses import normalize_statuses,status_info
        spec=normalize_statuses(EXAMPLE);spec['requirements'][0]['acceptance'][0]['status']='已通过'
        self.assertFalse([i for i in validate_spec(spec) if i.level=='error'])
        spec['requirements'][0]['acceptance'][0]['status']='已部署'
        self.assertTrue(any(i.code=='STATUS_INVALID' and '.acceptance[0].status' in i.path for i in validate_spec(spec)))
        self.assertEqual('neutral',status_info('已部署','acceptance')['tone'])

    def test_header_color_does_not_change_with_active_tab(self):
        spec=copy.deepcopy(EXAMPLE);spec['metadata']['status']='开发中'
        result=self.run_js('return ["requirements","apis","tables"].map(mode=>{state.mode=mode;renderSnapshot();return [nodes.documentState.textContent,nodes.documentState.className]});',spec)
        self.assertTrue(all(row==['开发中','document-state status progress'] for row in result))

    def test_render_always_rejects_invalid_development_status(self):
        from html_sdd.renderer import render_spec
        from pathlib import Path
        spec=copy.deepcopy(EXAMPLE);spec['metadata']['statusPolicy']='legacy';spec['apis'][0]['developmentStatus']='完成一半'
        with self.assertRaises(ValueError):render_spec(spec,Path(__file__).resolve().parents[1]/'html_sdd/assets/console.html')

    def test_legacy_tooltips_keep_both_old_text_and_note(self):
        spec=copy.deepcopy(EXAMPLE);spec['metadata'].update(status='旧阶段说明',statusNote='额外说明',statusPolicy='legacy')
        result=self.run_js('renderSnapshot();return {title:nodes.documentState.title,badge:status("旧文字","apis","备注")};',spec)
        self.assertIn('旧阶段说明',result['title']);self.assertIn('额外说明',result['title'])
        self.assertIn('旧文字',result['badge']);self.assertIn('备注',result['badge'])
