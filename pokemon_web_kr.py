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

# モデルごとの日付取得関数
def extract_date(entry, model):
    if model in ["pokemon_info_kr", "card_news_kr"]:
        list_items = entry.select("ul.list-split li")
        if len(list_items) >= 2:
            return list_items[1].text.strip()
        else:
            return None
    else:
        p_tags = entry.find_all("p")
        date_regex = re.compile(r"\d{4}년 \d{2}월 \d{2}일")
        for p in p_tags:
            text = p.text.strip()
            if date_regex.fullmatch(text):
                return text
        return None

def process_pokemon_kr_news(model, payload_data):
    last_data, input_data = load_common_data(model)
    today_date = get_today_date()

    try:
        response = requests_post(input_data['api_url'], data=payload_data)
        soup = parse_html(response["text"])
        entries = soup.find_all('li', class_='col-lg-3 col-6')

        if not entries:
            logging.error(f"ニュースデータが見つかりませんでした。")
            return
        
        new_entries_to_notify = []

        for entry in entries:
            date_str = extract_date(entry, model)
            if not date_str or date_str != today_date["local"]["date_kr"]:
                continue

            title_tag = entry.find('h3')
            image_tag = entry.find('img')
            link_tag = entry.find('a')
            href = link_tag.get('href', '')

            if not title_tag or not image_tag or not link_tag:
                logging.warning(f"{model}: 必須情報が不足しているためスキップ: {entry}")
                continue

            base_url = "https://pokemoncard.co.kr" if model == "card_news_kr" else "https://pokemonkorea.co.kr"

            title = title_tag.text.strip()
            url = href if href.startswith("http") else base_url + href
            image_url = image_tag['src']

            new_data = {
                'title': title,
                'url': url,
                "image_url": image_url,
                'date': date_str
            }

            if new_data in last_data:
                logging.info(f"{model}: 重複データ → スキップ: {title}")
                continue

            new_entries_to_notify.append(new_data)

        if not new_entries_to_notify:
            logging.info(f"{model}: 今日の新しいエントリーはありません。")
            return

        # embedを一括で構築
        embeds = []
        for entry in new_entries_to_notify:
            embed = {
                "title": entry['title'],
                "url": entry['url'],
                "color": 0xFFCC00
            }
            if entry["image_url"]:
                embed["image"] = {"url": entry["image_url"]}
                
            embeds.append(embed)

        # Discordの制限に従って10件ずつ送信
        for chunk in chunk_list(embeds, 10):
            content = f"<@&{input_data['role_id']}>"
            payload = {"content": content, "embeds": chunk}
            send_discord_notification(input_data['webhook_url'], payload)

        # 新しいデータを保存
        last_data.extend(new_entries_to_notify)
        save_last_data(model, last_data)

    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")

def main():
    news_configs = [
        ("pokemon_info_kr", {
            'pn': '1',
            'cate': '0',
            'sword': '',
            'rcode': 'menu_news'
        }),
        ("card_news_kr", {
            'pn': '1',
            'cate': '2',
            'sword': '',
            'rcode': 'menu_news'
        }),
        ("go_news_kr", {
            'pn': '1',
            'vcate1': 'go',
            'vcate2': 'menu64',
            'muid': '15',
            'sfuid': '64',
            'mode': ''
        }),
        ("unite_news_kr", {
            'pn': '1',
            'vcate1': 'pokemon-unite',
            'vcate2': 'menu127',
            'muid': '28',
            'sfuid': '127',
            'mode': ''
        }),
        ("caferemix_news_kr", {
            'pn': '1',
            'vcate1': 'pokemoncaferemix',
            'vcate2': 'menu162',
            'muid': '33',
            'sfuid': '162',
            'mode': ''
        }),
        ("home_news_kr", {
            'pn': '1',
            'vcate1': 'pokemonhome',
            'vcate2': 'menu300',
            'muid': '51',
            'sfuid': '300',
            'mode': ''
        }),
        ("tcgpocket_news_kr", {
            'pn': '1',
            'vcate1': 'pokemon_tcg_pocket',
            'vcate2': 'menu492',
            'muid': '67',
            'sfuid': '492',
            'mode': ''
        }),
        ("champions_news_kr", {
            'pn': '1',
            'vcate1': 'pokemon_champions',
            'vcate2': 'menu651',
            'muid': '87',
            'sfuid': '651',
            'mode': ''
        }),
    ]

    for model, payload_data in news_configs:
        process_pokemon_kr_news(model, payload_data)

if __name__ == "__main__":
    main()
