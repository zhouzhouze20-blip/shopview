"""Hourly server collector. Writes private staging data, not published sales.

The browser stays open between runs. Credentials are used only for initial login
or an expired session; they are neither logged nor saved in browser storage files.
Run --once on the target host before enabling a long-running service.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import fcntl
import json
import os
from pathlib import Path
import re
import time
from zoneinfo import ZoneInfo

from services.fungkids_retail_import import parse_export, import_snapshot

REPORT_URL = "https://app.fungkids.com.cn/#/1769376695904768/130041"
INTERVAL_SECONDS = 3600


def query_window(now=None):
    now = now or datetime.now(ZoneInfo("Asia/Shanghai"))
    if now.tzinfo is None:
        raise ValueError("查询时间必须包含时区")
    end = now.astimezone(ZoneInfo("Asia/Shanghai")).date()
    return end - timedelta(days=1), end


def collect(page, root: Path):
    from playwright.sync_api import expect

    start, end = query_window()
    if "#/1769376695904768/130041" not in page.url:
        page.goto(REPORT_URL, wait_until="domcontentloaded")
    # Wait for either the report or the login form, not a fixed loading delay.
    report = page.get_by_role("button", name="重置", exact=True)
    username = page.get_by_placeholder("请输入账户名", exact=True)
    expect(report.or_(username).first).to_be_visible(timeout=60000)
    if username.is_visible():
        user, password = os.getenv("FUNGKIDS_USERNAME"), os.getenv("FUNGKIDS_PASSWORD")
        if not user or not password:
            raise RuntimeError("缺少服务器登录凭据")
        username.fill(user)
        page.get_by_placeholder("请输入密码", exact=True).fill(password)
        page.get_by_role("button", name="登录", exact=True).click()
        page.wait_for_url(lambda url: "#/login" not in url, timeout=60000)
        page.goto(REPORT_URL, wait_until="domcontentloaded")
    expect(report).to_be_visible(timeout=60000)
    report.click()
    start_input = page.get_by_placeholder("开始日期", exact=True).first
    end_input = page.get_by_placeholder("结束日期", exact=True).first
    start_input.fill(start.isoformat())
    end_input.fill(end.isoformat())
    end_input.press("Enter")
    expect(start_input).to_have_value(start.isoformat())
    expect(end_input).to_have_value(end.isoformat())
    query = page.get_by_role("button", name="查询", exact=True).last
    query.click()
    # Fail closed if completion cannot be observed; never export a stale grid.
    busy = page.get_by_role("button", name=re.compile("查询")).last
    expect(busy).to_be_disabled(timeout=10000)
    expect(query).to_be_enabled(timeout=120000)
    count_text = page.get_by_text(re.compile(r"共\s*\d+\s*条记录")).last.inner_text()
    match = re.search(r"共\s*(\d+)\s*条记录", count_text)
    if not match:
        raise RuntimeError("无法核对网页记录数")
    count = int(match.group(1))
    if count == 0:
        raise RuntimeError("查询返回空报表，保留既有数据并等待核查")
    with page.expect_download(timeout=120000) as event:
        page.get_by_role("button", name="导出", exact=True).last.click()
    download = event.value
    if download.failure():
        raise RuntimeError("报表下载失败")
    stamp = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S-%f")
    destination = root / "exports" / f"retail-{start}-{end}-{stamp}.xlsx"
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    download.save_as(destination)
    export = parse_export(destination, start=start, end=end)
    if len(export.lines) != count:
        raise ValueError("下载明细数与网页记录数不一致")
    result = import_snapshot(root / "staging.sqlite3", export)
    result["completed_at"] = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    root = args.data_dir.resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    from playwright.sync_api import sync_playwright

    with (root / "collector.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, chromium_sandbox=True)
            context = browser.new_context(accept_downloads=True, timezone_id="Asia/Shanghai")
            page = context.new_page()
            try:
                while True:
                    began = time.monotonic()
                    try:
                        result = collect(page, root)
                        print(json.dumps({"status": "staged", **result}, ensure_ascii=False), flush=True)
                        status = {"status": "staged", **result}
                    except Exception as exc:
                        # Third-party error messages can include page data or input values.
                        status = {"status": "failed", "error_type": type(exc).__name__,
                                  "failed_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()}
                        print(json.dumps(status), flush=True)
                    temporary = root / "status.tmp"
                    temporary.write_text(json.dumps(status, ensure_ascii=False), encoding="utf-8")
                    temporary.replace(root / "status.json")
                    if args.once:
                        if status["status"] == "failed":
                            raise SystemExit(1)
                        return
                    time.sleep(max(1, INTERVAL_SECONDS - (time.monotonic() - began)))
            finally:
                browser.close()


if __name__ == "__main__":
    main()
