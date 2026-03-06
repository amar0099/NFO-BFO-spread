# ─────────────────────────────────────────────
# auto_token.py
# Fully automatic token generator using TOTP
# Run once manually or schedule it daily at 8:45am
# ─────────────────────────────────────────────

import os
import pyotp
import requests
import json
from fyers_apiv3 import fyersModel
from config import CLIENT_ID, SECRET_KEY, REDIRECT_URI, TOKEN_FILE

# ─────────────────────────────────────────────
# LOAD CREDENTIALS FROM ENVIRONMENT VARIABLES
# Set these once on your PC / server:
#
# Windows (PowerShell):
#   $env:FYERS_CLIENT_ID  = "XJ12345-100"
#   $env:FYERS_SECRET_KEY = "your_secret_key"
#   $env:FYERS_USERNAME   = "your_fyers_username"
#   $env:FYERS_PIN        = "1234"
#   $env:FYERS_TOTP_KEY   = "JBSWY3DPEHPK3PXP"
#
# To set permanently on Windows:
#   Search "Environment Variables" → System Properties
#   → Environment Variables → New (User variable)
# ─────────────────────────────────────────────

FYERS_CLIENT_ID  = os.environ.get("FYERS_CLIENT_ID",  CLIENT_ID)
FYERS_SECRET_KEY = os.environ.get("FYERS_SECRET_KEY",  SECRET_KEY)
FYERS_USERNAME   = os.environ.get("FYERS_USERNAME",   "")
FYERS_PIN        = os.environ.get("FYERS_PIN",        "")
FYERS_TOTP_KEY   = os.environ.get("FYERS_TOTP_KEY",   "")


def generate_totp():
    """Generate current 6-digit TOTP from secret key"""
    totp = pyotp.TOTP(FYERS_TOTP_KEY)
    return totp.now()


def auto_login():
    """
    Fully automated Fyers login using TOTP.
    No browser, no manual steps.
    """
    print("\n" + "="*50)
    print("   FYERS AUTO TOKEN GENERATOR")
    print("="*50)

    # Validate env vars
    missing = []
    if not FYERS_USERNAME: missing.append("FYERS_USERNAME")
    if not FYERS_PIN:      missing.append("FYERS_PIN")
    if not FYERS_TOTP_KEY: missing.append("FYERS_TOTP_KEY")

    if missing:
        print(f"\n❌ Missing environment variables: {', '.join(missing)}")
        print("   Please set them first. See instructions above.")
        return False

    print("\n[1/4] Generating TOTP...")
    totp_code = generate_totp()
    print(f"      ✅ TOTP: {totp_code}")

    print("\n[2/4] Sending login request to Fyers...")
    try:
        # Step 1 — Send login with TOTP
        session = fyersModel.SessionModel(
            client_id=FYERS_CLIENT_ID,
            secret_key=FYERS_SECRET_KEY,
            redirect_uri=REDIRECT_URI,
            response_type="code",
            grant_type="authorization_code"
        )

        # Fyers API v3 headless login
        login_response = session.generate_authcode_headless(
            identification=FYERS_USERNAME,
            otp=totp_code,
            pin=FYERS_PIN
        )

        if login_response.get("s") != "ok":
            print(f"\n❌ Login failed: {login_response}")
            return False

        auth_code = login_response.get("auth_code", "")
        if not auth_code:
            print(f"\n❌ No auth_code in response: {login_response}")
            return False

        print(f"      ✅ Auth code received!")

    except Exception as e:
        print(f"\n❌ Login error: {e}")
        return False

    print("\n[3/4] Generating access token...")
    try:
        session.set_token(auth_code)
        token_response = session.generate_token()

        if "access_token" not in token_response:
            print(f"\n❌ Token generation failed: {token_response}")
            return False

        access_token = token_response["access_token"]

    except Exception as e:
        print(f"\n❌ Token error: {e}")
        return False

    print("\n[4/4] Saving access token...")
    with open(TOKEN_FILE, "w") as f:
        f.write(access_token)

    print(f"      ✅ Token saved to '{TOKEN_FILE}'")
    print("\n" + "="*50)
    print("   ✅ READY! Run: streamlit run dashboard.py")
    print("="*50 + "\n")
    return True


if __name__ == "__main__":
    auto_login()
