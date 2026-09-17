import base64
import os
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

# Page configuration
st.set_page_config(
    page_title="Stockimyze AlgoTrade | STK Algo",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_dotenv()

# State initialization
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Dashboard"

if "broker_status" not in st.session_state:
    binance_key = os.getenv('BINANCE_API_KEY', '')
    binance_connected = bool(binance_key and "YOUR_REAL" not in binance_key)
    st.session_state["broker_status"] = {
        "Zerodha": {"status": "EXPIRED", "key": "ujqr••••rv31", "expiry": "16 Sept 2026", "type": "Stocks"},
        "Dhan": {"status": "DISCONNECTED", "key": "-", "expiry": "-", "type": "Stocks"},
        "Angel One": {"status": "DISCONNECTED", "key": "-", "expiry": "-", "type": "Stocks"},
        "Upstox": {"status": "DISCONNECTED", "key": "-", "expiry": "-", "type": "Stocks"},
        "Binance": {"status": "CONNECTED" if binance_connected else "DISCONNECTED", "key": f"{binance_key[:4]}••••{binance_key[-4:]}" if binance_connected else "-", "expiry": "Permanent", "type": "Crypto"},
        "Bybit": {"status": "DISCONNECTED", "key": "-", "expiry": "-", "type": "Crypto"},
        "CoinSwitch": {"status": "CONNECTED", "key": "c71f••••ef41", "expiry": "-", "type": "Crypto"},
        "Cosmic Trade": {"status": "CONNECTED", "key": "QBF6••••HWFg", "expiry": "-", "type": "Crypto"}
    }

# Live Market Tickers Fetcher (Indian Indices + Crypto + Gold)
@st.cache_data(ttl=10)
def get_live_tickers():
    prices = {
        "NIFTY": 25390.40,
        "BANKNIFTY": 52120.15,
        "SENSEX": 83140.80,
        "BTC": 76480.00,
        "ETH": 2645.00,
        "GOLD": 2585.00
    }
    
    # 1. Fetch Real Indian Indices via Yahoo Finance lightweight API
    try:
        url_in = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=^NSEI,^NSEBANK,^BSESN"
        headers = {"User-Agent": "Mozilla/5.0"}
        res_in = requests.get(url_in, headers=headers, timeout=3).json()
        for item in res_in.get("quoteResponse", {}).get("result", []):
            sym = item.get("symbol")
            price = item.get("regularMarketPrice")
            if sym == "^NSEI" and price: prices["NIFTY"] = float(price)
            elif sym == "^NSEBANK" and price: prices["BANKNIFTY"] = float(price)
            elif sym == "^BSESN" and price: prices["SENSEX"] = float(price)
    except Exception:
        pass

    # 2. Fetch Real Crypto & Gold via Binance Live API
    try:
        res_cr = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=2).json()
        ticker_map = {item['symbol']: float(item['price']) for item in res_cr if item['symbol'] in ['BTCUSDT', 'ETHUSDT', 'PAXGUSDT']}
        if 'BTCUSDT' in ticker_map: prices["BTC"] = ticker_map['BTCUSDT']
        if 'ETHUSDT' in ticker_map: prices["ETH"] = ticker_map['ETHUSDT']
        if 'PAXGUSDT' in ticker_map: prices["GOLD"] = ticker_map['PAXGUSDT']
    except Exception:
        pass

    return prices

live_prices = get_live_tickers()
active_count = sum(1 for b in st.session_state["broker_status"].values() if b["status"] == "CONNECTED")

