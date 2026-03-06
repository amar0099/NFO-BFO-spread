# ─────────────────────────────────────────────
# auto_token.py
# Generates Fyers token using TOTP
# ─────────────────────────────────────────────

import os
import pyotp

def get_secret(key):
    """Read from Streamlit secrets or environment variables"""
    try:
        import streamlit as st   # import inside function to avoid circular import
        val = st.secrets.get(key, "")
        if val:
            return str(val)
    except Exception:
        pass
    return os.environ.get(key, "")


def generate_token():
    """
    Auto-generate Fyers access token using TOTP.
    Returns (access_token, error_message)
    """
    from fyers_apiv3 import fyersModel

    client_id  = get_secret("FYERS_CLIENT_ID")
    secret_key = get_secret("FYERS_SECRET_KEY")
    username   = get_secret("FYERS_USERNAME")
    pin        = get_secret("FYERS_PIN")
    totp_key   = get_secret("FYERS_TOTP_KEY")

    # Validate all credentials present
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
        # Generate TOTP code
        totp_code = pyotp.TOTP(totp_key).now()

        # Build session
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
            return None, f"Login failed: {login_response}"

        auth_code = login_response.get("auth_code", "")
        if not auth_code:
            return None, f"No auth_code in response: {login_response}"

        # Exchange auth_code for access token
        session.set_token(auth_code)
        token_response = session.generate_token()

        access_token = token_response.get("access_token")
        if not access_token:
            return None, f"Token generation failed: {token_response}"

        return access_token, None

    except Exception as e:
        return None, f"Exception: {str(e)}"
