from __future__ import annotations

import copy
import json

from typing import Any, Iterable, Optional

from .references import expand_api
from .statuses import question_is_open


SECTION_ORDER = (
    "agents",
    "requirements",
    "plans",
    "apis",
    "existingInterfaces",
    "tables",
    "architecture",
    "configs",
    "evidence",
    "questions",
)

ROLE_FOCUS = {
    "owner": ("requirements", "plans", "questions", "evidence"),
    "reviewer": ("requirements", "plans", "apis", "existingInterfaces", "tables", "architecture", "configs", "questions", "evidence"),
    "executor": ("requirements", "plans", "apis", "existingInterfaces", "tables", "architecture", "configs", "evidence"),
}

MAX_RELATED_RECORDS = 48
MAX_DEPENDENCIES = 12
MAX_BLOCKERS = 8
MAX_EVIDENCE = 8
SUMMARY_LIMIT = 240


class ContextError(ValueError):
    """Raised when a requested context cannot be built from the SDD."""


def _record_index(spec: dict[str, Any]) -> dict[str, tuple[str, dict[str, Any]]]:
    records: dict[str, tuple[str, dict[str, Any]]] = {}
    for section in SECTION_ORDER:
        values = spec.get(section, [])
        if not isinstance(values, list):
            continue
        for record in values:
            if not isinstance(record, dict) or not isinstance(record.get("id"), str):
                continue
            records.setdefault(record["id"], (section, record))
    return records


def _values(record: dict[str, Any], key: str) -> list[str]:
    values = record.get(key)
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, str)]


def _display_title(record_id: str, record: dict[str, Any]) -> str:
    for field in ("title", "name", "main", "label", "question", "module", "group"):
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            return value
    return record_id


def _summary(record: dict[str, Any]) -> str:
    for field in ("summary", "scope", "question", "progress", "note"):
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            if len(value) > SUMMARY_LIMIT:
                return value[: SUMMARY_LIMIT - 1].rstrip() + "…"
            return value
    return ""


def _compact_record(
    record_id: str,
    section: str,
    record: dict[str, Any],
    relation: Optional[list[str]] = None,
) -> dict[str, Any]:
    claim = record.get("claim")
    compact_claim = None
    if isinstance(claim, dict):
        compact_claim = {
            key: claim[key]
            for key in ("statement", "kind", "confidence")
            if isinstance(claim.get(key), str)
        }
        if isinstance(compact_claim.get("statement"), str):
            statement = compact_claim["statement"]
            if len(statement) > SUMMARY_LIMIT:
                compact_claim["statement"] = statement[: SUMMARY_LIMIT - 1].rstrip() + "…"
    evidence_ids = _values(record, "evidenceIds")
    result = {
        "id": record_id,
        "section": section,
        "title": _display_title(record_id, record),
        "status": record.get("status"),
        "state": record.get("state"),
        "summary": _summary(record),
        "claim": compact_claim,
        "evidenceIds": evidence_ids[:MAX_EVIDENCE],
    }
    if isinstance(record.get("statusNote"),str):
        result["statusNote"] = record["statusNote"][:SUMMARY_LIMIT]
    if section == "questions" and isinstance(record.get("requiresUserDecision"), bool):
        result["requiresUserDecision"] = record["requiresUserDecision"]
    if section in {"apis", "tables"} and record.get("developmentStatus") in ("已完成", "部分完成", "未开发"):
        result["developmentStatus"] = record["developmentStatus"]
    if section == "plans" and type(record.get("sequence")) is int and record["sequence"] > 0:
        result["sequence"] = record["sequence"]
    if relation is not None:
        result["relation"] = sorted(set(relation))
    return result


def _ordered_ids(ids: Iterable[str], records: dict[str, tuple[str, dict[str, Any]]]) -> list[str]:
    section_rank = {section: index for index, section in enumerate(SECTION_ORDER)}
    return sorted(
        {record_id for record_id in ids if record_id in records},
        key=lambda record_id: (section_rank[records[record_id][0]], record_id),
    )


def _evidence_relations(record: dict[str, Any]) -> dict[str, set[str]]:
    relations: dict[str, set[str]] = {}

    def add(record_ids: Iterable[str], relation: str) -> None:
        for evidence_id in record_ids:
            relations.setdefault(evidence_id, set()).add(relation)

    add(_values(record, "evidenceIds"), "evidenceIds")
    claim = record.get("claim")
    if isinstance(claim, dict):
        add(_values(claim, "evidenceIds"), "claim.evidenceIds")
    links = record.get("links")
    if isinstance(links, dict):
        add(_values(links, "evidence"), "links.evidence")
    acceptance = record.get("acceptance", [])
    if isinstance(acceptance, list):
        for index, item in enumerate(acceptance):
            if isinstance(item, dict):
                evidence_id = item.get("evidence")
                if isinstance(evidence_id, str) and evidence_id.startswith("EVID-"):
                    add([evidence_id], f"acceptance[{index}].evidence")
    return relations


