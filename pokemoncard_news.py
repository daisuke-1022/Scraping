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

# 今日の日付のニュースを抽出する関数
def parse_news(input_data):
    today_date = get_today_date()

    response = requests_get(input_data['api_url'])
    soup = parse_html(response["text"])
    news_section = soup.find('li', {'class': 'KSTabContents_item', 'id': 'newsTab_all'})

    if not news_section:
        logging.info("newsTab_all セクションが見つかりませんでした。")
        return []

    news_items = []
    list_items = news_section.find_all('li', class_='List_item')

    for item in list_items:
        date_tag = item.find('span', class_='Date Date-small')
        if date_tag and date_tag.text.strip() == today_date["local"]["date_dot_unpadded"]:
            title_tag = item.find('div', class_='List_body')
            title_raw = title_tag.get_text(strip=True)
            title = re.sub(r'^\d{4}\.\d{1,2}\.\d{1,2}\s*', '', title_raw)

            href = item.find('a')['href']
            if href.startswith("http"):
                url = href
            else:
                url = "https://www.pokemon-card.com" + href

            image_src = item.find('img')['data-src']
            if image_src.startswith("http"):
                image_url = image_src
            else:
                image_url = f"https://www.pokemon-card.com{image_src}"

            news_items.append({
                'title': title,
                'url': url,
                "image_url": image_url
            })

    return news_items

# APIからデータを取得し、必要に応じて更新を処理する関数
def process_card_news_jp(model):
    last_data, input_data = load_common_data(model)
    
    new_items = parse_news(input_data)
    if not new_items:
        logging.info("今日の日付のニュースがありません。処理を終了します。")
        return

    last_urls = {item['url'] for item in last_data}
    fresh_items = [item for item in new_items if item['url'] not in last_urls]

    if not fresh_items:
        logging.info("新しいニュースはありません。処理を終了します。")
        return

    # Embedを作成してまとめて送信
    embeds = []
    for item in fresh_items:
        embed = {
            "title": item['title'],
            "url": item['url'],
            "color": 0x003A70
        }
        if item.get("image_url", '').startswith("http"):
            embed["image"] = {"url": item["image_url"]}

        embeds.append(embed)

    # 10件ずつに分割して送信
    for chunk in chunk_list(embeds, 10):
        content = f"<@&{input_data['role_id']}>"
        payload = {"content": content, "embeds": chunk}
        send_discord_notification(input_data['webhook_url'], payload)

    # データ保存
    save_last_data(model, new_items)

def main():
    try:
        process_card_news_jp("card_news_jp")
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()