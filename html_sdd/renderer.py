from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path
from typing import Any, Optional

from .diffing import diff_specs

from .release_check import release_path_records
from .references import field_change_errors, validate_references
from .statuses import registry, status_css, status_issues
from .summary import build_page_summary

PLACEHOLDER = "__HTML_SDD_SPEC_JSON__"


def _script_data(value: Any) -> str:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


def render_spec(
    spec: dict[str, Any], template_path: Path, *, baseline: Optional[dict] = None,
    source_path: Optional[Path] = None, output_path: Optional[Path] = None,
) -> str:
    validate_references(spec)
    invalid = next(field_change_errors(spec), None)
    if invalid is not None:
        raise ValueError(f"{invalid}: 字段变更状态只能为新增、修改或删除")
    errors=[item for item in status_issues(spec) if item[0]=='error']
    if errors:raise ValueError(errors[0][2]+': '+errors[0][3])
    template = Path(template_path).read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise ValueError(f"template must contain {PLACEHOLDER}")
    rendered_spec, release_paths = release_path_records(spec, source_path, output_path)
    payload = _script_data(rendered_spec)
    field_diff = {}
    if baseline is not None:
        for change in diff_specs(baseline, spec):
            if change.after is None:
                continue
            fields = change.fields
            if fields or change.ddl_changed_without_columns:
                field_diff.setdefault(change.section, {})[change.record_id] = {
                    "rows": fields, "ddlOnly": change.ddl_changed_without_columns,
                }
    statuses=json.dumps(registry(),ensure_ascii=False,separators=(',',':'))
    metadata=spec.get('metadata',{})
    title=metadata.get('title') if isinstance(metadata,dict) else None
    title=title.strip() if isinstance(title,str) and title.strip() else '需求方案'
    document_title = f"HTML SDD Spec {title}"
    replacements={PLACEHOLDER:payload,'__HTML_SDD_FIELD_DIFF__':_script_data(field_diff),'__HTML_SDD_DOCUMENT_TITLE__':escape(document_title),'__HTML_SDD_STATUSES__':statuses,'__HTML_SDD_STATUS_CSS__':status_css()}
    replacements["__HTML_SDD_RELEASE_PATHS__"] = _script_data(release_paths)
    if "__HTML_SDD_SUMMARY__" in template:
        replacements["__HTML_SDD_SUMMARY__"] = _script_data(build_page_summary(spec))
    # Insert each value once, without interpreting placeholder-like text inside user content.
    return re.sub('|'.join(re.escape(key) for key in replacements),lambda match:replacements[match.group()],template)
