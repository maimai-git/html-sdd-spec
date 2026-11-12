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

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "section": self.section,
            "recordId": self.record_id,
            "summary": self.summary,
            "before": self.before,
            "after": self.after,
        }


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
    return "\n".join(f"{change.kind.upper()} {change.section} {change.record_id}: {change.summary}" for change in changes)
