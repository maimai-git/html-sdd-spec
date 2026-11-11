# HTML SDD Spec

HTML SDD Spec 是一套把产品需求、当前代码、技术方案、Agent 排期和验证证据放进同一份文档的轻量规范。

它把 `方案事实源.json` 作为机器可读的事实源，把单文件 HTML 作为人和 AI 共同阅读、讨论和复核的界面。

## 适合解决什么问题

- 产品目标、技术方案和现有代码状态分散在不同文档里；
- 接口、数据表、DDL、配置和排期无法回到同一个需求；
- 负责人、审核人和执行人对“已经实现”和“准备实现”的理解不一致；
- 需求变更后，很难快速看出接口、表和任务发生了什么变化。

## 三分钟运行

环境要求：Python 3.9 或更高版本，不依赖第三方 Python 运行时。
页面使用浏览器原生 gzip 解压；架构图/时序图有网络时按需加载 Mermaid CDN，无网络时保留图源和文字回退。请使用当前版本的 Chrome、Edge、Firefox 或 Safari。

完整安装和同事接入流程见 [安装与使用](docs/安装使用.md)。

~~~bash
git clone git@github.com:maimai-git/html-sdd-spec.git
cd html-sdd-spec

# 可选：安装本地 CLI
python3 -m pip install -e .

# 检查并渲染真实资产库示例
html-sdd check examples/asset-library/sdd.json
html-sdd render examples/asset-library/sdd.json \
  --output examples/asset-library/index.html

# macOS 打开页面；其他系统直接用浏览器打开该文件
open examples/asset-library/index.html
~~~

不安装 CLI 或使用较旧的 Python 环境时，可以在仓库根目录直接运行 `python3 -m html_sdd ...`：

~~~bash
python3 -m html_sdd check examples/asset-library/sdd.json
python3 -m html_sdd render examples/asset-library/sdd.json \
  --output examples/asset-library/index.html
~~~

## 最短使用方式

使用 HTML SDD 不需要先写三份 Agent 提示词。通常一句话就够：

~~~text
用 HTML SDD 实现这个需求：给订单履约增加批量发货能力，结合当前项目代码梳理接口、表、排期和上线配置。
~~~

Agent 会自动读取项目规则和代码，先建立当前版本基线，再生成或更新 `html-sdd-spec/<开发需求目录>/方案事实源.json` 和离线 HTML。只有业务规则、权限、数据迁移或执行授权会改变方案的问题才会反问；普通技术细节由 Agent 根据代码证据处理并标记假设。负责人、审核人、执行人是内部协作角色，用户无需分别编写提示词。

如果项目还没有 SDD，可以直接说：

~~~text
用 HTML SDD 先梳理这个项目，不改代码。
~~~

第一轮会交付现状、接口、数据表、架构、配置、证据和待确认问题；没有确认的内容会保持 `codingReady=false`。

## Agent 数量怎么选

默认自动判断，不需要每次询问。单模块、无接口/数据变化或小范围文档任务使用单 Agent；跨模块、同时涉及接口和数据、存在可并行任务或需要独立审核时使用多 Agent。你也可以直接说“单 Agent”或“多 Agent 并行”。多 Agent 不可用时，负责人会在一个会话内按负责人、审核人、执行人顺序完成。

## 页面包含什么

顶部分类固定为：

1. **需求**：目标、范围、验收标准和关联记录；
2. **排期**：主模块、子模块、优先级、需求关联、Agent 分工、依赖和进度；
3. **接口**：接口分组、变更类型、当前代码现状、请求参数、返回参数、请求实例和响应实例；
4. **数据表**：新增/变更/复用状态、表作用、当前状态、结构差异和 DDL；
5. **架构设计**：技术方案说明卡、架构图、时序图和 Mermaid 图源；
6. **上线需要配置**：环境变量、Apollo、手工 DDL 和其他非敏感配置文本。

页面一次只展示一个选中的接口、表或架构条目；排期使用整页表格，方便扫读和比较。
AI 后续协作时优先从 `方案事实源.json` 按需求 ID 提取当前任务所需内容，不要每轮重新读取完整 HTML；完整页面保留给人浏览。
生成的 HTML 会把数据压缩后内嵌，保持单文件打开；Mermaid 只在进入需要图源的架构条目时请求 CDN，加载失败时直接展示图源。AI 应读取可读的 `方案事实源.json`，不要把 HTML 当事实源加载进上下文。
页面默认先显示摘要：版本细节、编码门禁、接口实例、DDL、验收证据和关联记录按需展开；排期使用宽屏横向表格，主表显示优先级、模块/主任务、关联需求、执行人、计划时间、状态、最新进度、备注、阻塞和详情，完整任务说明在单行详情中查看。

## 事实源和编码门禁

