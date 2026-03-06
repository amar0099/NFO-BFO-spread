# ─────────────────────────────────────────────
# data_fetcher.py
# Fetches candle data from Fyers API
# ─────────────────────────────────────────────

import pandas as pd
import os
from datetime import date
from fyers_apiv3 import fyersModel
from config import CLIENT_ID, TOKEN_FILE, SAVE_TO_CSV, CSV_FOLDER

# ─────────────────────────────────────────────
# FYERS SYMBOL FORMAT
# Correct format confirmed:
# BSE: BSE:SENSEX2631280000CE  → YYMDD (no leading zero on month)
# NSE: NSE:NIFTY2631324800CE   → YYMDD (no leading zero on month)
# Strike comes BEFORE CE/PE
# No -OPT suffix
# ─────────────────────────────────────────────

def build_symbol(exchange, underlying, expiry, option_type, strike):
    """
    Builds correct Fyers symbol string.

    expiry     : YYMMDD string e.g. "260312"
    option_type: "C" or "CE" for Call, "P" or "PE" for Put
    strike     : integer e.g. 80000

    Output example:
      BSE:SENSEX2631280000CE
      NSE:NIFTY2631324800CE
    """
    # Normalize CE/PE
    ot = "CE" if option_type.upper() in ("C", "CE") else "PE"

    # Convert YYMMDD → YYMDD (strip leading zero from month)
    # e.g. "260312" → yy="26", mm="03", dd="12" → "26312"
    yy           = expiry[0:2]
    mm           = expiry[2:4]
    dd           = expiry[4:6]
    expiry_fyers = yy + str(int(mm)) + dd   # "26312"

    return f"{exchange}:{underlying}{expiry_fyers}{strike}{ot}"


# ─────────────────────────────────────────────
# LOAD FYERS CLIENT
# ─────────────────────────────────────────────

def load_fyers():
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(
            f"'{TOKEN_FILE}' not found. Please run token_gen.py first!"
        )
    with open(TOKEN_FILE, "r") as f:
        access_token = f.read().strip()

    fyers = fyersModel.FyersModel(
        client_id=CLIENT_ID,
        token=access_token,
        log_path=""
    )
    return fyers


# ─────────────────────────────────────────────
# FETCH CANDLES FOR ONE SYMBOL
# ─────────────────────────────────────────────

def fetch_candles(fyers, symbol, interval, date_str=None):
    """
    Fetches OHLCV candles for a symbol.
    date_str : "YYYY-MM-DD", defaults to today
    Returns  : DataFrame indexed by datetime (IST)
    """
    if date_str is None:
        date_str = date.today().strftime("%Y-%m-%d")

    data = {
        "symbol"      : symbol,
        "resolution"  : str(interval),
        "date_format" : "1",
        "range_from"  : date_str,
        "range_to"    : date_str,
        "cont_flag"   : "1"
    }

    response = fyers.history(data=data)

    if response.get("s") != "ok":
        print(f"  No data for {symbol}: {response.get('message', 'unknown error')}")
        return pd.DataFrame()

    candles = response["candles"]
    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["datetime"] = (
        pd.to_datetime(df["timestamp"], unit="s")
        .dt.tz_localize("UTC")
        .dt.tz_convert("Asia/Kolkata")
        .dt.tz_localize(None)
    )
    df = df.drop(columns=["timestamp"]).set_index("datetime")
    return df


# ─────────────────────────────────────────────
# SAVE / LOAD CSV
# ─────────────────────────────────────────────

def save_to_csv(df, date_str=None):
    if date_str is None:
        date_str = date.today().strftime("%Y-%m-%d")
    os.makedirs(CSV_FOLDER, exist_ok=True)
    filepath = os.path.join(CSV_FOLDER, f"spread_{date_str}.csv")
    df.to_csv(filepath)
    print(f"Saved to {filepath}")


def load_from_csv(date_str):
    filepath = os.path.join(CSV_FOLDER, f"spread_{date_str}.csv")
    if os.path.exists(filepath):
        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        return df
    return pd.DataFrame()


# ─────────────────────────────────────────────
# FETCH SPOT PRICE (latest quote)
# NSE:NIFTY50-INDEX  / BSE:SENSEX-INDEX
# ─────────────────────────────────────────────

def fetch_spot_candles(fyers, symbol, interval, date_str=None):
    """
    Fetches candles for a spot index symbol.
    Returns DataFrame indexed by datetime (IST)
    """
    return fetch_candles(fyers, symbol, interval, date_str)


def round_to(value, base):
    """Round value to nearest base (e.g. 100)"""
    return int(round(value / base) * base)
