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

def is_today(date_str):
    try:
        input_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        today_date = get_today_date()
        return input_date == today_date["utc"]["date_object"]
    except ValueError:
        logging.error(f"日付変換エラー: {date_str}")
        return False

def extract_new_entries(data):
    entries = data.get("results", [])
    new_entries = []

    for entry in entries:
        start_date = entry.get("start_date", "")
        if is_today(start_date):
            new_entries.append(entry)

    return new_entries

def notify_discord(input_data, entries):
    sent_notifications = set()
    seen_titles = set()
    embeds = []

    for entry in entries:
        title = entry["title"]
        if title in seen_titles or title in sent_notifications:
            continue

        image_url = entry.get('img_1') or "https://www.poke-maze.jp/assets/og/fb.jpg"
        embed = {
            "title": entry['title'],
            "url": entry.get('full_uniq', ''),
            "color": 0xF4A261
        }
        if image_url:
            embed["image"] = {"url": image_url}

        embeds.append(embed)

        seen_titles.add(title)
        sent_notifications.add(title)

    if not embeds:
        logging.info("送信対象の新規embedはありません。")
        return

    # 最大10件ずつに分割して送信
    for chunk in chunk_list(embeds, 10):
        content = f"<@&{input_data['role_id']}>"
        payload = {"content": content, "embeds": chunk}
        send_discord_notification(input_data['webhook_url'], payload)

def process_pokemaze_news_jp(model):
    last_data, input_data = load_common_data(model)
    
    response = requests_get(input_data['api_url'])

    current_data = response["json"]
    new_entries = extract_new_entries(current_data)

    if new_entries != last_data:
        logging.info(f"{model}: 新しい更新があります。")
        save_last_data(model, new_entries)
        notify_discord(input_data, new_entries)
    else:
        logging.info(f"{model}: 更新はありません。")

def main():
    try:
        process_pokemaze_news_jp('pokemaze_news_jp')
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()