def _relation_map(record: dict[str, Any]) -> dict[str, set[str]]:
    relations: dict[str, set[str]] = {}

    def add(record_ids: list[str], relation: str) -> None:
        for record_id in record_ids:
            relations.setdefault(record_id, set()).add(relation)

    add(_values(record, "related"), "related")
    add(_values(record, "requirementIds"), "requirementIds")
    links = record.get("links")
    if isinstance(links, dict):
        for category, values in links.items():
            if isinstance(values, list):
                add([value for value in values if isinstance(value, str)], "links." + str(category))
    return relations


def _inbound_relations(record: dict[str, Any], target_id: str) -> set[str]:
    relations: set[str] = set()
    if target_id in _values(record, "related"):
        relations.add("reverse-related")
    if target_id in _values(record, "requirementIds"):
        relations.add("requirementIds")
    if target_id in _values(record, "evidenceIds"):
        relations.add("evidenceIds")
    claim = record.get("claim")
    if isinstance(claim, dict) and target_id in _values(claim, "evidenceIds"):
        relations.add("claim.evidenceIds")
    links = record.get("links")
    if isinstance(links, dict):
        for category, values in links.items():
            if isinstance(values, list) and target_id in values:
                relations.add("reverse-links." + str(category))
    acceptance = record.get("acceptance", [])
    if isinstance(acceptance, list):
        if any(isinstance(item, dict) and item.get("evidence") == target_id for item in acceptance):
            relations.add("acceptance.evidence")
    return relations


def _is_open_blocker(section: str, record: dict[str, Any]) -> bool:
    state = record.get("state")
    status = str(record.get("status") or "")
    if section == "questions":
        return question_is_open(record)
    return state == "blocked" or "阻塞" in status or bool(record.get("blocker"))


def _blocker_entry(record_id: str, section: str, record: dict[str, Any]) -> dict[str, Any]:
    message = record.get("blocker") or record.get("note") or record.get("question") or record.get("statusNote") or record.get("status") or "待处理"
    if not isinstance(message, str):
        message = str(message)
    result = {
        "id": record_id,
        "section": section,
        "status": record.get("status"),
        "message": message[:SUMMARY_LIMIT],
    }

    if section == "questions" and isinstance(record.get("requiresUserDecision"), bool):
        result["requiresUserDecision"] = record["requiresUserDecision"]
    return result


