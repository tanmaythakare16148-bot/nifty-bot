import os, requests, time
from flask import Flask
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler
import datetime

app = Flask(__name__)
@app.route('/')
def home(): return "V7.3 DIRECT API LIVE"
@app.route('/send')
def send_route():
    check_market()
    return "V7.3 Sent!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=20)
    except: pass

def get_nifty_direct():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?range=1mo&interval=1d"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15).json()
        result = r['chart']['result'][0]
        closes = [c for c in result['indicators']['quote'][0]['close'] if c is not None]
        highs = [h for h in result['indicators']['quote'][0]['high'] if h is not None]
        lows = [l for l in result['indicators']['quote'][0]['low'] if l is not None]

        close = closes[-1]
        l5h = max(highs[-5:])
        l5l = min(lows[-5:])
        prev_h = highs[-2]
        prev_l = lows[-2]
        return close, prev_h, prev_l, l5h, l5l
    except Exception as e:
        print(f"Yahoo Direct Error: {e}")
        return None

def check_market():
    data = get_nifty_direct()
    if not data:
        send_telegram("⚠️ Yahoo fail. Kal 9:20 AM auto chalega.")
        return

    close, prev_h, prev_l, l5h, l5l = data

    pcr_text = "PCR: Market band (6PM ke baad NSE band)"
    fii_msg = "Kal FII entry dikhayega"
    try:
        s = requests.Session()
        s.headers.update({"User-Agent": "Mozilla/5.0", "Referer": "https://www.nseindia.com/"})
        s.get("https://www.nseindia.com", timeout=10)
        time.sleep(1)
        r = s.get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY", timeout=15).json()
        ce_oi=0; pe_oi=0
        for item in r['records']['data']:
            if 'CE' in item: ce_oi+=item['CE']['openInterest']
            if 'PE' in item: pe_oi+=item['PE']['openInterest']
        pcr = pe_oi/ce_oi if ce_oi>0 else 0
        pcr_text = f"PCR {pcr:.2f}"
    except: pass

    liq = f"🔥 SSL {l5l:.0f} Sweep Watch" if close<=l5l+15 else f"🔥 BSL {l5h:.0f} Sweep" if close>=l5h-15 else f"Range {l5l:.0f}-{l5h:.0f}"

    ist = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))

    msg = f"📊 *V7.3 FINAL - WORKING*\n\n💰 NIFTY {close:.0f} | {pcr_text}\n{liq}\nPrev H {prev_h:.0f} L {prev_l:.0f}\n\n🎯 {fii_msg}\n\n✅ NSE block khatam. Kal 9:20 AM auto ayega.\n⏰ {ist.strftime('%d-%m %I:%M %p')}"
    send_telegram(msg)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(check_market, 'cron', hour=9, minute=20, day_of_week='mon-fri')
    scheduler.add_job(check_market, 'cron', hour=14, minute=45, day_of_week='mon-fri')
    scheduler.start()
    check_market()
    while True: time.sleep(60)
