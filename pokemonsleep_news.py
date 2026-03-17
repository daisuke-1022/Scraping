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

# HTMLから今日の日付のニュースを探して、タイトル、URL、画像URLを抽出します
def parse_news(input_data):
    news_items = []
    today_date = get_today_date()
    response = requests_get(input_data['api_url'])
    soup = parse_html(response["text"])
    list_items = soup.find_all('li', class_='a_fadein_1 is_b2t')
    
    for news_item in list_items:
        date_tag = news_item.find('time')
        if date_tag and date_tag['datetime'] == today_date["local"]["date_slash_padded"]:
            title = news_item.find('p', class_='banner_2__title').text.strip()
            url = news_item.find('a')['href']
            if not url.startswith('http'):
                url = f"https://www.pokemonsleep.net{url}"

            img_tag = news_item.select_one('.banner_2__eyecatch img')
            image_url = img_tag['src'] if img_tag else ''
            if image_url and not image_url.startswith(('http://', 'https://')):
                image_url = f"https://www.pokemonsleep.net{image_url}"

            news_items.append({'title': title, 'url': url, "image_url": image_url})

    return news_items  # 複数のアイテムを返す

def process_sleep_news(model):
    last_data, input_data = load_common_data(model)
    new_items = parse_news(input_data)
    if not new_items:
        logging.info("今日の日付の記事は見つかりませんでした。")
        return

    # 通知がまだのアイテムだけ抽出
    diff_items = [
        item for item in new_items
        if not any(last['title'] == item['title'] for last in last_data)
    ]

    if not diff_items:
        logging.info("すべての記事はすでに通知済みです。処理を終了します。")
        return

    # embedを作成してまとめる
    embeds = []
    for item in diff_items:
        embed = {
            "title": item['title'],
            "url": item['url'],
            "color": 0x1F3A93
        }
        if item.get("image_url"):
            embed["image"] = {"url": item.get("image_url")}

        embeds.append(embed)

    # 10件ずつに分けて送信
    for chunk in chunk_list(embeds, 10):
        content = f"<@&{input_data['role_id']}>"
        payload = {"content": content, "embeds": chunk}
        send_discord_notification(input_data['webhook_url'], payload)

    # 通知対象を保存（差分または全体）
    save_last_data(model, new_items)

def main():
    try:
        process_sleep_news("sleep_news_jp")
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
