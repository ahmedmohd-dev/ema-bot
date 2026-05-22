import pandas as pd
import numpy as np

# ==============================
# CONFIG
# ==============================
RISK_PER_TRADE = 0.003   # 0.3%
RR = 4                   # 1:4
BE_RR = 2                # break even at 1:2
PIP_VALUE = 1.0          # 10 pips = 1.0 for XAUUSD

# ==============================
# LOAD DATA
# ==============================
def load_data(path):
    df = pd.read_csv(path, sep="\t")
    df.columns = df.columns.str.replace("<", "").str.replace(">", "").str.strip()
    
    df["datetime"] = pd.to_datetime(df["DATE"] + " " + df["TIME"])
    df = df.sort_values("datetime").reset_index(drop=True)

    return df


# ==============================
# INDICATORS
# ==============================
def calculate_indicators(df):
    df["ema20"] = df["CLOSE"].ewm(span=20).mean()
    df["ema50"] = df["CLOSE"].ewm(span=50).mean()
    return df


# ==============================
# SIGNALS
# ==============================
def generate_signals(df):
    signals = []

    for i in range(1, len(df)):
        prev_fast = df.iloc[i-1]["ema20"]
        prev_slow = df.iloc[i-1]["ema50"]
        curr_fast = df.iloc[i]["ema20"]
        curr_slow = df.iloc[i]["ema50"]

        if prev_fast < prev_slow and curr_fast > curr_slow:
            signals.append((i, "BUY"))
        elif prev_fast > prev_slow and curr_fast < curr_slow:
            signals.append((i, "SELL"))

    return signals


# ==============================
# BACKTEST ENGINE
# ==============================
def run_backtest(df, signals):
    balance = 1000
    equity_curve = []
    trades = []

    for idx, signal in signals:
        if idx + 1 >= len(df):
            continue

        # Entry at next candle open
        entry_row = df.iloc[idx + 1]
        entry_price = entry_row["OPEN"]

        spread = entry_row["SPREAD"] / 1000  # adjust if needed

        if signal == "BUY":
            entry_price += spread

        # SL (simple method)
        ema20 = df.iloc[idx]["ema20"]
        ema50 = df.iloc[idx]["ema50"]
        cross_price = (ema20 + ema50) / 2

        if signal == "BUY":
            sl = cross_price - PIP_VALUE
            risk = entry_price - sl
            tp = entry_price + RR * risk
        else:
            sl = cross_price + PIP_VALUE
            risk = sl - entry_price
            tp = entry_price - RR * risk

        if risk <= 0:
            continue

        # position sizing
        risk_amount = balance * RISK_PER_TRADE
        lot = risk_amount / risk

        # simulate trade forward
        trade_result = None
        be_triggered = False

        for j in range(idx + 1, len(df)):
            row = df.iloc[j]

            high = row["HIGH"]
            low = row["LOW"]

            if signal == "BUY":
                # BE trigger
                if not be_triggered and high >= entry_price + BE_RR * risk:
                    sl = entry_price
                    be_triggered = True

                if low <= sl:
                    trade_result = (sl - entry_price) * lot
                    break
                elif high >= tp:
                    trade_result = (tp - entry_price) * lot
                    break

            else:
                if not be_triggered and low <= entry_price - BE_RR * risk:
                    sl = entry_price
                    be_triggered = True

                if high >= sl:
                    trade_result = (entry_price - sl) * lot
                    break
                elif low <= tp:
                    trade_result = (entry_price - tp) * lot
                    break

        if trade_result is not None:
            balance += trade_result
            equity_curve.append(balance)

            trades.append({
                "type": signal,
                "entry": entry_price,
                "sl": sl,
                "tp": tp,
                "profit": trade_result,
                "balance": balance
            })

    return trades, equity_curve


# ==============================
# MAIN
# ==============================
df = load_data("xauusd_m1.csv")
df = calculate_indicators(df)
signals = generate_signals(df)

trades, equity = run_backtest(df, signals)

print(f"Total Trades: {len(trades)}")
print(f"Final Balance: {equity[-1] if equity else 1000}")