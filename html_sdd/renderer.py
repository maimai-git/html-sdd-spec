from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path
from typing import Any

from .references import validate_references
from .statuses import registry, status_css, status_issues

PLACEHOLDER = "__HTML_SDD_SPEC_JSON__"


def render_spec(spec: dict[str, Any], template_path: Path) -> str:
    validate_references(spec)
    errors=[item for item in status_issues(spec) if item[0]=='error']
    if errors:raise ValueError(errors[0][2]+': '+errors[0][3])
    template = Path(template_path).read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise ValueError(f"template must contain {PLACEHOLDER}")
    payload = json.dumps(spec, ensure_ascii=False, separators=(",", ":"))
    # Escape HTML-sensitive characters while keeping the decoded JSON unchanged.
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    statuses=json.dumps(registry(),ensure_ascii=False,separators=(',',':'))
    metadata=spec.get('metadata',{})
    title=metadata.get('title') if isinstance(metadata,dict) else None
    title=title.strip() if isinstance(title,str) and title.strip() else '需求方案'
    document_title = f"HTML SDD Spec {title}"
    replacements={PLACEHOLDER:payload,'__HTML_SDD_DOCUMENT_TITLE__':escape(document_title),'__HTML_SDD_STATUSES__':statuses,'__HTML_SDD_STATUS_CSS__':status_css()}
    # Insert each value once, without interpreting placeholder-like text inside user content.
    return re.sub('|'.join(re.escape(key) for key in replacements),lambda match:replacements[match.group()],template)
