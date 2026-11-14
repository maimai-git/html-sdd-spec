from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Iterable, Optional

from .references import DefinitionError, field_change_errors, validate_references
from .statuses import registry, status_issues

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
REMOTE_URL_PATTERN = re.compile(r"\b(?:https?|ssh|git)://[^\s<>'\"，；、。]+", re.I)
LOCAL_MACHINE_PATH_PATTERN = re.compile(
    r"(?<![\w./\\-])(?:"
    r"file://|[A-Z]:[\\/]|\\\\[^\\/\s]+\\|~/|"
    r"/(?:Users|home|tmp|private|Volumes|var/(?:tmp|folders|log))/|"
    r"/root/[^/\s，；、。]+(?:/|\.[A-Z0-9])"
    r")",
    re.I | re.ASCII,
)
PLAN_STATUSES = frozenset(registry()['sections']['plans'])
DEVELOPMENT_STATUSES = frozenset(registry()['sections']['developmentStatus'])
RECORD_STATES = frozenset({
    "observed", "proposed", "pending", "in_progress", "verified", "blocked", "accepted", "cancelled",
})
CLAIM_KINDS = frozenset({"fact", "proposal", "pending"})
CONFIDENCE_LEVELS = frozenset({"high", "medium", "low"})
LINK_TARGET_SECTIONS = {
    "requirements": "requirements",
    "plans": "plans",
    "apis": "apis",
    "tables": "tables",
    "architecture": "architecture",
    "configs": "configs",
    "evidence": "evidence",
    "questions": "questions",
}
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
            if section == "requirements" and "outOfScope" in record:
                exclusions = record["outOfScope"]
                if not isinstance(exclusions, list) or any(
                    not isinstance(item, str) or not item.strip() for item in exclusions
                ):
                    issues.append(Issue(
                        "error", "OUT_OF_SCOPE_INVALID", f"{section}[{index}].outOfScope",
                        "非范围必须为非空字符串组成的数组，可省略或留空",
                    ))
            for field in required:
                if field not in record or record[field] in (None, "", []):
                    issues.append(Issue("error", "FIELD_MISSING", f"{section}[{index}].{field}", f"缺少必填字段：{field}"))
    return issues


