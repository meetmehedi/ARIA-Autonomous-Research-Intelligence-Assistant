import sys
import requests
from aria.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_message(message: str) -> bool:
    """Sends a message to Mehedi's Telegram via Bot API."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram bot credentials not configured in .env file.", file=sys.stderr)
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json().get("ok", False)
    except Exception as e:
        print(f"Error sending Telegram notification: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    print("Telegram Notifier tool loaded.")
