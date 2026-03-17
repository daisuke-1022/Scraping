import os
import json
import sys
from .logging import logging

def load_common_data(model):
    return load_last_data(model), load_input_data(model)

def load_input_data(model):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, '../input_data')

    def read_json(file):
        with open(os.path.join(input_path, file), 'r', encoding='utf-8') as f:
            return json.load(f)

    try:
        data = read_json('data.json')
        result = {}
        if model in ['app_store', 'google_play']:
            result['apps'] = read_json('apps.json')
        elif model in ['pokemoncenter']:
            result['center_data'] = read_json('center.json')
        elif model.endswith('_twitch'):
            twitch = read_json('twitch.json')
            result['client_id'] = twitch.get('client_id')
            result['client_secret'] = twitch.get('client_secret')
            result['channels'] = twitch['channels'].get(model)
        elif model.endswith('_youtube'):
            youtube = read_json('youtube.json')
            result['channels'] = youtube['channels'].get(model)

        if model in data:
            result.update({
                'role_id': data[model].get('role_id'),
                'api_url': data[model].get('api_url'),
                'webhook_url': data[model].get('webhook_url'),
            })
        else:
            logging.error(f"{model}のデータが見つかりません。")
            sys.exit(1)

        return result

    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"ファイル読み込みエラー: {e}")
        sys.exit(1)

def load_last_data(model):
    path = os.path.join(os.path.dirname(__file__), '../last_data', f'{model}.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_last_data(model, data):
    path = os.path.join(os.path.dirname(__file__), '../last_data', f'{model}.json')
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"{path} の保存に失敗しました: {e}")
