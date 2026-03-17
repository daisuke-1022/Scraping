import feedparser
from .logging import logging

def feedparser_parse(url):
    try:
        logging.info(f"RSS取得中: {url}")
        feed = feedparser.parse(url)
        return feed.entries
    except Exception as e:
        logging.error(f"RSSパース失敗: {e}")
        return None