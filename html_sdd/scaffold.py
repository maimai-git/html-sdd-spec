from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .renderer import render_spec


STANDARD_SDD_ROOT = Path("html-sdd-spec")
STANDARD_SDD_DIRECTORY = STANDARD_SDD_ROOT / "新开发需求"
SOURCE_FILE_NAME = "方案事实源.json"
HTML_FILE_NAME = "方案对齐.html"


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
    (target / HTML_FILE_NAME).write_text(render_spec(spec, template_path), encoding="utf-8")
    (target / ".gitignore").write_text(
        "# 本地记录与过程文档\n/变更记录/\n/证据/\n/临时文件/\n"
        "# 兼容旧版归档路径\n/证据索引/\n", encoding="utf-8"
    )