`方案事实源.json` 保留以下分类字段；每个分类的数组可以为空：

~~~text
metadata / baseline / agents / requirements / plans
apis / tables / architecture / configs / evidence / questions
~~~

空分类会在页面中显示“本次未涉及”或“待补充”。只有本次需求实际影响的接口、数据表、架构和上线配置才需要建立记录，不为了填满页面虚构内容。

可以用 `metadata.sectionCoverage` 记录空分类的原因，用 `impact.apis`、`impact.tables` 等字段说明某个需求明确不涉及接口或数据表。

正式项目建议在 `metadata.readiness` 中维护：

- `overall`：当前总体状态；
- `codingReady`：是否可以把任务交给执行人 Agent；
- `blockingItems`：尚未关闭的阻塞项；
- `exitCriteria`：达到编码 READY 必须满足的条件。

只看到路由或类存在，不能直接标记为全链路完成。数据库未执行、外部平台未接入、真实 Chat/生成链路未验收时，`codingReady` 应保持 `false`。

## 方案发生变化怎么办

HTML SDD 是持续更新的事实源。架构、接口、数据表、配置、验收或排期发生变化时，先改方案事实源，再运行 `check`、`render` 和 `diff`，最后继续编码。重大变化要暂停受影响任务，由审核人重新评估；如果原方案不再成立，负责人把 `codingReady` 改回 `false`。生成后的 HTML 不直接手改，可选用 `metadata.changeLog` 记录原因和前后差异。

架构技术方案统一使用 `conclusion`、`current`、`steps`、`impact`、`risks` 字段；架构图或时序图使用 `diagramType` 加 `diagramEngine`、`diagramSvg`、`diagramSource` 或 `fallback`。`diagramEngine` 可选 `mermaid`、`inline-svg`、`text`；使用 `mermaid` 时必须提供 `diagramSource`。`check` 会检查这些字段和子需求到排期的关联。

## SDD 文件目录约定

项目根目录固定使用 `html-sdd-spec/`，下面一个完整开发过程一个目录。比如产品经理提出“资产库引用”这个大需求，就在同一个目录和 HTML 里登记“模特、风格、引用”等子需求/子模块，以及它们各自的接口、数据表和排期。需求目录和文档文件名使用中文，可夹杂 `HTML-SDD` 等英文；同一开发过程只保留一份 JSON 事实源和一份生成 HTML，不复制多份版本：

~~~text
html-sdd-spec/
└── 资产库引用/
    ├── 方案事实源.json       唯一可编辑的机器事实源
    ├── 方案对齐.html         由 JSON 生成的人和 AI 阅读页面
    ├── 使用说明.md           本地检查和渲染命令
    ├── 变更记录/
    │   └── 说明.md           重大方案变化的记录入口
    └── 证据索引/
        └── 说明.md           代码、测试、迁移和上线验收证据索引
~~~

`requirements[]` 记录这次开发过程下的子需求，使用 `REQ-*` ID 与排期、接口、数据表、架构和验收关联；只有完全独立的开发过程才新建目录。工具源码、测试和执行脚本（例如 `html_sdd/`、`tests/`、`scripts/`）可以继续使用英文命名；根目录 `html-sdd-spec/` 是约定的英文例外。已有项目若已有其他 SDD 路径，先登记现状，确认无冲突后再迁移，不要直接生成第二份事实源。

## 三类 Agent 的协作方式

- **负责人 Agent**：和用户对齐目标、维护 SDD、拆分排期、安排 Agent、汇报进度；
- **审核人 Agent**：查代码和 migration，拆需求，审核接口、表、架构、配置和编码门禁；
- **执行人 Agent**：只领取已经对齐的任务，写代码、测试、验证并回填证据。

建议流程：

~~~text
需求输入 -> 审核人查现状/拆解 -> 负责人确认 -> 编码 READY
-> 执行人开发/验证 -> 回填证据 -> 负责人汇报
~~~

排期由 Agent 自动维护：负责人登记计划和对外进度，审核人更新审核/阻塞状态，执行人回填开发进度和验证证据。排期状态只能使用固定枚举：待拆分、待确认、编码 READY、待开始、进行中、待接入、待执行、待复核、待验收、阻塞、已完成、已取消；详细原因写在“备注”列。没有新证据时保留原状态并写“无变化”，不会凭感觉标记完成。

## 多 Agent 怎么协作

推荐顺序是：负责人建立基线 → 主审核人冻结接口/数据契约 → 主执行人和协作执行人按模块并行 → 审核人统一复核 → 负责人汇总上线。一份 SDD 只设一个负责人；每个 PLAN 设一个主审核人和一个主执行人，也可以用 `reviewerIds`、`executorIds` 增加协作角色。每个执行任务要写清 `ownerPaths`、依赖、完成条件和交接信息，避免多个 Agent 同时改同一文件或数据库对象。对外只由负责人汇报，执行人的进度作为内部输入。

