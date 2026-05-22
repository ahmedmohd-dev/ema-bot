import MetaTrader5 as mt5
import pandas as pd
import time
import requests

# ===== SETTINGS =====
BOT_TOKEN = "8737122866:AAE55FmnwltxwyEqlkydqNNVa3HsNjcEt2s"
CHAT_ID = "6674481670"

SYMBOL = "XAUUSDm"
TIMEFRAME = mt5.TIMEFRAME_M1

# ===== TELEGRAM FUNCTION =====
def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.get(url, params={"chat_id": CHAT_ID, "text": text})

# ===== CONNECT TO MT5 =====
if not mt5.initialize():
    print("Default connection failed, trying with path...")

    # 👉 CHANGE THIS PATH if needed
    if not mt5.initialize("C:\Program Files\MetaTrader 5\terminal64.exe"):
        print("❌ Failed to connect to MT5")
        print("Error:", mt5.last_error())
        quit()

print("✅ Connected to MT5")
send_message("✅ Bot is running and connected to MT5")
send_message("🟢 TEST BUY SIGNAL")
send_message("🔴 TEST SELL SIGNAL")
# ===== CHECK SYMBOL =====
symbol_info = mt5.symbol_info(SYMBOL)
if symbol_info is None:
    print(f"❌ Symbol {SYMBOL} not found")
    mt5.shutdown()
    quit()

if not symbol_info.visible:
    mt5.symbol_select(SYMBOL, True)

last_signal = None

# ===== MAIN LOOP =====
while True:
    try:
        rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 100)

        # SAFETY CHECK
        if rates is None or len(rates) == 0:
            print("⚠️ No data received")
            time.sleep(30)
            continue

        df = pd.DataFrame(rates)

        # EMA CALCULATION
        df["ema12"] = df["close"].ewm(span=12).mean()
        df["ema26"] = df["close"].ewm(span=26).mean()

        prev = df.iloc[-2]
        curr = df.iloc[-1]

        # ===== BUY SIGNAL =====
        if prev["ema12"] < prev["ema26"] and curr["ema12"] > curr["ema26"]:
            if last_signal != "BUY":
                send_message("🟢 BUY XAUUSDm now")
                print("🟢 BUY signal sent")
                last_signal = "BUY"

        # ===== SELL SIGNAL =====
        elif prev["ema12"] > prev["ema26"] and curr["ema12"] < curr["ema26"]:
            if last_signal != "SELL":
                send_message("🔴 SELL XAUUSDm now")
                print("🔴 SELL signal sent")
                last_signal = "SELL"

        time.sleep(30)

    except Exception as e:
        print("Error:", e)
        time.sleep(30)