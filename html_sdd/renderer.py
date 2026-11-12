from __future__ import annotations

import json
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
    return template.replace('__HTML_SDD_STATUSES__',statuses).replace('__HTML_SDD_STATUS_CSS__',status_css()).replace(PLACEHOLDER, payload, 1)
