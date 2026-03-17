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

def process_pokemoncenter_online(model):
    last_data, input_data = load_common_data(model)

    response = requests_get(input_data['api_url'])
    soup = parse_html(response["text"])

    today_date = get_today_date()
    today = today_date['local']["date_jp_padded"]

    items = soup.select("ul.noticeUl li")

    for item in items:
        time_tag = item.select_one("span.time")
        title_tag = item.select_one("span.ttl")
        link_tag = item.find("a")

        if not (time_tag and title_tag and link_tag):
            continue

        date_str = time_tag.text.strip()
        if date_str != today:
            continue

        title = title_tag.text.strip()
        url = link_tag['href']
        if not url.startswith("http"):
            url = urlparse(input_data['api_url']).scheme + "://" + urlparse(input_data['api_url']).netloc + url

        entry_id = {
            'date': date_str,
            'title': title,
            'url': url
        }

        if last_data == entry_id:
            logging.info("既に送信済みのエントリーです。")
            return

        embed = {
            "title": title,
            "url": url,
            "image": {"url": "https://www.pokemoncenter-online.com/on/demandware.static/-/Sites-POL-Library/default/dw2264f023/images/og_img/OGP_banner_B.jpg"}
        }

        payload = {"embeds": [embed]}
        send_discord_notification(input_data['webhook_url'], payload)
        logging.info("Discord に通知を送信しました。")

        save_last_data(model, entry_id)
        return

    logging.info("本日の日付に一致する未送信のお知らせはありません。")

# メイン処理
def main():
    try:
        process_pokemoncenter_online("pokemoncenter_online")
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")

if __name__ == '__main__':
    main()
