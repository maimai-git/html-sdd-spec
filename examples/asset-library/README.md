# 资产库正式示例

这是一份基于 `sample-asset-service` 当前代码快照的完整示例，覆盖：

- 文件资产库：历史文件、目录、上传、收藏、企业发布、批量下载、回收站；
- 空间与同步：个人资源、企业副本、身份和成员校验；
- 风格与模特：CRUD、参考图、官方收藏、生成任务；
- Chat 引用：`asset_refs`、独立校验和真实 turns 接入门禁。

页面会明确区分“代码已实现”“迁移待执行”“待接入”和“未核实”，不把设计方案冒充成全链路完成。

~~~bash
cd /path/to/html-sdd-spec
python3 -m html_sdd check examples/asset-library/sdd.json
python3 -m html_sdd render examples/asset-library/sdd.json --output examples/asset-library/index.html
~~~

当前示例的 `metadata.readiness.codingReady` 为 `false`，阻塞项包括数据库迁移、企业成员校验、生成平台回执、Chat turns 接入和官方模特目录。

示例中的数据库迁移只作为方案文本展示，没有执行任何 DDL；应用启动也不会自动创建这些表。
