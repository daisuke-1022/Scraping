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

def is_today(unix_ms):
    try:
        input_date = datetime.fromtimestamp(int(unix_ms) / 1000).date()
        today_date = get_today_date()
        return input_date == today_date["local"]["date_object"]
    except Exception as e:
        logging.error(f"日付判定エラー: {unix_ms}, {e}")
        return False

def extract_new_entries(current_data):
    current_entries = current_data["data"]["blogPosts"]
    new_entries = []

    for entry in current_entries:
        start_date = entry["status"]["publishedAtTimestamp"]
        if is_today(start_date):
            new_entries.append(entry)

    return new_entries

def notify_discord(input_data, entries):
    sent_notifications = set()
    seen_titles = set()
    embeds = []

    for entry in entries:
        title = entry["fields"]["meta"]["title"]
        image_url = entry["fields"]["meta"].get("image", {}).get("url")

        embed = {
            "title": entry["fields"]["meta"]["title"],
            "url": f"https://pokemongo.com{entry['url']}",
            "color": 0x0494EA
        }
        if image_url:
            embed["image"] = {"url": image_url}

        embeds.append(embed)

        seen_titles.add(title)
        sent_notifications.add(title)

    if not embeds:
        logging.info("送信対象の新規embedはありません。")
        return

    for chunk in chunk_list(embeds, 10):
        content = f"<@&{input_data['role_id']}>"
        payload = {"content": content, "embeds": chunk}
        send_discord_notification(input_data['webhook_url'], payload)

def get_entry_ids(entries):
    ids = set()
    for entry in entries:
        entry_id = entry.get("id") or entry.get("url")
        if entry_id:
            ids.add(entry_id)
    return ids

def process_go_news(model):
    last_data, input_data = load_common_data(model)
    headers = {
        "Accept-Language": "ja",
        "Content-Type": "application/json",
        "Cache-Control": "no-cache"
    }
    payload_json = {"locale": "ja"}

    response = requests_post(input_data['api_url'], headers=headers, json=payload_json)
    current_data = response["json"]

    new_entries = extract_new_entries(current_data)

    if not new_entries:
        return

    new_entry_ids = get_entry_ids(new_entries)
    last_entry_ids = get_entry_ids(last_data)

    if new_entry_ids != last_entry_ids:
        diff_ids = new_entry_ids - last_entry_ids
        diff_entries = [e for e in new_entries if (e.get("id") or e.get("url")) in diff_ids]
        logging.info(f"{model}: 新しい更新があります。({len(diff_entries)}件)")
        notify_discord(input_data, diff_entries)
        save_last_data(model, new_entries)
    else:
        logging.info(f"{model}: 更新はありません。")

def main():
    try:
        process_go_news('go_news_jp')
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
