from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .checker import load_spec, validate_spec
from .renderer import render_spec
from .diffing import diff_specs, format_changes
from .scaffold import STANDARD_SDD_DIRECTORY, init_project
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
    render = sub.add_parser("render", help="生成离线 HTML")
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
    if args.command == "check":
        return check_command(args.path, args.as_json)
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
