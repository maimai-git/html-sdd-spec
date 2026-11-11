from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Iterable, Optional

RECORD_SECTIONS = (
    "agents",
    "requirements",
    "plans",
    "apis",
    "tables",
    "architecture",
    "configs",
    "evidence",
    "questions",
)

REQUIRED_TOP_LEVEL = {
    "specVersion",
    "metadata",
    "baseline",
    "agents",
    "requirements",
    "plans",
    "apis",
    "tables",
    "architecture",
    "configs",
    "evidence",
    "questions",
}

ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9-]*$")
SENSITIVE_PATTERNS = (
    re.compile(r"(?i)(?:password|passwd|token|api[_-]?key|secret)\s*[:=]\s*(?!<|$)(?!\[[^\]]+\])[^\s#]+"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._-]{16,}"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
    re.compile(r"(?i)\bjdbc:[^\s]+"),
)
PLAN_STATUSES = frozenset({
    "待拆分", "待确认", "编码 READY", "待开始", "进行中", "待接入",
    "待执行", "待复核", "待验收", "阻塞", "已完成", "已取消",
})
DIAGRAM_ENGINES = frozenset({"mermaid", "inline-svg", "text"})


@dataclass(frozen=True)
class Issue:
    level: str
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "level": self.level,
            "code": self.code,
            "path": self.path,
            "message": self.message,
        }


