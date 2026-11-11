# HTML SDD payload compression spike

1. Add a renderer regression test that decodes the generated gzip/Base64 payload and compares it with the JSON source.
2. Compress only the embedded payload; keep the readable JSON source unchanged and the generated HTML self-contained.
3. Show a readable error if the browser cannot decompress the payload.
4. Run Python tests, JavaScript syntax checks, compare file sizes, and open the generated HTML directly from `file://` in Edge.
