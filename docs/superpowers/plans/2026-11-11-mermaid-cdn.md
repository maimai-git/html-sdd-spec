# Mermaid CDN 图表渲染实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标：** 让 HTML SDD 的架构图/时序图在存在 `diagramSource` 时按需通过 Mermaid CDN 渲染，并在无网络或渲染失败时保留可读的图源回退。

**架构：** JSON 继续作为唯一事实源，新增可选 `diagramEngine` 字段。HTML 模板只在打开架构图且需要 Mermaid 时动态加载固定版本的 CDN 脚本；内联 SVG 和文字回退保持兼容。打包模板与源码模板保持完全一致。

**技术栈：** Python 3.9+ 标准库、JSON Schema、内嵌数据 HTML、Mermaid 11 CDN、浏览器原生 JavaScript。

## 全局约束

- 不引入 Python 或 Node 运行时依赖。
- Mermaid CDN 只负责可选的浏览器展示，不能成为 JSON 校验和 CLI 渲染的硬依赖。
- 没有网络、CSP 拒绝或 Mermaid 语法错误时，页面仍可打开并展示图源/文字回退。
- 页面不执行外部业务请求，不读取或写入敏感信息。
- `templates/console.html` 与 `html_sdd/assets/console.html` 必须一致。

## 评审重点

- Mermaid 脚本只在需要时加载，避免每个 HTML 页面都无条件请求 CDN。
- 同一页面切换多个架构条目时不会重复初始化或报错。
- 图源含 HTML 特殊字符时不能破坏模板脚本。
- CDN 失败时不能让架构详情为空。
- 旧的 `diagramSvg` / `fallback` 数据仍能通过校验并正常显示。

### 任务 1：增加 Mermaid 数据契约和失败测试

**文件：** `schema/html-sdd.schema.json`、`html_sdd/checker.py`、`tests/test_mermaid.py`、`examples/asset-library/sdd.json`

- [x] 写测试：`diagramEngine=mermaid` 必须有 `diagramSource`，未知引擎需要报错，现有 SVG/回退记录保持兼容。
- [x] 运行定向测试，确认在实现前失败。
- [x] 增加 `diagramEngine` 枚举和语义校验。
- [x] 为已有 Mermaid 图源示例补充 `diagramEngine`。
- [x] 运行定向测试和示例 `check`。

### 任务 2：接入按需 CDN 渲染和回退

**文件：** `templates/console.html`、`html_sdd/assets/console.html`、`tests/test_renderer.py`

- [x] 写模板测试：存在 CDN 地址、按需加载函数、渲染失败回退节点。
- [x] 运行定向测试，确认在实现前失败。
- [x] 实现固定版本 Mermaid CDN 的懒加载、单例 Promise 和安全初始化。
- [x] `renderArchitecture` 对 `diagramSource` 输出 Mermaid 节点，失败时保留源码并显示提示。
- [x] 保持 `diagramSvg` 优先和 `fallback` 兼容。
- [x] 运行 Node 语法检查。

### 任务 3：更新说明、生成示例并做浏览器验证

**文件：** `README.md`、`README.en.md`、`SPEC.md`、`docs/superpowers/specs/2026-11-10-html-sdd-v01-design.md`、`docs/superpowers/plans/2026-11-10-html-sdd-v01.md`、`skills/html-sdd-spec/SKILL.md`、`examples/asset-library/index.html`

- [x] 说明 Mermaid CDN 是可选增强，断网时读取图源。
- [x] 重新渲染资产库示例。
- [x] 运行全量 Python 测试、`check`、`render` 和 Node 语法检查。
- [x] 启动临时静态服务器，用真实浏览器检查时序图 SVG、源码回退和控制台日志。
- [x] 复核 Git diff、敏感信息和模板一致性。
