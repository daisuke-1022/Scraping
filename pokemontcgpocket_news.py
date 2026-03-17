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

# 指定モデルから本日分の新着エントリを取得（重複除外）
def get_new_entries(last_data, input_data):
    response = requests_get(input_data['api_url'])
    current_data = response["json"]
    today_date = get_today_date()

    titles_in_last = [d['start_datetime'] for d in last_data] if last_data else []

    new_entries = []

    for entry in current_data['results']:
        start_date_str = entry.get('start_datetime', "")[:10]
        try:
            input_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            if input_date == today_date["local"]["date_object"]:
                if entry['start_datetime'] not in titles_in_last:
                    new_entries.append(entry)
        except ValueError:
            logging.warning(f"日付の解析に失敗しました: {start_date_str}")
            continue

    return new_entries

# ニュースのDiscord通知を処理
def process_tcgpocket_news_jp(model):
    last_data, input_data = load_common_data(model)
    new_entries = get_new_entries(last_data, input_data)

    if not new_entries:
        logging.info(f"[{model}] 新しいニュースはありません。")
        return

    embeds = []
    for entry in new_entries:
        embed = {
            "title": entry['title'],
            "url": f"https://www.pokemontcgpocket.com{entry['uniq']}",
            "color": 0x3C89E0
        }
        if entry.get('img_1'):
            embed["image"] = {"url": entry.get('img_1')}

        embeds.append(embed)

    for chunk in chunk_list(embeds, 10):
        content = f"<@&{input_data['role_id']}>"
        payload = {"content": content, "embeds": chunk}
        send_discord_notification(input_data['webhook_url'], payload)

    save_last_data(model, new_entries)

# ムービーのDiscord通知を処理
def process_tcgpocket_movies_jp(model):
    last_data, input_data = load_common_data(model)
    new_entries = get_new_entries(last_data, input_data)

    if not new_entries:
        logging.info(f"[{model}] 新しいムービーはありません。")
        return

    for entry in new_entries:
        content = (
            f"<@&{input_data['role_id']}>\n"
            f"**{entry['title']}**\n"
            f"{entry['body_link']}"
        )
        payload = {"content": content}
        send_discord_notification(input_data['webhook_url'], payload)

    save_last_data(model, new_entries)

# メイン関数
def main():
    try:
        process_tcgpocket_news_jp('tcgpocket_news_jp')
        process_tcgpocket_movies_jp('tcgpocket_movies_jp')
    except Exception as e:
        logging.exception("処理中にエラーが発生しました。")

if __name__ == "__main__":
    main()
