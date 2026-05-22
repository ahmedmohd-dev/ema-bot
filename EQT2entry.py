import MetaTrader5 as mt5
import pandas as pd
import requests
import time


# =========================================================
# TELEGRAM
# =========================================================

BOT_TOKEN = "8737122866:AAE55FmnwltxwyEqlkydqNNVa3HsNjcEt2s"
CHAT_ID = "6674481670"

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
# CONFIG
# =========================================================

SYMBOL = "XAUUSDm"

TIMEFRAME = mt5.TIMEFRAME_M15

FAST_EMA = 12
SLOW_EMA = 26

ATR_PERIOD = 14
ATR_SL_MULTIPLIER = 1.0

RR = 5.0

FIRST_TRADE_RISK = 300.0
SECOND_TRADE_RISK = 700.0

SECOND_ENTRY_DROP = 10.0

MAX_TRADES_PER_DAY = 3

CHECK_INTERVAL = 5


# =========================================================
# CONNECT MT5
# =========================================================

if not mt5.initialize():

    if not mt5.initialize(
        "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
    ):

        print("❌ Failed to connect MT5")
        quit()

print("✅ Connected to MT5")

send_message(
    "✅ EMA Scale-In Bot Connected"
)


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
# ATR
# =========================================================

def compute_atr(df, period=14):

    high = df["high"]

    low = df["low"]

    prev_close = df["close"].shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1
    ).max(axis=1)

    return tr.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()


# =========================================================
# STATE
# =========================================================

pending_buy = False

trade1 = None
trade2 = None

second_entry_taken = False

last_bar_time = None

daily_trade_count = {}


# =========================================================
# MAIN LOOP
# =========================================================

