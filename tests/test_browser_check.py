import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from html_sdd.browser_check import browser_check

class BrowserCheckTest(unittest.TestCase):
    def run_check(self, output, code=0):
        with tempfile.TemporaryDirectory() as tmp:
            script=Path(tmp)/'check.js'; script.write_text('async page => true')
            log=Path(tmp)/'run.log'
            with patch('html_sdd.browser_check.shutil.which', return_value='/bin/playwright-cli'), patch('html_sdd.browser_check.subprocess.run', return_value=subprocess.CompletedProcess([],code,output,'')):
                result, summary=browser_check(script, 'demo', log=log, max_output=300)
            self.assertEqual(output,log.read_text())
            self.assertLessEqual(len(summary)+1,300)
            return result,summary

    def test_success_does_not_echo_script(self):
        code,out=self.run_check('### Result\n{"checks":18}\n### Ran Playwright code\n'+'VERY_LONG_SCRIPT'*500)
        self.assertEqual(0,code); self.assertIn('18',out); self.assertNotIn('VERY_LONG_SCRIPT',out)

    def test_cli_error_is_failure_even_when_exit_zero(self):
        code,out=self.run_check('### Error\nAssertionError: 筛选失败\n### Ran Playwright code\nsecret_script')
        self.assertEqual(1,code); self.assertIn('筛选失败',out); self.assertNotIn('secret_script',out)

    def test_nonzero_exit_and_large_errors_are_bounded(self):
        code,out=self.run_check('bad '*5000,1)
        self.assertEqual(1,code); self.assertIn('FAIL',out)

    def test_error_marker_in_echoed_script_is_not_failure(self):
        code, out = self.run_check('### Result\n{"checks":1}\n### Ran Playwright code\nconsole.log("### Error")')
        self.assertEqual(0, code)

    def test_timeout_is_reported_and_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp)/'check.js'; script.write_text('async page => true')
            log = Path(tmp)/'timeout.log'
            with patch('html_sdd.browser_check.shutil.which', return_value='/bin/playwright-cli'), patch('html_sdd.browser_check.subprocess.run', side_effect=subprocess.TimeoutExpired([], 120)):
                code, output = browser_check(script, 'demo', log=log)
            self.assertEqual(1, code)
            self.assertIn('120', output)
            self.assertIn('120', log.read_text())

    def test_multiline_error_header_in_echoed_code_is_not_failure(self):
        code, out = self.run_check('### Result\n{"checks":1}\n### Ran Playwright code\nconst str = `\n### Error\n`;')
        self.assertEqual(0, code)

    def test_timeout_preserves_partial_stdout_and_stderr(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp)/'check.js'; script.write_text('async page => true')
            log = Path(tmp)/'timeout.log'
            error = subprocess.TimeoutExpired([], 120, output=b'last browser step', stderr=b'network pending')
            with patch('html_sdd.browser_check.shutil.which', return_value='/bin/playwright-cli'), patch('html_sdd.browser_check.subprocess.run', side_effect=error):
                code, output = browser_check(script, 'demo', log=log)
            self.assertEqual(1, code)
            self.assertIn('last browser step', log.read_text())
            self.assertIn('network pending', log.read_text())
