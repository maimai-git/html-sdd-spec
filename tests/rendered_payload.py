import base64
import gzip
import json
import re


def decode_html_payload(html: str) -> dict:
    match = re.search(r'const specGzipBase64="([A-Za-z0-9+/=]+)";', html)
    if match is None:
        raise AssertionError("generated HTML has no compressed SDD payload")
    return json.loads(gzip.decompress(base64.b64decode(match.group(1))))
