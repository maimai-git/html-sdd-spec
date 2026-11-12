"""Small-output wrapper for an existing Playwright CLI browser session."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


def browser_check(script: Path, session: str, log: Path | None = None,
                  max_output: int = 1600) -> tuple[int, str]:
    if max_output < 256:
        return 1, 'FAIL --max-output 至少为 256'
    script = script.resolve()
    if not script.is_file():
        return 1, 'FAIL 找不到浏览器检查脚本'
    executable = shutil.which('playwright-cli')
    if not executable:
        return 1, 'FAIL 未安装 playwright-cli；本命令不会自动安装依赖'
    log = log or Path('output/playwright') / (script.stem + '.log')
    timed_out = False
    try:
        process = subprocess.run(
            [executable, '-s=' + session, 'run-code', '--filename=' + str(script)],
            capture_output=True, text=True, timeout=120,
        )
        output = process.stdout + process.stderr
        result_area = output.split('### Ran Playwright code', 1)[0]
        failed = process.returncode != 0 or re.search(r'^### Error\s*$', result_area, re.MULTILINE) is not None
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        def partial(value):
            return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else (value or '')
        output = partial(exc.stdout) + partial(exc.stderr)
        output += '\n浏览器检查超过 120 秒；请检查原会话状态后重试。'
        failed = True
    except OSError as exc:
        return 1, ('FAIL 无法运行浏览器检查：' + str(exc))[:max_output - 1]
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(output, encoding='utf-8')
    except OSError as exc:
        return 1, ('FAIL 无法保存检查日志：' + str(exc))[:max_output - 1]
    heading = ('FAIL' if failed else 'PASS') + ' 浏览器检查'
    if timed_out:
        heading += '（超过 120 秒）'
    detail = ''
    if failed:
        detail = output.split('### Ran Playwright code', 1)[0].split('### Error', 1)[-1].strip()
    elif '### Result' in output:
        raw = output.split('### Result', 1)[1].split('###', 1)[0].strip()
        try:
            result = json.loads(raw)
            if isinstance(result, dict):
                detail = json.dumps({key:result[key] for key in ('checks', 'offline') if key in result}, ensure_ascii=False)
        except ValueError:
            detail = '已运行；返回内容见日志'
    footer = '\n完整本地日志：' + str(log)
    # Keep the result header even when an unusually long log path consumes the budget.
    footer = footer[:max_output // 2]
    room = max_output - 1 - len(heading) - len(footer) - 1
    return int(failed), heading + '\n' + detail[:room] + footer
