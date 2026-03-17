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

def parse_pokemoncenter_page(api_url):
    response = requests_get(api_url)
    soup = parse_html(response["text"])
    cards = soup.find_all('div', class_='sub-cell x1of3')

    data_list = []
    for card in cards:
        data = {
            "sub-name": card.find('p', class_='sub-name').text.strip() if card.find('p', class_='sub-name') else None,
            "ex-groupLink": card.find('a', class_='ex-groupLink')['href'] if card.find('a', class_='ex-groupLink') else None,
            "mod-image": card.find('p', class_='mod-image').img['src'] if card.find('p', class_='mod-image') and card.find('p', class_='mod-image').img else None,
            "ex-topNewsTitle": card.find('p', class_='ex-topNewsTitle').text.strip() if card.find('p', class_='ex-topNewsTitle') else None,
            "ex-tag": card.find('p', class_='ex-tag').text.strip() if card.find('p', class_='ex-tag') else None,
            "ex-date": card.find('p', class_='ex-date').text.strip() if card.find('p', class_='ex-date') else None
        }
        data_list.append(data)
    return data_list

def get_updated_items(current_data, last_data, comparison_keys):
    updated_items = []
    for new_item in current_data:
        is_new = True
        for old_item in last_data:
            if all(new_item.get(key) == old_item.get(key) for key in comparison_keys):
                is_new = False
                if new_item != old_item:
                    updated_items.append(new_item)
                break
        if is_new:
            updated_items.append(new_item)
    return updated_items

def send_discord_notification_generic(webhook_url, items, get_username=None, get_avatar_url=None, get_content=None, get_image_url=None, get_thread_id=None, get_embed_title=None, get_embed_url=None):
    for item in items:
        thread_id = get_thread_id(item) if get_thread_id else None

        full_webhook_url = webhook_url
        if thread_id:
            if '?' in full_webhook_url:
                full_webhook_url += f"&thread_id={thread_id}"
            else:
                full_webhook_url += f"?thread_id={thread_id}"

        # Webhook作成
        webhook = DiscordWebhook(
            url=full_webhook_url
        )

        # Optional: ユーザー名とアイコン
        if get_username:
            webhook.username = get_username(item)
        if get_avatar_url:
            webhook.avatar_url = get_avatar_url(item)

        # Embed作成
        embed = DiscordEmbed()

        # タイトルとURLを設定
        if get_embed_title:
            embed.title = get_embed_title(item)
        if get_embed_url:
            embed.url = get_embed_url(item)

        # 画像
        image_url = get_image_url(item) if get_image_url else None
        if image_url:
            embed.set_image(url=image_url)

        webhook.add_embed(embed)
        webhook.execute()

def process_generic(model, parse_func, comparison_keys, webhook_func):
    last_data, input_data = load_common_data(model)
    current_data = parse_func(input_data['api_url'])
    
    updated_items = get_updated_items(current_data, last_data, comparison_keys)

    if updated_items:
        logging.info(f"{len(updated_items)} 件の更新が検出されました。")
        webhook_func(input_data, updated_items)
        save_last_data(model, current_data)
    else:
        logging.info("更新はありません。")

def process_pokemoncenter(model):
    def webhook_func(input_data, updated_items):
        send_discord_notification_generic(
            webhook_url=input_data['webhook_url'],
            items=updated_items,
            get_username=lambda item: item['sub-name'],
            get_avatar_url=lambda item: input_data['center_data'].get(item['sub-name'], {}).get("icon_url"),
            get_embed_title=lambda item: item['ex-topNewsTitle'],
            get_embed_url=lambda item: item['ex-groupLink'],
            get_image_url=lambda item: item.get('mod-image'),
            get_thread_id=lambda item: input_data['center_data'].get(item['sub-name'], {}).get("thread_id")
        )
    
    process_generic(
        model=model,
        parse_func=parse_pokemoncenter_page,
        comparison_keys=['sub-name', 'ex-topNewsTitle'],
        webhook_func=webhook_func
    )

def process_pokemoncafe(model):
    def parse_json_data(api_url):
        response = requests_get(api_url)
        current_data = response["json"]
        return current_data

    def webhook_func(input_data, updated_items):
        send_discord_notification_generic(
            webhook_url=input_data['webhook_url'],
            items=updated_items,
            get_embed_title=lambda item: item['NewsTitle'],
            get_embed_url=lambda item: f"https://www.pokemon-cafe.jp{item['NewsUrl']}",
            get_image_url=lambda item: (
                f"https://www.pokemon-cafe.jp{item['NewsImage']}" 
                if item.get('NewsImage') 
                else "https://www.pokemon-cafe.jp/common/img/news/news_noimage.png"
            )
        )

    process_generic(
        model=model,
        parse_func=parse_json_data,
        comparison_keys=['NewsUrl', 'NewsTitle'],
        webhook_func=webhook_func
    )

def main():
    try:
        process_pokemoncenter("pokemoncenter")
        process_pokemoncafe("pokemoncafe")
        process_pokemoncafe("pikachusweets")
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")

if __name__ == '__main__':
    main()
