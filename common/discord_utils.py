import os
import requests
from io import BytesIO
from urllib.parse import urlparse
from .network import  requests_post
from .logging import logging

def chunk_list(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

def send_discord_notification(webhook_url, payload):
    try:
        requests_post(webhook_url, json=payload)
        logging.info("Discord通知送信成功")
    except Exception as e:
        logging.error(f"Discord通知エラー: {e}")

def get_extension_from_magic_number(header_bytes):
    if header_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return '.png'
    elif header_bytes.startswith(b'\xff\xd8'):
        return '.jpg'
    elif header_bytes.startswith(b'GIF87a') or header_bytes.startswith(b'GIF89a'):
        return '.gif'
    elif header_bytes.startswith(b'BM'):
        return '.bmp'
    elif header_bytes.startswith(b'\x00\x00\x01\x00'):
        return '.ico'
    else:
        return '.bin'

def send_discord_notification_with_image(webhook_url, content, image_url):
    try:
        response = requests.get(image_url)
        response.raise_for_status()

        image_data = BytesIO(response.content)

        # ヘッダーから拡張子を推測
        header = image_data.getvalue()[:16]
        extension = get_extension_from_magic_number(header)

        # オリジナルファイル名を取得
        original_name = os.path.basename(urlparse(image_url).path)
        name_without_ext = os.path.splitext(original_name)[0] or "image"
        filename = f"{name_without_ext}{extension}"
        image_data.name = filename

        payload = {"content": content}
        files = {"file": (filename, image_data, f"image/{extension.lstrip('.')}")}

        # 送信
        requests.post(webhook_url, data=payload, files=files)
        logging.info("Discord画像通知送信成功")

    except Exception as e:
        logging.error(f"Discord画像送信失敗: {e}")