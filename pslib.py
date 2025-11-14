'''
pslib.py : Project-specific Stable Library. Includes stable functions that are not expected to change.
'''

import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

KOR_TIMEZONE = timezone(timedelta(hours=9))
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
DART_API_KEY = os.getenv("DART_API_KEY")
if BOT_TOKEN is None or CHAT_ID is None or DART_API_KEY is None:
    from config import BOT_TOKEN, CHAT_ID, DART_API_KEY


def send_message(text, bot_token=BOT_TOKEN, chat_id=CHAT_ID, parse_mode="HTML"):
    # Sends a message to the Telegram chat.
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode, "link_preview_options": {"is_disabled": True}}
    response = requests.post(url, json=data)
    if not response.ok:
        raise Exception(f"Telegram API error: {response.text}")
        
def read_news(news_list):
    datas = []
    only_codes = []
    for news_item in news_list:
        title = news_item.get("title", "")
        url = news_item.get("url", "")
        date = news_item.get("date", "")
        if title and url:
            datas.append({"title": title, "url": url, "date": date})
            only_codes.append(url)
    return datas, only_codes
