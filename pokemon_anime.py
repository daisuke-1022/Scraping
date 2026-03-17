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

def parse_data(input_data):
    response = requests_get(input_data['api_url'])
    soup = parse_html(response["text"])

    # 「次回予告」の情報取得
    next_section = soup.find("div", id="next")
    next_li_1 = next_section.find_next("li")
    next_li_2 = next_li_1.find_next("li")
    next_iframe = next_section.find_next("iframe")

    next_episode = {
        "date": next_li_1.text.strip(),
        "title": next_li_2.text.strip(),
        "url": next_iframe["src"]
    }

    # 「最新話見逃し配信」の情報取得
    latest_section = soup.find("div", id="latest").find_next("div", class_="contentsBox fadein")
    latest_li_1 = latest_section.find("li")
    latest_li_2 = latest_li_1.find_next("li")
    latest_iframe = latest_section.find("iframe")

    latest_episode = {
        "date": latest_li_1.text.strip(),
        "title": latest_li_2.text.strip(),
        "url": latest_iframe["src"]
    }

    return {
        "next_episode": next_episode,
        "latest_episode": latest_episode
    }

def parse_news(input_data):
    response = requests_get(input_data['api_url'] + "news/")
    soup = parse_html(response["text"])

    entries = soup.find_all("div", class_="entry")
    news_list = []
    
    for entry in entries:
        title = entry.find("div", class_="entryttl").text.strip()
        date = entry.find("div", class_="date").text.strip()
        content_html = entry.find("div", class_="txtbox").decode_contents().strip()

        soup = parse_html(content_html)
        for a_tag in soup.find_all("a", href=True):
            if a_tag["href"] == "../data/":
                a_tag["href"] = "https://www.tv-tokyo.co.jp/anime/pocketmonster2023/data/"
        
        content = str(soup)

        images = entry.find_all("img")
        image_urls = [img["src"] if img["src"].startswith("http") else "https://www.tv-tokyo.co.jp" + img["src"] for img in images]

        news_list.append({
            "date": date,
            "title": title,
            "content": content,
            "images": image_urls
        })

    return news_list

def main():
    model = "pokemon_anime"
    last_data, input_data = load_common_data(model)

    new_data = parse_data(input_data)
    new_news = parse_news(input_data)
    
    if last_data and last_data == {"next_episode": new_data["next_episode"], "latest_episode": new_data["latest_episode"], "news": new_news}:
        logging.info(f"{model}: 変更なし")
        return
    
    if last_data is None or last_data["latest_episode"] != new_data["latest_episode"]:
        episode = new_data["latest_episode"]
        category = "最新話見逃し配信"
        content = (
            f"**{category}**\n"
            f"{episode['date']}  {episode['title']}\n"
            f"{episode['url']}"
        )
        payload = {"content": content}
        send_discord_notification(input_data['webhook_url'], payload)

    if last_data is None or last_data["next_episode"] != new_data["next_episode"]:
        episode = new_data["next_episode"]
        category = "次回予告"
        content = (
            f"**{category}**\n"
            f"{episode['date']}  {episode['title']}\n"
            f"{episode['url']}"
        )
        payload = {"content": content}
        send_discord_notification(input_data['webhook_url'], payload)

    if last_data is None or last_data["news"][0] != new_news[0]:
        news = new_news[0]
        category = "おしらせ"
        soup = parse_html(news["content"])

        for strong in soup.find_all("strong"):
            strong.insert_before("**")
            strong.insert_after("**")
            strong.unwrap()

        for a_tag in soup.find_all("a", href=True):
            link_text = a_tag.text.strip()

            if not link_text and a_tag.find("img"):
                img_tag = a_tag.find("img")
                link_text = img_tag.get("alt", "画像リンク")

            href = a_tag["href"]
            if not href.startswith("http"):
                href = "https://www.tv-tokyo.co.jp" + href

            a_tag.replace_with(f"[{link_text}](<{href}>)")

        content = soup.get_text("")

        content = (
            f"**{category}**\n"
            f"{news['date']}  {news['title']}\n"
            f"{content}"
        )
        embeds = [{"image": {"url": img}} for img in news["images"]]
        payload = {"content": content, "embeds": embeds}
        send_discord_notification(input_data['webhook_url'], payload)

    new_data["news"] = new_news
    save_last_data(model, new_data)
    logging.info(f"{model}: 更新を検出し、通知を送信しました")

if __name__ == "__main__":
    main()
