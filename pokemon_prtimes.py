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

# company_ids はコード内に直接定義
COMPANY_IDS = ["26665", "29227", "36293", "43550", "105086", "106093", "126093"]

def fetch_latest_from_company(api_url, company_id):
    api_url = f"{api_url}/companies/{company_id}/press_releases?search_word=ポケモン"
    response = requests_get(api_url)
    data = response.get("json", {})
    
    items = data.get("data", {}).get("data")
    if not items:
        return None

    latest = items[0]
    return {
        "title": latest['title'],
        "url": f"https://prtimes.jp{latest['url']}"
    }

def fetch_latest_from_topics(api_url):
    api_url = f"{api_url}?type=topics&v=ポケモン"
    response = requests_get(api_url)
    current_data = response["json"]

    if not current_data or 'articles' not in current_data or not current_data['articles']:
        return None
    latest = current_data['articles'][0]
    return {
        "title": latest.get("title", ""),
        "url": f"https://prtimes.jp{latest.get('url', '')}"
    }

def notify_discord(input_data, result):
    content = (
        f"**{result['title']}**\n"
        f"{result['url']}"
    )
    payload = {"content": content}
    send_discord_notification(input_data['webhook_url'], payload)

def handle_multi_company_mode(input_data, last_data):
    latest_news = {}
    new_data_found = False

    for company_id in COMPANY_IDS:
        result = fetch_latest_from_company(input_data['api_url'], company_id)
        if result:
            last_url = last_data.get(company_id, {}).get("url")
            if last_url != result["url"]:
                notify_discord(input_data, result)
                new_data_found = True
            latest_news[company_id] = result
        else:
            if company_id in last_data:
                latest_news[company_id] = last_data[company_id]

    return latest_news if new_data_found else None

def handle_topic_mode(input_data, last_data):
    result = fetch_latest_from_topics(input_data['api_url'])

    if result and last_data.get("url") != result["url"]:
        notify_discord(input_data, result)
        return {"title": result["title"], "url": result["url"]}
    return None

def run_mode(model, handler):
    last_data, input_data = load_common_data(model)
    updated_data = handler(input_data, last_data)
    if updated_data:
        save_last_data(model, updated_data)
        logging.info(f"{model}: 新しいデータを保存しました。")
    else:
        logging.info(f"{model}: 新しいデータはありませんでした。")

def main():
    run_mode("pokemon_prtimes", handle_multi_company_mode)
    run_mode("pokemon_prtimes2", handle_topic_mode)

if __name__ == "__main__":
    main()