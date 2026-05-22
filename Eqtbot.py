import MetaTrader5 as mt5
import pandas as pd
import time
import requests
from datetime import datetime

# =========================================================
# SETTINGS
# =========================================================
BOT_TOKEN = "8737122866:AAE55FmnwltxwyEqlkydqNNVa3HsNjcEt2s"
CHAT_ID = "6674481670"

SYMBOL = "XAUUSDm"

# MAIN SIGNAL TF
TIMEFRAME = mt5.TIMEFRAME_M15

# EMA SETTINGS
FAST_EMA = 12
SLOW_EMA = 26

# ATR SETTINGS
ATR_PERIOD = 14
ATR_SL_MULTIPLIER = 1.0

# RR
RISK_REWARD_RATIO = 5.0

# LIMIT
MAX_TRADES_PER_DAY = 3

# CHECK EVERY X SECONDS
SLEEP_SECONDS = 10

# =========================================================
# TELEGRAM
# =========================================================
def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        requests.get(
            url,
            params={
                "chat_id": CHAT_ID,
                "text": text
            },
            timeout=10
        )
    except Exception as e:
        print("Telegram Error:", e)

# =========================================================
# CONNECT MT5
# =========================================================
if not mt5.initialize():
    if not mt5.initialize("C:\\Program Files\\MetaTrader 5\\terminal64.exe"):
        print("❌ Failed to connect MT5")
        quit()

print("✅ Connected to MT5")
send_message("✅ EMA ATR BOT connected to MT5")

# =========================================================
# SYMBOL CHECK
# =========================================================
symbol_info = mt5.symbol_info(SYMBOL)

if symbol_info is None:
    print(f"❌ Symbol {SYMBOL} not found")
    mt5.shutdown()
    quit()

if not symbol_info.visible:
    mt5.symbol_select(SYMBOL, True)

# =========================================================
# FUNCTIONS
# =========================================================
def get_15m_data():
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 300)

    if rates is None or len(rates) == 0:
        return None

    df = pd.DataFrame(rates)

    df["time"] = pd.to_datetime(df["time"], unit="s")

    return df


def get_1h_atr():
    rates = mt5.copy_rates_from_pos(
        SYMBOL,
        mt5.TIMEFRAME_H1,
        0,
        200
    )

    if rates is None or len(rates) == 0:
        return None

    df = pd.DataFrame(rates)

    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ],
        axis=1
    ).max(axis=1)

    atr = tr.ewm(alpha=1 / ATR_PERIOD, adjust=False).mean()

    return atr.iloc[-2]


# =========================================================
# STATE
# =========================================================
last_signal_time = None
active_trade = None

daily_trade_count = {}
last_bar_time = None