while True:

    try:

        rates = mt5.copy_rates_from_pos(
            SYMBOL,
            TIMEFRAME,
            0,
            500
        )

        if rates is None or len(rates) == 0:

            time.sleep(CHECK_INTERVAL)

            continue

        df = pd.DataFrame(rates)

        df["time"] = pd.to_datetime(
            df["time"],
            unit="s"
        )

        # =================================================
        # EMA
        # =================================================

        df["ema12"] = df["close"].ewm(
            span=FAST_EMA,
            adjust=False
        ).mean()

        df["ema26"] = df["close"].ewm(
            span=SLOW_EMA,
            adjust=False
        ).mean()

        # =================================================
        # ATR
        # =================================================

        df["atr"] = compute_atr(
            df,
            ATR_PERIOD
        )

        prev = df.iloc[-2]
        curr = df.iloc[-1]

        current_bar_time = curr["time"]

        # =================================================
        # ONLY NEW CANDLE
        # =================================================

        if last_bar_time == current_bar_time:

            time.sleep(CHECK_INTERVAL)

            continue

        last_bar_time = current_bar_time

        o = float(curr["open"])
        h = float(curr["high"])
        l = float(curr["low"])
        c = float(curr["close"])

        print(f"\n🕒 New Candle: {current_bar_time}")

        # =================================================
        # EXECUTE FIRST TRADE
        # =================================================

        if pending_buy and trade1 is None:

            atr = float(curr["atr"])

            sl_distance = ATR_SL_MULTIPLIER * atr

            if sl_distance > 0:

                units1 = FIRST_TRADE_RISK / sl_distance

                sl_price = o - sl_distance

                tp_price = (
                    o + (sl_distance * RR)
                )

                trade1 = {
                    "entry": o,
                    "sl": sl_price,
                    "tp": tp_price,
                    "units": units1,
                    "risk_amount": FIRST_TRADE_RISK,
                }

                second_entry_taken = False

                send_message(
                    f"🔥 GOLD BUY\n\n"
                    f"Entry: {o:.2f}\n"
                    f"🛑 SL: {sl_price:.2f}\n"
                    f"🎯 TP: {tp_price:.2f}\n\n"
                    f"Risk: ${FIRST_TRADE_RISK:.0f}\n"
                    f"EMA Scale-In Strategy"
                )

                print("✅ FIRST BUY SENT")

            pending_buy = False

        # =================================================
        # SECOND ENTRY
        # =================================================

        if (
            trade1 is not None
            and trade2 is None
            and not second_entry_taken
        ):

            trigger_price = (
                trade1["entry"]
                - SECOND_ENTRY_DROP
            )

            if l <= trigger_price:

                risk_distance = (
                    trigger_price
                    - trade1["sl"]
                )

                if risk_distance > 0:

                    units2 = (
                        SECOND_TRADE_RISK
                        / risk_distance
                    )

                    tp2 = (
                        trigger_price
                        + (risk_distance * RR)
                    )

                    trade2 = {
                        "entry": trigger_price,
                        "sl": trade1["sl"],
                        "tp": tp2,
                        "units": units2,
                        "risk_amount": SECOND_TRADE_RISK,
                    }

                    second_entry_taken = True

                    send_message(
                        f"🔥 GOLD BUY AGAIN\n\n"
                        f"Entry: {trigger_price:.2f}\n"
                        f"🛑 SL: {trade1['sl']:.2f}\n"
                        f"🎯 TP: {tp2:.2f}\n\n"
                        f"Risk: ${SECOND_TRADE_RISK:.0f}\n"
                        f"EMA Scale-In Strategy"
                    )

                    print("✅ SECOND BUY SENT")

        # =================================================
        # TRADE 1 MANAGEMENT
        # =================================================

        if trade1 is not None:

            hit_sl = l <= trade1["sl"]

            hit_tp = h >= trade1["tp"]

            if hit_sl or hit_tp:

                if hit_tp:

                    exit_price = trade1["tp"]

                    pnl_points = (
                        exit_price
                        - trade1["entry"]
                    )

                    send_message(
                        f"✅ CLOSE FIRST BUY NOW\n\n"
                        f"Exit: {exit_price:.2f}\n"
                        f"Profit: +{pnl_points:.2f} points"
                    )

                else:

                    exit_price = trade1["sl"]

                    pnl_points = (
                        exit_price
                        - trade1["entry"]
                    )

                    send_message(
                        f"❌ CLOSE FIRST BUY NOW\n\n"
                        f"Exit: {exit_price:.2f}\n"
                        f"Loss: {pnl_points:.2f} points"
                    )

                # CLOSE SECOND TRADE TOO
                if trade2 is not None:

                    pnl2 = (
                        exit_price
                        - trade2["entry"]
                    )

                    if pnl2 >= 0:

                        send_message(
                            f"✅ CLOSE SECOND BUY NOW\n\n"
                            f"Exit: {exit_price:.2f}\n"
                            f"Profit: +{pnl2:.2f} points"
                        )

                    else:

                        send_message(
                            f"❌ CLOSE SECOND BUY NOW\n\n"
                            f"Exit: {exit_price:.2f}\n"
                            f"Loss: {pnl2:.2f} points"
                        )

                    trade2 = None

                trade1 = None

                second_entry_taken = False

        # =================================================
        # SECOND TRADE TP
        # =================================================

        if trade2 is not None:

            if h >= trade2["tp"]:

                exit_price = trade2["tp"]

                pnl2 = (
                    exit_price
                    - trade2["entry"]
                )

                send_message(
                    f"🔥 CLOSE SECOND BUY NOW\n\n"
                    f"Exit: {exit_price:.2f}\n"
                    f"Profit: +{pnl2:.2f} points"
                )

                trade2 = None

        # =================================================
        # EMA CROSS EXIT
        # =================================================

        cross_below = (
            prev["ema12"] >= prev["ema26"]
            and
            curr["ema12"] < curr["ema26"]
        )

        if trade1 is not None and cross_below:

            exit_price = o

            pnl1 = (
                exit_price
                - trade1["entry"]
            )

            if pnl1 >= 0:

                send_message(
                    f"⚠️ EMA CROSS EXIT\n\n"
                    f"CLOSE FIRST BUY NOW\n"
                    f"Exit: {exit_price:.2f}\n"
                    f"Profit: +{pnl1:.2f} points"
                )

            else:

                send_message(
                    f"⚠️ EMA CROSS EXIT\n\n"
                    f"CLOSE FIRST BUY NOW\n"
                    f"Exit: {exit_price:.2f}\n"
                    f"Loss: {pnl1:.2f} points"
                )

            if trade2 is not None:

                pnl2 = (
                    exit_price
                    - trade2["entry"]
                )

                if pnl2 >= 0:

                    send_message(
                        f"⚠️ EMA CROSS EXIT\n\n"
                        f"CLOSE SECOND BUY NOW\n"
                        f"Exit: {exit_price:.2f}\n"
                        f"Profit: +{pnl2:.2f} points"
                    )

                else:

                    send_message(
                        f"⚠️ EMA CROSS EXIT\n\n"
                        f"CLOSE SECOND BUY NOW\n"
                        f"Exit: {exit_price:.2f}\n"
                        f"Loss: {pnl2:.2f} points"
                    )

                trade2 = None

            trade1 = None

            second_entry_taken = False

        # =================================================
        # BUY SIGNAL
        # =================================================

        today = current_bar_time.date()

        trades_today = daily_trade_count.get(
            today,
            0
        )

        cross_above = (
            prev["ema12"] <= prev["ema26"]
            and
            curr["ema12"] > curr["ema26"]
        )

        if (
            cross_above
            and trade1 is None
            and trades_today < MAX_TRADES_PER_DAY
        ):

            pending_buy = True

            daily_trade_count[today] = (
                trades_today + 1
            )

            print("📈 BUY SIGNAL DETECTED")

        time.sleep(CHECK_INTERVAL)

    except Exception as e:

        print("ERROR:", e)

        time.sleep(10)