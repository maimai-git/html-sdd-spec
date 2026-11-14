"""Read-only checks for the release files attached to an SDD."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator, Optional

from .checker import Issue

PROPERTIES = Path("上线配置清单/上线配置.properties")
SQL = Path("上线SQL清单/上线SQL.sql")
CONFIG_KINDS = {"apollo", "env", "环境变量", "配置", "spring 配置"}
TARGET_FIELDS = ("目标环境", "数据库类型", "目标实例", "数据库", "schema", "前置条件", "跨库依赖")
SECTION = {
    PROPERTIES: re.compile(r"^\s*#\s*=+\s*([^/=]+)\s*/\s*([^/=]+)\s*/\s*(.+?)\s*=+\s*$"),
    SQL: re.compile(r"^\s*--\s*=+\s*\d+\s+([^/=]+)\s*/\s*(.+?)\s*=+\s*$"),
}
PROPERTY = re.compile(r"^\s*[^\s=:#]+\s*=\s*(.*)$")
FIELD = re.compile(r"^([^：:]+)[：:]\s*(.*)$")
UNCONFIRMED = re.compile(r"^(?:<.*>|\{\{.*\}\}|(?:待(?:核对|确认|填写|核实|补充)|todo|tbd)[。.]?)$", re.I)


def _repo_root(directory: Path) -> Path:
    parents = (directory, *directory.parents)
    for parent in parents:
        if (parent / ".git").exists():
            return parent
    return next((parent.parent for parent in parents if parent.name == "html-sdd-spec"), directory)


def _release_file(record: dict) -> Optional[Path]:
    kind = record.get("kind")
    label = kind.strip().casefold() if isinstance(kind, str) else ""
    source = record.get("source")
    filename = source.replace("\\", "/").rsplit("/", 1)[-1] if isinstance(source, str) else ""
    if label in {"ddl", "sql", "手工 ddl"} or filename.endswith(".sql"):
        return SQL
    if label in CONFIG_KINDS or filename.endswith(".properties"):
        return PROPERTIES
    return None


def _sections(text: str, relative: Path) -> Iterator[tuple[int, re.Match, list[str]]]:
    lines = text.splitlines()
    headers = [(i, match) for i, line in enumerate(lines) if (match := SECTION[relative].fullmatch(line))]
    for pos, (i, match) in enumerate(headers):
        end = headers[pos + 1][0] if pos + 1 < len(headers) else len(lines)
        yield i + 1, match, lines[i + 1:end]


def _fields(lines: list[str], comment: str) -> dict[str, str]:
    fields = {}
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith(comment):
            break
        match = FIELD.fullmatch(stripped[len(comment):].strip())
        if match:
            key = re.sub(r"（.*?）|\(.*?\)", "", match[1]).strip().casefold()
            fields[key] = match[2].strip()
    return fields


def _check_fields(fields: dict[str, str], required: tuple[str, ...], location: str) -> Iterator[Issue]:
    for label in required:
        value = fields.get(label.casefold(), "")
        if not value:
            yield Issue("error", "RELEASE_SECTION_FIELD", location, f"发布分段缺少「{label}」")
        elif UNCONFIRMED.fullmatch(value):
            yield Issue("error", "RELEASE_TARGET_UNCONFIRMED", location, f"请提单前核对「{label}」")


def _check_properties(lines: list[str], location: str, header_line: int) -> Iterator[Issue]:
    comments = []
    count = 0
    for line_number, raw in enumerate(lines, header_line + 1):
        line = raw.strip()
        if line.startswith("#"):
            comments.append(line[1:].strip())
            continue
        if not line:
            comments.clear()
            continue
        line_path = f"{location}:{line_number}"
        value = PROPERTY.fullmatch(line)
        if value is None:
            yield Issue("error", "RELEASE_CONFIG_FORMAT", line_path, "配置项须使用单行 key=value")
            comments.clear()
            continue
        count += 1
        if not value[1].strip():
            yield Issue("error", "RELEASE_CONFIG_VALUE", line_path, "配置项缺少值")
        sources = ("本地生效值", "示例值", "目标环境确认值")
        provenance = next((note for note in reversed(comments) if note.startswith(sources)), "")
        description = [note for note in comments if re.search(r"[\u3400-\u9fff]", note)
                       and not note.startswith(sources)]
        details = " ".join(description)
        has_purpose = "用途" in details or "｜" in details or "|" in details
        if not description or not has_purpose or "默认" not in details or not provenance:
            yield Issue(
                "error", "RELEASE_CONFIG_COMMENT", line_path,
                "每项配置上方须单独注明中文名称、用途、默认值和值的来源。描述可用「名称｜用途」",
            )
        if provenance.startswith("示例值"):
            yield Issue("error", "RELEASE_CONFIG_EXAMPLE", line_path, "请在提单前核对示例项的目标环境取值")
        elif UNCONFIRMED.fullmatch(value[1].strip()):
            yield Issue("error", "RELEASE_TARGET_UNCONFIRMED", line_path, "请在提单前核对配置值")
        comments.clear()
    if not count:
        yield Issue("error", "RELEASE_SECTION_EMPTY", f"{location}:{header_line}", "配置段缺少配置项")


def _check_layout(text: str, relative: Path, location: str) -> Iterator[Issue]:
    sections = list(_sections(text, relative))
    comment = "--" if relative == SQL else "#"
    if not sections:
        yield Issue("error", "RELEASE_SECTION_MISSING", location, "发布文件缺少目标分段标题")
        return
    if any(line.strip() and not line.lstrip().startswith(comment)
           for line in text.splitlines()[:sections[0][0] - 1]):
        yield Issue("error", "RELEASE_SECTION_MISSING", location, "段头之前的内容缺少发布目标")
    for line, heading, body in sections:
        fields = _fields(body, comment)
        line_path = f"{location}:{line}"
        if relative == SQL:
            yield from _check_fields(fields, TARGET_FIELDS, line_path)
            if not any(item.strip() and not item.lstrip().startswith(comment) for item in body):
                yield Issue("error", "RELEASE_SECTION_EMPTY", line_path, "目标库段缺少 SQL")
        else:
            required = ("目标环境", "AppId", "namespace") if heading[2].strip().casefold() == "apollo" else (
                "目标环境", "部署位置",
            )
            yield from _check_fields(fields, required, line_path)
            yield from _check_properties(body, location, line)


def validate_release(spec: dict, path: Path) -> list[Issue]:
    directory = path.parent.resolve()
    root = _repo_root(directory)
    issues = []
    seen = set()
    configs = spec.get("configs")
    if not isinstance(configs, list):
        return issues
    for index, record in enumerate(configs):
        if not isinstance(record, dict) or record.get("status") == "不适用":
            continue
        relative = _release_file(record)
        if relative is None:
            continue
        field_path = f"configs[{index}].source"
        source = record.get("source")
        expected = (directory / relative).relative_to(root).as_posix()
        if source != expected:
            issues.append(Issue("error", "RELEASE_SOURCE_INVALID", field_path, f"执行文件应指向 {expected}"))
            continue
        file = root / expected
        try:
            if not file.resolve().is_relative_to(directory):
                issues.append(Issue("error", "RELEASE_SOURCE_INVALID", field_path, "执行文件须位于当前需求目录"))
                continue
            text = file.read_text(encoding="utf-8")
        except (OSError, UnicodeError, RuntimeError):
            issues.append(Issue("error", "RELEASE_FILE_MISSING", field_path, "发布文件不存在或无法按 UTF-8 读取"))
            continue
        content = record.get("content")
        if not isinstance(content, str) or text.rstrip("\n") != content.replace("\r\n", "\n").rstrip("\n"):
            issues.append(Issue("error", "RELEASE_CONTENT_STALE", f"configs[{index}].content", "事实源与发布文件不一致，更新副本后重新生成 HTML"))
        if relative not in seen:
            issues.extend(_check_layout(text, relative, expected))
            seen.add(relative)
    for relative in (PROPERTIES, SQL):
        if (directory / relative).is_file() and relative not in seen:
            issues.append(Issue("error", "RELEASE_FILE_UNLINKED", relative.as_posix(), "发布文件缺少对应的配置执行源记录"))
    return issues
