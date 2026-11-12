import copy
import json
import unittest
from html_sdd.context import build_context, ContextError
from html_sdd.cli import main
from tests import test_context as existing
from contextlib import redirect_stdout
from io import StringIO


class ContextBudgetTest(unittest.TestCase):
    def test_default_is_small_and_pages_do_not_overlap(self):
        spec=existing.EXAMPLE
        first=build_context(spec,'REQ-001','reviewer')
        self.assertLessEqual(first['includedCount'],8)
        second=build_context(spec,'REQ-001','reviewer',offset=first['pagination']['nextOffset'])
        self.assertFalse({r['id'] for r in first['relatedRecords']} & {r['id'] for r in second['relatedRecords']})
        self.assertEqual(first['totalCount'],first['includedCount']+first['omittedCount'])

    def test_all_pages_cover_related_ids_without_dropping_blockers(self):
        spec=existing.EXAMPLE;offset=0;seen=[]
        while True:
            page=build_context(spec,'REQ-001','reviewer',limit=3,offset=offset)
            seen.extend(r['id'] for r in page['relatedRecords'])
            self.assertTrue(page['blockers'])
            offset=page['pagination']['nextOffset']
            if offset is None:break
        self.assertEqual(page['totalCount'],len(seen))
        self.assertEqual(len(seen),len(set(seen)))

    def test_budget_is_enforced_for_actual_json_and_text_output(self):
        for as_json in (True,False):
            args=['context',str(existing.ROOT/'examples/asset-library/sdd.json'),'REQ-001','--role','reviewer','--limit','48','--max-chars','6500']
            if as_json:args.append('--json')
            stream=StringIO()
            with redirect_stdout(stream): code=main(args)
            self.assertEqual(0,code,stream.getvalue())
            self.assertLessEqual(len(stream.getvalue()),6500)
            if as_json:
                result=json.loads(stream.getvalue())
                self.assertTrue(result['blockers'])
                self.assertEqual(result['includedCount'],result['pagination']['nextOffset'])
                self.assertGreater(result['omittedCount'],0)

    def test_invalid_pagination_options_raise_readable_errors(self):
        for kwargs in ({'limit':0},{'limit':49},{'offset':-1}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ContextError):
                build_context(existing.EXAMPLE,'REQ-001',**kwargs)

    def test_budget_boundary_and_auxiliary_lists_are_preserved(self):
        from html_sdd.context import serialize_context
        context = build_context(existing.EXAMPLE, 'REQ-001', 'reviewer', limit=48, offset=3)
        output = serialize_context(context, as_json=True, max_chars=6500)
        result = json.loads(output)
        self.assertEqual(3 + result['includedCount'], result['pagination']['nextOffset'])
        self.assertEqual(context['totalCount'] - 3 - result['includedCount'], result['pagination']['remainingCount'])
        for key in ('record', 'dependencies', 'blockers', 'evidence'):
            self.assertEqual(context[key], result[key])
        self.assertEqual(output, serialize_context(result, as_json=True, max_chars=len(output)+1))
        # The trailing CLI newline also consumes budget.
        shorter = serialize_context(result, as_json=True, max_chars=len(output))
        self.assertLess(len(json.loads(shorter)['relatedRecords']), result['includedCount'])

    def test_offset_past_end_and_invalid_types(self):
        page = build_context(existing.EXAMPLE, 'REQ-001', offset=9999)
        self.assertEqual([], page['relatedRecords'])
        self.assertIsNone(page['pagination']['nextOffset'])
        self.assertEqual(0, page['pagination']['remainingCount'])
        for kwargs in ({'limit': True}, {'offset': False}, {'offset': 1.5}):
            with self.assertRaises(ContextError):
                build_context(existing.EXAMPLE, 'REQ-001', **kwargs)

    def test_full_target_cannot_be_silently_cut_to_fit_budget(self):
        from html_sdd.context import serialize_context
        spec=copy.deepcopy(existing.EXAMPLE)
        spec['requirements'][0]['scope']='完整任务合同'*5000
        context=build_context(spec,'REQ-001',full=True)
        before=copy.deepcopy(context)
        with self.assertRaisesRegex(ContextError,'预算'):
            serialize_context(context,full=True,as_json=True,max_chars=3000)
        self.assertEqual(before,context)


if __name__=='__main__':unittest.main()
