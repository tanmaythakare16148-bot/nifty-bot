import os
import requests
import yfinance as yf
import time
from datetime import datetime

# --- CONFIG - Safe tarike se ---
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PAIR = "^NSEI" # Nifty ke liye

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        print(f"Alert bheja: {msg}")
    except Exception as e:
        print(e)

# ... niche tera purana sweep logic same rahega ...

send_telegram("✅ Nifty Bot START ho gaya - Purana wala wapas ON hai")
