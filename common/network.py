import requests
from .logging import logging
from requests.exceptions import RequestException, HTTPError

def _handle_response(response):
    response.encoding = "utf-8"
    try:
        json_data = response.json()
    except ValueError:
        json_data = None
    return {
        "response": response,
        "text": response.text,
        "content": response.content,
        "json": json_data
    }

def _handle_exception(e, method):
    logging.error(f"{method}リクエスト失敗: {e}")
    return {
        "response": None,
        "text": None,
        "content": None,
        "json": None
    }

def requests_get(url, headers=None, params=None):
    logging.info(f"GETリクエスト: {url}")
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return _handle_response(response)
    except (HTTPError, RequestException) as e:
        return _handle_exception(e, "GET")

def requests_post(url, headers=None, params=None, data=None, json=None, files=None):
    logging.info(f"POSTリクエスト: {url}")
    try:
        response = requests.post(url,headers=headers,params=params,data=data,json=json,files=files)
        response.raise_for_status()
        return _handle_response(response)
    except (HTTPError, RequestException) as e:
        return _handle_exception(e, "POST")

def requests_patch(url, headers=None, json=None):
    logging.info(f"PATCHリクエスト: {url}")
    try:
        response = requests.patch(url, headers=headers, json=json)
        response.raise_for_status()
        return _handle_response(response)
    except (HTTPError, RequestException) as e:
        return _handle_exception(e, "POST")