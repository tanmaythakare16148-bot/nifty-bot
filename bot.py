import requests
import yfinance as yf
import time
from datetime import datetime

# --- CONFIG ---
TELEGRAM_TOKEN = "APNA_NAYA_TOKEN_YAHAN_DALO"  # @BotFather wala naya token
CHAT_ID = "APNA_CHAT_ID_YAHAN_DALO"  # getUpdates wala ID
PAIR = "GC=F" # Gold Futures - XAUUSD ke liye

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        print(f"Alert bheja: {msg}")
    except Exception as e:
        print(e)

def check_gold():
    # Gold ka 15min data le raha hai
    data = yf.download(PAIR, period="2d", interval="15m")
    if len(data) < 20:
        return
    
    last_price = data['Close'].iloc[-1]
    asia_low = data['Low'].iloc[-20:-10].min() # Asia session ka low
    asia_high = data['High'].iloc[-20:-10].max()

    print(f"{datetime.now()} - Gold: {last_price} | Asia Low: {asia_low}")

    # SWEEP LOGIC - Agar price ne Asia Low ko tod ke wapas upar aaya
    if last_price < float(asia_low) * 1.001 and last_price > float(asia_low):
        # Ye sweep hua
        entry = round(float(last_price), 2)
        sl = round(entry - 4, 2)
        tp = round(entry + 8, 2)
        
        msg = f"""🔥 *GOLD BUY SWEEP ALERT* 🔥
        
Pair: XAUUSD
Price ne Asia Low Sweep kiya hai!

*Entry:* {entry}
*SL:* {sl} (-$4)
*TP:* {tp} (+$8)

Time: London Open ke aas paas
Reason: SSL Sweep + BOS

XM Micro me 0.01 lot lena!"""
        send_telegram(msg)
        time.sleep(3600) # 1 ghante tak dubara alert nahi

# --- MAIN LOOP ---
send_telegram("✅ Gold Sweep Bot START ho gaya hai bhai!")
while True:
    check_gold()
    time.sleep(900) # Har 15 min me check karega