# =========================================================
# MAIN LOOP
# =========================================================
while True:

    try:

        df = get_15m_data()

        if df is None:
            time.sleep(SLEEP_SECONDS)
            continue

        # =================================================
        # EMA
        # =================================================
        df["EMA_12"] = df["close"].ewm(
            span=FAST_EMA,
            adjust=False
        ).mean()

        df["EMA_26"] = df["close"].ewm(
            span=SLOW_EMA,
            adjust=False
        ).mean()

        # CLOSED CANDLE
        prev = df.iloc[-3]
        curr = df.iloc[-2]

        current_bar_time = curr["time"]

        # ONLY RUN ON NEW CLOSED BAR
        if last_bar_time == current_bar_time:
            time.sleep(SLEEP_SECONDS)
            continue

        last_bar_time = current_bar_time

        # =================================================
        # TRADE MANAGEMENT
        # =================================================
        if active_trade is not None:

            current_price = mt5.symbol_info_tick(SYMBOL).bid

            entry = active_trade["entry"]
            sl = active_trade["sl"]
            tp = active_trade["tp"]
            risk = active_trade["risk"]

            # =============================================
            # BUY
            # =============================================
            if active_trade["type"] == "BUY":

                # MOVE TO BE AT 1:2
                if (
                    not active_trade["be_moved"]
                    and current_price >= entry + (2 * risk)
                ):

                    active_trade["sl"] = entry
                    active_trade["be_moved"] = True

                    send_message(
                        "⚖️ Move SL to entry"
                    )

                # SL / BE HIT
                if current_price <= active_trade["sl"]:

                    if active_trade["be_moved"]:
                        send_message("⚖️ Break Even hit")
                    else:
                        send_message("❌ SL hit")

                    active_trade = None

                # TP HIT
                elif current_price >= tp:

                    send_message("🔥 Full TP smashed")

                    active_trade = None

            # =============================================
            # SELL
            # =============================================
            else:

                if (
                    not active_trade["be_moved"]
                    and current_price <= entry - (2 * risk)
                ):

                    active_trade["sl"] = entry
                    active_trade["be_moved"] = True

                    send_message(
                        "⚖️ Move SL to entry"
                    )

                # SL / BE HIT
                if current_price >= active_trade["sl"]:

                    if active_trade["be_moved"]:
                        send_message("⚖️ Break Even hit")
                    else:
                        send_message("❌ SL hit")

                    active_trade = None

                # TP HIT
                elif current_price <= tp:

                    send_message("🔥 Full TP smashed")

                    active_trade = None

        # =================================================
        # SIGNALS
        # =================================================
        if active_trade is None:

            today = datetime.now().date()

            trades_today = daily_trade_count.get(today, 0)

            # LIMIT DAILY TRADES
            if trades_today >= MAX_TRADES_PER_DAY:
                print("Daily trade limit reached")
                time.sleep(SLEEP_SECONDS)
                continue

            # EMA CROSS
            cross_above = (
                prev["EMA_12"] <= prev["EMA_26"]
                and curr["EMA_12"] > curr["EMA_26"]
            )

            cross_below = (
                prev["EMA_12"] >= prev["EMA_26"]
                and curr["EMA_12"] < curr["EMA_26"]
            )

            atr = get_1h_atr()

            if atr is None:
                time.sleep(SLEEP_SECONDS)
                continue

            # =================================================
            # BUY SIGNAL
            # =================================================
            if cross_above:

                entry = mt5.symbol_info_tick(SYMBOL).ask

                sl_distance = atr * ATR_SL_MULTIPLIER

                sl = entry - sl_distance

                risk = entry - sl

                tp = entry + (risk * RISK_REWARD_RATIO)

                active_trade = {
                    "type": "BUY",
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "risk": risk,
                    "be_moved": False
                }

                daily_trade_count[today] = trades_today + 1

                send_message(
                    f"🚀 EMA ATR SIGNAL\n\n"
                    f"👉 BUY GOLD\n\n"
                    f"Entry: {entry:.2f}\n"
                    f"🛑 SL: {sl:.2f}\n"
                    f"✅ TP: {tp:.2f}\n\n"
                    f"RR: 1:{RISK_REWARD_RATIO}\n"
                    f"SL Method: {ATR_SL_MULTIPLIER}x ATR({ATR_PERIOD}) 1H\n"
                    f"Timeframe: 15M\n\n"
                    f"⚠️ Risk only 1-3% per trade"
                )

                print("BUY SIGNAL SENT")

            # =================================================
            # SELL SIGNAL
            # =================================================
            elif cross_below:

                entry = mt5.symbol_info_tick(SYMBOL).bid

                sl_distance = atr * ATR_SL_MULTIPLIER

                sl = entry + sl_distance

                risk = sl - entry

                tp = entry - (risk * RISK_REWARD_RATIO)

                active_trade = {
                    "type": "SELL",
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "risk": risk,
                    "be_moved": False
                }

                daily_trade_count[today] = trades_today + 1

                send_message(
                    f"🚀 EMA ATR SIGNAL\n\n"
                    f"👉 SELL GOLD\n\n"
                    f"Entry: {entry:.2f}\n"
                    f"🛑 SL: {sl:.2f}\n"
                    f"✅ TP: {tp:.2f}\n\n"
                    f"RR: 1:{RISK_REWARD_RATIO}\n"
                    f"SL Method: {ATR_SL_MULTIPLIER}x ATR({ATR_PERIOD}) 1H\n"
                    f"Timeframe: 15M\n\n"
                    f"⚠️ Risk only 1-3% per trade"
                )

                print("SELL SIGNAL SENT")

        time.sleep(SLEEP_SECONDS)

    except Exception as e:

        print("ERROR:", e)

        time.sleep(10)