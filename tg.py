from time import sleep
import requests
from config import telegram_alerts_chats, telegram_alerts_token


def send_telegram_message(message, chat_id=telegram_alerts_chats, bot_token=telegram_alerts_token, max_retries=10):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    for chat in chat_id if isinstance(chat_id, list) else [chat_id]:
        payload = {"chat_id": chat, "text": message, "parse_mode": "HTML"}
        
        for i in range(max_retries + 1):
            try:
                response = requests.post(url, json=payload)
                response.raise_for_status()
                if response.status_code == 200:
                    return
            except Exception:
                sleep(int(1.5 ** i))
        else:
            raise Exception("send_telegram_message Max retries reached. Message sending failed.")