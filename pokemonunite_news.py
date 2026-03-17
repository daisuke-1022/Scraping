# coding: UTF-8
import re, time
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

def process_unite_news_jp(model):
    last_data, input_data = load_common_data(model)

    if not last_data or not isinstance(last_data, dict):
        last_data = {"last_checked": "1970-01-01T09:00:00", "notified_ids": []}

    last_checked = last_data.get("last_checked")

    params = {
        "after": last_checked,
        "status": "publish",
        "orderby": "date",
        "order": "asc",
        "per_page": 100,
        "cache_bust": int(time.time())
    }

    response = requests_get(input_data['api_url'], params=params)
    current_data = response["json"]
    if not current_data:
        logging.info("取得データなし")
        return

    if isinstance(current_data, list):
        news_data = current_data
    elif isinstance(current_data, dict):
        news_data = current_data.get("results", [])
    else:
        news_data = []

    if not news_data:
        logging.info("新着記事なし")
        return

    # embed 作成
    embeds = []
    for article in news_data:
        title = unescape(article.get('title', {}).get('rendered', 'No Title'))
        url = article.get('link')

        # wp:featuredmedia から画像URLを取得
        media_url = None
        featuredmedia_links = article.get('_links', {}).get('wp:featuredmedia', [])
        if featuredmedia_links:
            media_url = featuredmedia_links[0].get('href')
            
            # メディア情報を取得して画像URLを取得
            media_response = requests_get(media_url)
            media_data = media_response["json"]
            if media_response and isinstance(media_response, dict):
                media_url = media_data.get('source_url')
            else:
                logging.error(f"メディア情報の取得に失敗しました: {media_url}")

        embed = {
            "title": title,
            "url": url,
            "color": 0x7F3FBF
        }
        if media_url:
            embed["image"] = {"url": media_url}

        embeds.append(embed)

    # 分割送信（10件ずつ）
    for chunk in chunk_list(embeds, 10):
        content = f"<@&{input_data['role_id']}>"
        payload = {"content": content, "embeds": chunk}
        send_discord_notification(input_data['webhook_url'], payload)

    # 最新日時保存
    newest_date = max(article['date'] for article in news_data)
    save_last_data(model, {
        "last_checked": newest_date,
        "notified_ids": [a["id"] for a in news_data]
    })

def process_unite_news_en(model):
    last_data, input_data = load_common_data(model)
    response = requests_get(input_data['api_url'])

    if response:
        soup = parse_html(response["content"])
        ul_element = soup.find('ul', class_='linkList')
        if ul_element:
            second_item = ul_element.find_all('li')[1]
            title = second_item.a.text.strip()
            url = second_item.a['href']

            new_data = {'title': title, 'url': url}

            if last_data == new_data:
                logging.info(f"{model}: 変更なし")
                return

            content = (
                f"<@&{input_data['role_id']}>\n"
                f"**{title}**\n"
                f"{url}"
            )
            payload = {"content": content}
            
            send_discord_notification(input_data['webhook_url'], payload)

            save_last_data(model, new_data)

def process_unite_news_pts(model):
    last_data, input_data = load_common_data(model)
    response = requests_get(input_data['api_url'])
    if response:
        soup = parse_html(response["content"])
        txt2 = soup.find('p', class_='txt2').text.strip()
        list_txt = soup.find('ul', class_='list_txt').text.strip()

        new_data = {'txt2': txt2, 'list_txt': list_txt}
        
        if last_data == new_data:
            logging.info(f"{model}: 変更なし")
            return

        content = (
            f"<@&{input_data['role_id']}>\n"
            f"**{txt2}**\n"
            f"{list_txt}\n"
            f"{input_data['api_url']}"
        )

        payload = {"content": content}

        send_discord_notification(input_data['webhook_url'], payload)

        save_last_data(model, new_data)

def process_unite_news_cn(model):
    last_data, input_data = load_common_data(model)
    
    params = {
        'serviceId': '428',
        'source': 'web_pc',
        'tagids': '*'
    }

    response = requests_get(input_data['api_url'], params=params)
    
    if response is not None:
        try:
            current_data = response["json"]
            items = current_data.get('data', {}).get('items', [])

            today_date = get_today_date()
            today_start = datetime.strptime(today_date["local"]["date_dash_padded"], '%Y-%m-%d')
            yesterday_start = today_start - timedelta(days=1)

            today_entries = []
            for i, article in enumerate(items):
                if not isinstance(article, dict):
                    continue

                sIdxTime = article.get('sIdxTime')
                if not sIdxTime:
                    continue

                try:
                    cst_time = datetime.strptime(sIdxTime, '%Y-%m-%d %H:%M:%S')
                    jst_time = cst_time + timedelta(hours=1)
                    if yesterday_start <= jst_time < today_start + timedelta(days=1):
                        today_entries.append(article)
                except ValueError as e:
                    logging.error(f"sIdxTimeの解析に失敗しました: {sIdxTime}, エラー: {e}")

        except Exception as e:
            logging.error(f"JSONパースエラー: {e}")
            today_entries = []
    else:
        today_entries = []

    if not today_entries:
        logging.info("今日の日付のエントリーはありません。")
        return

    saved_ids = {item.get('iDocID') for item in last_data}
    new_entries = [
        article for article in today_entries
        if article.get('iDocID') not in saved_ids
    ]

    if not new_entries:
        logging.info("新しいエントリーはありません。")
        return

    embeds = []
    for article in new_entries:
        image_url = f"https:{article.get('sIMG')}" if article.get('sIMG') else None

        embed = {
            "title": article.get('sTitle'),
            "url": f"https://unite.qq.com/web202310/news_detail.html?docid={article.get('iDocID')}",
            "color": 0x7F3FBF
        }
        if image_url:
            embed["image"] = {"url": image_url}

        embeds.append(embed)

    # ← ループ外に出す
    for chunk in chunk_list(embeds, 10):
        payload = {"embeds": chunk}
        send_discord_notification(input_data['webhook_url'], payload)

    save_last_data(model, today_entries)

def main():
    try:
        process_unite_news_jp('unite_news_jp')
        process_unite_news_en('unite_news_en')
        process_unite_news_pts('unite_news_pts')
        process_unite_news_cn("unite_news_cn")
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()