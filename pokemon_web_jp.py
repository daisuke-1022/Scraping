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

# 通知済みでない一意なエントリを取得する
def get_unique_entries(model, new_entries, sent_notifications):
    seen_titles = set()
    unique_entries = []

    for entry in new_entries:
        title = entry['event_title'] if model == "pokemon_calendar" else entry['title']
        if title not in seen_titles and title not in sent_notifications:
            unique_entries.append(entry)
            seen_titles.add(title)
            sent_notifications.add(title)

    return unique_entries

# embedを構築（pokemon_movie以外用）
def build_discord_embeds(model, entries):
    embeds = []
    for entry in entries:
        title = entry['event_title'] if model == "pokemon_calendar" else entry['title']
        embed = {
            "title": title,
            "url": entry['full_uniq'],
            "color": 0xFFCC00
        }
        if entry.get('img_1'):
            embed["image"] = {"url": entry.get('img_1')}
            
        embeds.append(embed)
    return embeds

# 指定されたモデルのデータを取得して更新をチェックする
def process_updates(model):
    sent_notifications = set()
    last_data, input_data = load_common_data(model)
    today_date = get_today_date()
    response = requests_get(input_data['api_url'])
    current_data = response["json"]

    if not current_data or 'results' not in current_data:
        return

    if model == "pokemon_calendar":
        new_entries = [entry for entry in current_data['results']
                       if entry.get('event_date_start') == today_date["local"]["date_dash_padded"]]
    else:
        new_entries = [entry for entry in current_data['results'] if entry.get('new') == 1]

    if new_entries != last_data:
        logging.info(f"{model} に更新があります。")
        save_last_data(model, new_entries)

        unique_entries = get_unique_entries(model, new_entries, sent_notifications)
        logging.info(f"{model} の一意エントリ数: {len(unique_entries)}")

        if not unique_entries:
            return

        if model == "pokemon_movie":
            content = f"<@&{input_data['role_id']}>"
            payload = {"content": content}
            send_discord_notification(input_data['webhook_url'], payload)

            for entry in unique_entries:
                content = (
                    f"**{entry['title']}**\n"
                    f"{entry['body_link']}"
                )
                payload = {"content": content}
                send_discord_notification(input_data['webhook_url'], payload)

        else:
            chunks = list(chunk_list(unique_entries, 10))
            for idx, chunk in enumerate(chunks):
                content = ""
                if idx == 0 and model != "pokemon_calendar":
                    content = f"<@&{input_data['role_id']}>"

                embeds = build_discord_embeds(model, chunk)
                payload = {"content": content, "embeds": embeds}
                send_discord_notification(input_data['webhook_url'], payload)
    else:
        logging.info(f"{model} に更新がありません。")

# メイン処理
def main():
    try:
        process_updates("pokemon_info_jp")
        process_updates("pokemon_goods")
        process_updates("pokemon_movie")
        process_updates("pokemon_calendar")            
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
