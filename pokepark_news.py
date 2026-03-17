# coding: UTF-8
import re
from time import mktime
from html import unescape
from urllib.parse import urlparse, urlencode, urlunparse, parse_qs
from datetime import date, datetime, timezone, timedelta
from discord_webhook import DiscordEmbed, DiscordWebhook, AsyncDiscordWebhook
from common import (
    get_today_date, load_common_data, save_last_data,
    parse_html, fetch_json_from_url, logging, 
    requests_get, requests_post, requests_patch, feedparser_parse,
    chunk_list, send_discord_notification, send_discord_notification_with_image
)

# UNIXタイムスタンプを日付で比較するためのヘルパー関数
def is_today(date_value):
    try:
        input_date = datetime.fromisoformat(date_value).date()
        today_date = get_today_date()
        return input_date == today_date["utc"]["date_object"]
    except ValueError:
        logging.error(f"UNIXタイムスタンプの変換に失敗しました: {date_value}")
        return False

# 更新をチェックする
def process_pokepark_news(model):
    sent_notifications = set()
    
    last_data, input_data = load_common_data(model)
    
    response = requests_get(input_data['api_url'])
    current_data = response["json"]

    if not current_data:
        logging.info(f"{model}に更新がありません。")
        return

    # 今日の日付のエントリのみ抽出
    new_entries = [entry for entry in current_data['announcements'] if is_today(entry.get('displayPeriodFrom'))]

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

        # --- embedをまとめて10件ずつ送信 ---
        embeds = []
        for entry in unique_entries:
            color = 0x3B7F3C
            url = f"https://www.pokepark-kanto.co.jp/ppark/announcement/{entry.get('announcementId')}/detail/index"
            image_url = f"{entry.get('thumbnail')}" if entry.get('thumbnail') else None
            embed = {
                "title": entry['title'],
                "url": url,
                "description": entry["body"],
                "color": color
            }
            if image_url:
                embed["image"] = {"url": image_url}

            embeds.append(embed)

        for chunk in chunk_list(embeds, 10):
            payload = {"embeds": chunk}
            send_discord_notification(input_data['webhook_url'], payload)
    else:
        logging.info(f"{model}に更新がありません。")

def main():
    try:
        process_pokepark_news("pokepark_news")
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
