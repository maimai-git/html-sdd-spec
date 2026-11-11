import copy
import json
import unittest
from pathlib import Path

from html_sdd.diffing import diff_specs

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = json.loads((ROOT / "examples/asset-library/sdd.json").read_text())


class DiffTest(unittest.TestCase):
    def test_reports_added_removed_and_changed_records(self):
        before = copy.deepcopy(EXAMPLE)
        after = copy.deepcopy(EXAMPLE)
        after["requirements"].append({
            "id": "REQ-099",
            "group": "新增模块",
            "title": "新需求",
            "summary": "新增",
            "status": "待拆分",
            "acceptance": []
        })
        after["apis"][0]["summary"] = "接口说明已更新"
        after["tables"].pop()
        changes = diff_specs(before, after)
        kinds = {(change.kind, change.section, change.record_id) for change in changes}
        self.assertIn(("added", "requirements", "REQ-099"), kinds)
        self.assertIn(("changed", "apis", EXAMPLE["apis"][0]["id"]), kinds)
        self.assertIn(("removed", "tables", EXAMPLE["tables"][-1]["id"]), kinds)

    def test_diff_covers_agent_evidence_questions_and_root_changes(self):
        before = copy.deepcopy(EXAMPLE)
        after = copy.deepcopy(EXAMPLE)
        after["agents"][0]["name"] = "负责人（新）"
        after["evidence"].append({"id": "EVID-099", "kind": "test", "label": "新增证据", "source": "tests", "status": "已检查"})
        after["questions"].append({"id": "Q-099", "question": "是否需要灰度？", "status": "待确认"})
        after["baseline"]["commit"] = "new-commit"
        changes = diff_specs(before, after)
        sections = {(change.section, change.record_id) for change in changes}
        self.assertIn(("agents", EXAMPLE["agents"][0]["id"]), sections)
        self.assertIn(("evidence", "EVID-099"), sections)
        self.assertIn(("questions", "Q-099"), sections)
        self.assertIn(("baseline", "baseline"), sections)
        baseline_change = next(change for change in changes if change.section == "baseline")
        self.assertEqual(EXAMPLE["baseline"]["branch"], baseline_change.before["branch"])
        self.assertEqual("new-commit", baseline_change.after["commit"])


if __name__ == "__main__":
    unittest.main()