# Modern Fintech SaaS Styling
st.markdown("""
<style>
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 1.2rem !important;
    }
    .stApp {
        background-color: #f8fafc;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0;
        padding-top: 10px !important;
    }
    section[data-testid="stSidebar"] .stButton > button {
        border: none !important;
        background: transparent !important;
        color: #475569 !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        padding: 8px 12px !important;
        border-radius: 8px !important;
        text-align: left !important;
        justify-content: flex-start !important;
        width: 100% !important;
        margin-bottom: 2px !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #f1f5f9 !important;
        color: #0f172a !important;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background-color: #eff6ff !important;
        color: #2563eb !important;
        font-weight: 600 !important;
        border-left: 3px solid #2563eb !important;
        border-radius: 0 8px 8px 0 !important;
    }
    .sidebar-section {
        font-size: 11px;
        font-weight: 700;
        color: #94a3b8;
        letter-spacing: 0.08em;
        margin-top: 14px;
        margin-bottom: 6px;
        padding-left: 8px;
        text-transform: uppercase;
    }

    /* 2-Line Multi-Market Ticker Container */
    .ticker-matrix-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 8px 14px;
        display: flex;
        flex-direction: column;
        gap: 6px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .ticker-row {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
    }
    .row-badge {
        font-size: 10px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 3px 8px;
        border-radius: 6px;
        min-width: 60px;
        text-align: center;
    }
    .badge-in { background: #e0f2fe; color: #0369a1; }
    .badge-global { background: #fef3c7; color: #b45309; }

    .market-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 4px 10px;
        border-radius: 7px;
    }
    .market-chip .symbol {
        font-size: 12px;
        font-weight: 700;
        color: #475569;
    }
    .market-chip .val {
        font-size: 14px;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.01em;
    }
    
    .status-pill {
        padding: 4px 10px;
        border-radius: 16px;
        font-size: 11px;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .pill-green { background: #dcfce7; color: #15803d; }
    .pill-orange { background: #ffedd5; color: #c2410c; }
    .pill-red { background: #fee2e2; color: #b91c1c; }

    /* Welcome Banner */
    .welcome-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 5px solid #2563eb;
        border-radius: 12px;
        padding: 12px 18px;
        margin-top: 14px;
        margin-bottom: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .welcome-text {
        font-size: 18px;
        font-weight: 800;
        color: #0f172a;
    }
    .welcome-sub {
        font-size: 12px;
        color: #64748b;
        margin-top: 1px;
    }

    /* Stat Cards */
    .stat-box {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
        margin-bottom: 10px;
    }
    .stat-title {
        color: #64748b;
        font-size: 12px;
        font-weight: 600;
        display: flex;
        justify-content: space-between;
    }
    .stat-val {
        color: #0f172a;
        font-size: 24px;
        font-weight: 800;
        margin: 4px 0;
    }

    /* Broker Cards */
    .broker-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .broker-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .broker-meta {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .broker-logo {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 13px;
        color: white;
    }
    .broker-info-row {
        display: flex;
        background: #f8fafc;
        border-radius: 8px;
        padding: 9px 11px;
        border: 1px solid #f1f5f9;
        margin-bottom: 12px;
        justify-content: space-between;
    }
    .info-label { font-size: 11px; color: #94a3b8; font-weight: 600; }
    .info-val { font-size: 12px; color: #1e293b; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# Dialog Modal for Connecting Brokers
@st.dialog("Connect Broker Account")
def open_broker_modal(broker_name):
    st.markdown(f"### 🔌 Setup {broker_name} Connection")
    st.caption("Enter credentials to connect this account.")
    
    current_data = st.session_state["broker_status"].get(broker_name, {})
    is_crypto = current_data.get("type") == "Crypto"
    
    api_key_input = st.text_input(f"{broker_name} API Key", placeholder="Enter API Key...")
    api_secret_input = st.text_input(f"{broker_name} Secret Key", type="password", placeholder="Enter Secret Key...")
    
    if not is_crypto:
        st.text_input("TOTP Key / PIN (Optional)", placeholder="6-digit TOTP or PIN")
    
    col_save, col_cancel = st.columns([2, 1])
    with col_save:
        if st.button("Save & Connect", type="primary", use_container_width=True):
            if api_key_input.strip() and api_secret_input.strip():
                if broker_name == "Binance":
                    with open(".env", "w") as f:
                        f.write(f"BINANCE_API_KEY={api_key_input.strip()}\n")
                        f.write(f"BINANCE_API_SECRET={api_secret_input.strip()}\n")
                        f.write("TRADING_SYMBOL=BTCUSDT\nTRADE_QUANTITY=0.001\nTRAILING_GAP_PCT=0.01\n")
                
                masked = f"{api_key_input[:4]}••••{api_key_input[-4:]}" if len(api_key_input) > 8 else "Active••••"
                st.session_state["broker_status"][broker_name]["status"] = "CONNECTED"
                st.session_state["broker_status"][broker_name]["key"] = masked
                st.session_state["broker_status"][broker_name]["expiry"] = "Live Session"
                st.success(f"{broker_name} connected successfully!")
                st.rerun()
            else:
                st.error("Please enter both API Key and Secret.")
                
    with col_cancel:
        if st.button("Cancel", use_container_width=True):
            st.rerun()

# ----------------- SIDEBAR -----------------
with st.sidebar:
    logo_file = None
    for name in ["logo.png", "logo.jpg", "logo.jpeg", "logo.png.jpg"]:
        if os.path.exists(name):
            logo_file = name
            break
            
    img_tag = ""
    if logo_file:
        with open(logo_file, "rb") as img_f:
            b64 = base64.b64encode(img_f.read()).decode("utf-8")
        img_tag = f'<img src="data:image/png;base64,{b64}" style="width: 65px; height: 65px; object-fit: contain; border-radius: 10px; margin-bottom: 6px;">'
    else:
        img_tag = '<div style="font-size: 30px; margin-bottom: 6px;">⚡</div>'

    st.markdown(f"""
    <div style="padding-top: 0px; margin-bottom: 16px;">
        {img_tag}
        <div style="font-weight: 800; font-size: 18px; color: #0b192c; letter-spacing: -0.02em; line-height: 1.2;">
            Stockimyze AlgoTrade
        </div>
        <div style="color: #627289; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 3px;">
            STK ALGO EXECUTION ENGINE
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">TRADING</div>', unsafe_allow_html=True)

    nav_items = [
        ("Dashboard", "📊  Dashboard"),
        ("Strategies", "🎯  Strategies"),
        ("Live Trading", "🔴  Live Trading"),
        ("Paper Trading", "📄  Paper Trading"),
        ("Backtesting", "⏳  Backtesting"),
        ("Broker Connections", "🔌  Broker Connections"),
        ("Orders", "📑  Orders"),
        ("Positions", "💼  Positions"),
        ("Portfolio", "🪙  Portfolio"),
        ("PnL Analytics", "📈  PnL Analytics"),
        ("Trade History", "📜  Trade History"),
        ("Reports", "📋  Reports"),
    ]

    for key, label in nav_items:
        is_active = (st.session_state["current_page"] == key)
        if st.button(label, key=f"nav_{key}", type="primary" if is_active else "secondary", use_container_width=True):
            st.session_state["current_page"] = key
            st.rerun()

    st.markdown('<div class="sidebar-section">ACCOUNT</div>', unsafe_allow_html=True)
    st.button("🔔  Notifications", key="nav_notif", use_container_width=True)
    st.button("👤  Haider (User Profile)", key="nav_user", use_container_width=True)

# ----------------- 2-LINE LIVE TICKER + PROFILE BAR -----------------
col_strip, col_usr = st.columns([4.2, 1.1])

with col_strip:
    st.markdown(f"""
    <div class="ticker-matrix-card">
        <!-- LINE 1: INDIAN INDICES -->
        <div class="ticker-row">
            <span class="row-badge badge-in">INDIAN</span>
            <div class="market-chip" style="border-left: 3px solid #0284c7;">
                <span class="symbol" style="color: #0284c7;">🇮🇳 NIFTY 50</span>
                <span class="val">{live_prices['NIFTY']:,.2f}</span>
            </div>
            <div class="market-chip" style="border-left: 3px solid #7c3aed;">
                <span class="symbol" style="color: #7c3aed;">🏦 BANK NIFTY</span>
                <span class="val">{live_prices['BANKNIFTY']:,.2f}</span>
            </div>
            <div class="market-chip" style="border-left: 3px solid #059669;">
                <span class="symbol" style="color: #059669;">📈 SENSEX</span>
                <span class="val">{live_prices['SENSEX']:,.2f}</span>
            </div>
            <span class="status-pill pill-green" style="margin-left: auto;">● Market Live</span>
        </div>
        <!-- LINE 2: CRYPTO & COMMODITIES -->
        <div class="ticker-row">
            <span class="row-badge badge-global">GLOBAL</span>
            <div class="market-chip" style="border-left: 3px solid #f59e0b;">
                <span class="symbol" style="color: #d97706;">₿ BTC/USDT</span>
                <span class="val">${live_prices['BTC']:,.2f}</span>
            </div>
            <div class="market-chip" style="border-left: 3px solid #4f46e5;">
                <span class="symbol" style="color: #4f46e5;">⟠ ETH/USDT</span>
                <span class="val">${live_prices['ETH']:,.2f}</span>
            </div>
            <div class="market-chip" style="border-left: 3px solid #eab308;">
                <span class="symbol" style="color: #a16207;">🏅 GOLD (PAXG)</span>
                <span class="val">${live_prices['GOLD']:,.2f}</span>
            </div>
            <span class="status-pill pill-orange" style="margin-left: auto;">⚡ {active_count}/8 Brokers</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_usr:
    with st.popover("👤 Haider (User)", use_container_width=True):
        st.markdown("**Haider Ali**")
        st.caption("haider@stockimyze.com • Tier 1 Algo Plan")
        st.divider()
        st.markdown("🔹 **API Status:** Live Connected")
        st.markdown("🔹 **Execution Engine:** AWS Singapore")
        st.divider()
        st.button("⚙️ Settings", key="u_set", use_container_width=True)
        if st.button("🚪 Logout", key="u_out", type="primary", use_container_width=True):
            st.rerun()

selected_page = st.session_state["current_page"]

def get_badge(status):
    if status == "CONNECTED":
        return '<span class="status-pill pill-green">● CONNECTED</span>'
    elif status == "EXPIRED":
        return '<span class="status-pill pill-red">● EXPIRED</span>'
    else:
        return '<span class="status-pill pill-red">● DISCONNECTED</span>'

# ==============================================================================
# PAGE: DASHBOARD
# ==============================================================================
if selected_page == "Dashboard":
    # Reflecting Welcome Banner
    st.markdown("""
    <div class="welcome-card">
        <div>
            <div class="welcome-text">✨ Welcome to Stockimyze Algo</div>
            <div class="welcome-sub">Institutional High-Frequency Multi-Asset Algorithmic Infrastructure</div>
        </div>
        <div style="font-size: 12px; font-weight: 700; color: #2563eb; background: #eff6ff; border: 1px solid #bfdbfe; padding: 5px 14px; border-radius: 20px;">
            ⚡ Engine v2.4 Live
        </div>
    </div>
    """, unsafe_allow_html=True)

    csv_f = 'trades_log_mainnet.csv' if os.path.exists('trades_log_mainnet.csv') else 'trades_log.csv'
    pnl_val = 0.0
    win_rate = 54.2
    if os.path.exists(csv_f):
        try:
            df_trades = pd.read_csv(csv_f)
            if not df_trades.empty and 'PnL_$' in df_trades.columns:
                closed = df_trades[df_trades['Side'].str.startswith('SELL')]
                if len(closed) > 0:
                    pnl_val = closed['PnL_$'].sum()
                    win_rate = (len(closed[closed['PnL_$'] > 0]) / len(closed)) * 100
        except Exception:
            pass

    # Row 1 Stat Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown('<div class="stat-box"><div class="stat-title">Today\'s P/L — Options <span>₹</span></div><div class="stat-val">₹0</div><div style="font-size:11px;color:#64748b;font-weight:600;">Ready to trade</div></div>', unsafe_allow_html=True)
    with c2:
        pnl_col = "#16a34a" if pnl_val >= 0 else "#dc2626"
        st.markdown(f'<div class="stat-box"><div class="stat-title">Today\'s P/L — Crypto <span>$</span></div><div class="stat-val" style="color:{pnl_col};">${pnl_val:+,.2f}</div><div style="font-size:11px;color:#16a34a;font-weight:600;">↗ 0.00% Live Engine</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="stat-box"><div class="stat-title">Total Capital <span>💼</span></div><div class="stat-val">$10,387</div><div style="font-size:11px;color:#16a34a;font-weight:600;">↗ 0.00% Available Margin</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="stat-box"><div class="stat-title">Active Strategies <span>📈</span></div><div class="stat-val">11</div><div style="font-size:11px;color:#64748b;font-weight:600;">1 Running on BTCUSDT</div></div>', unsafe_allow_html=True)

    # Row 2 Stat Cards
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.markdown('<div class="stat-box"><div class="stat-title">Running Bots <span>🤖</span></div><div class="stat-val">1</div><div style="font-size:11px;color:#16a34a;font-weight:600;">● STK Algo Auto-Pilot</div></div>', unsafe_allow_html=True)
    with c6:
        st.markdown(f'<div class="stat-box"><div class="stat-title">Broker Connected <span>🔌</span></div><div class="stat-val">{active_count}/8 Brokers</div><div style="font-size:11px;color:#16a34a;font-weight:600;">✓ Active Session</div></div>', unsafe_allow_html=True)
    with c7:
        st.markdown('<div class="stat-box"><div class="stat-title">Open Positions <span>⚡</span></div><div class="stat-val">1</div><div style="font-size:11px;color:#64748b;font-weight:600;">Trailing Gap: 1.0%</div></div>', unsafe_allow_html=True)
    with c8:
        st.markdown(f'<div class="stat-box"><div class="stat-title">Win Rate <span>%</span></div><div class="stat-val">{win_rate:.1f}%</div><div style="font-size:11px;color:#16a34a;font-weight:600;">↗ Algo Accuracy</div></div>', unsafe_allow_html=True)

    # Single Candlestick Chart
    try:
        url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=60"
        res = requests.get(url, timeout=3).json()
        df_market = pd.DataFrame(res, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'ct', 'qav', 't', 'tbv', 'tqv', 'ig'])
        df_market['time'] = pd.to_datetime(df_market['time'], unit='ms')
        for c in ['open', 'high', 'low', 'close']:
            df_market[c] = df_market[c].astype(float)
        df_market['EMA'] = df_market['close'].ewm(span=200, adjust=False).mean()

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df_market['time'],
            open=df_market['open'],
            high=df_market['high'],
            low=df_market['low'],
            close=df_market['close'],
            name="BTCUSDT",
            increasing_line_color='#10b981',
            increasing_fillcolor='#10b981',
            decreasing_line_color='#ef4444',
            decreasing_fillcolor='#ef4444'
        ))
        fig.add_trace(go.Scatter(
            x=df_market['time'],
            y=df_market['EMA'],
            mode='lines',
            line=dict(color='#2563eb', width=1.5),
            name='EMA 200'
        ))
        fig.update_layout(
            xaxis_rangeslider_visible=False,
            height=370,
            margin=dict(l=10, r=40, t=10, b=10),
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            font=dict(color="#64748b", size=11),
            yaxis=dict(side="right", showgrid=True, gridcolor='#f8fafc', zeroline=False),
            xaxis=dict(showgrid=True, gridcolor='#f8fafc', zeroline=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.markdown('<div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:10px; box-shadow:0 1px 3px rgba(0,0,0,0.02); margin-top: 10px;">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    except Exception:
        st.info("Chart live feed loading...")

# ==============================================================================
# PAGE: BROKER CONNECTIONS
# ==============================================================================
elif selected_page == "Broker Connections":
    st.markdown("<h2 style='margin-top: 10px; margin-bottom: 2px; color: #0f172a;'>Broker Connections</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 14px; margin-bottom: 20px;'>Connect and manage your broker accounts for live execution.</p>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        z_data = st.session_state["broker_status"]["Zerodha"]
        st.markdown(f"""
        <div class="broker-card">
            <div class="broker-top">
                <div class="broker-meta">
                    <div class="broker-logo" style="background:#0284c7;">ZE</div>
                    <div><div style="font-weight:700; font-size:15px; color:#0f172a;">Zerodha</div><div style="font-size:12px; color:#64748b;">Stocks</div></div>
                </div>
                {get_badge(z_data["status"])}
            </div>
            <div class="broker-info-row">
                <div><div class="info-label">API Key</div><div class="info-val">{z_data["key"]}</div></div>
                <div><div class="info-label">Token Expiry</div><div class="info-val">{z_data["expiry"]}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if z_data["status"] == "CONNECTED":
            if st.button("Disconnect", key="z_dc", use_container_width=True):
                st.session_state["broker_status"]["Zerodha"]["status"] = "DISCONNECTED"
                st.session_state["broker_status"]["Zerodha"]["key"] = "-"
                st.rerun()
        else:
            z1, z2 = st.columns(2)
            with z1:
                if st.button("Re-login", key="z_relogin", use_container_width=True): open_broker_modal("Zerodha")
            with z2:
                if st.button("Connect", key="z_conn", use_container_width=True): open_broker_modal("Zerodha")

    with c2:
        dh_data = st.session_state["broker_status"]["Dhan"]
        st.markdown(f"""
        <div class="broker-card">
            <div class="broker-top">
                <div class="broker-meta">
                    <div class="broker-logo" style="background:#2563eb;">DH</div>
                    <div><div style="font-weight:700; font-size:15px; color:#0f172a;">Dhan</div><div style="font-size:12px; color:#64748b;">Stocks</div></div>
                </div>
                {get_badge(dh_data["status"])}
            </div>
            <div class="broker-info-row">
                <div><div class="info-label">API Key</div><div class="info-val">{dh_data["key"]}</div></div>
                <div><div class="info-label">Token Expiry</div><div class="info-val">{dh_data["expiry"]}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if dh_data["status"] == "CONNECTED":
            if st.button("Disconnect", key="dh_dc", use_container_width=True):
                st.session_state["broker_status"]["Dhan"]["status"] = "DISCONNECTED"
                st.session_state["broker_status"]["Dhan"]["key"] = "-"
                st.rerun()
        else:
            if st.button("⚡ Connect", key="dhan_conn", use_container_width=True): open_broker_modal("Dhan")

    with c3:
        an_data = st.session_state["broker_status"]["Angel One"]
        st.markdown(f"""
        <div class="broker-card">
            <div class="broker-top">
                <div class="broker-meta">
                    <div class="broker-logo" style="background:#ea580c;">AN</div>
                    <div><div style="font-weight:700; font-size:15px; color:#0f172a;">Angel One</div><div style="font-size:12px; color:#64748b;">Stocks</div></div>
                </div>
                {get_badge(an_data["status"])}
            </div>
            <div class="broker-info-row">
                <div><div class="info-label">API Key</div><div class="info-val">{an_data["key"]}</div></div>
                <div><div class="info-label">Token Expiry</div><div class="info-val">{an_data["expiry"]}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if an_data["status"] == "CONNECTED":
            if st.button("Disconnect", key="an_dc", use_container_width=True):
                st.session_state["broker_status"]["Angel One"]["status"] = "DISCONNECTED"
                st.session_state["broker_status"]["Angel One"]["key"] = "-"
                st.rerun()
        else:
            if st.button("⚡ Connect", key="angel_conn", use_container_width=True): open_broker_modal("Angel One")

    with c4:
        up_data = st.session_state["broker_status"]["Upstox"]
        st.markdown(f"""
        <div class="broker-card">
            <div class="broker-top">
                <div class="broker-meta">
                    <div class="broker-logo" style="background:#7c3aed;">UP</div>
                    <div><div style="font-weight:700; font-size:15px; color:#0f172a;">Upstox</div><div style="font-size:12px; color:#64748b;">Stocks</div></div>
                </div>
                {get_badge(up_data["status"])}
            </div>
            <div class="broker-info-row">
                <div><div class="info-label">API Key</div><div class="info-val">{up_data["key"]}</div></div>
                <div><div class="info-label">Token Expiry</div><div class="info-val">{up_data["expiry"]}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if up_data["status"] == "CONNECTED":
            if st.button("Disconnect", key="up_dc", use_container_width=True):
                st.session_state["broker_status"]["Upstox"]["status"] = "DISCONNECTED"
                st.session_state["broker_status"]["Upstox"]["key"] = "-"
                st.rerun()
        else:
            if st.button("⚡ Connect", key="upstox_conn", use_container_width=True): open_broker_modal("Upstox")

    c5, c6, c7, c8 = st.columns(4)

    with c5:
        bi_data = st.session_state["broker_status"]["Binance"]
        st.markdown(f"""
        <div class="broker-card">
            <div class="broker-top">
                <div class="broker-meta">
                    <div class="broker-logo" style="background:#f59e0b;">BI</div>
                    <div><div style="font-weight:700; font-size:15px; color:#0f172a;">Binance</div><div style="font-size:12px; color:#64748b;">Crypto</div></div>
                </div>
                {get_badge(bi_data["status"])}
            </div>
            <div class="broker-info-row">
                <div><div class="info-label">API Key</div><div class="info-val">{bi_data["key"]}</div></div>
                <div><div class="info-label">Token Expiry</div><div class="info-val">{bi_data["expiry"]}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if bi_data["status"] == "CONNECTED":
            b1, b2 = st.columns(2)
            with b1:
                if st.button("Reconnect", key="bi_rec", use_container_width=True): open_broker_modal("Binance")
            with b2:
                if st.button("Disconnect", key="bi_dc", use_container_width=True):
                    st.session_state["broker_status"]["Binance"]["status"] = "DISCONNECTED"
                    st.session_state["broker_status"]["Binance"]["key"] = "-"
                    st.rerun()
        else:
            if st.button("⚡ Connect", key="bi_conn", use_container_width=True): open_broker_modal("Binance")

    with c6:
        by_data = st.session_state["broker_status"]["Bybit"]
        st.markdown(f"""
        <div class="broker-card">
            <div class="broker-top">
                <div class="broker-meta">
                    <div class="broker-logo" style="background:#d97706;">BY</div>
                    <div><div style="font-weight:700; font-size:15px; color:#0f172a;">Bybit</div><div style="font-size:12px; color:#64748b;">Crypto</div></div>
                </div>
                {get_badge(by_data["status"])}
            </div>
            <div class="broker-info-row">
                <div><div class="info-label">API Key</div><div class="info-val">{by_data["key"]}</div></div>
                <div><div class="info-label">Token Expiry</div><div class="info-val">{by_data["expiry"]}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if by_data["status"] == "CONNECTED":
            if st.button("Disconnect", key="by_dc", use_container_width=True):
                st.session_state["broker_status"]["Bybit"]["status"] = "DISCONNECTED"
                st.session_state["broker_status"]["Bybit"]["key"] = "-"
                st.rerun()
        else:
            if st.button("⚡ Connect", key="bybit_conn", use_container_width=True): open_broker_modal("Bybit")

    with c7:
        cs_data = st.session_state["broker_status"]["CoinSwitch"]
        st.markdown(f"""
        <div class="broker-card">
            <div class="broker-top">
                <div class="broker-meta">
                    <div class="broker-logo" style="background:#4f46e5;">CO</div>
                    <div><div style="font-weight:700; font-size:15px; color:#0f172a;">CoinSwitch</div><div style="font-size:12px; color:#64748b;">Crypto</div></div>
                </div>
                {get_badge(cs_data["status"])}
            </div>
            <div class="broker-info-row">
                <div><div class="info-label">API Key</div><div class="info-val">{cs_data["key"]}</div></div>
                <div><div class="info-label">Token Expiry</div><div class="info-val">{cs_data["expiry"]}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if cs_data["status"] == "CONNECTED":
            cs1, cs2 = st.columns(2)
            with cs1:
                if st.button("Reconnect", key="cs_rec", use_container_width=True): open_broker_modal("CoinSwitch")
            with cs2:
                if st.button("Disconnect", key="cs_dc", use_container_width=True):
                    st.session_state["broker_status"]["CoinSwitch"]["status"] = "DISCONNECTED"
                    st.session_state["broker_status"]["CoinSwitch"]["key"] = "-"
                    st.rerun()
        else:
            if st.button("⚡ Connect", key="cs_conn", use_container_width=True): open_broker_modal("CoinSwitch")

    with c8:
        ct_data = st.session_state["broker_status"]["Cosmic Trade"]
        st.markdown(f"""
        <div class="broker-card">
            <div class="broker-top">
                <div class="broker-meta">
                    <div class="broker-logo" style="background:#0f172a;">CO</div>
                    <div><div style="font-weight:700; font-size:15px; color:#0f172a;">Cosmic Trade</div><div style="font-size:12px; color:#64748b;">Crypto</div></div>
                </div>
                {get_badge(ct_data["status"])}
            </div>
            <div class="broker-info-row">
                <div><div class="info-label">API Key</div><div class="info-val">{ct_data["key"]}</div></div>
                <div><div class="info-label">Token Expiry</div><div class="info-val">{ct_data["expiry"]}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if ct_data["status"] == "CONNECTED":
            ct1, ct2 = st.columns(2)
            with ct1:
                if st.button("Reconnect", key="ct_rec", use_container_width=True): open_broker_modal("Cosmic Trade")
            with ct2:
                if st.button("Disconnect", key="ct_dc", use_container_width=True):
                    st.session_state["broker_status"]["Cosmic Trade"]["status"] = "DISCONNECTED"
                    st.session_state["broker_status"]["Cosmic Trade"]["key"] = "-"
                    st.rerun()
        else:
            if st.button("⚡ Connect", key="ct_conn", use_container_width=True): open_broker_modal("Cosmic Trade")

else:
    st.markdown(f"## {selected_page}")
    st.info(f"{selected_page} execution route is active.")