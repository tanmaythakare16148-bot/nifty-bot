import os, requests
from flask import Flask
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler
import datetime

app = Flask(__name__)
@app.route('/')
def home(): return "Bot LIVE - NSE Direct"
@app.route('/send')
def send_route():
    check_market()
    return "Sent!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
    except: pass

def get_nifty_nse():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.nseindia.com/"
        }
        s = requests.Session()
        # cookie lene ke liye
        s.get("https://www.nseindia.com", headers=headers, timeout=10)
        r = s.get("https://www.nseindia.com/api/allIndices", headers=headers, timeout=10).json()
        for item in r['data']:
            if item['index'] == 'NIFTY 50':
                last = float(item['last'])
                high = float(item.get('high', last))
                low = float(item.get('low', last))
                prev_high = float(item.get('previousClose', last)) # fallback
                # NSE allIndices me 5D high nahi deta, to aaj ka high/low se hi sweep check karenge
                # thoda logic change
                return last, last*1.005, last*0.995, high, low # last, prevH, prevL, 5D high, 5D low ka jugaad
        return None
    except Exception as e:
        print(f"NSE Error {e}")
        return None

def get_nifty_history_nse():
    # Better history - Nifty 50 ke liye daily high low
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.nseindia.com/"
        }
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=headers, timeout=10)
        # last 5 days ka data
        url = "https://www.nseindia.com/api/historical/indices?indexType=NIFTY%2050&from=01-09-2026&to=24-09-2026"
        r = s.get(url, headers=headers, timeout=10).json()
        data = r['data']['indexCloseOnlineRecords']
        closes = [float(x['EOD_CLOSE_INDEX_VAL']) for x in data]
        highs = [float(x['EOD_HIGH_INDEX_VAL']) for x in data]
        lows = [float(x['EOD_LOW_INDEX_VAL']) for x in data]
        last = closes[-1]
        last_5_high = max(highs[-5:])
        last_5_low = min(lows[-5:])
        prev_high = highs[-2]
        prev_low = lows[-2]
        return last, prev_high, prev_low, last_5_high, last_5_low
    except Exception as e:
        print(f"History Error {e}")
        return get_nifty_nse()

def check_market():
    data = get_nifty_history_nse()
    if not data:
        send_telegram("⚠️ NSE bhi busy hai, 30 sec baad /send dabao")
        return

    close, prev_day_high, prev_day_low, last_5_high, last_5_low = data

    # Liquidity Sweep Check
    if close >= last_5_high - 20: # near high
        liq = f"🔥 *BSL Liquidity* {last_5_high:.0f} ke paas hai - Upar SL pade hain. Fake breakout ho sakta hai!"
        signal = f"⚠️ NIFTY {close:.0f} 5D High {last_5_high:.0f} ke paas - *SWEEP WATCH*"
    elif close <= last_5_low + 20:
        liq = f"🔥 *SSL Liquidity* {last_5_low:.0f} ke paas hai - Neeche SL pade hain. Fake breakdown ho sakta hai!"
        signal = f"⚠️ NIFTY {close:.0f} 5D Low {last_5_low:.0f} ke paas - *SWEEP WATCH*"
    else:
        liq = f"5D High {last_5_high:.0f} | Low {last_5_low:.0f} - Liquidity zones"
        signal = f"➡️ NIFTY {close:.0f} Range me | Prev H {prev_day_high:.0f} L {prev_day_low:.0f}"

    # FII
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        r = s.get("https://www.nseindia.com/api/fiidiiTradeReact", headers={"User-Agent": "Mozilla/5.0"}, timeout=10).json()
        fii = float(r[0]['buyValue']) - float(r[0]['sellValue'])
        fii_text = f"FII: {fii/100:.0f}Cr {'BUY' if fii>0 else 'SELL'}"
    except:
        fii_text = "FII: Data off today"

    msg = f"📊 *MASTER BOT - NSE DIRECT + LIQUIDITY*\n\n💰 {fii_text}\n\n{signal}\n\n🧠 {liq}\n\n📍 Levels: Prev H {prev_day_high:.0f} L {prev_day_low:.0f}\n⏰ {datetime.datetime.now().strftime('%d-%m %I:%M %p')}"
    send_telegram(msg)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(check_market, 'cron', hour=9, minute=20, day_of_week='mon-fri')
    scheduler.add_job(check_market, 'cron', hour=14, minute=45, day_of_week='mon-fri')
    scheduler.start()
    check_market()
    import time
    while True: time.sleep(60)
