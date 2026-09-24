import os, requests
from flask import Flask
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler
import datetime

app = Flask(__name__)
@app.route('/')
def home(): return "V7 FII OPTION RADAR LIVE"
@app.route('/send')
def send_route():
    check_market()
    return "V7 Sent!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=20)
    except: pass

def get_all_data():
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.nseindia.com/"}
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=headers, timeout=10)
        # 1. History
        r1 = s.get("https://www.nseindia.com/api/historical/indices?indexType=NIFTY%2050&from=01-09-2026&to=24-09-2026", headers=headers, timeout=15).json()
        hist = r1['data']['indexCloseOnlineRecords'][-20:]
        # 2. PCR + Option Chain
        r2 = s.get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY", headers=headers, timeout=15).json()
        # 3. VIX
        r3 = s.get("https://www.nseindia.com/api/allIndices", headers=headers, timeout=10).json()
        vix = None
        for it in r3['data']:
            if it['index']=='INDIA VIX': vix=float(it['last'])
        # 4. FII DII
        r4 = s.get("https://www.nseindia.com/api/fiidiiTradeReact", headers=headers, timeout=10).json()
        return hist, r2, vix, r4
    except Exception as e:
        print(f"Data Error {e}")
        return None, None, None, None

def check_market():
    hist, chain, vix, fii_data = get_all_data()
    if not hist:
        send_telegram("⚠️ NSE busy hai, 30 sec baad /send dabao")
        return

    closes = [float(x['EOD_CLOSE_INDEX_VAL']) for x in hist]
    highs = [float(x['EOD_HIGH_INDEX_VAL']) for x in hist]
    lows = [float(x['EOD_LOW_INDEX_VAL']) for x in hist]
    close = closes[-1]
    l5h = max(highs[-5:]); l5l = min(lows[-5:])

    # --- FII OPTION ENTRY RADAR ---
    fii_option_msg = "FII Option: Data wait"
    pcr = 0
    try:
        ce_oi = 0; pe_oi = 0
        top_ce = []; top_pe = []
        for item in chain['records']['data']:
            if 'CE' in item:
                ce_oi += item['CE']['openInterest']
                top_ce.append((item['strikePrice'], item['CE']['openInterest'], item['CE']['changeinOpenInterest']))
            if 'PE' in item:
                pe_oi += item['PE']['openInterest']
                top_pe.append((item['strikePrice'], item['PE']['openInterest'], item['PE']['changeinOpenInterest']))

        pcr = pe_oi/ce_oi if ce_oi>0 else 0

        # Sabse zyada OI Change jaha hua = FII Entry
        top_ce_sorted = sorted(top_ce, key=lambda x: x[2], reverse=True)[:2]
        top_pe_sorted = sorted(top_pe, key=lambda x: x[2], reverse=True)[:2]

        ce_entry = f"{top_ce_sorted[0][0]}CE (+{top_ce_sorted[0][2]/1000:.0f}k OI)" if top_ce_sorted else ""
        pe_entry = f"{top_pe_sorted[0][0]}PE (+{top_pe_sorted[0][2]/1000:.0f}k OI)" if top_pe_sorted else ""

        if top_ce_sorted[0][2] > top_pe_sorted[0][2] * 1.5:
            fii_option_msg = f"🔴 *FII CALL SELLING ENTRY* {ce_entry} pe - Upar rok rahe hain!"
        elif top_pe_sorted[0][2] > top_ce_sorted[0][2] * 1.5:
            fii_option_msg = f"🟢 *FII PUT SELLING / CALL BUYING* {pe_entry} pe - Neeche support de rahe hain! Tezi"
        else:
            fii_option_msg = f"⚖️ FII Mix - CE {ce_entry} | PE {pe_entry}"

    except Exception as e:
        print(e)

    # FII Cash
    try:
        fii_cash = float(fii_data[0]['buyValue']) - float(fii_data[0]['sellValue'])
        dii_cash = float(fii_data[1]['buyValue']) - float(fii_data[1]['sellValue'])
        fii_text = f"FII {fii_cash/100:.0f}Cr {'BUY' if fii_cash>0 else 'SELL'} | DII {dii_cash/100:.0f}Cr"
    except:
        fii_text = "FII N/A"

    pcr_text = f"PCR {pcr:.2f} {'Oversold' if pcr>1.2 else 'Overbought' if pcr<0.8 else 'Neutral'}" if pcr else "PCR N/A"
    vix_text = f"VIX {vix:.1f}" if vix else "VIX N/A"
    liq = f"BSL {l5h:.0f}" if close>=l5h-30 else f"SSL {l5l:.0f}" if close<=l5l+30 else f"Range H{l5h:.0f} L{l5l:.0f}"

    # Patterns (short)
    pat = []
    if abs(highs[-1]-highs[-2])<40 and close>=l5h-30: pat.append("Double Top")
    if abs(lows[-1]-lows[-2])<40 and close<=l5l+30: pat.append("Double Bottom")
    if closes[-1]>closes[-2] and closes[-2]<closes[-3]: pat.append("Hammer/Bullish")

    final_pat = ", ".join(pat) if pat else "Range"

    msg = f"📊 *V7 FII OPTION RADAR*\n\n💰 {fii_text}\n📈 {pcr_text} | {vix_text}\nNIFTY {close:.0f} | {liq}\n\n🎯 *FII LIVE ENTRY:*\n{fii_option_msg}\n\n🕯️ Pattern: {final_pat}\n\n⏰ {datetime.datetime.now().strftime('%d-%m %I:%M %p')}\n\n⚡ Matlab: FII jaha OI badha raha hai, wahi SL rakh ke trade lo!"
    send_telegram(msg)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(check_market, 'cron', hour=9, minute=20, day_of_week='mon-fri')
    scheduler.add_job(check_market, 'cron', hour=11, minute=30, day_of_week='mon-fri')
    scheduler.add_job(check_market, 'cron', hour=14, minute=45, day_of_week='mon-fri')
    scheduler.start()
    check_market()
    import time
    while True: time.sleep(60)
