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
CHANGELOG_DIRECTORY_NAME = "变更记录"


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
    (target / CHANGELOG_DIRECTORY_NAME).mkdir(parents=True, exist_ok=True)
    spec = skeleton_spec()
    (target / SOURCE_FILE_NAME).write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (target / GUIDE_FILE_NAME).write_text(
        "# HTML SDD 方案\n\n"
        f"编辑 `{SOURCE_FILE_NAME}`，然后运行：\n\n"
        f"html-sdd check '{SOURCE_FILE_NAME}'\n"
        f"html-sdd render '{SOURCE_FILE_NAME}' --output '{HTML_FILE_NAME}'\n\n"
        "一个开发过程使用一个目录；多个子需求登记在同一份事实源中。这份 JSON 是唯一事实源，HTML 由它生成，不要直接修改 HTML。变更记录/、证据索引/、证据/ 用于本地归档，已由 .gitignore 排除。JSON 保留当前结论、简短验收结果和可访问的引用。\n",
        encoding="utf-8",
    )
    (target / HTML_FILE_NAME).write_text(render_spec(spec, template_path), encoding="utf-8")
    (target / CHANGELOG_DIRECTORY_NAME / "说明.md").write_text(
        "# 本地变更记录\n\n"
        "每条只记一件影响交付的事。先写结论，再用短句说明原因、影响和验证。"
        "需要追溯时附记录编号或提交。\n\n"
        "## YYYY-MM-DD｜一句话说明改动\n\n"
        "- 原因：为什么要改。\n"
        "- 影响：涉及哪些需求、接口或任务。\n"
        "- 验证：在哪个环境核对了什么，结果如何。缺证据时写待核实。\n",
        encoding="utf-8",
    )
    (target / ".gitignore").write_text(
        "# 本地变更记录与证据归档\n/变更记录/\n/证据索引/\n/证据/\n", encoding="utf-8"
    )
