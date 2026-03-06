# ─────────────────────────────────────────────
# dashboard.py
# Live spread dashboard — run with: streamlit run dashboard.py
# ─────────────────────────────────────────────

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date
import time

from data_fetcher import load_fyers, build_symbol, fetch_candles
from auto_token import generate_token
from config import REFRESH_SECONDS

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="SENSEX/NIFTY Spread Dashboard",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
<style>
    .stApp { background-color: #0e0e0e; color: #ffffff; }
    section[data-testid="stSidebar"] { background-color: #111122; }
    .metric-card {
        background: #1a1a2e;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        border: 1px solid #2a2a4a;
        margin-bottom: 8px;
    }
    .ce-value  { color: #ff4444; font-size: 26px; font-weight: bold; }
    .pe-value  { color: #44ff88; font-size: 26px; font-weight: bold; }
    .diff-pos  { color: #ff4444; font-size: 26px; font-weight: bold; }
    .diff-neg  { color: #44ff88; font-size: 26px; font-weight: bold; }
    .label     { color: #888;    font-size: 12px; margin-bottom: 4px; }
    .sublabel  { color: #555;    font-size: 11px; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR — ALL CONTROLS
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📊 Spread Settings")

    # ── SENSEX ───────────────────────────────
    st.markdown("### 🔵 Leg 1 (SENSEX)")

    sensex_exchange = st.selectbox("Exchange", ["BSE", "NSE"], index=0, key="sx_exch")
    sensex_underlying = st.selectbox("Underlying", ["SENSEX", "BANKEX"], index=0, key="sx_under")

    col1, col2 = st.columns(2)
    with col1:
        sensex_ce_expiry = st.text_input("CE Expiry", value="260312", key="sx_ce_exp", help="YYMMDD e.g. 260312")
    with col2:
        sensex_pe_expiry = st.text_input("PE Expiry", value="260312", key="sx_pe_exp")

    col3, col4 = st.columns(2)
    with col3:
        sensex_ce_strike = st.number_input("CE Strike", value=80000, step=100, key="sx_ce_str")
    with col4:
        sensex_pe_strike = st.number_input("PE Strike", value=80000, step=100, key="sx_pe_str")

    st.divider()

    # ── NIFTY ────────────────────────────────
    st.markdown("### 🟠 Leg 2 (NIFTY)")

    nifty_exchange = st.selectbox("Exchange", ["NSE", "BSE"], index=0, key="nf_exch")
    nifty_underlying = st.selectbox("Underlying", ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"], index=0, key="nf_under")

    col5, col6 = st.columns(2)
    with col5:
        nifty_ce_expiry = st.text_input("CE Expiry", value="260310", key="nf_ce_exp", help="YYMMDD e.g. 260310")
    with col6:
        nifty_pe_expiry = st.text_input("PE Expiry", value="260310", key="nf_pe_exp")

    col7, col8 = st.columns(2)
    with col7:
        nifty_ce_strike = st.number_input("CE Strike", value=24800, step=50, key="nf_ce_str")
    with col8:
        nifty_pe_strike = st.number_input("PE Strike", value=24800, step=50, key="nf_pe_str")

    st.divider()

    # ── FORMULA & DISPLAY ────────────────────
    st.markdown("### ⚙️ Formula & Display")

    multiplier = st.number_input(
        "Leg 2 Multiplier", value=3.3, step=0.1, min_value=0.1, key="mult",
        help="Spread = Leg1 − (Leg2 × multiplier)"
    )
    candle_interval = st.selectbox("Candle Interval (min)", [1, 3, 5, 10, 15, 30, 60], index=2)
    selected_date   = st.date_input("📅 Date", value=date.today())
    date_str        = selected_date.strftime("%Y-%m-%d")

    st.divider()

    show_raw     = st.checkbox("Show Raw Prices Chart", value=False)
    show_diff    = st.checkbox("Show CE+PE Total Spread", value=True)
    show_synth   = st.checkbox("Show Synthetic Future",     value=True)
    auto_refresh = st.checkbox("Auto Refresh",          value=True)
    refresh_secs = st.slider("Refresh every (sec)", 5, 60, REFRESH_SECONDS)

    st.divider()
    fetch_btn = st.button("🔄 Fetch / Refresh Data", use_container_width=True, type="primary")



# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

st.title("📊 SENSEX / NIFTY Synthetic Spread")
st.caption(
    f"{sensex_exchange}:{sensex_underlying} − ({nifty_exchange}:{nifty_underlying} × {multiplier}) "
    f"| {candle_interval}min | {date_str}"
)

# ─────────────────────────────────────────────
# BUILD & SHOW TICKER SYMBOLS
# ─────────────────────────────────────────────

sym_sx_ce = build_symbol(sensex_exchange, sensex_underlying, sensex_ce_expiry, "C", int(sensex_ce_strike))
sym_sx_pe = build_symbol(sensex_exchange, sensex_underlying, sensex_pe_expiry, "P", int(sensex_pe_strike))
sym_nf_ce = build_symbol(nifty_exchange,  nifty_underlying,  nifty_ce_expiry,  "C", int(nifty_ce_strike))
sym_nf_pe = build_symbol(nifty_exchange,  nifty_underlying,  nifty_pe_expiry,  "P", int(nifty_pe_strike))

with st.expander("🔍 Active Symbols (click to verify)"):
    c1, c2, c3, c4 = st.columns(4)
    c1.code(sym_sx_ce, language=None)
    c2.code(sym_sx_pe, language=None)
    c3.code(sym_nf_ce, language=None)
    c4.code(sym_nf_pe, language=None)

# ─────────────────────────────────────────────
# FYERS CLIENT
# ─────────────────────────────────────────────

def get_fyers_client():
    """
    Try loading token from file first (local),
    then auto-generate using TOTP (hosted/cloud)
    """
    from fyers_apiv3 import fyersModel
    from config import CLIENT_ID, TOKEN_FILE
    import os

    # Try local token file first (local PC)
    try:
        return load_fyers()
    except FileNotFoundError:
        pass

    # Auto-generate token using TOTP (Streamlit Cloud)
    token, error = generate_token()

    if not token:
        st.error(f"❌ Token generation failed: {error}")
        return None

    fyers = fyersModel.FyersModel(
        client_id=CLIENT_ID,
        token=token,
        log_path=""
    )
    return fyers

# ─────────────────────────────────────────────
# FETCH DATA
# ─────────────────────────────────────────────

def fetch_live_data():
    fyers = get_fyers_client()
    if fyers is None:
        st.error("❌ Could not generate access token. Check your credentials in Streamlit Secrets.")
        return pd.DataFrame()

    with st.spinner("Fetching option & spot prices from Fyers..."):
        # Spread options
        df_sx_ce   = fetch_candles(fyers, sym_sx_ce,          candle_interval, date_str)
        df_sx_pe   = fetch_candles(fyers, sym_sx_pe,          candle_interval, date_str)
        df_nf_ce   = fetch_candles(fyers, sym_nf_ce,          candle_interval, date_str)
        df_nf_pe   = fetch_candles(fyers, sym_nf_pe,          candle_interval, date_str)
        # Spot index candles
        df_sx_spot = fetch_spot_candles(fyers, "BSE:SENSEX-INDEX", candle_interval, date_str)
        df_nf_spot = fetch_spot_candles(fyers, "NSE:NIFTY50-INDEX", candle_interval, date_str)
        st.info(f"SENSEX spot rows: {len(df_sx_spot)} | NIFTY spot rows: {len(df_nf_spot)}")

    if any(df.empty for df in [df_sx_ce, df_sx_pe, df_nf_ce, df_nf_pe]):
        st.warning("⚠️ One or more symbols returned no data. Check expiry/strike values in sidebar.")
        return pd.DataFrame()

    # Remove duplicate timestamps before merging
    for d in [df_sx_ce, df_sx_pe, df_nf_ce, df_nf_pe, df_sx_spot, df_nf_spot]:
        d.drop(d.index[d.index.duplicated(keep="last")], inplace=True)

    df = pd.DataFrame({
        "sensex_ce"   : df_sx_ce["close"],
        "sensex_pe"   : df_sx_pe["close"],
        "nifty_ce"    : df_nf_ce["close"],
        "nifty_pe"    : df_nf_pe["close"],
    }).dropna()

    # Spot prices (use close, round to 100)
    if not df_sx_spot.empty and not df_nf_spot.empty:
        df_sx_spot = df_sx_spot[~df_sx_spot.index.duplicated(keep="last")]
        df_nf_spot = df_nf_spot[~df_nf_spot.index.duplicated(keep="last")]
        df["sensex_spot"] = df_sx_spot["close"].reindex(df.index, method="ffill")
        df["nifty_spot"]  = df_nf_spot["close"].reindex(df.index, method="ffill")
        df["sensex_atm"]  = df["sensex_spot"].apply(lambda x: round_to(x, 100))
        df["nifty_atm"]   = df["nifty_spot"].apply(lambda x: round_to(x, 100))
        # Synthetic Future = spot_rounded + CE_at_ATM - PE_at_ATM
        # Since CE/PE are already fetched at user-defined strikes,
        # we use those as proxy for ATM options
        df["sensex_synth"] = df["sensex_atm"] + df["sensex_ce"] - df["sensex_pe"]
        df["nifty_synth"]  = df["nifty_atm"]  + df["nifty_ce"]  - df["nifty_pe"]
        df["synth_spread"] = df["sensex_synth"] - (df["nifty_synth"] * multiplier)
    else:
        df["sensex_spot"] = None
        df["nifty_spot"]  = None
        df["synth_spread"] = None

    df["ce_spread"] = df["sensex_ce"] - (df["nifty_ce"] * multiplier)
    df["pe_spread"] = df["sensex_pe"] - (df["nifty_pe"] * multiplier)
    df["diff"]      = df["ce_spread"] + df["pe_spread"]

    return df

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()

if fetch_btn or st.session_state.df.empty:
    st.session_state.df = fetch_live_data()

df = st.session_state.df

# ─────────────────────────────────────────────
# RENDER DASHBOARD
# ─────────────────────────────────────────────

if df.empty:
    st.info("👈 Set your strikes and expiry in the sidebar, then click **Fetch / Refresh Data**.")
else:
    latest   = df.iloc[-1]
    ce_val   = latest["ce_spread"]
    pe_val   = latest["pe_spread"]
    diff_val = latest["diff"]
    updated  = df.index[-1].strftime("%H:%M:%S")
    is_today = date_str == date.today().strftime("%Y-%m-%d")

    # ── METRIC CARDS ─────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='label'>🔴 CE Spread</div>
            <div class='ce-value'>{ce_val:.2f}</div>
            <div class='sublabel'>{sensex_underlying} CE {int(sensex_ce_strike)} − {nifty_underlying} CE {int(nifty_ce_strike)}×{multiplier}</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='label'>🟢 PE Spread</div>
            <div class='pe-value'>{pe_val:.2f}</div>
            <div class='sublabel'>{sensex_underlying} PE {int(sensex_pe_strike)} − {nifty_underlying} PE {int(nifty_pe_strike)}×{multiplier}</div>
        </div>""", unsafe_allow_html=True)

    with col3:
        diff_cls = "diff-pos" if diff_val >= 0 else "diff-neg"
        st.markdown(f"""
        <div class='metric-card'>
            <div class='label'>🟠 CE + PE Total</div>
            <div class='{diff_cls}'>{diff_val:+.2f}</div>
            <div class='sublabel'>CE Spread plus PE Spread</div>
        </div>""", unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='label'>🕐 Last Candle</div>
            <div style='font-size:20px;font-weight:bold;color:#aaa'>{updated}</div>
            <div class='sublabel'>{'🔴 LIVE' if is_today else '📂 Historical'} | {len(df)} candles</div>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # ── SPREAD CHART ─────────────────────────
    rows       = 1 + int(show_diff) + int(show_synth)
    heights    = [0.6] if rows == 1 else ([0.5, 0.25, 0.25] if rows == 3 else [0.65, 0.35])
    fig = make_subplots(
        rows=rows, cols=1,
        shared_xaxes=True,
        row_heights=heights,
        vertical_spacing=0.04
    )
    diff_row  = 2 if show_diff else None
    synth_row = (3 if show_diff else 2) if show_synth else None

    fig.add_trace(go.Scatter(
        x=df.index, y=df["ce_spread"], name="CE Spread",
        line=dict(color="#ff4444", width=2),
        hovertemplate="%{x|%H:%M}<br>CE: %{y:.2f}<extra></extra>"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df["pe_spread"], name="PE Spread",
        line=dict(color="#44ff88", width=2),
        hovertemplate="%{x|%H:%M}<br>PE: %{y:.2f}<extra></extra>"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=pd.concat([df.index.to_series(), df.index.to_series()[::-1]]).values,
        y=pd.concat([df["ce_spread"], df["pe_spread"][::-1]]).values,
        fill="toself", fillcolor="rgba(255,100,100,0.07)",
        line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip"
    ), row=1, col=1)

    fig.add_hline(y=0, line_dash="dash", line_color="#444", row=1, col=1)

    if show_diff:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["diff"], name="4 Leg",
            line=dict(color="#ffaa00", width=2),
            hovertemplate="%{x|%H:%M}<br>4 Leg: %{y:.2f}<extra></extra>"
        ), row=diff_row, col=1)
        fig.add_hline(y=0, line_dash="dash", line_color="#444", row=diff_row, col=1)

    if show_synth and "synth_spread" in df.columns and df["synth_spread"].notna().any():
        fig.add_trace(go.Scatter(
            x=df.index, y=df["synth_spread"], name="Synthetic Future",
            line=dict(color="#00bfff", width=2),
            hovertemplate="%{x|%H:%M}<br>Synth: %{y:.2f}<extra></extra>"
        ), row=synth_row, col=1)
        fig.add_hline(y=0, line_dash="dash", line_color="#444", row=synth_row, col=1)

    fig.update_layout(
        height=560,
        plot_bgcolor="#0e0e0e", paper_bgcolor="#0e0e0e",
        font=dict(color="#cccccc"),
        legend=dict(bgcolor="#1a1a2e", bordercolor="#333"),
        hovermode="x unified",
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(gridcolor="#1a1a1a"),
        yaxis=dict(gridcolor="#1a1a1a", title="Spread (₹)"),
    )
    if show_diff:
        fig.update_yaxes(gridcolor="#1a1a1a", title_text="4 Leg", row=diff_row, col=1)
        fig.update_xaxes(gridcolor="#1a1a1a", row=diff_row, col=1)
    if show_synth and synth_row:
        fig.update_yaxes(gridcolor="#1a1a1a", title_text="Synth Future", row=synth_row, col=1)
        fig.update_xaxes(gridcolor="#1a1a1a", row=synth_row, col=1)
    fig.update_layout(height=560 + (120 if show_synth else 0))

    st.plotly_chart(fig, use_container_width=True)

    # ── RAW PRICES ───────────────────────────
    if show_raw:
        st.subheader("📋 Raw Option Prices")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df.index, y=df["sensex_ce"], name=f"{sensex_underlying} CE", line=dict(color="#ff6666")))
        fig2.add_trace(go.Scatter(x=df.index, y=df["sensex_pe"], name=f"{sensex_underlying} PE", line=dict(color="#66ff99")))
        fig2.add_trace(go.Scatter(x=df.index, y=df["nifty_ce"],  name=f"{nifty_underlying} CE",  line=dict(color="#ff9999", dash="dot")))
        fig2.add_trace(go.Scatter(x=df.index, y=df["nifty_pe"],  name=f"{nifty_underlying} PE",  line=dict(color="#99ffbb", dash="dot")))
        fig2.update_layout(
            height=320, plot_bgcolor="#0e0e0e", paper_bgcolor="#0e0e0e",
            font=dict(color="#cccccc"), hovermode="x unified",
            margin=dict(l=20, r=20, t=10, b=20),
            xaxis=dict(gridcolor="#1a1a1a"),
            yaxis=dict(gridcolor="#1a1a1a", title="Price (₹)")
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── DATA TABLE ───────────────────────────
    with st.expander("📄 Raw Data Table"):
        st.dataframe(
            df[[c for c in ["sensex_ce","sensex_pe","nifty_ce","nifty_pe","sensex_spot","nifty_spot","ce_spread","pe_spread","diff","synth_spread"] if c in df.columns]]
            .rename(columns={
                "sensex_ce": f"{sensex_underlying} CE",
                "sensex_pe": f"{sensex_underlying} PE",
                "nifty_ce" : f"{nifty_underlying} CE",
                "nifty_pe" : f"{nifty_underlying} PE",
            })
            .round(2).sort_index(ascending=False),
            use_container_width=True
        )

# ─────────────────────────────────────────────
# AUTO REFRESH
# ─────────────────────────────────────────────

if auto_refresh and date_str == date.today().strftime("%Y-%m-%d") and not df.empty:
    time.sleep(refresh_secs)
    st.session_state.df = fetch_live_data()
    st.rerun()
