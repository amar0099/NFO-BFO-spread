# ─────────────────────────────────────────────
# auto_token.py
# Generates Fyers token using TOTP
# Works both locally and on Streamlit Cloud
# ─────────────────────────────────────────────

import os
import pyotp

def get_secret(key):
    """
    Read from Streamlit secrets (hosted) or
    environment variables (local)
    """
    try:
        import streamlit as st
        return st.secrets.get(key, os.environ.get(key, ""))
    except Exception:
        return os.environ.get(key, "")


def generate_token():
    """
    Auto-generate Fyers access token using TOTP.
    Returns access_token string or None on failure.
    """
    from fyers_apiv3 import fyersModel

    client_id  = get_secret("FYERS_CLIENT_ID")
    secret_key = get_secret("FYERS_SECRET_KEY")
    username   = get_secret("FYERS_USERNAME")
    pin        = get_secret("FYERS_PIN")
    totp_key   = get_secret("FYERS_TOTP_KEY")

    # Validate
    missing = [k for k, v in {
        "FYERS_CLIENT_ID" : client_id,
        "FYERS_SECRET_KEY": secret_key,
        "FYERS_USERNAME"  : username,
        "FYERS_PIN"       : pin,
        "FYERS_TOTP_KEY"  : totp_key,
    }.items() if not v]

    if missing:
        print(f"Missing credentials: {', '.join(missing)}")
        return None

    try:
        # Generate TOTP
        totp_code = pyotp.TOTP(totp_key).now()

        # Create session
        session = fyersModel.SessionModel(
            client_id=client_id,
            secret_key=secret_key,
            redirect_uri="http://127.0.0.1:8080/",
            response_type="code",
            grant_type="authorization_code"
        )

        # Headless login
        login_response = session.generate_authcode_headless(
            identification=username,
            otp=totp_code,
            pin=pin
        )

        if login_response.get("s") != "ok":
            print(f"Login failed: {login_response}")
            return None

        auth_code = login_response.get("auth_code", "")

        # Exchange for token
        session.set_token(auth_code)
        token_response = session.generate_token()

        access_token = token_response.get("access_token")
        if not access_token:
            print(f"Token generation failed: {token_response}")
            return None

        return access_token

    except Exception as e:
        print(f"Auto token error: {e}")
        return None
