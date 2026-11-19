import copy
import json
import shutil
import unittest
from pathlib import Path

from html_sdd.checker import validate_spec
from html_sdd.context import build_context

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = json.loads((ROOT / "examples/asset-library/sdd.json").read_text())


@unittest.skipUnless(shutil.which("node"), "模板运行回归需要 Node；页面端到端由 Playwright 验证")
class AlignmentSummaryTest(unittest.TestCase):
    def run_js(self,spec,expression):
        from tests import test_catalog_filters as catalog
        return catalog.CatalogFiltersTest.run_js(self,expression,spec)

    def test_project_status_is_not_inferred_from_coding_readiness(self):
        from html_sdd.statuses import registry
        neutral=registry()['tones']['neutral']
        spec=copy.deepcopy(EXAMPLE)
        for ready in (False,True):
            spec['metadata']['readiness']['codingReady']=ready
            self.assertEqual(neutral,self.run_js(spec,'return tone(spec.metadata.status);'))
        spec['metadata'].pop('status')
        spec['metadata']['statusPolicy']='legacy'
        self.assertEqual(neutral,self.run_js(spec,'return tone(spec.metadata.status);'))

    def test_blank_status_and_missing_blockers_are_not_reported_as_ready(self):
        spec=copy.deepcopy(EXAMPLE)
        spec['metadata']['status']='  '
        spec['metadata']['statusPolicy']='legacy'
        spec['metadata']['readiness']={'codingReady':True,'overall':'状态待记录'}
        result=self.run_js(spec,'return {ready:summary.codingReady,issues:summary.readinessIssues};')
        self.assertIs(False,result['ready'])
        self.assertTrue(result['issues'])

    def test_global_conditions_are_not_added_to_subrequirements(self):
        output=self.run_js(EXAMPLE,'return {global:readiness,detail:spec.requirements[0]};')
        self.assertIn('blockingItems',output['global'])
        self.assertNotIn('readiness',output['detail'])

    def test_incomplete_or_failed_status_is_not_green(self):
        from html_sdd.statuses import registry
        texts=['已实现，迁移待执行','代码完成，尚未验收','已完成，校验失败','已完成','待开始','待复核','未验证','部分完成']
        result=self.run_js(EXAMPLE,'return '+json.dumps(texts,ensure_ascii=False)+'.map(tone);')
        tones=registry()['tones']
        self.assertEqual([tones[kind] for kind in ['neutral','neutral','neutral','done','neutral','review','neutral','wait']],result)

    def test_questions_are_classified_without_guessing_and_closed_ones_are_hidden(self):
        spec=copy.deepcopy(EXAMPLE)
        spec['questions']=[
            {'id':'Q-USER','question':'保留多久？','status':'待确认','requiresUserDecision':True},
            {'id':'Q-TECH','question':'验证接口','status':'待确认','requiresUserDecision':False},
            {'id':'Q-OLD','question':'旧问题','status':'待确认'},
            {'id':'Q-DONE','question':'已决定','status':'已确认','requiresUserDecision':True},
            {'id':'Q-CANCEL','question':'已撤销','state':'cancelled','status':'待确认','requiresUserDecision':True},
        ]
        result=self.run_js(spec,'return summary.openQuestions.map(item=>[item.id,questionKind(item)]);')
        self.assertEqual([['Q-USER','等用户决定'],['Q-TECH','AI 继续核实'],['Q-OLD','待分类']],result)

    def test_all_pending_decisions_preserve_text_for_vue_escaping(self):
        spec=copy.deepcopy(EXAMPLE)
        spec['questions']=[{'id':f'Q-{i}','question':f'决定{i}<script>alert(1)</script>','status':'待确认','requiresUserDecision':True} for i in range(5)]
        result=self.run_js(spec,'return summary.openQuestions.map(item=>item.title);')
        self.assertEqual([question['question'] for question in spec['questions']],result)


class QuestionContractTest(unittest.TestCase):
    def test_optional_decision_flag_accepts_only_booleans(self):
        for value in (None, "false", 1, [], {}):
            with self.subTest(value=value):
                spec = copy.deepcopy(EXAMPLE)
                spec["questions"][0]["requiresUserDecision"] = value
                self.assertTrue(any(i.code == "QUESTION_DECISION_FLAG" for i in validate_spec(spec)))
        for value in (True, False):
            spec = copy.deepcopy(EXAMPLE)
            spec["questions"][0]["requiresUserDecision"] = value
            self.assertFalse(any(i.code == "QUESTION_DECISION_FLAG" for i in validate_spec(spec)))

    def test_context_closes_resolved_questions_before_checking_stale_blockers(self):
        for field, values in (("state", ("cancelled", "verified", "accepted")),
                              ("status", ("已确认", "已解决", "已关闭", "已完成", "已取消"))):
            for value in values:
                with self.subTest(field=field, value=value):
                    spec = copy.deepcopy(EXAMPLE)
                    question = spec["questions"][0]
                    question[field] = value
                    question["blocker"] = "遗留阻塞说明"
                    result = build_context(spec, "REQ-001", role="executor")
                    self.assertNotIn(question["id"], [q["id"] for q in result["blockers"]])

    def test_executor_blockers_retain_explicit_decision_flag(self):
        for value in (True, False):
            spec = copy.deepcopy(EXAMPLE)
            spec["questions"][0]["requiresUserDecision"] = value
            result = build_context(spec, "REQ-001", role="executor")
            question = next(q for q in result["blockers"] if q["id"] == "Q-001")
            self.assertIs(value, question.get("requiresUserDecision"))

    def test_schema_declares_optional_boolean_without_requiring_old_data_to_change(self):
        schema = json.loads((ROOT / "schema/html-sdd.schema.json").read_text())
        contract = schema["$defs"]["question"]["allOf"][1]
        self.assertEqual("boolean", contract["properties"]["requiresUserDecision"]["type"])
        self.assertNotIn("requiresUserDecision", contract["required"])


if __name__ == "__main__":
    unittest.main()
