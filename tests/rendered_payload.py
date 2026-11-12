import json
import re


def decode_html_payload(html: str) -> dict:
    match = re.search(r'<script id="html-sdd-spec" type="application/json">(.*?)</script>', html, re.DOTALL)
    if match is None:
        raise AssertionError("generated HTML has no plain SDD JSON payload")
    return json.loads(match.group(1))