负责人对用户的汇报保持简短，默认 300 字以内，固定写阶段目标、进行中、下阶段规划目标、已完成任务/需求、存在问题五行；技术细节留在 HTML SDD 中，除非用户要求展开。多个执行人并行时要填写不重叠的 `ownerPaths`；进入编码 READY 前，子需求必须有排期，验收项必须有证据。

## 覆盖整个研发周期

HTML SDD 可以从需求一直维护到上线验收：

```text
需求 → 现状 → 方案 → 评审排期 → 编码 READY
→ 开发 → 测试 → 发布准备 → 上线 → 上线验收
```

每个阶段登记当前状态、责任人、更新时间、下一步和证据。代码全文、完整日志、密钥和部署系统原始数据留在原系统，HTML SDD 保存摘要、引用和结果。

## CLI 命令

~~~bash
# 创建一个开发需求骨架，默认生成 ./html-sdd-spec/新开发需求/
html-sdd init

# 检查必填字段、稳定 ID、关联关系、敏感信息和 READY 门禁
html-sdd check ./html-sdd-spec/资产库引用/方案事实源.json

# 输出适合脚本处理的 JSON 检查结果
html-sdd check ./html-sdd-spec/资产库引用/方案事实源.json --json

# 从 JSON 生成单文件 HTML；Mermaid 图表按需使用 CDN，失败时保留图源
html-sdd render ./html-sdd-spec/资产库引用/方案事实源.json \
  --output ./html-sdd-spec/资产库引用/方案对齐.html

# 也可以指定一个自定义的需求目录
html-sdd init ./html-sdd-spec/订单履约

# 比较两版需求事实源
html-sdd diff ./before.json ./after.json

# 输出给脚本或 Agent 读取的变更 JSON（包含 before/after）
html-sdd diff ./before.json ./after.json --json
~~~

## 真实示例

[资产库正式示例](examples/asset-library/index.html) 基于 `sample-asset-service` 当前代码快照，包含：

- 文件资产库；
- 个人/企业空间同步；
- 风格和模特；
- 模特生成任务；
- Chat `asset_refs`；
- 42 个接口、17 张表、9 个排期任务和 6 个架构条目。

示例明确区分代码已实现、迁移待执行、待接入和未核实，不会把方案文本当成运行证据。示例中的 DDL 只展示，不会自动执行。

### 控制台效果

页面采用顶部分类、左侧分组和右侧单项详情布局；排期切换后使用宽屏表格，状态、备注和详情可直接扫读。

![HTML SDD 控制台示例](docs/images/html-sdd-console.png)

![HTML SDD 排期示例](docs/images/html-sdd-schedule.png)

架构设计中的 Mermaid 时序图会在浏览器中按需渲染；下面是资产库示例的实际效果。

![Mermaid 时序图示例](docs/images/html-sdd-mermaid.png)

## 仓库目录

~~~text
html_sdd/                 本地 CLI、检查器、渲染器和差异比较
schema/                   JSON Schema
templates/                离线 HTML 控制台模板
skills/html-sdd-spec/     可直接复制给 Agent 使用的 Skill 入口
prompts/                  owner/reviewer/executor Agent 提示词
examples/                 可运行的真实项目示例
tests/                    标准库测试
docs/                     设计说明和实施计划
~~~

如果要给其他 Agent 使用，直接把 `skills/html-sdd-spec/SKILL.md` 作为 Skill 说明加载；完整仓库中的 CLI、模板、Schema 和示例可继续按上面的命令运行。

## 开发和验证

~~~bash
python3 -m unittest discover -s tests -v
python3 -m html_sdd check examples/asset-library/sdd.json
python3 -m html_sdd render examples/asset-library/sdd.json \
  --output /tmp/html-sdd-index.html
~~~

提交前还应检查生成页面的 JavaScript 语法，并在真实浏览器中切换需求、排期、接口、数据表和架构分类。

## 安全边界

- HTML SDD 不连接实时仓库或数据库；
- 不自动执行 DDL、环境变量或 Apollo 配置；
- 不提交 Token、密码、Cookie、私钥、连接串或真实密钥；
- 配置和示例使用占位符；
- 当前代码、migration 文件和数据库已执行证据必须分别描述。

## 贡献和版本

规范字段、Schema、CLI、模板和示例都是公开协作内容。请先阅读 [贡献指南](CONTRIBUTING.md)，提交前运行完整检查。

- 变更记录：[CHANGELOG.md](CHANGELOG.md)
- English guide：[README.en.md](README.en.md)
- 许可证：[MIT License](LICENSE)
- 安全问题：[SECURITY.md](SECURITY.md)
- 发布检查：[docs/release-checklist.md](docs/release-checklist.md)
