"""Verify the installed CLI and the rendered Vue page report the same work."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def render(cli, directory, name, spec):
    source = directory / f"{name}.json"
    source.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    html = directory / f"{name}.html"
    subprocess.run([cli, "render", str(source), "--output", str(html)], check=True)
    summary = json.loads(subprocess.check_output([cli, "summary", str(source), "--json"]))
    return html.as_uri(), summary


def main():
    cli = os.environ.get("HTML_SDD_CLI", "html-sdd")
    spec = json.loads((ROOT / "examples/订单状态筛选/方案事实源.json").read_text(encoding="utf-8"))
    spec["questions"] = [
        {"id": "Q-OPEN", "question": "是否支持取消订单？", "status": "待确认", "requiresUserDecision": True},
        {"id": "Q-CLOSED", "question": "列表支持分页吗？", "status": "已解决"},
        {"id": "Q-CANCELLED", "question": "旧问题", "status": "待确认", "state": "cancelled"},
    ]
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as playwright:
        directory = Path(tmp)
        source_url, summary = render(cli, directory, "ready", spec)
        browser = playwright.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(source_url)
        expect(page.get_by_text("编码条件 · 可开始", exact=True)).to_be_visible()
        todo = page.locator('[data-summary="todo"]')
        todo.locator(":scope > summary").click()
        questions = todo.locator('[data-summary="openQuestions"]')
        questions.locator("summary").click()
        expect(questions.get_by_text("等用户决定", exact=False)).to_be_visible()
        assert [item["id"] for item in summary["openQuestions"]] == ["Q-OPEN"]
        assert questions.locator("li").evaluate_all("(rows) => rows.map(row => row.dataset.id)") == ["Q-OPEN"]
        delivery = todo.locator('[data-summary="deliveryGaps"]')
        delivery.locator("summary").click()
        assert [item["id"] for item in summary["deliveryGaps"]] == ["API-001"]
        expect(delivery.locator('[data-id="API-001"]')).to_contain_text("待部署")

        spec["requirements"] = []
        invalid_url, invalid_summary = render(cli, directory, "invalid", spec)
        assert invalid_summary["codingReady"] is False
        page.goto(invalid_url)
        readiness = page.get_by_text("编码条件 · 待确认", exact=True)
        expect(readiness).to_be_visible()
        readiness.click()
        expect(page.get_by_text("整单可编码至少需要一条未取消的需求", exact=False)).to_be_visible()
        browser.close()
        assert not errors, errors


if __name__ == "__main__":
    main()
