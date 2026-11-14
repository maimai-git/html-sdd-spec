from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .renderer import render_spec


STANDARD_SDD_ROOT = Path("html-sdd-spec")
STANDARD_SDD_DIRECTORY = STANDARD_SDD_ROOT / "新开发需求"
SOURCE_FILE_NAME = "方案事实源.json"
HTML_FILE_NAME = "方案对齐.html"
GUIDE_FILE_NAME = "使用说明.md"


def skeleton_spec() -> dict[str, Any]:
    spec = {
        "specVersion": "0.1",
        "metadata": {
            "id": "PROJECT-SDD-001",
            "title": "[项目名] / [需求名]",
            "summary": "[用一句话说明要达成什么]",
            "status": "方案待对齐",
            "statusPolicy": "strict",
            "updatedAt": "[YYYY-MM-DDTHH:mm:ss+08:00]",
            "language": "zh-CN",
            "readiness": {
                "overall": "待验收",
                "codingReady": False,
                "blockingItems": [],
                "exitCriteria": [
                    "需求、接口、数据表、配置和验证证据可追踪",
                    "未决问题已经明确负责人和下一步",
                ],
            },
            "sectionCoverage": {
                "requirements": {"status": "pending", "reason": "待录入需求"},
                "plans": {"status": "pending", "reason": "待拆分排期"},
                "apis": {"status": "pending", "reason": "待核对接口影响"},
                "tables": {"status": "pending", "reason": "待核对数据影响"},
                "architecture": {"status": "pending", "reason": "待梳理技术方案"},
                "configs": {"status": "pending", "reason": "待核对上线配置"},
            },
        },
        "baseline": {
            "repository": "[仓库路径]",
            "branch": "[分支]",
            "commit": "[完整 commit]",
            "inspectedAt": "[YYYY-MM-DD HH:mm:ss]",
            "timezone": "Asia/Shanghai",
            "worktreeState": "unknown",
            "relevantDirtyPaths": [],
        },
        "agents": [
            {"id": "AGENT-OWNER", "name": "负责人 Agent", "role": "和用户对齐、分派和汇报"},
            {"id": "AGENT-REVIEWER", "name": "审核人 Agent", "role": "拆需求、查现状、审核方案"},
            {"id": "AGENT-EXECUTOR", "name": "执行人 Agent", "role": "写代码、测试和验证"},
        ],
        "requirements": [],
        "plans": [],
        "apis": [],
        "tables": [],
        "architecture": [],
        "configs": [],
        "evidence": [],
        "questions": [],
    }

    for agent in spec["agents"]:
        agent["status"]="待开始"
    return spec


def init_project(target: Path, template_path: Path) -> None:
    if target.exists() and any(target.iterdir()):
        raise FileExistsError(f"目标目录非空：{target}")
    target.mkdir(parents=True, exist_ok=True)
    spec = skeleton_spec()
    (target / SOURCE_FILE_NAME).write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (target / GUIDE_FILE_NAME).write_text(
        "# HTML SDD 方案\n\n"
        f"编辑 `{SOURCE_FILE_NAME}`，然后运行：\n\n"
        f"html-sdd check '{SOURCE_FILE_NAME}'\n"
        f"html-sdd render '{SOURCE_FILE_NAME}' --output '{HTML_FILE_NAME}'\n\n"
        "一个开发过程使用一个目录，多个子需求登记在同一份事实源中。先更新 JSON，再生成 HTML。\n\n"
        "## 记录变更和验收\n\n"
        "记录规则默认生效，有实际内容时创建文件。两个归档目录均由 Git 忽略。\n\n"
        "- 影响交付的变更写入 `变更记录/变更记录.md`。每条写日期、结论、原因、影响、关联编号和验证。\n"
        "- 验收时在事实源的 `evidence[]` 记录证据编号、环境和结果。需要保留原件时，按 "
        "`证据/<证据编号>-<环境>-<验证事项>.<扩展名>` 保存脱敏文件。同一编号有多份材料时，建同名目录集中保存。\n"
        "- 单凭编号无法快速找齐多个批次的文件时，建立 `证据/索引.md`，"
        "登记编号、环境、批次和需求目录内的相对路径。\n\n"
        "过程草案、调研笔记和实施计划按需放在 `临时文件/`，由 Git 忽略。已确认的方案和交付合同保存在共享文档。\n\n"
        "上线时按需创建 上线配置清单/ 和 上线SQL清单/。配置只记录本期新增且上线必需的条目，填写核实过的本地实际非敏感值。发布人按目标环境填写工单值。配置和 SQL 各放一份。配置固定写入 上线配置清单/上线配置.properties，每项键值上一行用 # 写中文配置名。SQL 固定写入 上线SQL清单/上线SQL.sql。文件顶部注释写清提交位置、适用条件、操作顺序和验收。\n",
        encoding="utf-8",
    )
    (target / HTML_FILE_NAME).write_text(render_spec(spec, template_path), encoding="utf-8")
    (target / ".gitignore").write_text(
        "# 本地记录与过程文档\n/变更记录/\n/证据/\n/临时文件/\n"
        "# 兼容旧版归档路径\n/证据索引/\n", encoding="utf-8"
    )
