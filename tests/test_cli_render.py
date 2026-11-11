import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.rendered_payload import decode_html_payload

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/asset-library/sdd.json"


class CliRenderTest(unittest.TestCase):
    def test_render_command_writes_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "index.html"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "html_sdd",
                    "render",
                    str(EXAMPLE),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue(output.exists())
            self.assertIn("asset_library_resource", str(decode_html_payload(output.read_text())))


if __name__ == "__main__":
    unittest.main()
