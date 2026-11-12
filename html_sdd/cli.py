from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from .checker import load_spec, validate_spec
from .renderer import render_spec
from .diffing import diff_specs, format_changes
from .scaffold import STANDARD_SDD_DIRECTORY, init_project
from .context import ContextError, build_context, serialize_context
from . import __version__


def _print_issues(issues, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps([issue.as_dict() for issue in issues], ensure_ascii=False, indent=2))
        return
    for issue in issues:
        print(f"{issue.level.upper()} {issue.code} {issue.path}: {issue.message}")


def check_command(path: Path, as_json: bool = False) -> int:
    try:
        spec = load_spec(str(path))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        if as_json:
            print(
                json.dumps(
                    [
                        {
                            "level": "error",
                            "code": "INPUT_ERROR",
                            "path": str(path),
                            "message": str(exc),
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 1
        print(f"ERROR INPUT {path}: {exc}")
        return 1
    issues = validate_spec(spec)
    if as_json:
        _print_issues(issues, True)
    else:
        _print_issues(issues, False)
    errors = [issue for issue in issues if issue.level == "error"]
    if errors:
        return 1
    if not as_json:
        print(f"OK {path}")
    return 0


def context_command(
    path: Path,
    record_id: str,
    role: Optional[str] = None,
    as_json: bool = False,
    full: bool = False,
    limit: int = 8,
    offset: int = 0,
    max_chars: int = 12000,
) -> int:
    try:
        spec = load_spec(str(path))
        context = build_context(spec, record_id, role, full=full, limit=limit, offset=offset)
        output = serialize_context(context, full=full, as_json=as_json, max_chars=max_chars)
    except (OSError, ValueError, json.JSONDecodeError, ContextError) as exc:
        if as_json:
            print(
                json.dumps(
                    {
                        "code": "CONTEXT_ERROR",
                        "path": str(path),
                        "recordId": record_id,
                        "message": str(exc),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(f"ERROR CONTEXT {path} {record_id}: {exc}")
        return 1
    print(output)
    return 0


def _template_path() -> Path:
    """Return the bundled template, with a source-tree fallback for development."""
    bundled = Path(__file__).resolve().parent / "assets" / "console.html"
    if bundled.exists():
        return bundled
    return Path(__file__).resolve().parents[1] / "templates" / "console.html"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="html-sdd", description="HTML SDD Spec local CLI")
    parser.add_argument("--version", action="version", version=f"html-sdd {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="检查 JSON 规范")
    check.add_argument("path", type=Path)
    check.add_argument("--json", action="store_true", dest="as_json")
    context = sub.add_parser("context", help="按记录 ID 输出关联上下文")
    context.add_argument("path", type=Path, help="方案事实源 JSON 文件")
    context.add_argument("record_id", help="稳定记录 ID，例如 REQ-001")
    context.add_argument(
        "--role",
        choices=("owner", "reviewer", "executor"),
        help="按负责人、审核人或执行人的关注范围整理输出",
    )
    context.add_argument("--json", action="store_true", dest="as_json", help="输出机器可读 JSON")
    context.add_argument("--full", action="store_true", help="展开目标记录；关联记录仍保持精简")
    context.add_argument("--limit", type=int, default=8, help="每页关联摘要数，1..48，默认 8")
    context.add_argument("--offset", type=int, default=0, help="关联摘要起始位置，默认 0")
    context.add_argument("--max-chars", type=int, default=12000, help="实际输出字符预算（非精确 Token），至少 1024")
    statuses = sub.add_parser("statuses", help="查询统一状态及颜色字典")
    statuses.add_argument("--section", help="板块，例如 plans、apis、metadata")
    statuses.add_argument("--json", action="store_true", dest="as_json")
    reuse = sub.add_parser("reuse", help="预览完全相同参数/规则的公共定义提取；--output 写候选文件")
    reuse.add_argument("path", type=Path)
    reuse.add_argument("--output", type=Path)
    browser = sub.add_parser("browser-check", help="运行已有 Playwright 会话脚本，仅回传摘要；完整日志留本地")
    browser.add_argument("script", type=Path)
    browser.add_argument("--session", required=True)
    browser.add_argument("--log", type=Path)
    browser.add_argument("--max-output", type=int, default=1600)
    render = sub.add_parser("render", help="生成单文件 HTML（Mermaid 图表按需使用 CDN）")
    render.add_argument("path", type=Path)
    render.add_argument("--output", type=Path, required=True)
    diff = sub.add_parser("diff", help="比较两个 JSON 规范")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    diff.add_argument("--json", action="store_true", dest="as_json")
    init = sub.add_parser("init", help="创建 HTML SDD 项目骨架")
    init.add_argument(
        "directory",
        type=Path,
        nargs="?",
        default=STANDARD_SDD_DIRECTORY,
        help="开发需求目录，默认：html-sdd-spec/新开发需求；一个开发过程使用一个目录",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "statuses":
        from .statuses import registry
        data=registry()
        if args.section and args.section not in data["sections"]:
            print("ERROR STATUS_SECTION: 不存在的状态板块")
            return 1
        sections={args.section:data["sections"][args.section]} if args.section else data["sections"]
        result={name:[dict(label=label,tone=data["statuses"][label],**data["tones"][data["statuses"][label]]) for label in labels] for name,labels in sections.items()}
        if args.as_json:print(json.dumps(result,ensure_ascii=False,indent=2))
        else:
            for name,items in result.items():print(name+"："+"、".join(item["label"]+"("+item["color"]+")" for item in items))
        return 0
    if args.command == "reuse":
        from .reuse import reuse_spec, format_spec
        try:
            source_bytes = args.path.read_bytes()
            spec = json.loads(source_bytes)
            if not isinstance(spec, dict):
                raise ValueError("规范根节点必须是对象")
            errors = [issue for issue in validate_spec(spec) if issue.level == "error"]
            if errors:
                _print_issues(errors)
                return 1
            result = reuse_spec(spec)
            size = lambda item: len(json.dumps(item, ensure_ascii=False, separators=(",", ":")).encode())
            print(f"紧凑 JSON：{size(spec)} → {size(result)} 字节；净减少 {size(spec) - size(result)} 字节")
            text = format_spec(result)
            if result == spec:
                text = source_bytes.decode("utf-8")
            elif len(text.encode()) >= len(source_bytes):
                text = json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n"
            print(f"保存格式：{len(source_bytes)} → {len(text.encode())} 字节")
            if args.output:
                if args.path.resolve() == args.output.resolve():
                    raise ValueError("请输出到新的候选文件；核对后再替换事实源")
                args.output.parent.mkdir(parents=True, exist_ok=True)
                with args.output.open("x", encoding="utf-8") as handle:
                    handle.write(text)
                print(f"OK {args.output}")
            else:
                print("仅预览，未写文件；使用 --output <候选.json> 保存")
            return 0
        except (OSError, ValueError) as exc:
            print(f"ERROR REUSE: {exc}")
            return 1
    if args.command == "browser-check":
        from .browser_check import browser_check
        code, output = browser_check(args.script, args.session, args.log, args.max_output)
        print(output)
        return code
    if args.command == "check":
        return check_command(args.path, args.as_json)
    if args.command == "context":
        return context_command(args.path, args.record_id, args.role, args.as_json, args.full, args.limit, args.offset, args.max_chars)
    if args.command == "render":
        try:
            spec = load_spec(str(args.path))
            html = render_spec(spec, _template_path())
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(html, encoding="utf-8")
            print(f"OK {args.output}")
            return 0
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"ERROR RENDER {args.path}: {exc}")
            return 1
    if args.command == "diff":
        try:
            before = load_spec(str(args.before))
            after = load_spec(str(args.after))
            changes = diff_specs(before, after)
            if args.as_json:
                print(json.dumps([change.as_dict() for change in changes], ensure_ascii=False, indent=2))
            else:
                print(format_changes(changes))
            return 0
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"ERROR DIFF: {exc}")
            return 1
    if args.command == "init":
        try:
            init_project(args.directory, _template_path())
            print(f"OK {args.directory}")
            return 0
        except (OSError, ValueError) as exc:
            print(f"ERROR INIT {args.directory}: {exc}")
            return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
