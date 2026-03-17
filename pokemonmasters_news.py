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
    news_items = []
    today_date = get_today_date()
    response = requests_get(input_data['api_url'])
    soup = parse_html(response["text"])
    list_items = soup.find_all('li', class_='announcements-item')

    for news_item in list_items:
        date_tag = news_item.find('div', class_='announcements-item-date')
        if date_tag and date_tag.text.startswith(today_date["local"]["date_slash_padded"]):
            # 'title' または 'title' で始まるクラスを持つ要素からテキストを抽出
            title_elements = news_item.find_all(class_=lambda class_name: class_name and class_name.startswith('title'))
            title = " ".join(element.get_text(strip=True) for element in title_elements)
            
            url = "https://pokemonmasters-game.com" + news_item.find('a')['href']  # フルURLに変更
            image_url = news_item.find('img', class_='banner')['src']

            # headings-text要素を取得し、<br>タグを改行に置き換える
            headings_text_tag = news_item.find('div', class_='headings-text')
            if headings_text_tag:
                headings_text = headings_text_tag.get_text(separator=" ", strip=True)  # <br>を改行に置き換え
            else:
                headings_text = ""

            # データ構造に追加
            news_items.append({
                'title': title,
                'url': url,
                "image_url": image_url,
                'headings_text': headings_text
            })

    return news_items

# APIからデータを取得し、必要に応じて更新を処理する関数
def process_masters_news(model):
    last_data, input_data = load_common_data(model)
    new_items = parse_news(input_data)
    if not new_items:
        logging.info("今日の日付のニュースがありません。処理を終了します。")
        return

    # 差分を抽出（前回保存されていないものだけ）
    diff_items = [item for item in new_items if item not in last_data]

    if not diff_items:
        logging.info("前回と同じニュースです。処理を終了します。")
        return

    if diff_items:
        content = f"<@&{input_data['role_id']}>"
        payload = {"content": content}
        send_discord_notification(input_data['webhook_url'], payload)

    # 新しい差分ニュースのみ通知
    for new_item in diff_items:
        # 通常のニュースコンテンツ（メンションなし）
        content = f"**{new_item['title']}**\n"
        if new_item['headings_text']:
            content += f"{new_item['headings_text']}\n"
        content += f"<{new_item['url']}>"

        send_discord_notification_with_image(input_data['webhook_url'], content, new_item["image_url"])

    # 最新の全件で上書き保存
    save_last_data(model, new_items)

def main():
    try:
        process_masters_news("masters_news")
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
