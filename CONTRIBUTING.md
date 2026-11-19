# 贡献指南

## 提交一个规范改动

1. 修改规范、Schema、CLI、模板或示例。
2. 运行完整测试：

~~~bash
python3 -m unittest discover -s tests -v
python3 -m html_sdd check examples/asset-library/sdd.json
python3 -m html_sdd render examples/asset-library/sdd.json --output /tmp/html-sdd-index.html
~~~

3. 在浏览器直接打开生成的本地 Vue 页面，确认 Vue CDN 加载成功及交互正常。
4. Pull Request 说明改变了哪些字段、兼容性影响和验证结果。

Vue 浏览器回归使用 Playwright Python：安装当前包和 `playwright==1.59.0`，运行 `python -m playwright install chromium` 后执行 `python tests/browser/console.py` 和 `python tests/browser/summary.py`。这两个用例分别验证页面交互和 CLI 摘要一致性。

## 设计原则

- HTML 是阅读界面，方案事实源 JSON 是事实源；新项目默认放在项目根目录的 `html-sdd-spec/<开发需求目录>/`。
- 稳定 ID 不随文案变化。
- 当前现状和提案分开表达。
- 没有证据就写待核实。
- 不提交真实 Token、密码、Cookie、私钥或连接串。
- 不把项目专属规则写进通用模板。
