import sys
import requests
from aria.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from aria.logging_setup import get_logger

logger = get_logger(__name__)

def send_telegram_message(message: str) -> bool:
    """Sends a message to Mehedi's Telegram via Bot API."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram bot credentials not configured in .env file.")
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
        logger.warning("Error sending Telegram notification: %s", e)
        return False

if __name__ == "__main__":
    print("Telegram Notifier tool loaded.")
