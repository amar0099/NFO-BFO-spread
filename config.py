# ─────────────────────────────────────────────
# config.py — Only edit API credentials here
# All strikes, expiry, exchange are set from
# the dashboard sidebar — no need to touch this
# ─────────────────────────────────────────────

# Fyers API Credentials (from myapi.fyers.in)
CLIENT_ID    = "0Z0FI0BJS0-100"    # e.g. "XJ12345-100"
SECRET_KEY   = "MZS89VWU3I"    # long string from Fyers dashboard
REDIRECT_URI = "http://127.0.0.1:8080/"

# Token file path
TOKEN_FILE   = "access_token.txt"

# Auto-refresh default (seconds) — changeable in sidebar too
REFRESH_SECONDS = 10

# Save candle data to CSV automatically
SAVE_TO_CSV = False
CSV_FOLDER  = "data"
