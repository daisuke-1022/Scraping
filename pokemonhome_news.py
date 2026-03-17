# coding: UTF-8
import re
from time import mktime
from html import unescape
from urllib.parse import urlparse, urlencode, urlunparse, parse_qs
from datetime import datetime, timezone, timedelta
from discord_webhook import DiscordEmbed, DiscordWebhook, AsyncDiscordWebhook
from common import (
    get_today_date, load_common_data, save_last_data,
    parse_html, fetch_json_from_url, logging, 
    requests_get, requests_post, requests_patch, feedparser_parse,
    chunk_list, send_discord_notification, send_discord_notification_with_image
)

base_urls = {
    "home_news": "https://news.pokemon-home.com/ja/",
    "home_sv_news": "https://sv-news.pokemon.co.jp/ja/",
    "home_plza_news": "https://plza-news.pokemon-home.com/ja/",
    "home_champions_news": "https://champions-news.pokemon-home.com/ja/",
}

# UNIXタイムスタンプを日付で比較するためのヘルパー関数
def is_today(unix_timestamp):
    try:
        unix_timestamp = int(unix_timestamp)
        input_date = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc).date()
        today_date = get_today_date()
        return input_date == today_date["utc"]["date_object"]
    except ValueError:
        logging.error(f"UNIXタイムスタンプの変換に失敗しました: {unix_timestamp}")
        return False

# 更新をチェックする
def process_home_news(model):
    sent_notifications = set()
    
    last_data, input_data = load_common_data(model)
    
    response = requests_get(input_data['api_url'])
    current_data = response["json"]

    if not current_data:
        logging.info(f"{model}に更新がありません。")
        return

    # 今日の日付のエントリのみ抽出
    new_entries = [entry for entry in current_data['data'] if is_today(entry.get('stAt', 0))]

    if new_entries != last_data:
        logging.info(f"{model}に更新があります。")
        save_last_data(model, new_entries)

        seen_titles = set()
        unique_entries = []
        for entry in new_entries:
            title = entry['title']
            if title not in seen_titles and title not in sent_notifications:
                unique_entries.append(entry)
                seen_titles.add(title)
                sent_notifications.add(title)

        logging.info(f"一意のエントリ: {unique_entries}")

        # --- embedをまとめて10件ずつ送信 ---
        embeds = []
        for entry in unique_entries:
            base_url = base_urls.get(model)

            url = f"{base_url}{entry['link']}"
            image_url = f"{base_url}{entry.get('banner')}" if entry.get('banner') else None

            embed = {
                "title": entry['title'],
                "url": url
            }
            if image_url:
                embed["image"] = {"url": image_url}

            embeds.append(embed)

        for chunk in chunk_list(embeds, 10):
            content = f"<@&{input_data['role_id']}>"
            payload = {"content": content, "embeds": chunk}
            send_discord_notification(input_data['webhook_url'], payload)
    else:
        logging.info(f"{model}に更新がありません。")

def main():
    try:
        process_home_news("home_news")
        process_home_news("home_sv_news")
        process_home_news("home_plza_news")
        process_home_news("home_champions_news")
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
