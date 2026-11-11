# HTML SDD Spec

HTML SDD Spec is a lightweight format for aligning product requirements, the current codebase, technical design, Agent work plans, and verification evidence in one document.

`方案事实源.json` is the machine-readable source of truth. The generated HTML is an offline reader for people and AI agents.

## Quick start

Requires Python 3.9+.
The offline page uses the browser's native gzip decompressor; use a current Chrome, Edge, Firefox, or Safari.

```bash
python3 -m pip install -e .
html-sdd check examples/asset-library/sdd.json
html-sdd render examples/asset-library/sdd.json \
  --output examples/asset-library/index.html
```

Open `examples/asset-library/index.html` in a browser. The page has six sections: requirements, schedule, APIs, data tables, architecture, and release configuration.

Without installing the CLI, or when using an older local setup, run `python3 -m html_sdd ...` from the repository root.

## Minimal invocation

You do not need to write separate prompts for the owner, reviewer, and executor. One sentence is normally enough:

```text
Use HTML SDD to implement this requirement: add batch shipment to order fulfillment, using the current codebase to define APIs, tables, schedule, and release configuration.
```

The Agent reads project rules and source code, builds the current baseline, and generates or updates `html-sdd-spec/<requirement-directory>/方案事实源.json` and the offline HTML. It asks only about business rules, permissions, migrations, external integrations, or execution authority that would change the plan. Routine technical details are derived from code evidence and marked as assumptions when needed.
The generated HTML embeds compressed data to remain a single offline file. Agents should read the human-readable `方案事实源.json` by relevant IDs instead of loading the full HTML into context.

For a project without an SDD, say:

```text
Use HTML SDD to map this project first. Do not change code.
```

The first pass delivers the current snapshot, APIs, tables, architecture, configuration, evidence, and open questions. Unconfirmed items keep `codingReady=false`.

HTML SDD can stay with the work through the full lifecycle: requirements, baseline, design, review and schedule, coding, testing, release preparation, deployment, and post-release acceptance. Each phase records status, owner, update time, next step, and evidence. Source code, full logs, secrets, and raw deployment-system data stay in their original systems; SDD keeps references, summaries, and results.

## Choosing the Agent mode

The default is automatic. Use one Agent for a single-module change, no API/data impact, documentation, or a small fix. Use multiple Agents when work crosses modules, changes both APIs and data, has independent tasks that can run in parallel, or needs an independent review. One SDD has one owner; each plan has one primary reviewer and one primary executor, with optional `reviewerIds` and `executorIds` collaborators. You can override this with “single Agent” or “parallel Agents”. If sub-agents are unavailable, the owner performs the three roles sequentially.

## What the document aligns

- Current repository snapshot and evidence;
- Requirements, acceptance criteria, and stable IDs;
- Module schedule, priority, dependencies, and Agent ownership;
- API change type, parameters, request/response examples, and current route evidence;
- Data table purpose, migration status, and DDL text;
- Architecture notes, diagrams, sequence diagrams, and source text;
- Environment variables, Apollo values, and manual release steps;
- Open questions and a `metadata.readiness` coding gate.

A route or class existing in the codebase is evidence of current code only. Top-level sections remain present in `方案事实源.json`, but their arrays may be empty when a section is not relevant or has not been split yet. The HTML shows “not applicable” or “to be completed” instead of inventing records. `codingReady` remains false while applicable migrations, external providers, Chat integration, or real acceptance evidence are missing.

Use `metadata.sectionCoverage` to explain empty sections, and `impact.apis` or `impact.tables` to state that a requirement explicitly does not affect APIs or data tables.

## When the plan changes

HTML SDD is a living source of alignment. If architecture, APIs, tables, configuration, acceptance criteria, or schedule changes, update the JSON source first, then run `check`, `render`, and `diff`. Pause affected tasks for a reviewer re-check; set `codingReady=false` when the previous plan no longer holds. Do not hand-edit generated HTML. Optionally keep the reason and before/after values in `metadata.changeLog`.
`html-sdd diff --json` includes changes across metadata, baseline, agents, requirements, plans, APIs, tables, architecture, configuration, evidence, and questions, with before/after values for machine review.

## Artifact layout

The project root is `html-sdd-spec/`, with one complete development process per child directory. A large product requirement such as asset-library references can keep model, style, and reference sub-requirements/modules in the same JSON and HTML. Use Chinese names for requirement directories and documents, with English such as `HTML-SDD` allowed in the name:

```text
html-sdd-spec/资产库引用/
├── 方案事实源.json
├── 方案对齐.html
├── 使用说明.md
├── 变更记录/说明.md
└── 证据索引/说明.md
```

Tool source, tests, and executable scripts may keep English names; the root directory `html-sdd-spec/` is the agreed English exception. If an existing project already has an SDD elsewhere, record it and migrate only after checking for duplicate sources.

## Agent roles

- **Owner** aligns goals with the user, maintains the SDD, assigns work, and reports progress.
- **Reviewer** inspects the codebase, decomposes requirements, and reviews API/data/design readiness.
- **Executor** takes only aligned tasks, implements backend changes, verifies them, and records evidence.

## CLI

```bash
html-sdd init
html-sdd check ./html-sdd-spec/资产库引用/方案事实源.json
html-sdd check ./html-sdd-spec/资产库引用/方案事实源.json --json
html-sdd render ./html-sdd-spec/资产库引用/方案事实源.json \
  --output ./html-sdd-spec/资产库引用/方案对齐.html
html-sdd diff before.json after.json
html-sdd diff before.json after.json --json
```

## Example

The [asset-library example](examples/asset-library/index.html) is based on a real sample-asset-service snapshot. It includes file assets, personal/enterprise spaces, styles, models, generation tasks, Chat `asset_refs`, 42 APIs, 17 tables, 9 schedule tasks, and 6 architecture entries.

The example deliberately separates implemented code, manual migrations, pending integrations, and unverified runtime evidence. It never executes DDL.

## Safety and scope

HTML SDD is an offline planning and alignment artifact. It does not connect to production databases, execute DDL, apply deployment configuration, or store tokens, passwords, cookies, private keys, or connection strings.

See [CONTRIBUTING.md](CONTRIBUTING.md), [CHANGELOG.md](CHANGELOG.md), [SECURITY.md](SECURITY.md), the [release checklist](docs/release-checklist.md), and the [MIT License](LICENSE).
