# ─────────────────────────────────────────────
# auto_token.py
# Fully automated Fyers login using TOTP
# ─────────────────────────────────────────────

import os
import json
import pyotp
import requests
import hashlib
from urllib.parse import parse_qs, urlparse
from fyers_apiv3 import fyersModel

BASE_URL        = "https://api-t2.fyers.in/vagator/v2"
BASE_URL_2      = "https://api-t1.fyers.in/api/v3"
URL_SEND_OTP    = BASE_URL   + "/send_login_otp_v3"
URL_VERIFY_TOTP = BASE_URL   + "/verify_otp"
URL_VERIFY_PIN  = BASE_URL   + "/verify_pin_v2"
URL_TOKEN       = BASE_URL_2 + "/token"


def get_secret(key):
    """Read from Streamlit secrets or environment variables"""
    try:
        import streamlit as st
        val = st.secrets.get(key, "")
        if val:
            return str(val)
    except Exception:
        pass
    return os.environ.get(key, "")


def generate_token():
    """
    Fully automated Fyers login using TOTP via direct HTTP calls.
    Returns (access_token, error_message)
    """
    client_id  = get_secret("FYERS_CLIENT_ID")   # e.g. "XJ12345-100"
    secret_key = get_secret("FYERS_SECRET_KEY")
    username   = get_secret("FYERS_USERNAME")     # e.g. "XJ12345"
    pin        = get_secret("FYERS_PIN")          # 4 digit PIN as string
    totp_key   = get_secret("FYERS_TOTP_KEY")
    redirect_uri = "http://127.0.0.1:8080/"

    # Validate credentials
    missing = [k for k, v in {
        "FYERS_CLIENT_ID" : client_id,
        "FYERS_SECRET_KEY": secret_key,
        "FYERS_USERNAME"  : username,
        "FYERS_PIN"       : pin,
        "FYERS_TOTP_KEY"  : totp_key,
    }.items() if not v]

    if missing:
        return None, f"Missing credentials: {', '.join(missing)}"

    try:
        # Extract APP_ID (e.g. "XJ12345" from "XJ12345-100")
        app_id = client_id.split("-")[0]

        # SHA256 hash of client_id:secret_key
        app_id_hash = hashlib.sha256(
            f"{client_id}:{secret_key}".encode("utf-8")
        ).hexdigest()

        # ── STEP 1: Send login OTP ────────────
        r1 = requests.post(URL_SEND_OTP, json={
            "fy_id" : username,
            "app_id": "2"
        }, timeout=10)
        r1_data = r1.json()
        if r1_data.get("s") != "ok":
            return None, f"Step 1 (send OTP) failed: {r1_data}"

        request_key = r1_data["request_key"]

        # ── STEP 2: Verify TOTP ───────────────
        totp_code = pyotp.TOTP(totp_key).now()
        r2 = requests.post(URL_VERIFY_TOTP, json={
            "request_key"  : request_key,
            "identity_type": "totp",
            "identifier"   : totp_code
        }, timeout=10)
        r2_data = r2.json()
        if r2_data.get("s") != "ok":
            return None, f"Step 2 (verify TOTP) failed: {r2_data}"

        request_key2 = r2_data["request_key"]

        # ── STEP 3: Verify PIN ────────────────
        r3 = requests.post(URL_VERIFY_PIN, json={
            "request_key"  : request_key2,
            "identity_type": "pin",
            "identifier"   : pin
        }, timeout=10)
        r3_data = r3.json()
        if r3_data.get("s") != "ok":
            return None, f"Step 3 (verify PIN) failed: {r3_data}"

        access_token_trade = r3_data["data"]["access_token"]

        # ── STEP 4: Get auth code ─────────────
        r4 = requests.post(URL_TOKEN, json={
            "fyers_id"     : username,
            "app_id"       : app_id,
            "redirect_uri" : redirect_uri,
            "appType"      : "100",
            "code_challenge": "",
            "state"        : "sample",
            "scope"        : "",
            "nonce"        : "",
            "response_type": "code",
            "create_cookie": True
        }, headers={"Authorization": f"Bearer {access_token_trade}"}, timeout=10)
        r4_data = r4.json()
        if r4_data.get("s") != "ok":
            return None, f"Step 4 (get auth code) failed: {r4_data}"

        auth_code = parse_qs(
            urlparse(r4_data["Url"]).query
        ).get("auth_code", [None])[0]

        if not auth_code:
            return None, f"Could not extract auth_code from URL: {r4_data}"

        # ── STEP 5: Exchange for access token ─
        session = fyersModel.SessionModel(
            client_id=client_id,
            secret_key=secret_key,
            redirect_uri=redirect_uri,
            response_type="code",
            grant_type="authorization_code"
        )
        session.set_token(auth_code)
        r5_data = session.generate_token()

        access_token = r5_data.get("access_token")
        if not access_token:
            return None, f"Step 5 (token exchange) failed: {r5_data}"

        return access_token, None

    except Exception as e:
        return None, f"Exception: {str(e)}"
