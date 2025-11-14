import requests

class ChatBot:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
    
    def send_message(self, chat_id: str, text: str, parse_mode = "HTML"):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode, "link_preview_options": {"is_disabled": True}}
        response = requests.post(url, json=data)
        if not response.ok: raise Exception(f"Telegram API error: {response.text}")