def _walk_strings(value: Any, path: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            yield from _walk_strings(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_strings(child, f"{path}[{index}]")


def _record_ids(spec: dict[str, Any]) -> tuple[dict[str, str], list[Issue]]:
    locations: dict[str, str] = {}
    issues: list[Issue] = []
    for section in RECORD_SECTIONS:
        records = spec.get(section, [])
        if not isinstance(records, list):
            continue
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                issues.append(Issue("error", "RECORD_SHAPE", f"{section}[{index}]", "记录必须是对象"))
                continue
            record_id = record.get("id")
            path = f"{section}[{index}].id"
            if not isinstance(record_id, str) or not record_id:
                issues.append(Issue("error", "ID_MISSING", path, "记录缺少稳定 ID"))
                continue
            if not ID_PATTERN.fullmatch(record_id):
                issues.append(Issue("error", "ID_FORMAT", path, f"ID 不符合大写稳定 ID 规则：{record_id}"))
            if record_id in locations:
                issues.append(Issue("error", "ID_DUPLICATE", path, f"ID {record_id} 已在 {locations[record_id]} 出现"))
            else:
                locations[record_id] = path
            if section == "requirements":
                for acceptance_index, acceptance in enumerate(record.get("acceptance", [])):
                    if not isinstance(acceptance, dict):
                        continue
                    acceptance_id = acceptance.get("id")
                    acceptance_path = f"{section}[{index}].acceptance[{acceptance_index}].id"
                    if not isinstance(acceptance_id, str) or not acceptance_id:
                        issues.append(Issue("error", "ID_MISSING", acceptance_path, "验收项缺少稳定 ID"))
                    elif not ID_PATTERN.fullmatch(acceptance_id):
                        issues.append(Issue("error", "ID_FORMAT", acceptance_path, f"ID 不符合大写稳定 ID 规则：{acceptance_id}"))
                    elif acceptance_id in locations:
                        issues.append(Issue("error", "ID_DUPLICATE", acceptance_path, f"ID {acceptance_id} 已在 {locations[acceptance_id]} 出现"))
                    else:
                        locations[acceptance_id] = acceptance_path
    return locations, issues


def _check_references(spec: dict[str, Any], known_ids: set[str]) -> list[Issue]:
    issues: list[Issue] = []
    agents = {
        agent.get("id"): agent
        for agent in spec.get("agents", [])
        if isinstance(agent, dict) and agent.get("id")
    }
    plan_ids = {
        plan.get("id")
        for plan in spec.get("plans", [])
        if isinstance(plan, dict) and plan.get("id")
    }

    def agent_role(agent: dict[str, Any]) -> Optional[str]:
        text = f"{agent.get('role', '')} {agent.get('name', '')}".lower()
        if "owner" in text or "负责人" in text:
            return "owner"
        if "review" in text or "审核" in text:
            return "reviewer"
        if "execut" in text or "执行" in text:
            return "executor"
        return None

    def check_agent_role(agent_id: Any, expected: str, path: str) -> None:
        if agent_id not in agents:
            return
        actual = agent_role(agents[agent_id])
        if actual != expected:
            issues.append(
                Issue(
                    "error",
                    "AGENT_ROLE_MISMATCH",
                    path,
                    f"Agent {agent_id} 应为 {expected} 角色，实际为 {actual or '未声明'}",
                )
            )

    def check_list(values: Any, path: str) -> None:
        if values is None:
            return
        if not isinstance(values, list):
            issues.append(Issue("error", "REF_SHAPE", path, "关联字段必须是 ID 数组"))
            return
        for index, value in enumerate(values):
            if value not in known_ids:
                issues.append(Issue("error", "REF_MISSING", f"{path}[{index}]", f"关联 ID 不存在：{value}"))

    for section in RECORD_SECTIONS:
        records = spec.get(section, [])
        if not isinstance(records, list):
            continue
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            base = f"{section}[{index}]"
            check_list(record.get("related"), f"{base}.related")
            if section == "plans":
                check_list(record.get("requirementIds"), f"{base}.requirementIds")
                deps = record.get("deps")
                if deps is not None:
                    if not isinstance(deps, list):
                        issues.append(Issue("error", "REF_SHAPE", f"{base}.deps", "依赖必须是计划 ID 数组"))
                    else:
                        for dep_index, dependency in enumerate(deps):
                            if dependency not in plan_ids:
                                issues.append(
                                    Issue(
                                        "error",
                                        "REF_MISSING",
                                        f"{base}.deps[{dep_index}]",
                                        f"计划依赖 ID 不存在：{dependency}",
                                    )
                                )
                for role in ("owner", "reviewer", "executor"):
                    role_id = record.get(role)
                    if role_id not in known_ids:
                        issues.append(Issue("error", "REF_MISSING", f"{base}.{role}", f"Agent ID 不存在：{role_id}"))
                    else:
                        check_agent_role(role_id, role, f"{base}.{role}")
                for role_ids in ("reviewerIds", "executorIds"):
                    role_values = record.get(role_ids)
                    check_list(role_values, f"{base}.{role_ids}")
                    expected_role = "reviewer" if role_ids == "reviewerIds" else "executor"
                    for role_index, role_id in enumerate(role_values if isinstance(role_values, list) else []):
                        check_agent_role(role_id, expected_role, f"{base}.{role_ids}[{role_index}]")
            if section == "requirements":
                for acceptance_index, acceptance in enumerate(record.get("acceptance", [])):
                    if not isinstance(acceptance, dict):
                        continue
                    evidence = acceptance.get("evidence")
                    if isinstance(evidence, str) and evidence.startswith("EVID-"):
                        evidence_path = f"{base}.acceptance[{acceptance_index}].evidence"
                        if evidence not in known_ids:
                            issues.append(Issue("error", "REF_MISSING", evidence_path, f"关联 ID 不存在：{evidence}"))
            if section == "questions" and record.get("owner") is not None:
                check_list([record.get("owner")], f"{base}.owner")
    return issues


def _check_required_fields(spec: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    for section, required in {
        "requirements": ("group", "title", "summary", "status", "acceptance"),
        "plans": ("priority", "module", "requirementIds", "main", "sub", "owner", "reviewer", "executor", "status"),
        "apis": ("group", "name", "method", "path", "changeType", "status", "summary", "request", "response", "requestExample", "responseExample"),
        "tables": ("group", "name", "changeType", "status", "purpose", "ddl"),
        "architecture": ("group", "type", "title", "status"),
        "configs": ("group", "kind", "title", "environment", "status", "content"),
    }.items():
        records = spec.get(section, [])
        if not isinstance(records, list):
            issues.append(Issue("error", "SECTION_SHAPE", section, "分类必须是数组"))
            continue
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            for field in required:
                if field not in record or record[field] in (None, "", []):
                    issues.append(Issue("error", "FIELD_MISSING", f"{section}[{index}].{field}", f"缺少必填字段：{field}"))
    return issues


def _check_plan_statuses(spec: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    for index, plan in enumerate(spec.get("plans", [])):
        if not isinstance(plan, dict):
            continue
        status = plan.get("status")
        if status not in PLAN_STATUSES:
            issues.append(
                Issue(
                    "error",
                    "PLAN_STATUS_INVALID",
                    f"plans[{index}].status",
                    f"排期状态不在固定枚举中：{status}；可选值：{'、'.join(sorted(PLAN_STATUSES))}",
                )
            )
    return issues


def _check_integrity(spec: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []

    def missing(path: str, field: str, message: str) -> None:
        issues.append(Issue("error", "ARCH_FIELD_MISSING", f"{path}.{field}", message))

    for index, architecture in enumerate(spec.get("architecture", [])):
        if not isinstance(architecture, dict):
            continue
        path = f"architecture[{index}]"
        if architecture.get("type") == "solution":
            for field in ("conclusion", "current", "steps", "impact", "risks"):
                if architecture.get(field) in (None, "", []):
                    missing(path, field, f"solution 架构记录必须提供 {field}，并使用模板可渲染的字段名")
        elif architecture.get("type") == "diagram":
            if not architecture.get("diagramType"):
                missing(path, "diagramType", "diagram 架构记录必须说明图类型")
            if not any(architecture.get(field) for field in ("diagramSvg", "diagramSource", "fallback")):
                missing(path, "diagramSource", "diagram 架构记录至少需要 diagramSvg、diagramSource 或 fallback")
            engine = architecture.get("diagramEngine")
            if engine is not None and (not isinstance(engine, str) or engine not in DIAGRAM_ENGINES):
                issues.append(
                    Issue(
                        "error",
                        "ARCH_DIAGRAM_ENGINE_INVALID",
                        f"{path}.diagramEngine",
                        f"diagramEngine 不在固定枚举中：{engine}；可选值：{'、'.join(sorted(DIAGRAM_ENGINES))}",
                    )
                )
            elif engine == "mermaid" and not architecture.get("diagramSource"):
                issues.append(
                    Issue(
                        "error",
                        "ARCH_DIAGRAM_SOURCE_MISSING",
                        f"{path}.diagramSource",
                        "diagramEngine=mermaid 时必须提供 Mermaid 图源",
                    )
                )
            elif engine == "inline-svg" and not architecture.get("diagramSvg"):
                missing(path, "diagramSvg", "diagramEngine=inline-svg 时必须提供内联 SVG")
            elif engine == "text" and not architecture.get("fallback"):
                missing(path, "fallback", "diagramEngine=text 时必须提供文字回退")

    plan_requirement_ids = {
        requirement_id
        for plan in spec.get("plans", [])
        if isinstance(plan, dict)
        for requirement_id in (plan.get("requirementIds") or [])
    }
    for index, requirement in enumerate(spec.get("requirements", [])):
        if not isinstance(requirement, dict):
            continue
        requirement_id = requirement.get("id")
        if requirement_id and requirement_id not in plan_requirement_ids:
            issues.append(
                Issue(
                    "warning",
                    "LINT_PLAN_LINK_MISSING",
                    f"requirements[{index}]",
                    f"子需求 {requirement_id} 尚未关联排期计划",
                )
            )

    plans = [plan for plan in spec.get("plans", []) if isinstance(plan, dict)]
    plan_dependencies = {
        plan.get("id"): set(plan.get("deps") or [])
        for plan in plans
        if plan.get("id")
    }

    plan_indexes = {
        plan.get("id"): index
        for index, plan in enumerate(spec.get("plans", []))
        if isinstance(plan, dict) and plan.get("id")
    }
    cycle_keys: set[tuple[str, ...]] = set()

    def visit_plan(plan_id: str, stack: list[str], active: set[str], visited: set[str]) -> None:
        if plan_id in active:
            cycle = tuple(stack[stack.index(plan_id):] + [plan_id])
            key = tuple(sorted(set(cycle)))
            if key not in cycle_keys:
                cycle_keys.add(key)
                index = plan_indexes.get(plan_id, 0)
                issues.append(
                    Issue(
                        "error",
                        "LINT_DEPENDENCY_CYCLE",
                        f"plans[{index}].deps",
                        f"计划依赖形成循环：{' -> '.join(cycle)}",
                    )
                )
            return
        if plan_id in visited:
            return
        active.add(plan_id)
        stack.append(plan_id)
        for dependency in plan_dependencies.get(plan_id, set()):
            if dependency in plan_indexes:
                visit_plan(dependency, stack, active, visited)
        stack.pop()
        active.remove(plan_id)
        visited.add(plan_id)

    visited_plans: set[str] = set()
    for plan_id in plan_indexes:
        visit_plan(plan_id, [], set(), visited_plans)

    def depends_on(start_id: str, target_id: str) -> bool:
        pending = list(plan_dependencies.get(start_id, set()))
        visited: set[str] = set()
        while pending:
            dependency = pending.pop()
            if dependency in visited:
                continue
            if dependency == target_id:
                return True
            visited.add(dependency)
            pending.extend(plan_dependencies.get(dependency, set()))
        return False

    owner_paths: list[tuple[int, str, str, str]] = []
    for index, plan in enumerate(plans):
        paths = plan.get("ownerPaths")
        executor_ids = plan.get("executorIds") or []
        if paths is not None and (
            not isinstance(paths, list) or any(not isinstance(path, str) or not path.strip() for path in paths)
        ):
            issues.append(Issue("error", "LINT_OWNER_PATHS_SHAPE", f"plans[{index}].ownerPaths", "ownerPaths 必须是非空字符串数组"))
            continue
        if len(executor_ids) > 1 and not paths:
            issues.append(
                Issue(
                    "warning",
                    "LINT_OWNER_PATHS_MISSING",
                    f"plans[{index}]",
                    "多个执行人并行时必须声明 ownerPaths，避免修改范围冲突",
                )
            )
        for path in paths or []:
            owner_paths.append((index, plan.get("id", f"PLAN-{index}"), path.rstrip("/"), f"plans[{index}].ownerPaths"))

    for left_index, (left_plan_index, left_plan_id, left_path, _) in enumerate(owner_paths):
        for right_plan_index, right_plan_id, right_path, right_location in owner_paths[left_index + 1 :]:
            if left_plan_index == right_plan_index:
                continue
            if depends_on(left_plan_id, right_plan_id) or depends_on(right_plan_id, left_plan_id):
                continue
            if left_path == right_path or left_path.startswith(right_path + "/") or right_path.startswith(left_path + "/"):
                issues.append(
                    Issue(
                        "warning",
                        "LINT_OWNER_PATH_OVERLAP",
                        right_location,
                        f"{right_plan_id} 与 {left_plan_id} 的 ownerPaths 重叠：{left_path} / {right_path}",
                    )
                )
    return issues


def _check_ready_gate(spec: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    section_names = ("apis", "tables", "architecture", "configs")
    records_by_section = {
        section: {
            record.get("id"): record
            for record in spec.get(section, [])
            if isinstance(record, dict) and record.get("id")
        }
        for section in section_names
    }
    evidence_ids = {
        record.get("id")
        for record in spec.get("evidence", [])
        if isinstance(record, dict) and record.get("id")
    }
    plan_requirement_ids = {
        requirement_id
        for plan in spec.get("plans", [])
        if isinstance(plan, dict)
        for requirement_id in (plan.get("requirementIds") or [])
    }
    for index, requirement in enumerate(spec.get("requirements", [])):
        if not isinstance(requirement, dict) or requirement.get("status") != "编码 READY":
            continue
        acceptance = requirement.get("acceptance") or []
        related = requirement.get("related") or []
        if requirement.get("id") not in plan_requirement_ids:
            issues.append(Issue("error", "READY_INCOMPLETE", f"requirements[{index}]", "编码 READY 必须关联至少一个排期计划"))
        if not acceptance or not related:
            issues.append(Issue("error", "READY_INCOMPLETE", f"requirements[{index}]", "编码 READY 至少需要验收项和关联记录"))
        for acceptance_index, item in enumerate(acceptance):
            if not isinstance(item, dict) or not item.get("evidence"):
                issues.append(Issue("error", "READY_INCOMPLETE", f"requirements[{index}].acceptance[{acceptance_index}]", "编码 READY 的验收项必须有证据"))
            elif not isinstance(item.get("evidence"), str) or item.get("evidence") not in evidence_ids:
                issues.append(
                    Issue(
                        "error",
                        "READY_EVIDENCE_UNLINKED",
                        f"requirements[{index}].acceptance[{acceptance_index}].evidence",
                        "编码 READY 的验收证据必须引用 evidence 中已有的 EVID-* 记录",
                    )
                )
        impact = requirement.get("impact") or {}
        related_ids = set(related)
        for section in section_names:
            if impact.get(section) == "not_applicable":
                continue
            if not related_ids.intersection(records_by_section[section]):
                issues.append(
                    Issue(
                        "error",
                        "READY_IMPACT_MISSING",
                        f"requirements[{index}].impact.{section}",
                        f"编码 READY 需要在 related 中关联至少一条 {section} 记录，或明确标记 not_applicable",
                    )
                )
    return issues


def _check_sensitive(spec: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    for path, value in _walk_strings(spec):
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(value):
                issues.append(Issue("error", "SENSITIVE_VALUE", path, "疑似包含敏感值，请改成占位符"))
                break
    return issues


def validate_spec(spec: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    if not isinstance(spec, dict):
        return [Issue("error", "ROOT_SHAPE", "", "规范根节点必须是对象")]
    missing = sorted(REQUIRED_TOP_LEVEL - set(spec))
    for name in missing:
        issues.append(Issue("error", "TOP_LEVEL_MISSING", name, f"缺少顶层分类：{name}"))
    if spec.get("specVersion") != "0.1":
        issues.append(Issue("error", "SPEC_VERSION", "specVersion", "当前 CLI 只支持 specVersion 0.1"))
    known_ids, id_issues = _record_ids(spec)
    issues.extend(id_issues)
    issues.extend(_check_required_fields(spec))
    issues.extend(_check_plan_statuses(spec))
    issues.extend(_check_references(spec, set(known_ids)))
    issues.extend(_check_integrity(spec))
    issues.extend(_check_ready_gate(spec))
    issues.extend(_check_sensitive(spec))
    return issues


def load_spec(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("规范根节点必须是对象")
    return value
