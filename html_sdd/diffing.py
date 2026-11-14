from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Optional

from .references import expanded_spec

SECTIONS = (
    "metadata", "baseline", "agents", "requirements", "plans", "apis",
    "tables", "architecture", "configs", "evidence", "questions", "existingInterfaces", "definitions",
)


@dataclass(frozen=True)
class Change:
    kind: str
    section: str
    record_id: str
    summary: str
    before: Optional[dict[str, Any]] = None
    after: Optional[dict[str, Any]] = None

    @property
    def fields(self) -> list[dict]:
        if self.section not in ("apis", "existingInterfaces", "tables"):
            return []
        areas = ("columns",) if self.section == "tables" else ("request", "response")
        return [
            change
            for area in areas
            for change in _field_changes(self.before, self.after, area)
        ]

    @property
    def ddl_changed_without_columns(self) -> bool:
        if self.section != "tables":
            return False
        old, new = self.before or {}, self.after or {}
        return (old.get("ddl") != new.get("ddl")
                and (self.before is not None and not isinstance(old.get("columns"), list)
                     or self.after is not None and not isinstance(new.get("columns"), list)))

    def as_dict(self) -> dict[str, Any]:
        result = {
            "kind": self.kind,
            "section": self.section,
            "recordId": self.record_id,
            "summary": self.summary,
            "before": self.before,
            "after": self.after,
        }
        fields = self.fields
        if fields:
            result["fieldChanges"] = fields
        if self.ddl_changed_without_columns:
            result["ddlChangedWithoutColumns"] = True
        return result


def _field_index(rows: list, area: str) -> Optional[dict]:
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            return None
        if row.get("changeStatus") == "删除":
            continue
        name = row.get("name") or row.get("field")
        location = (row.get("location") or row.get("where") or "") if area == "request" else ""
        if not isinstance(name, str) or not name or not isinstance(location, str):
            return None
        key = (location, name)
        if key in result:
            return None
        normalized = dict(row)
        normalized.pop("changeStatus", None)
        for alias, canonical in (("field", "name"), ("where", "location"), ("desc", "description")):
            if alias in normalized:
                normalized.setdefault(canonical, normalized.pop(alias))
        if area == "request":
            normalized["location"] = location
        result[key] = normalized
    return result


def _field_changes(before: Optional[dict], after: Optional[dict], area: str) -> list[dict]:
    # An omitted column inventory represents unknown schema, while a new record has no prior fields.
    default = None if area == "columns" else []
    old = before.get(area, default) if before is not None else []
    new = after.get(area, default) if after is not None else []
    if not isinstance(old, list) or not isinstance(new, list):
        return []
    left, right = _field_index(old, area), _field_index(new, area)
    if left is None or right is None:
        return []
    changes = []
    for location, name in sorted(left.keys() | right.keys()):
        previous, current = left.get((location, name)), right.get((location, name))
        if not _equal(previous, current):
            kind = "added" if previous is None else "removed" if current is None else "changed"
            changes.append(dict(area=area, location=location, name=name, kind=kind,
                                before=previous, after=current))
    return changes


def _records(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list):
        return {}
    return {record.get("id"): record for record in value if isinstance(record, dict) and record.get("id")}


def _section_records(spec: dict[str, Any], section: str) -> dict[str, dict[str, Any]]:
    value = spec.get(section)
    if section in {"metadata", "baseline"}:
        return {section: value} if isinstance(value, dict) else {}
    if section == "definitions" and isinstance(value, dict):
        return {category + "/" + name: {"value": item}
                for category, values in value.items() for name, item in values.items()}
    return _records(value)


def _equal(left: Any, right: Any) -> bool:
    # Python equates False/0 and True/1; JSON contracts must retain those distinctions.
    return json.dumps(left, ensure_ascii=False, sort_keys=True) == json.dumps(right, ensure_ascii=False, sort_keys=True)


def diff_specs(before: dict[str, Any], after: dict[str, Any]) -> list[Change]:
    before, after = expanded_spec(before), expanded_spec(after)
    changes: list[Change] = []
    for section in SECTIONS:
        left = _section_records(before, section)
        right = _section_records(after, section)
        for record_id in sorted(right.keys() - left.keys()):
            changes.append(Change("added", section, record_id, "新增记录", None, right[record_id]))
        for record_id in sorted(left.keys() - right.keys()):
            changes.append(Change("removed", section, record_id, "删除记录", left[record_id], None))
        for record_id in sorted(left.keys() & right.keys()):
            if not _equal(left[record_id], right[record_id]):
                before_keys = set(left[record_id])
                after_keys = set(right[record_id])
                changed_keys = sorted(key for key in before_keys | after_keys if key not in left[record_id] or key not in right[record_id] or not _equal(left[record_id][key], right[record_id][key]))
                changes.append(Change("changed", section, record_id, "字段变化：" + ", ".join(changed_keys), left[record_id], right[record_id]))
    return changes


def format_changes(changes: list[Change]) -> str:
    if not changes:
        return "无变化"
    lines = []
    for change in changes:
        lines.append(f"{change.kind.upper()} {change.section} {change.record_id}: {change.summary}")
        for field in change.fields:
            name = " / ".join(filter(None, (field["area"], field["location"], field["name"])))
            lines.append(f'  {field["kind"].upper()} {name}')
        if change.ddl_changed_without_columns:
            lines.append("  DDL 已变更，缺少列快照")
    return "\n".join(lines)
