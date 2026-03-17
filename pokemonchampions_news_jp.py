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

# 日本版の処理（ニュース）
def process_champions_news_jp(model):
    last_data, input_data = load_common_data(model)
    
    response = requests_get(input_data['api_url'])
    current_data = response["json"]
    today_date = get_today_date()
    new_entries = []

    for entry in current_data['news']:
        start_date_str = entry.get('date', "")[:10]
        try:
            input_date = datetime.strptime(start_date_str, "%Y.%m.%d").date()
            if input_date == today_date["local"]["date_object"]:
                new_entries.append(entry)
        except ValueError:
            continue

    unique_entries = []
    if last_data is not None:
        titles_in_last = [d['title'] for d in last_data]
    else:
        titles_in_last = []

    for entry in new_entries:
        if last_data is None or entry['title'] not in titles_in_last:
            unique_entries.append(entry)

    if not unique_entries:
        logging.info(f"{model}: 新しいデータはありません。")
        return

    # --- embedを作成し、10件ずつ送信 ---
    embeds = []
    for entry in unique_entries:
        embed = {
            "title": entry['title'],
            "url": f"https://www.pokemonchampions.jp{entry['url']}",
            "color": 0xF9DB37
        }
        if entry.get('thumbnail'):
            embed["image"] = {"url": f"https://www.pokemonchampions.jp{entry['thumbnail']}"}
        embeds.append(embed)

    for chunk in chunk_list(embeds, 10):
        content = f"<@&{input_data['role_id']}>"
        payload = {"content": content, "embeds": chunk}
        send_discord_notification(input_data['webhook_url'], payload)

    save_last_data(model, new_entries)

def main():
    try:
        process_champions_news_jp('champions_news_jp')
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
