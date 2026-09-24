import os, requests, time
from flask import Flask
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler
import datetime

app = Flask(__name__)
@app.route('/')
def home(): return "V7.1 ANTI-BLOCK LIVE"
@app.route('/send')
def send_route():
    check_market()
    return "V7.1 Sent!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=20)
    except: pass

def nse_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.nseindia.com/",
        "Accept-Language": "en-US,en;q=0.9"
    })
    try:
        s.get("https://www.nseindia.com", timeout=10)
        time.sleep(1)
    except: pass
    return s

def get_data_with_retry():
    for attempt in range(3): # 3 baar try karega
        try:
            s = nse_session()
            r1 = s.get("https://www.nseindia.com/api/historical/indices?indexType=NIFTY%2050&from=01-09-2026&to=24-09-2026", timeout=15).json()
            hist = r1['data']['indexCloseOnlineRecords'][-20:]

            r2 = s.get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY", timeout=15).json()

            r3 = s.get("https://www.nseindia.com/api/allIndices", timeout=15).json()
            vix = None
            for it in r3['data']:
                if it['index']=='INDIA VIX': vix=float(it['last'])

            r4 = s.get("https://www.nseindia.com/api/fiidiiTradeReact", timeout=15).json()

            return hist, r2, vix, r4
        except Exception as e:
            print(f"Attempt {attempt+1} fail: {e}")
            time.sleep(2 + attempt) # 2sec, 3sec, 4sec wait
    return None, None, None, None

def check_market():
    hist, chain, vix, fii_data = get_data_with_retry()
    if not hist:
        send_telegram("⚠️ NSE ne IP block kiya hai (Render shared IP). 2 min ruko fir /send dabao. Ye NSE ka daily natak hai, bot sahi hai.")
        return

    closes = [float(x['EOD_CLOSE_INDEX_VAL']) for x in hist]
    highs = [float(x['EOD_HIGH_INDEX_VAL']) for x in hist]
    lows = [float(x['EOD_LOW_INDEX_VAL']) for x in hist]
    close = closes[-1]
    l5h = max(highs[-5:]); l5l = min(lows[-5:])

    # FII OPTION RADAR
    fii_option_msg = "Mix"
    pcr = 0
    try:
        ce_oi = 0; pe_oi = 0; top_ce=[]; top_pe=[]
        for item in chain['records']['data']:
            if 'CE' in item:
                ce_oi += item['CE']['openInterest']
                top_ce.append((item['strikePrice'], item['CE']['changeinOpenInterest']))
            if 'PE' in item:
                pe_oi += item['PE']['openInterest']
                top_pe.append((item['strikePrice'], item['PE']['changeinOpenInterest']))
        pcr = pe_oi/ce_oi if ce_oi>0 else 0
        top_ce = sorted(top_ce, key=lambda x: x[1], reverse=True)[:1]
        top_pe = sorted(top_pe, key=lambda x: x[1], reverse=True)[:1]

        if top_pe and top_ce and top_pe[0][1] > top_ce[0][1]*1.3:
            fii_option_msg = f"🟢 FII PUT ENTRY {top_pe[0][0]}PE (+{top_pe[0][1]/1000:.0f}k) - Support"
        elif top_ce and top_pe and top_ce[0][1] > top_pe[0][1]*1.3:
            fii_option_msg = f"🔴 FII CALL ENTRY {top_ce[0][0]}CE (+{top_ce[0][1]/1000:.0f}k) - Resistance"
        else:
            fii_option_msg = f"⚖️ Mix CE {top_ce[0][0]} PE {top_pe[0][0]}"
    except: pass

    try:
        fii_cash = float(fii_data[0]['buyValue']) - float(fii_data[0]['sellValue'])
        dii_cash = float(fii_data[1]['buyValue']) - float(fii_data[1]['sellValue'])
        fii_text = f"FII {fii_cash/100:.0f}Cr | DII {dii_cash/100:.0f}Cr"
    except: fii_text = "FII Data Wait"

    pcr_text = f"PCR {pcr:.2f}"
    vix_text = f"VIX {vix:.1f}" if vix else "VIX N/A"
    liq = f"SSL {l5l:.0f} Sweep" if close<=l5l+30 else f"BSL {l5h:.0f} Sweep" if close>=l5h-30 else f"Range"

    msg = f"📊 *V7.1 FIXED - FII RADAR*\n\n💰 {fii_text}\n📈 {pcr_text} | {vix_text}\nNIFTY {close:.0f} | {liq}\n\n🎯 {fii_option_msg}\n\n⏰ {datetime.datetime.now().strftime('%d-%m %I:%M %p')}"
    send_telegram(msg)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(check_market, 'cron', hour=9, minute=20, day_of_week='mon-fri')
    scheduler.add_job(check_market, 'cron', hour=11, minute=30, day_of_week='mon-fri')
    scheduler.add_job(check_market, 'cron', hour=14, minute=45, day_of_week='mon-fri')
    scheduler.start()
    check_market()
    while True: time.sleep(60)
