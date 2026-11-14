"""Read-only inventory of the recorded work and acceptance gaps."""
from __future__ import annotations

from typing import Any, Iterable

from .checker import check_ready_gate, section_is_not_applicable
from .statuses import question_is_open, registry, status_info


def _records(value: Any) -> Iterable[dict]:
    if isinstance(value, list):
        yield from (item for item in value if isinstance(item, dict))


def _brief(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = " ".join(value.split())
    return text if len(text) <= 240 else text[:239] + "…"


def _entry(record: dict, section: str) -> dict:
    record_id = _brief(record.get("id"))
    title = next(
        (text for key in ("title", "main", "name", "question", "text")
         if (text := _brief(record.get(key)))),
        record_id,
    )
    status = status_info(record.get("status"), section)
    result = {"id": record_id, "title": title, "status": status["label"], "section": section}
    notes = dict.fromkeys(filter(None, (
        _brief(record.get("note")), _brief(record.get("progress")),
        _brief(record.get("statusNote")), _brief(status["note"]),
    )))
    if notes:
        result["note"] = _brief("；".join(notes))
    return result


def build_summary(spec: dict) -> dict:
    metadata = spec.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    readiness = metadata.get("readiness")
    readiness = readiness if isinstance(readiness, dict) else {}
    result = {
        "title": _brief(metadata.get("title")),
        "codingReady": readiness.get("codingReady") if isinstance(readiness.get("codingReady"), bool) else None,
        "pendingPlans": [], "cancelledPlans": [], "acceptanceGaps": [],
        "deliveryGaps": [], "blockingItems": [], "openQuestions": [],
        "unverified": [], "missingCoverage": [],
    }
    if result["codingReady"]:
        issues = check_ready_gate(spec)
        if issues:
            result["codingReady"] = False
            result["readinessIssues"] = [issue.as_dict() for issue in issues]
    agents = {
        _brief(agent.get("id")): _brief(agent.get("name"))
        for agent in _records(spec.get("agents"))
    }
    for section in ("requirements", "plans"):
        if not list(_records(spec.get(section))):
            result["missingCoverage"].append(section)
    for section in ("apis", "tables", "configs", "architecture"):
        if not list(_records(spec.get(section))) and not section_is_not_applicable(metadata, section):
            result["missingCoverage"].append(section)

    for plan in _records(spec.get("plans")):
        entry = _entry(plan, "plans")
        executor = _brief(plan.get("executor"))
        entry.update(
            module=_brief(plan.get("module")) or "未分组",
            executor=agents.get(executor) or executor or "待安排",
            blocker=_brief(plan.get("blocker")),
        )
        if entry["status"] == "已取消":
            result["cancelledPlans"].append(entry)
        elif entry["status"] != "已完成":
            result["pendingPlans"].append(entry)
    result["pendingPlans"].sort(key=lambda item: (item["module"], item["id"]))

    verified_evidence = {
        item["id"] for item in _records(spec.get("evidence"))
        if isinstance(item.get("id"), str) and item.get("status") == "已验证"
    }
    for requirement in _records(spec.get("requirements")):
        if requirement.get("status") == "已取消":
            continue
        acceptance = list(_records(requirement.get("acceptance")))
        if not acceptance:
            result["missingCoverage"].append(f'{_brief(requirement.get("id"))}.acceptance')
        for item in acceptance:
            entry = _entry(item, "acceptance")
            entry["requirementId"] = _brief(requirement.get("id"))
            if entry["status"] == "不适用":
                continue
            if entry["status"] == "已通过":
                evidence = item.get("evidence")
                if isinstance(evidence, str) and evidence in verified_evidence:
                    continue
                entry["status"] = "待核实"
                entry["reason"] = "验收标记为已通过，缺少已验证的关联证据"
            category = "unverified" if entry["status"] == "待核实" else "acceptanceGaps"
            result[category].append(entry)

    unfinished_development = set(registry()["sections"]["developmentStatus"]) - {"已完成"}
    for section in ("apis", "tables", "configs"):
        for record in _records(spec.get(section)):
            entry = _entry(record, section)
            if entry["status"] in ("不适用", "已取消"):
                continue
            development = record.get("developmentStatus")
            if isinstance(development, str) and development in unfinished_development:
                entry["developmentStatus"] = development
            if entry["status"] == "已验证" and "developmentStatus" not in entry:
                continue
            category = "unverified" if entry["status"] == "待核实" else "deliveryGaps"
            result[category].append(entry)

    for question in _records(spec.get("questions")):
        if question_is_open(question):
            entry = _entry(question, "questions")
            decision = question.get("requiresUserDecision")
            if isinstance(decision, bool):
                entry["requiresUserDecision"] = decision
            result["openQuestions"].append(entry)

    blockers = readiness.get("blockingItems")
    if isinstance(blockers, list):
        listed = {entry["id"] for entry in result["pendingPlans"] + result["openQuestions"]
                  if entry["status"] == "阻塞" or entry.get("blocker")}
        result["blockingItems"] = list(dict.fromkeys(
            text for value in blockers if (text := _brief(value)) and text not in listed
        ))
    return result


def build_page_summary(spec: dict) -> dict:
    """Keep CLI-selected IDs and derived exceptions in the HTML summary."""
    summary = build_summary(spec)
    records = {record.get("id"): record
               for section in ("plans", "apis", "tables", "configs", "questions")
               for record in _records(spec.get(section)) if isinstance(record.get("id"), str)}
    for requirement in _records(spec.get("requirements")):
        for item in _records(requirement.get("acceptance")):
            if isinstance(item.get("id"), str):
                records[item["id"]] = item
    for key in ("pendingPlans", "acceptanceGaps", "deliveryGaps", "openQuestions", "unverified"):
        entries = []
        for item in summary[key]:
            record = records.get(item["id"])
            if record is None:
                entries.append(item)
                continue
            extra = {}
            if item["status"] != record.get("status"):
                extra["status"] = item["status"]
            if "reason" in item:
                extra["reason"] = item["reason"]
            entries.append({"id": item["id"], **extra} if extra else item["id"])
        summary[key] = entries
    del summary["title"], summary["cancelledPlans"]
    return summary


def format_summary(summary: dict) -> str:
    coding_status = {True: "已就绪", False: "待就绪", None: "未记录"}
    lines = [summary["title"] or "需求盘点", f'编码条件 · {coding_status[summary["codingReady"]]}']
    for issue in summary.get("readinessIssues", []):
        lines.append(f'- {issue["path"]}：{issue["message"]}')
    for key, label in (
        ("pendingPlans", "未完成任务"), ("acceptanceGaps", "验收缺口"),
        ("deliveryGaps", "部署与验证待办"), ("blockingItems", "其他阻塞"),
        ("openQuestions", "未关闭问题"), ("unverified", "待核实"),
        ("missingCoverage", "待补充范围"), ("cancelledPlans", "已取消任务"),
    ):
        entries = summary[key]
        lines.append(f"\n{label}（{len(entries)}）")
        for entry in entries:
            if isinstance(entry, str):
                lines.append(f"- {entry}")
                continue
            decision = entry.get("requiresUserDecision")
            question_kind = (
                "等用户决定" if decision is True else "AI 继续核实" if decision is False else "待分类"
            ) if key == "openQuestions" else ""
            detail = " · ".join(filter(None, (question_kind,
                entry.get("module"), entry.get("requirementId"), entry["id"],
                entry["title"] if entry["title"] != entry["id"] else None, entry["status"],
                entry.get("developmentStatus"), entry.get("executor"), entry.get("blocker"),
                entry.get("reason"), entry.get("note"),
            )))
            lines.append(f"- {detail}")
    return "\n".join(lines)
