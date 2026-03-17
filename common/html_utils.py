import os
import json
from .logging import logging
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def parse_html(html: str):
    return BeautifulSoup(html, "html.parser")

def fetch_json_from_url(url: str, headers: dict = None, state_file: str = None) -> dict:
    with sync_playwright() as p:
        if os.path.exists(state_file):
            context = p.chromium.launch_persistent_context(
                user_data_dir="./user_data",
                headless=True,
                locale="ja-JP",
                extra_http_headers=headers or {}
            )
        else:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                locale="ja-JP",
                extra_http_headers=headers or {}
            )

        page = context.new_page()
        page.goto(url, timeout=60000)

        try:
            json_data = page.evaluate("() => JSON.parse(document.body.innerText)")
        except Exception as e:
            raise RuntimeError(f"JSONの解析に失敗しました: {e}")

        # セッション状態を保存
        try:
            temp_state = context.storage_state()
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(temp_state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.info(f"セッション状態の保存に失敗しました: {e}")

        context.close()

    return json_data
