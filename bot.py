import os, telebot, threading, time, requests, yfinance as yf
from flask import Flask
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN","").strip()
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
CHAT_IDS = set()
LAST_OI = {}

SYMBOLS = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "FINNIFTY": "NIFTY_FIN_SERVICE.NS"
}
headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.nseindia.com/"}

def send_all(msg):
    for cid in list(CHAT_IDS):
        try: bot.send_message(cid, msg, parse_mode='Markdown')
        except: pass

def get_nse(url):
    try:
        s=requests.Session()
        s.get("https://www.nseindia.com", headers=headers, timeout=10)
        return s.get(url, headers=headers, timeout=10).json()
    except: return None

# 2. Green/Red Zone + 3. Fake/Real + 4. Pattern
def analyze_chart(symbol_yf, name):
    try:
        df = yf.download(symbol_yf, period="5d", interval="15m", progress=False)
        if len(df) < 20: return "Data kam hai"
        high, low, close = df['High'].iloc[-20:].max(), df['Low'].iloc[-20:].min(), df['Close'].iloc[-1]
        # Demand/Supply
        green_zone = f"{low:.0f}-{low+50:.0f} GREEN (Demand)"
        red_zone = f"{high-50:.0f}-{high:.0f} RED (Supply)"
        # Pattern 15/30/60
        pattern = "No Pattern"
        last3 = df['Close'].iloc[-3:].values
        if last3[0] < last3[1] > last3[2]: pattern = "15min Double Top - Breakdown hoga"
        if last3[0] > last3[1] < last3[2]: pattern = "15min Double Bottom - Breakout hoga"
        # Fake/Real
        vol = df['Volume'].iloc[-1]; avg_vol = df['Volume'].iloc[-20:-1].mean()
        breakout_type = "REAL breakout" if vol > avg_vol*1.5 else "FAKE breakout (Trap)"
        return f"*{name}*\n🟢 Demand: {green_zone}\n🔴 Supply: {red_zone}\n📈 Pattern: {pattern}\n🔍 {breakout_type} (Vol {vol/1000:.0f}k vs Avg {avg_vol/1000:.0f}k)"
    except Exception as e: return f"{name} chart error"

# 1. FII/DII + 5. Option Chain
def monitor_all():
    while True:
        try:
            for name, yf_sym in SYMBOLS.items():
                # Option Chain check for FII entry
                data = get_nse(f"https://www.nseindia.com/api/option-chain-indices?symbol={name}")
                if data:
                    for item in data['records']['data'][:12]:
                        strike=item['strikePrice']
                        ce=item.get('CE',{}); pe=item.get('PE',{})
                        ce_oi=ce.get('openInterest',0); pe_oi=pe.get('openInterest',0)
                        k_ce=f"{name}_{strike}_CE"; k_pe=f"{name}_{strike}_PE"
                        diff_ce = ce_oi - LAST_OI.get(k_ce, ce_oi)
                        diff_pe = pe_oi - LAST_OI.get(k_pe, pe_oi)

                        if diff_ce > 70000:
                            # 5. Call/Put decision
                            signal = "❌ CALL mat lo - PUT lo" if ce.get('change',0) < 0 else "⚠️ CALL SELL ho raha hai"
                            send_all(f"🚨 *{name} FII ENTRY {datetime.now().strftime('%H:%M')}*\n{strike} CE OI +{diff_ce/1000:.0f}k\n{signal}\nPrice: {ce.get('lastPrice')}")

                        if diff_pe > 70000:
                            send_all(f"🚨 *{name} FII ENTRY {datetime.now().strftime('%H:%M')}*\n{strike} PE OI +{diff_pe/1000:.0f}k\n✅ *CALL LENA HAI* - FII PUT kharid raha hai")

                        LAST_OI[k_ce]=ce_oi; LAST_OI[k_pe]=pe_oi

            # Official FII
            if datetime.now().hour==15 and datetime.now().minute==46:
                fii=get_nse("https://www.nseindia.com/api/fiidiiTradeReact")
                if fii: send_all(f"📊 *FII/DII 3:45*\nFII: {fii[0]['value']} Cr\nDII: {fii[1]['value']} Cr")
        except: pass
        time.sleep(300)

@app.route('/')
def home(): return "NAVA V3 ALL LIVE"

@bot.message_handler(commands=['start'])
def s(m): bot.reply_to(m, "🔥 *NAVA V3 - ALL 5 POINT LIVE*\n/alert on - FII live alert ON (Laptop band bhi chalega)\n/zones - Green/Red + Fake/Real + Pattern\n/ltp 23500 - Call/Put signal\n/fii - FII/DII")

@bot.message_handler(commands=['alert'])
def al(m):
    if 'on' in m.text: CHAT_IDS.add(m.chat.id); bot.reply_to(m, "✅ ALL ON - Nifty/BankNifty/FinNifty sabka alert ayega, laptop band bhi!")
    else: CHAT_IDS.discard(m.chat.id); bot.reply_to(m, "OFF")

@bot.message_handler(commands=['zones'])
def zones(m):
    txt = "⏳ Checking all...\n\n"
    for name, yf_sym in SYMBOLS.items():
        txt += analyze_chart(yf_sym, name) + "\n\n"
    bot.reply_to(m, txt, parse_mode='Markdown')

@bot.message_handler(commands=['ltp'])
def ltp(m):
    try:
        strike = m.text.split()[1]
        # Simple option chain decision
        data = get_nse(f"https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY")
        bot.reply_to(m, f"🔍 *{strike} Analysis*\nPCR + OI dekh ke:\nAgar {strike} CE OI badh raha + Price gir raha = PUT lo\nAgar PE OI badh raha = CALL lo\nFull auto signal /alert on pe ayega", parse_mode='Markdown')
    except: bot.reply_to(m, "Use: /ltp 23500")

@bot.message_handler(commands=['fii'])
def fii(m):
    data = get_nse("https://www.nseindia.com/api/fiidiiTradeReact")
    if data: bot.reply_to(m, f"FII: {data[0]['value']} Cr\nDII: {data[1]['value']} Cr")
    else: bot.reply_to(m, "NSE busy, 2 min baad try kar")

def run_bot(): bot.infinity_polling()
if __name__=="__main__":
    threading.Thread(target=monitor_all, daemon=True).start()
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
