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
        title = entry['title']
        if title not in seen_titles and title not in sent_notifications:
            unique_entries.append(entry)
            seen_titles.add(title)
            sent_notifications.add(title)

    return unique_entries

# 指定されたモデルのデータを取得して更新をチェックする
def process_updates(model):
    sent_notifications= set()
    last_data, input_data = load_common_data(model)
    today_date = get_today_date()
    response = requests_get(input_data['api_url'])
    current_data = response["json"]

    if not current_data or 'results' not in current_data:
        return

    # 新着エントリの抽出
    new_entries = []
    for entry in current_data['results']:
        if entry.get('start_date') == today_date["local"]["date_dot_padded"]:
            new_entries.append(entry)

    if new_entries != last_data:
        logging.info(f"{model} に更新があります。")
        save_last_data(model, new_entries)

        unique_entries = get_unique_entries(model, new_entries, sent_notifications)
        logging.info(f"{model} の一意エントリ数: {len(unique_entries)}")

        embeds = []
        for entry in unique_entries:
            embed = {
                "title": entry['title'],
                "url": f"https://www.pokemon.jp{entry['uniq']}",
                "color": 0xFFCC00
            }
            if entry.get('img_1'):
                embed["image"] = {"url": entry.get('img_1')}
                
            embeds.append(embed)

            for chunk in chunk_list(embeds, 10):
                payload = {"embeds": chunk}
                send_discord_notification(input_data['webhook_url'], payload)

    else:
        logging.info(f"{model} に更新がありません。")

# メイン処理
def main():
    try:
        process_updates("pokemonpdc_info")
        process_updates("pokemonpdc_look")
        process_updates("pokemonpdc_play")          
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
