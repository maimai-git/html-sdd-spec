"""用 Node 执行 Vue 页面的计算逻辑；真实 DOM 和响应式行为由浏览器用例验证。"""
import json
import re
import subprocess
from pathlib import Path

from html_sdd.renderer import render_spec

TEMPLATE = Path(__file__).resolve().parents[1] / "html_sdd/assets/console-vue.html"


def run_vue(expression, spec):
    html = render_spec(spec, TEMPLATE)
    payloads = dict(re.findall(r'<script id="([^"]+)" type="application/json">(.*?)</script>', html, re.S))
    script = re.findall(r'<script>(.*?)</script>', html, re.S)[-1]
    prelude = """
const payloads=PAYLOADS;
let view;
const Vue={
 ref:value=>({value}),reactive:value=>value,computed:get=>({get value(){return get()}}),
 watch(){},nextTick:async()=>{},createApp:options=>({mount(){view=options.setup()}}),
};
const window={Vue,location:{protocol:'file:'},addEventListener:(_,callback)=>callback()};
const document={getElementById:id=>({textContent:payloads[id]||'',innerHTML:''})};
""".replace("PAYLOADS", json.dumps(payloads, ensure_ascii=False))
    result = subprocess.run(
        ["node", "-"], input=prelude + script + "\nconsole.log(JSON.stringify((()=>{with(view){" + expression + "}})()));",
        capture_output=True, text=True,
    )
    if result.returncode:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)
