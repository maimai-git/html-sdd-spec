import shutil
import unittest

from tests.test_catalog_filters import fixture
from tests.vue_runtime import run_vue


@unittest.skipUnless(shutil.which("node"), "目录搜索回归需要 Node")
class CatalogSearchTest(unittest.TestCase):
    def test_current_and_existing_api_paths_are_searchable_in_full(self):
        spec=fixture()
        paths=["/api/files/{file_id}", '/api/<script>&"quote', "/api/long/"+"segment/"*20+"native-find-tail"]
        records=[dict(spec["apis"][0],id=f"API-{i}",path=path) for i,path in enumerate(paths)]
        spec["apis"]=records
        spec["existingInterfaces"]=records
        for mode in ("apis","existingInterfaces"):
            with self.subTest(mode=mode):
                result=run_vue(f'mode.value="{mode}";filters[mode.value].query="native-find-tail";return visible.value.map(x=>x.path);',spec)
                self.assertEqual([paths[-1]],result)
                self.assertEqual(paths,run_vue(f'mode.value="{mode}";return visible.value.map(x=>x.path);',spec))

    def test_search_does_not_leak_between_categories(self):
        spec=fixture()
        result=run_vue('filters.apis.query="absent";mode.value="tables";return visible.value.length;',spec)
        self.assertEqual(3,result)


if __name__ == "__main__":
    unittest.main()
