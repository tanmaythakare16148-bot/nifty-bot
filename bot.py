import os, requests
from flask import Flask
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler
import datetime

app = Flask(__name__)
@app.route('/')
def home(): return "Bot LIVE - Yahoo Direct API"
@app.route('/send')
def send_route():
    check_market()
    return "Done!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
    except: pass

def get_nifty_yahoo():
    # Direct Yahoo API - yfinance se tez
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?range=20d&interval=1d"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10).json()
        result = r['chart']['result'][0]
        closes = result['indicators']['quote'][0]['close']
        highs = result['indicators']['quote'][0]['high']
        lows = result['indicators']['quote'][0]['low']
        # last values
        close = closes[-1]
        prev_high = highs[-2]
        prev_low = lows[-2]
        last_5_high = max(highs[-5:])
        last_5_low = min(lows[-5:])
        return close, prev_high, prev_low, last_5_high, last_5_low
    except Exception as e:
        print(f"Yahoo Error {e}")
        return None

def check_market():
    data = get_nifty_yahoo()
    if not data:
        send_telegram("⚠️ Yahoo bhi slow hai, 1 min baad /send fir dabao")
        return

    close, prev_day_high, prev_day_low, last_5_high, last_5_low = data

    # Liquidity Sweep Logic
    if close > last_5_high:
        # For daily close we check sweep differently
        signal = f"✅ Breakout ke kareeb NIFTY {close:.0f} > 5D High {last_5_high:.0f}"
        liq = f"BSL Liquidity Test - Upar ka Zone {last_5_high:.0f}"
    elif close < last_5_low:
        signal = f"🔻 Breakdown ke kareeb NIFTY {close:.0f} < 5D Low {last_5_low:.0f}"
        liq = f"SSL Liquidity Test - Neeche ka Zone {last_5_low:.0f}"
    else:
        signal = f"➡️ NIFTY {close:.0f} Range me | Prev H:{prev_day_high:.0f} L:{prev_day_low:.0f}"
        liq = f"5D High {last_5_high:.0f} (BSL) | 5D Low {last_5_low:.0f} (SSL) - Sweep ka wait"

    # FII
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=headers, timeout=5)
        r = s.get("https://www.nseindia.com/api/fiidiiTradeReact", headers=headers, timeout=10).json()
        fii = float(r[0]['buyValue']) - float(r[0]['sellValue'])
        dii = float(r[1]['buyValue']) - float(r[1]['sellValue'])
        fii_text = f"FII: {fii/100:.0f}Cr {'BUY' if fii>0 else 'SELL'} | DII: {dii/100:.0f}Cr"
    except:
        fii_text = "FII/DII: Holiday"

    msg = f"📊 *MASTER BOT - FIXED V3*\n\n💰 {fii_text}\n\n{signal}\n\n🧠 Liquidity: {liq}\n\n⏰ {datetime.datetime.now().strftime('%d-%m %I:%M %p')}"
    send_telegram(msg)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(check_market, 'cron', minute='*/5', hour='9-15', day_of_week='mon-fri')
    scheduler.start()
    check_market()
    import time
    while True: time.sleep(60)