def _limited(items: list[dict[str, Any]], limit: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    included = items[:limit]
    return included, {
        "totalCount": len(items),
        "includedCount": len(included),
        "omittedCount": len(items) - len(included),
    }


def build_context(
    spec: dict[str, Any],
    record_id: str,
    role: Optional[str] = None,
    full: bool = False,
    limit: int = 8,
    offset: int = 0,
) -> dict[str, Any]:
    if type(limit) is not int or not 1 <= limit <= MAX_RELATED_RECORDS:
        raise ContextError("limit 必须为 1..48 的整数")
    if type(offset) is not int or offset < 0:
        raise ContextError("offset 必须为非负整数")
    records = _record_index(spec)
    if record_id not in records:
        raise ContextError(f"记录 ID 不存在：{record_id}")
    if role is not None and role not in ROLE_FOCUS:
        raise ContextError(f"角色不支持：{role}；可选值：{'、'.join(ROLE_FOCUS)}")

    section, record = records[record_id]
    allowed_sections = set(ROLE_FOCUS[role] if role else SECTION_ORDER)
    relations = _relation_map(record)
    for candidate_id, (candidate_section, candidate_record) in records.items():
        if candidate_id == record_id:
            continue
        inbound = _inbound_relations(candidate_record, record_id)
        if inbound:
            relations.setdefault(candidate_id, set()).update(inbound)
    relations.pop(record_id, None)

    candidate_ids = [
        item_id
        for item_id in _ordered_ids(relations, records)
        if records[item_id][0] in allowed_sections and records[item_id][0] != "evidence"
    ]
    all_candidate_ids = _ordered_ids(relations, records)
    all_related = [
        _compact_record(item_id, records[item_id][0], records[item_id][1], sorted(relations[item_id]))
        for item_id in candidate_ids
    ]
    related_records = all_related[offset:offset + limit]
    related_counts = {"totalCount": len(all_related), "includedCount": len(related_records),
                      "omittedCount": len(all_related) - len(related_records)}

    dependency_ids = set(_values(record, "deps"))
    for related_id in candidate_ids:
        related_section, related_record = records[related_id]
        if related_section == "plans":
            dependency_ids.update(_values(related_record, "deps"))
    dependencies_all = [
        _compact_record(item_id, records[item_id][0], records[item_id][1], ["deps"])
        for item_id in _ordered_ids(dependency_ids, records)
    ]
    dependencies, dependency_counts = _limited(dependencies_all, MAX_DEPENDENCIES)

    blocker_ids = [record_id] + all_candidate_ids
    blocker_records = [
        _blocker_entry(item_id, records[item_id][0], records[item_id][1])
        for item_id in blocker_ids
        if _is_open_blocker(records[item_id][0], records[item_id][1])
    ]
    blockers, blocker_counts = _limited(blocker_records, MAX_BLOCKERS)

    evidence_relations = _evidence_relations(record)
    for item_id in all_candidate_ids:
        if records[item_id][0] == "evidence":
            evidence_relations.setdefault(item_id, set()).update(relations[item_id])
    for related_id in all_candidate_ids:
        for evidence_id, sources in _evidence_relations(records[related_id][1]).items():
            evidence_relations.setdefault(evidence_id, set()).update(
                f"{related_id}.{source}" for source in sources
            )
    evidence_all = [
        _compact_record(item_id, records[item_id][0], records[item_id][1], sorted(evidence_relations[item_id]))
        for item_id in _ordered_ids(evidence_relations, records)
        if records[item_id][0] == "evidence"
    ]
    evidence, evidence_counts = _limited(evidence_all, MAX_EVIDENCE)

    compact_target = _compact_record(record_id, section, record)
    return {
        "recordId": record_id,
        "section": section,
        "role": role,
        "focusSections": list(ROLE_FOCUS[role] if role else SECTION_ORDER),
        "record": (expand_api(spec, record, record_id) if section in {"apis", "existingInterfaces"} else record) if full else compact_target,
        "relatedRecords": related_records,
        **related_counts,
        "pagination": _pagination(offset, limit, len(related_records), len(all_related)),
        "dependencies": dependencies,
        "dependencyCounts": dependency_counts,
        "blockers": blockers,
        "blockerCounts": blocker_counts,
        "evidence": evidence,
        "evidenceCounts": evidence_counts,
    }


def format_context(context: dict[str, Any], full: bool = False) -> str:
    def lines_for(items: list[dict[str, Any]], label: str, counts: Optional[dict[str, int]] = None) -> list[str]:
        heading = f"{label}："
        if counts is not None:
            heading += f"共 {counts['totalCount']}，返回 {counts['includedCount']}，省略 {counts['omittedCount']}"
        lines = [heading]
        if not items:
            lines.append("- 无")
            return lines
        for item in items:
            title = item.get("title")
            title = title or item.get("message") or item["id"]
            suffix = "；关系=" + ",".join(item["relation"]) if item.get("relation") else ""
            if item.get("statusNote"):
                suffix += "；状态说明=" + item["statusNote"]
            lines.append(f"- {item['id']} [{item['section']}] {title}{suffix}")
        return lines

    record = context["record"]
    role = context.get("role") or "未指定"
    lines = [
        f"记录：{context['recordId']}",
        f"分类：{context['section']}",
        f"角色：{role}",
        f"焦点分类：{'、'.join(context['focusSections'])}",
        f"标题：{record.get('title') or _display_title(context['recordId'], record)}",
        f"关联记录：共 {context['totalCount']}，返回 {context['includedCount']}，省略 {context['omittedCount']}",
    ]
    for key, label in (("status", "状态"), ("state", "生命周期"), ("summary", "摘要"), ("statusNote", "状态说明")):
        if record.get(key):
            lines.append(f"{label}：{record[key]}")
    claim = record.get("claim")
    if isinstance(claim, dict) and claim.get("statement"):
        lines.append(f"断言：{claim['statement']}")
    if full:
        lines.extend(["目标记录详情：", json.dumps(record, ensure_ascii=False, indent=2)])
    lines.extend(lines_for(context["relatedRecords"], "关联记录"))
    lines.extend(lines_for(context["blockers"], "阻塞", context["blockerCounts"]))
    lines.extend(lines_for(context["dependencies"], "依赖", context["dependencyCounts"]))
    lines.extend(lines_for(context["evidence"], "证据", context["evidenceCounts"]))
    page = context.get("pagination")
    if page and page["nextOffset"] is not None:
        lines.append(f"后续关联摘要：--offset {page['nextOffset']} --limit {page['limit']}；剩余 {page['remainingCount']} 条；摘要不能代替完整任务合同")
    return "\n".join(lines)


def _pagination(offset: int, limit: int, included: int, total: int) -> dict[str, Any]:
    end = offset + included
    return {"offset": offset, "limit": limit,
            "nextOffset": end if end < total else None,
            "remainingCount": max(0, total - end)}


def serialize_context(context: dict[str, Any], full: bool = False,
                      as_json: bool = False, max_chars: int = 12000) -> str:
    """Bound serialized output including the CLI newline; preserve target and auxiliary lists."""
    if type(max_chars) is not int or max_chars < 1024:
        raise ContextError("输出预算 --max-chars 必须为至少 1024 的整数")
    result = copy.deepcopy(context)
    had_related = bool(result["relatedRecords"])
    while True:
        output = json.dumps(result, ensure_ascii=False, indent=2) if as_json else format_context(result, full)
        if len(output) + 1 <= max_chars:
            if had_related and not result["relatedRecords"]:
                break
            return output
        if not result["relatedRecords"]:
            break
        result["relatedRecords"].pop()
        count = len(result["relatedRecords"])
        result["includedCount"] = count
        result["omittedCount"] = result["totalCount"] - count
        page = result["pagination"]
        result["pagination"] = _pagination(page["offset"], page["limit"], count, result["totalCount"])
    raise ContextError("输出预算不足：目标详情、依赖、阻塞和证据摘要不能裁掉。增加 --max-chars 或查询更具体的任务 ID；当前输出未交付完整合同。")
