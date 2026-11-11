# Changelog

所有重要变更都会记录在这里。

## [Unreleased]

### Changed

- 空分类允许保留为空，并可用 `metadata.sectionCoverage` 说明“本次未涉及”或“待补充”；
- `codingReady` 支持通过 `impact.apis`、`impact.tables` 声明明确不涉及接口或数据表；
- 离线页面在空分类时显示原因，不再只显示无上下文的空白状态；
- Agent 模式默认自动选择，先统一基线和契约，再决定是否并行拆分。
- 排期状态由 Agent 按证据维护，支持阻塞、待复核和待验收状态，禁止无证据标记完成。
- 明确多 Agent 的串行对齐、并行执行、统一验收协议和交接字段。
- 明确负责人唯一、主审核人/主执行人唯一，并支持 reviewerIds、executorIds 配置协作 Agent。
- 约定 HTML SDD 根目录为 `html-sdd-spec/`，一个需求一个子目录，生成文件使用中文命名。
- 约定负责人对用户使用 300 字以内的五行简明汇报格式。
- 增加架构字段契约和子需求到排期、验收证据的关联完整性检查。
- 增加并行执行的 ownerPaths 形状、缺失和重叠检查，并收紧编码 READY 门禁。
- 生成 HTML 时压缩内嵌事实源，保留单文件离线打开，并指导 Agent 按 ID 读取 JSON 事实源。
- 排期增加固定状态枚举、统一状态颜色和备注列；非法状态会被 `check` 阻断。
- `diff` 覆盖完整事实源分类，并支持包含 before/after 的 JSON 输出。

## [0.1.0] - 2026-11-10

### Added

- `sdd.json` 规范、JSON Schema、稳定 ID 和关联关系检查；
- 离线 HTML 控制台，包含需求、排期、接口、数据表、架构和上线配置；
- `init`、`check`、`render`、`diff` 本地 CLI；
- 负责人、审核人、执行人 Agent 提示词；
- 基于 sample-asset-service 当前快照的资产库正式示例；
- 编码门禁 `metadata.readiness`，区分当前代码、迁移、提案和真实验收证据；
- 标准库测试和 GitHub Actions 校验流程。

### Boundaries

- HTML 页面离线运行，不连接实时仓库或数据库；
- DDL、环境变量和 Apollo 配置只展示，不自动执行；
- 资产库示例中的数据库迁移、Chat turns 接入、生成平台回执和官方目录仍按页面阻塞项记录。
