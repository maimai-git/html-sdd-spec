"""验证唯一的 Vue 页面：目录、排期、参数、表名、转义及关联跳转。"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.parse import unquote

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def main():
    cli = os.environ.get("HTML_SDD_CLI", "html-sdd")
    spec = json.loads((ROOT / "tests/fixtures/目录筛选/方案事实源.json").read_text(encoding="utf-8"))
    spec["metadata"]["status"] = "开发中"
    for config in spec["configs"]:
        config.pop("source", None)
    attack = "<script>window.sddInjected=true</script>"
    spec["tables"][0]["displayName"] = "<文件&图>"
    spec["apis"][3]["path"] = '/api/<script>&"quote/' + "segment/" * 20 + "native-find-tail"
    spec["definitions"] = {
        "fields": {"身份": {"field": "Authorization", "location": "header", "type": "string",
                          "required": "是", "description": "调用身份", "example": "Bearer <token>"}},
        "rules": {"隔离": ["只读本人数据", "企业校验当前成员"]},
    }
    spec["apis"][0]["request"] = [{"$ref": "#/definitions/fields/身份"}, {"name": "folder_id"}]
    spec["apis"][0]["rules"] = [{"$ref": "#/definitions/rules/隔离"}]
    spec["apis"][1]["request"] = [
        {"name": "long_parameter_identifier", "location": "query", "type": "array<string>", "changeStatus": "修改"},
        {"name": "unchanged", "location": "query", "type": "string"},
    ]
    spec["tables"][1]["columns"] = [{"name": "status", "type": "text", "changeStatus": "新增"}]
    spec["plans"][0].update(main="文件查询 " + attack, note=attack, start="2026-11-01", end="验收后确认")
    spec["questions"] = [{"id": "Q-XSS", "question": attack, "status": "待确认", "requiresUserDecision": True}]

    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as playwright:
        source = Path(tmp) / "方案事实源.json"
        output = Path(tmp) / "方案对齐.html"
        source.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        subprocess.run([cli, "render", str(source), "--output", str(output)], check=True)
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1500, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(output.as_uri())
        expect(page.get_by_role("navigation", name="方案分类")).to_be_visible()
        expect(page).to_have_title("HTML SDD Spec " + spec["metadata"]["title"])

        def tab(mode):
            page.locator(f'[data-mode="{mode}"]').click()

        def ids():
            return page.locator("aside [data-record]").evaluate_all("rows=>rows.map(row=>row.dataset.record)")

        def apply(status="", change=""):
            page.get_by_label("本期开发状态", exact=True).select_option(status)
            page.get_by_label("变更类型", exact=True).select_option(change)

        header = page.locator("header .top .badge")
        color = header.evaluate("node=>getComputedStyle(node).color")
        for mode in ("requirements", "apis", "existingInterfaces", "tables", "architecture", "configs", "plans"):
            tab(mode)
            expect(header).to_have_text("开发中")
            assert header.evaluate("node=>getComputedStyle(node).color") == color

        tab("apis")
        for status, change, expected in (
            ("", "", ["API-001", "API-002", "API-003", "API-004"]),
            ("已完成", "新增接口", ["API-001"]),
            ("部分完成", "存量接口变更", ["API-002"]),
            ("未完成", "", ["API-002", "API-003"]),
            ("待核实", "新增接口", ["API-004"]),
            ("已完成", "存量接口复用", []),
        ):
            apply(status, change)
            assert ids() == expected
            expect(page.locator("aside > small")).to_have_text(f"{len(expected)} / 4 项")
            if not expected:
                expect(page.locator("main .empty")).to_have_text("没有符合条件的条目")
                expect(page.locator("main article")).to_have_count(0)
                expect(page.locator("aside .record.active")).to_have_count(0)

        apply("部分完成", "存量接口变更")
        expect(page.locator("article .head .tags")).to_contain_text("本期开发 · 部分完成")
        expect(page.locator("article .head .tags")).to_contain_text("部署/验证")
        expect(page.locator(".field-change-changed")).to_have_text("修改")
        page.get_by_label("只看变更", exact=True).check()
        expect(page.locator(".request-params tbody tr")).to_have_count(1)
        scroll = page.get_by_role("region", name="请求参数", exact=True)
        assert scroll.evaluate("node=>node.scrollWidth>node.clientWidth")
        assert scroll.locator("td").first.evaluate("node=>getComputedStyle(node).whiteSpace") == "nowrap"
        expect(page.locator('input[type="range"]')).to_have_count(0)
        tab("tables")
        expect(page.get_by_label("本期开发状态", exact=True)).to_have_value("")
        apply("未开发", "存量表变更")
        assert ids() == ["DATA-002"]
        expect(page.get_by_role("table", name="数据表字段状态")).to_contain_text("status")
        expect(page.locator(".field-change-added")).to_have_text("新增")
        tab("apis")
        expect(page.get_by_label("本期开发状态", exact=True)).to_have_value("部分完成")
        tab("tables")
        expect(page.get_by_label("本期开发状态", exact=True)).to_have_value("未开发")
        apply()
        expect(page.locator("article h1")).to_have_text("demo_file_1（<文件&图>）")
        expect(page.locator("article pre").first).to_have_text(spec["tables"][0]["ddl"])

        tab("apis")
        apply()
        expect(page.locator(".request-params tbody tr td:first-child")).to_have_text(["Authorization", "folder_id"])
        expect(page.locator('.param-scroll[aria-label="返回参数"] th')).to_have_text(["字段", "类型", "必填", "说明", "示例"])
        examples = page.locator("article details").filter(has=page.locator("pre"))
        assert examples.evaluate_all("rows=>rows.every(row=>row.open)")
        examples.first.locator("summary").click()
        assert not examples.first.evaluate("node=>node.open")
        rules = page.locator("article details").filter(has=page.locator(".api-rules"))
        assert not rules.evaluate("node=>node.open")
        rules.locator("summary").click()
        expect(rules.locator("li")).to_have_text(["只读本人数据", "企业校验当前成员"])
        native = page.evaluate("""()=>{
            window.getSelection().removeAllRanges();
            const found=window.find('native-find-tail',false,false,true,false,false,false);
            const node=window.getSelection().anchorNode;
            return {found,id:node?.parentElement?.closest('[data-record]')?.dataset.record};
        }""")
        assert native == {"found": True, "id": "API-004"}, native
        page.locator('[data-record="API-004"]').click()
        expect(page.locator("article .head .path")).to_contain_text(spec["apis"][3]["path"])
        expect(page.locator("article script")).to_have_count(0)

        tab("existingInterfaces")
        expect(page.get_by_label("本期开发状态", exact=True)).to_have_count(0)
        assert ids() == ["API-BASELINE"]
        tab("plans")
        expect(page.locator("aside")).to_have_count(0)
        expect(page.locator(".plan thead th")).to_have_text(["序号", "优先级", "模块 / 任务", "关联需求", "执行人", "状态", "进展与备注"])
        assert page.locator("tr[data-plan]").evaluate_all("rows=>rows.map(row=>Number(row.cells[0].textContent))") == [2, 8, 5, 1]
        page.get_by_label("按模块分组", exact=True).uncheck()
        assert page.locator("tr[data-plan]").evaluate_all("rows=>rows.map(row=>Number(row.cells[0].textContent))") == [2, 5, 8, 1]
        page.get_by_label("排期排序", exact=True).select_option("sequence")
        assert page.locator("tr[data-plan]").evaluate_all("rows=>rows.map(row=>Number(row.cells[0].textContent))") == [1, 2, 5, 8]
        row = page.locator('[data-plan="PLAN-001"]')
        expect(row).not_to_contain_text("2026-11-01")
        row.locator("button").first.click()
        expect(page.locator(".plan-expanded")).to_contain_text("2026-11-01")
        expect(page.locator(".plan-expanded")).to_contain_text("验收后确认")
        expect(page.locator(".plan-expanded")).to_contain_text(attack)
        expect(page.locator(".plan-expanded script")).to_have_count(0)
        row.get_by_role("button", name=spec["requirements"][0]["title"], exact=True).click()
        expect(page.locator("article h1")).to_have_text(spec["requirements"][0]["title"])
        todo = page.locator('[data-summary="todo"]')
        todo.locator(":scope > summary").click()
        questions = todo.locator('[data-summary="openQuestions"]')
        questions.locator("summary").click()
        expect(questions).to_contain_text(attack)
        expect(questions).to_contain_text("等用户决定")
        expect(questions.locator("script")).to_have_count(0)
        assert page.evaluate("window.sddInjected === undefined")
        tab("configs")
        expect(page.locator("article")).not_to_contain_text("只展示需要填写或执行的文本")

        # Use the published example with its real directory structure and release files.
        (Path(tmp) / ".git").mkdir()
        release_dir = Path(tmp) / "examples" / "订单筛选发布"
        shutil.copytree(ROOT / "examples/订单筛选发布", release_dir)
        release_html = release_dir / "方案对齐.html"
        subprocess.run([cli, "render", str(release_dir / "方案事实源.json"), "--output", str(release_html)], check=True)
        page.goto(release_html.as_uri())
        tab("configs")
        release_spec = json.loads((release_dir / "方案事实源.json").read_text(encoding="utf-8"))
        for config in release_spec["configs"]:
            page.locator(f'[data-record="{config["id"]}"]').click()
            link = page.locator("article a[target='_blank']")
            expect(link).to_have_text(config["source"])
            href = link.get_attribute("href")
            assert not href.startswith(("/", "http:", "https:", "file:"))
            target = (release_dir / unquote(href)).resolve()
            # Chromium may download these extensions on Linux instead of firing load.
            # Verify the actual file navigation without requiring an OS-specific viewer.
            with page.context.expect_event("request", predicate=lambda request: request.url == target.as_uri()) as navigation:
                with page.expect_popup() as popup:
                    link.click()
            opened = popup.value
            assert navigation.value.resource_type == "document"
            assert "orders" in target.read_text(encoding="utf-8").lower()
            if not opened.is_closed():
                opened.close()
        assert errors == [], errors
        browser.close()
        print("PASS Vue：目录筛选、状态、原生查找、公共参数、示例、排期、跳转和文本转义")


if __name__ == "__main__":
    main()
