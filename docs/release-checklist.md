# 发布检查清单

用于把 HTML SDD Spec 分享给同事或发布到公开仓库。

## 发布前

- [ ] `git status` 只包含预期文件，没有本机路径、Token、密码、Cookie、私钥或真实连接串。
- [ ] `python3 -m unittest discover -s tests -v` 全部通过。
- [ ] `python3 -m html_sdd check examples/asset-library/sdd.json` 通过。
- [ ] `python3 -m html_sdd render examples/asset-library/sdd.json --output /tmp/html-sdd-index.html` 成功。
- [ ] 使用 Node 检查生成 HTML 中的 JavaScript 语法。
- [ ] 在浏览器中切换需求、排期、接口、数据表、架构设计和上线需要配置，确认每个分类一次只展示当前条目。
- [ ] 检查 `metadata.readiness`，确认示例把“已实现、DDL 待执行、外部接入待完成、未核实”分开表达。
- [ ] 更新 `CHANGELOG.md` 和版本号。
- [ ] 确认 `pyproject.toml`、`setup.py` 和 `CHANGELOG.md` 的版本一致。
- [ ] 在临时虚拟环境安装 wheel，并运行 `html-sdd --version`、`check` 和 `render` 冒烟验证。

## 发布步骤

1. 提交一个单独的版本提交，例如 `chore: 发布 HTML SDD Spec v0.1.0`。
2. 创建版本标签，例如 `v0.1.0`。
3. 在目标 GitHub 仓库创建 Release，并附上变更摘要。
4. 让同事从干净目录执行 README 的三分钟运行步骤。

## 发布后

- [ ] 新用户可以直接从仓库根目录运行 `python3 -m html_sdd ...`。
- [ ] 已安装用户可以运行 `html-sdd check`、`render`、`diff` 和 `init`。
- [ ] Issue 模板、贡献指南、行为准则和安全说明链接可访问。
