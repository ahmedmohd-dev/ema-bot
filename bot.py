import MetaTrader5 as mt5
import pandas as pd
import time
import requests

# ===== SETTINGS =====
BOT_TOKEN = "8567849177:AAFxsueSGVHcOpEI1a0DVgIY1vu-jIl9Fbc"
CHAT_ID = "6674481670"

SYMBOL = "XAUUSDm"
TIMEFRAME = mt5.TIMEFRAME_M1

RR = 4
BE_RR = 2
PIP_VALUE = 1.0

# ===== TELEGRAM FUNCTION =====
def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.get(url, params={"chat_id": CHAT_ID, "text": text})

# ===== CONNECT TO MT5 =====
if not mt5.initialize():
    if not mt5.initialize("C:\\Program Files\\MetaTrader 5\\terminal64.exe"):
        print("❌ Failed to connect to MT5")
        quit()
    

print("✅ Connected to MT5")
send_message("✅ Bot is running and connected to MT5")

# ===== SYMBOL CHECK =====
symbol_info = mt5.symbol_info(SYMBOL)
if symbol_info is None:
    print(f"❌ Symbol {SYMBOL} not found")
    mt5.shutdown()
    quit()

if not symbol_info.visible:
    mt5.symbol_select(SYMBOL, True)

# ===== STATE =====
last_signal = None
active_trade = None  # store current trade

# ===== MAIN LOOP =====
while True:
    try:
        rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 100)

        if rates is None or len(rates) == 0:
            time.sleep(10)
            continue

        df = pd.DataFrame(rates)

        # ===== EMA =====
        df["ema12"] = df["close"].ewm(span=12).mean()
        df["ema26"] = df["close"].ewm(span=26).mean()

        prev = df.iloc[-2]
        curr = df.iloc[-1]

        price = curr["close"]

        # ==============================
        # CHECK ACTIVE TRADE
        # ==============================
        if active_trade is not None:
            high = curr["high"]
            low = curr["low"]

            entry = active_trade["entry"]
            sl = active_trade["sl"]
            tp = active_trade["tp"]
            risk = active_trade["risk"]
            direction = active_trade["type"]

            # ===== BUY MANAGEMENT =====
            if direction == "BUY":

                # BE TRIGGER
                if not active_trade["be"] and high >= entry + BE_RR * risk:
                    active_trade["sl"] = entry
                    active_trade["be"] = True
                    send_message("⚖️ Move SL to entry")

                # SL HIT
                if low <= active_trade["sl"]:
                    if active_trade["be"]:
                        send_message("⚖️ Break Even hit")
                    else:
                        send_message("❌ SL hit")
                    active_trade = None

                # TP HIT
                elif high >= tp:
                    send_message("🔥 Full TP smashed")
                    active_trade = None

            # ===== SELL MANAGEMENT =====
            else:

                if not active_trade["be"] and low <= entry - BE_RR * risk:
                    active_trade["sl"] = entry
                    active_trade["be"] = True
                    send_message("⚖️ Move SL to entry")

                if high >= active_trade["sl"]:
                    if active_trade["be"]:
                        send_message("⚖️ Break Even hit")
                    else:
                        send_message("❌ SL hit")
                    active_trade = None

                elif low <= tp:
                    send_message("🔥 Full TP smashed")
                    active_trade = None

        # ==============================
        # NEW SIGNAL (ONLY IF NO TRADE)
        # ==============================
        if active_trade is None:

            # ===== BUY =====
            if prev["ema12"] < prev["ema26"] and curr["ema12"] > curr["ema26"]:
                if last_signal != "BUY":

                    entry = price

                    cross_price = (curr["ema12"] + curr["ema26"]) / 2
                    sl = cross_price - PIP_VALUE
                    risk = entry - sl
                    tp = entry + RR * risk

                    if risk > 0:
                        active_trade = {
                            "type": "BUY",
                            "entry": entry,
                            "sl": sl,
                            "tp": tp,
                            "risk": risk,
                            "be": False
                        }

                        send_message(
                            f"HIGH risk traDE ☠️\n"
                            f"👉🏾 BUY GOLD\n"
                            f"Entry {entry:.2f}\n"
                            f"🛑 SL {sl:.2f}\n"
                            f"✅ TP {tp:.2f}\n"
                            f"disclaimer: Past  Profits do not predict future earnings. Risk only 1-3 % per position.\n"
                            f"No automatic reward."
                        )

                        last_signal = "BUY"

            # ===== SELL =====
            elif prev["ema12"] > prev["ema26"] and curr["ema12"] < curr["ema26"]:
                if last_signal != "SELL":

                    entry = price

                    cross_price = (curr["ema12"] + curr["ema26"]) / 2
                    sl = cross_price + PIP_VALUE
                    risk = sl - entry
                    tp = entry - RR * risk

                    if risk > 0:
                        active_trade = {
                            "type": "SELL",
                            "entry": entry,
                            "sl": sl,
                            "tp": tp,
                            "risk": risk,
                            "be": False
                        }

                        send_message(
                            f"HIGH risk traDE ☠️\n"
                            f"👉🏾 SELL GOLD\n"
                            f"Entry {entry:.2f}\n"
                            f"🛑 SL {sl:.2f}\n"
                            f"✅ TP {tp:.2f}\n"
                            f"disclaimer: Past  Profits do not predict future earnings. Risk only 1-3 % per position.\n"
                            f"No automatic reward."
                        )

                        last_signal = "SELL"

        time.sleep(5)

    except Exception as e:
        print("Error:", e)
        time.sleep(10)