import pandas as pd
import numpy as np

# Load data
import pandas as pd
import numpy as np

# Load data
df = pd.read_csv("xauusd_m1.csv")

# Clean column names (VERY IMPORTANT)
df.columns = df.columns.str.strip().str.upper()

print("Columns:", df.columns)  # debug

# Combine DATE + TIME
df['time'] = pd.to_datetime(df['DATE'] + ' ' + df['TIME'])

# Rename columns
df = df.rename(columns={
    'OPEN': 'open',
    'HIGH': 'high',
    'LOW': 'low',
    'CLOSE': 'close'
})

# Keep needed columns
df = df[['time', 'open', 'high', 'low', 'close']]

# Convert columns
df['time'] = pd.to_datetime(df['DATE'] + ' ' + df['TIME'])

df = df.rename(columns={
    'OPEN': 'open',
    'HIGH': 'high',
    'LOW': 'low',
    'CLOSE': 'close'
})

# Keep needed columns
df = df[['time', 'open', 'high', 'low', 'close']]

# EMA calculation
df['ema20'] = df['close'].ewm(span=20).mean()
df['ema50'] = df['close'].ewm(span=50).mean()

# Detect cross
df['signal'] = 0
df['signal'] = np.where(
    (df['ema20'] > df['ema50']) & (df['ema20'].shift(1) <= df['ema50'].shift(1)),
    1,
    df['signal']
)
df['signal'] = np.where(
    (df['ema20'] < df['ema50']) & (df['ema20'].shift(1) >= df['ema50'].shift(1)),
    -1,
    df['signal']
)

# Session classification
def get_session(hour):
    if 0 <= hour < 8:
        return "Asian"
    elif 8 <= hour < 16:
        return "London"
    else:
        return "NewYork"

df['session'] = df['time'].dt.hour.apply(get_session)

# Backtest
trades = []
pip = 0.1  # adjust if needed

for i in range(len(df) - 2):
    if df.loc[i, 'signal'] != 0:

        direction = df.loc[i, 'signal']
        entry = df.loc[i + 1, 'close']
        cross_price = df.loc[i, 'close']
        session = df.loc[i, 'session']

        # SL & TP
        if direction == 1:  # BUY
            sl = cross_price - (10 * pip)
            risk = entry - sl
            tp = entry + (5 * risk)
        else:  # SELL
            sl = cross_price + (10 * pip)
            risk = sl - entry
            tp = entry - (5 * risk)

        # Forward check
        for j in range(i + 2, len(df)):
            high = df.loc[j, 'high']
            low = df.loc[j, 'low']

            if direction == 1:
                if low <= sl:
                    trades.append((session, -1))
                    break
                elif high >= tp:
                    trades.append((session, 1))
                    break
            else:
                if high >= sl:
                    trades.append((session, -1))
                    break
                elif low <= tp:
                    trades.append((session, 1))
                    break

# Convert to DataFrame
results = pd.DataFrame(trades, columns=['session', 'result'])

# Overall stats
total = len(results)
wins = (results['result'] == 1).sum()
losses = (results['result'] == -1).sum()

print("===== OVERALL =====")
print("Total trades:", total)
print("Wins:", wins)
print("Losses:", losses)
print("Win rate:", round(wins / total * 100, 2) if total > 0 else 0, "%")

# Session stats
print("\n===== SESSION PERFORMANCE =====")

session_stats = results.groupby('session')['result'].agg(
    total='count',
    wins=lambda x: (x == 1).sum(),
    losses=lambda x: (x == -1).sum()
)

session_stats['win_rate'] = (session_stats['wins'] / session_stats['total']) * 100

print(session_stats)