def _check_plan_statuses(spec: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    sequences: set[int] = set()
    for index, plan in enumerate(spec.get("plans", [])):
        if not isinstance(plan, dict):
            continue
        if "sequence" in plan:
            sequence = plan["sequence"]
            if type(sequence) is not int or not 1 <= sequence <= 9007199254740991:
                issues.append(Issue("error", "PLAN_SEQUENCE_INVALID", f"plans[{index}].sequence", "任务序号必须为 1 到 9007199254740991 之间的整数"))
            elif sequence in sequences:
                issues.append(Issue("error", "PLAN_SEQUENCE_DUPLICATE", f"plans[{index}].sequence", "任务序号必须在整份排期中唯一"))
            else:
                sequences.add(sequence)
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


def _section_record_ids(spec: dict[str, Any]) -> dict[str, set[str]]:
    return {
        section: {
            record.get("id")
            for record in spec.get(section, [])
            if isinstance(record, dict) and isinstance(record.get("id"), str)
        }
        for section in RECORD_SECTIONS
    }


def _check_claims_and_links(spec: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    section_ids = _section_record_ids(spec)
    all_ids = set().union(*section_ids.values()) if section_ids else set()

    for section in RECORD_SECTIONS:
        records = spec.get(section, [])
        if not isinstance(records, list):
            continue
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            base = f"{section}[{index}]"

            if section == "tables" and "displayName" in record:
                label=record["displayName"]
                if not isinstance(label,str) or not label.strip():
                    issues.append(Issue("error", "TABLE_DISPLAY_NAME_INVALID", f"{base}.displayName", "中文表名必须为非空字符串；未知时省略"))

            if section == "configs" and "source" in record and not isinstance(record["source"], str):
                issues.append(Issue("error", "CONFIG_SOURCE_INVALID", f"{base}.source", "配置执行源 source 必须为字符串路径；未知时省略"))

            if section == "questions" and "requiresUserDecision" in record and not isinstance(record["requiresUserDecision"], bool):
                issues.append(Issue("error", "QUESTION_DECISION_FLAG", f"{base}.requiresUserDecision", "requiresUserDecision 只能为 true 或 false；省略表示待分类"))

            if section == "evidence":
                for field in ("locator", "capturedAt", "commit", "checkedBy", "confidence"):
                    if field not in record:
                        continue
                    value = record[field]
                    valid = isinstance(value, str)
                    if valid and field == "checkedBy":
                        valid = bool(ID_PATTERN.fullmatch(value))
                    if valid and field == "confidence":
                        valid = value in CONFIDENCE_LEVELS
                    if not valid:
                        issues.append(Issue(
                            "error", "EVIDENCE_METADATA_INVALID", f"{base}.{field}",
                            f"证据 {field} 类型或取值无效；checkedBy 应为记录 ID，confidence 为 high、medium、low，其余字段为字符串",
                        ))

            state = record.get("state")
            if "state" in record and (not isinstance(state, str) or state not in RECORD_STATES):
                issues.append(
                    Issue(
                        "error",
                        "STATE_INVALID",
                        f"{base}.state",
                        f"state 不在固定枚举中：{state}；可选值：{'、'.join(sorted(RECORD_STATES))}",
                    )
                )
            elif state in {"observed", "proposed"}:
                issues.append(
                    Issue(
                        "warning",
                        "STATE_DEPRECATED",
                        f"{base}.state",
                        f"state={state} 是兼容旧值；state 现在表示记录生命周期，请使用 pending、in_progress、verified、blocked、accepted 或 cancelled",
                    )
                )

            claim = record.get("claim")
            if "claim" in record:
                if not isinstance(claim, dict):
                    issues.append(Issue("error", "CLAIM_SHAPE", f"{base}.claim", "claim 必须是对象"))
                else:
                    kind = claim.get("kind")
                    if not isinstance(kind, str) or kind not in CLAIM_KINDS:
                        issues.append(
                            Issue(
                                "error",
                                "CLAIM_KIND_INVALID",
                                f"{base}.claim.kind",
                                f"claim.kind 必须是 fact、proposal 或 pending，当前为：{kind}",
                            )
                        )
                    confidence = claim.get("confidence")
                    if "confidence" in claim and (
                        not isinstance(confidence, str) or confidence not in CONFIDENCE_LEVELS
                    ):
                        issues.append(
                            Issue(
                                "error",
                                "CLAIM_CONFIDENCE_INVALID",
                                f"{base}.claim.confidence",
                                f"claim.confidence 必须是 high、medium 或 low，当前为：{confidence}",
                            )
                        )
                    statement = claim.get("statement")
                    if "statement" not in claim:
                        issues.append(
                            Issue(
                                "warning",
                                "CLAIM_STATEMENT_MISSING",
                                f"{base}.claim.statement",
                                "旧 claim 缺少 statement，仍兼容；请用自然语言标明该 claim 覆盖的具体断言",
                            )
                        )
                    elif not isinstance(statement, str) or not statement.strip():
                        issues.append(
                            Issue(
                                "error",
                                "CLAIM_STATEMENT_INVALID",
                                f"{base}.claim.statement",
                                "claim.statement 必须是非空字符串",
                            )
                        )

            evidence_ids = record.get("evidenceIds")
            if "evidenceIds" in record:
                if not isinstance(evidence_ids, list):
                    issues.append(Issue("error", "REF_SHAPE", f"{base}.evidenceIds", "evidenceIds 必须是 ID 数组"))
                else:
                    for evidence_index, evidence_id in enumerate(evidence_ids):
                        evidence_path = f"{base}.evidenceIds[{evidence_index}]"
                        if not isinstance(evidence_id, str) or evidence_id not in section_ids["evidence"]:
                            issues.append(
                                Issue(
                                    "error",
                                    "REF_MISSING",
                                    evidence_path,
                                    f"证据 ID 不存在：{evidence_id}",
                                )
                            )

            links = record.get("links")
            if "links" in record:
                if not isinstance(links, dict):
                    issues.append(Issue("error", "LINK_SHAPE", f"{base}.links", "links 必须是按分类组织的对象"))
                else:
                    for target_section, target_ids in links.items():
                        link_path = f"{base}.links.{target_section}"
                        expected_section = LINK_TARGET_SECTIONS.get(target_section)
                        if expected_section is None:
                            issues.append(
                                Issue(
                                    "error",
                                    "LINK_CATEGORY_INVALID",
                                    link_path,
                                    f"links 分类不支持：{target_section}；可选分类：{'、'.join(LINK_TARGET_SECTIONS)}",
                                )
                            )
                            continue
                        if not isinstance(target_ids, list):
                            issues.append(Issue("error", "LINK_SHAPE", link_path, "links 分类值必须是 ID 数组"))
                            continue
                        for target_index, target_id in enumerate(target_ids):
                            target_path = f"{link_path}[{target_index}]"
                            if not isinstance(target_id, str) or target_id not in all_ids:
                                issues.append(
                                    Issue(
                                        "error",
                                        "LINK_TARGET_MISSING",
                                        target_path,
                                        f"关联 ID 不存在：{target_id}（期望分类：{expected_section}）",
                                    )
                                )
                            elif target_id not in section_ids[expected_section]:
                                actual_section = next(
                                    section_name
                                    for section_name, ids in section_ids.items()
                                    if target_id in ids
                                )
                                issues.append(
                                    Issue(
                                        "error",
                                        "LINK_TARGET_MISMATCH",
                                        target_path,
                                        f"关联 ID {target_id} 位于 {actual_section}，但 links.{target_section} 期望 {expected_section}",
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


def _check_local_machine_paths(spec: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    for path, value in _walk_strings(spec):
        if LOCAL_MACHINE_PATH_PATTERN.search(REMOTE_URL_PATTERN.sub("", value)):
            issues.append(Issue(
                "warning", "LOCAL_MACHINE_PATH", path,
                "发现本机路径。仓内文件请用仓库根目录相对路径，外部资料请用共享链接，本机材料请标注本机留存。",
            ))
    return issues


def validate_spec(spec: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    if not isinstance(spec, dict):
        return [Issue("error", "ROOT_SHAPE", "", "规范根节点必须是对象")]
    try:
        validate_references(spec)
    except DefinitionError as exc:
        issues.append(Issue("error", "DEFINITION_ERROR", exc.path, str(exc)))
    missing = sorted(REQUIRED_TOP_LEVEL - set(spec))
    for name in missing:
        issues.append(Issue("error", "TOP_LEVEL_MISSING", name, f"缺少顶层分类：{name}"))
    if spec.get("specVersion") != "0.1":
        issues.append(Issue("error", "SPEC_VERSION", "specVersion", "当前 CLI 只支持 specVersion 0.1"))
    issues.extend(Issue(*item) for item in status_issues(spec))
    issues.extend(Issue("error", "FIELD_CHANGE_STATUS_INVALID", path, "字段变更状态只能为新增、修改或删除")
                  for path in field_change_errors(spec))
    known_ids, id_issues = _record_ids(spec)
    issues.extend(id_issues)
    issues.extend(_check_required_fields(spec))
    issues.extend(_check_plan_statuses(spec))
    issues.extend(_check_claims_and_links(spec))
    issues.extend(_check_references(spec, set(known_ids)))
    issues.extend(_check_integrity(spec))
    issues.extend(_check_ready_gate(spec))
    issues.extend(_check_sensitive(spec))
    issues.extend(_check_local_machine_paths(spec))
    return issues


def load_spec(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("规范根节点必须是对象")
    return value
