import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("node"), "模板函数回归需要 Node")
class CatalogSearchTest(unittest.TestCase):
    def render_catalog(self, mode):
        source = (ROOT / "templates/console.html").read_text()
        code = source[source.index("const statusInfo="):source.index("function relatedBlock")]
        esc = "const esc=s=>" + source.split("const esc=s=>", 1)[1].splitlines()[0]
        paths = ["/api/files/{file_id}", '/api/<script>&"quote', "/api/long/" + "segment/" * 20]
        records = [{"id": f"API-{i}", "name": f"接口{i}", "method": "GET", "path": path, "group": "文件"} for i, path in enumerate(paths)]
        from html_sdd.statuses import registry
        prelude = "const statusRegistry="+json.dumps(registry(),ensure_ascii=False)+";\n"+"""
const spec={metadata:{}};
const readiness={}, baseline={}, agents=[], sectionCoverage={};
const questions=[], requirements=[{id:'REQ-1',title:'需求',group:'文件'}];
const apis=RECORDS, existingInterfaces=apis, tables=[], architecture=[], configs=[];
const list=v=>Array.isArray(v)?v:[];
const state={mode:MODE,selectedId:'API-0'};
const nodes={};
const document={querySelectorAll:()=>[],getElementById:id=>(nodes[id]??={innerHTML:'',textContent:'',querySelectorAll:()=>[]})};
""".replace("RECORDS", json.dumps(records)).replace("MODE", json.dumps(mode))
        result = subprocess.run(["node", "-e", prelude + esc + code +
                                 "renderCatalog(); console.log(JSON.stringify(nodes.catalog.innerHTML));"],
                                capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def test_current_and_existing_api_paths_are_visible_for_native_find(self):
        for mode in ("apis", "existingInterfaces"):
            with self.subTest(mode=mode):
                html = self.render_catalog(mode)
                self.assertEqual(3, html.count('class="catalog-path"'))
                self.assertIn("/api/files/{file_id}", html)
                self.assertIn("/api/long/" + "segment/" * 20, html)
                self.assertIn("/api/&lt;script&gt;&amp;&quot;quote", html)
                self.assertNotIn("<script>", html)

    def test_non_api_catalog_does_not_get_empty_path_rows(self):
        self.assertNotIn('class="catalog-path"', self.render_catalog("requirements"))


if __name__ == "__main__":
    unittest.main()
