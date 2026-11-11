from __future__ import annotations

import base64
import gzip
import json
from pathlib import Path
from typing import Any

PLACEHOLDER = "__HTML_SDD_SPEC_GZIP_BASE64__"


def render_spec(spec: dict[str, Any], template_path: Path) -> str:
    template = Path(template_path).read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise ValueError(f"template must contain {PLACEHOLDER}")
    payload = json.dumps(spec, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")
    compressed = gzip.compress(payload.encode("utf-8"), compresslevel=9, mtime=0)
    encoded = base64.b64encode(compressed).decode("ascii")
    return template.replace(PLACEHOLDER, encoded, 1)
