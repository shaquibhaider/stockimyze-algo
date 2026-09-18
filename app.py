import base64
import hashlib
import hmac
import json
import os
import time
import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta
from dotenv import load_dotenv

st.set_page_config(
    page_title="Stockimyze AlgoTrade | STK Algo",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_dotenv()

# ==============================================================================
# 1. DATABASE & STORAGE ENGINE
# ==============================================================================
USERS_FILE = "users_db.json"
ADMIN_DATA_FILE = "admin_master_data.json"
LOG_FILE = "trades_log.csv"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_databases():
    if not os.path.exists(USERS_FILE):
        default_users = {
            "admin": {
                "name": "Master Admin",
                "password": hash_password("admin123"),
                "role": "admin",
                "status": "Active",
                "plan": "Enterprise Lifetime",
                "expiry": "2030-12-31",
                "created_at": "2026-01-01",
                "allowed_strategies": ["BTCUSDT HFT", "ETHUSDT HFT", "BTC Battle", "ETH Battle"],
                "max_leverage": 200,
                "brokers": {
                    "Cosmic Trade": {"status": "CONNECTED", "key": "QBF6••••HWFg", "secret": "demo_admin_secret", "expiry": "Permanent"}
                }
            },
            "client1": {
                "name": "Rahul Sharma",
                "password": hash_password("client123"),
                "role": "client",
                "status": "Active",
                "plan": "Pro Trader ($99/mo)",
                "expiry": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
                "created_at": datetime.now().strftime("%Y-%m-%d"),
                "allowed_strategies": ["BTCUSDT HFT", "BTC Battle"],
                "max_leverage": 50,
                "brokers": {
                    "Cosmic Trade": {"status": "DISCONNECTED", "key": "-", "secret": "", "expiry": "-"}
                }
            }
        }
        with open(USERS_FILE, "w") as f:
            json.dump(default_users, f, indent=4)

    if not os.path.exists(ADMIN_DATA_FILE):
        default_admin_data = {
            "payments": [
                {"id": "INV-1092", "user": "client1", "amount": 99.0, "currency": "USD", "plan": "Pro Trader", "date": datetime.now().strftime("%Y-%m-%d"), "status": "COMPLETED", "method": "USDT (TRC20)"}
            ],
            "tickets": [
                {"id": "TCK-401", "user": "client1", "subject": "Cosmic Trade API Latency", "category": "Broker Connection", "status": "OPEN", "priority": "HIGH", "date": datetime.now().strftime("%Y-%m-%d %H:%M")}
            ],
            "macro_alerts": [],
            "audit_logs": [
                {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "user": "admin", "action": "SYSTEM_START", "detail": "Battle Strategies Synced with EMA 200 Trend Filter"}
            ]
        }
        with open(ADMIN_DATA_FILE, "w") as f:
            json.dump(default_admin_data, f, indent=4)

    if not os.path.exists(LOG_FILE):
        df = pd.DataFrame(columns=[
            "Trade_ID", "User", "Date", "Entry_Time", "Exit_Time", "Symbol", "Strategy",
            "Side", "Leverage", "Quantity", "Entry_Price", "Exit_Price", 
            "Trigger_Type", "PnL_$", "PnL_Pct", "Status"
        ])
        df.to_csv(LOG_FILE, index=False)

init_databases()

def load_json(path):
    try:
        with open(path, "r") as f: return json.load(f)
    except Exception: return {}

def save_json(path, data):
    with open(path, "w") as f: json.dump(data, f, indent=4)

def log_audit(user, action, detail):
    adm = load_json(ADMIN_DATA_FILE)
    adm.setdefault("audit_logs", []).insert(0, {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user,
        "action": action,
        "detail": detail
    })
    save_json(ADMIN_DATA_FILE, adm)

def load_trade_logs():
    try: return pd.read_csv(LOG_FILE)
    except Exception: return pd.DataFrame()

def log_trade(trade_id, date, entry_time, exit_time, symbol, strategy, side, leverage, qty, entry_p, exit_p, trigger_type, pnl_usd, pnl_pct, status="CLOSED"):
    new_row = {
        "Trade_ID": trade_id,
        "User": st.session_state.get("username", "admin"),
        "Date": date,
        "Entry_Time": entry_time,
        "Exit_Time": exit_time,
        "Symbol": symbol,
        "Strategy": strategy,
        "Side": side,
        "Leverage": f"{leverage}x",
        "Quantity": qty,
        "Entry_Price": round(entry_p, 2),
        "Exit_Price": round(exit_p, 2),
        "Trigger_Type": trigger_type,
        "PnL_$": round(pnl_usd, 2),
        "PnL_Pct": f"{round(pnl_pct, 2)}%",
        "Status": status
    }
    pd.DataFrame([new_row]).to_csv(LOG_FILE, mode='a', header=False, index=False)

# ==============================================================================
# 2. HIGH-PROBABILITY ENGULFING BATTLE ENGINE (TREND ALIGNED + STRICT RR)
# ==============================================================================
def run_engulfing_battle_backtest(symbol="BTCUSDT", days=30, leverage=50):
    try:
        target_pts = 400.0 if "BTC" in symbol else 10.0
        end_ms = int(time.time() * 1000)
        start_ms = end_ms - (days * 24 * 60 * 60 * 1000)
        all_candles = []
        cur_start = start_ms

        while cur_start < end_ms:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&startTime={cur_start}&endTime={end_ms}&limit=1000"
            res = requests.get(url, timeout=5).json()
            if not res or not isinstance(res, list) or len(res) == 0: break
            all_candles.extend(res)
            cur_start = res[-1][0] + 1
            if len(res) < 1000: break
            time.sleep(0.04)

        if not all_candles: return pd.DataFrame()

        df = pd.DataFrame(all_candles, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'ct', 'qav', 't', 'tbv', 'tqv', 'ig'])
        df['time'] = pd.to_datetime(df['time'], unit='ms') + timedelta(hours=5, minutes=30)
        for col in ['open', 'high', 'low', 'close', 'vol']: df[col] = df[col].astype(float)
        df.drop_duplicates(subset=['time'], inplace=True)
        df.sort_values(by='time', inplace=True)

        df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
        df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['Body'] = abs(df['close'] - df['open'])

        trades = []
        in_pos = False
        pos_side = None
        entry_p = 0.0
        sl_p = 0.0
        tp_p = 0.0
        entry_time = None

        min_body_val = 30.0 if "BTC" in symbol else 1.0
        max_allowed_sl_dist = 220.0 if "BTC" in symbol else 5.5

        for i in range(5, len(df)):
            curr = df.iloc[i]
            p1 = df.iloc[i-1]
            p2 = df.iloc[i-2]

            if not in_pos:
                if curr['Body'] < min_body_val or p1['Body'] < (min_body_val * 0.4):
                    continue

                # 1. BEARISH ENGULFING (SELL)
                sl_distance_sell = curr['high'] - curr['close']
                if sl_distance_sell <= max_allowed_sl_dist:
                    upside_push = (p1['close'] > p1['open']) and (p1['high'] >= p2['high']) and (p1['close'] > curr['EMA20'])
                    prev_is_green = (p1['close'] > p1['open'])
                    curr_is_red = (curr['close'] < curr['open'])
                    pure_bear_engulf = (curr['open'] >= (p1['close'] - (8.0 if 'BTC' in symbol else 0.4))) and (curr['close'] < p1['open'])
                    trend_ok_sell = curr['close'] < curr['EMA200']

                    if upside_push and prev_is_green and curr_is_red and pure_bear_engulf and trend_ok_sell:
                        in_pos = True
                        pos_side = "SELL"
                        entry_p = curr['close']
                        sl_p = curr['high']
                        tp_p = entry_p - target_pts
                        entry_time = curr['time']
                        continue

                # 2. BULLISH ENGULFING (BUY)
                sl_distance_buy = curr['close'] - curr['low']
                if sl_distance_buy <= max_allowed_sl_dist:
                    downside_push = (p1['close'] < p1['open']) and (p1['low'] <= p2['low']) and (p1['close'] < curr['EMA20'])
                    prev_is_red = (p1['close'] < p1['open'])
                    curr_is_green = (curr['close'] > curr['open'])
                    pure_bull_engulf = (curr['open'] <= (p1['close'] + (8.0 if 'BTC' in symbol else 0.4))) and (curr['close'] > p1['open'])
                    trend_ok_buy = curr['close'] > curr['EMA200']

                    if downside_push and prev_is_red and curr_is_green and pure_bull_engulf and trend_ok_buy:
                        in_pos = True
                        pos_side = "BUY"
                        entry_p = curr['close']
                        sl_p = curr['low']
                        tp_p = entry_p + target_pts
                        entry_time = curr['time']
                        continue

            else:
                if pos_side == "BUY":
                    if curr['high'] >= tp_p:
                        pts_gain = tp_p - entry_p
                        pnl_pct = (pts_gain / entry_p) * 100 * leverage
                        trades.append({
                            "Date": str(entry_time.date()),
                            "Entry_Time": entry_time.strftime("%d-%b %H:%M"),
                            "Exit_Time": curr['time'].strftime("%d-%b %H:%M"),
                            "Strategy": "BTC Battle" if "BTC" in symbol else "ETH Battle",
                            "Side": "BUY",
                            "Entry": f"${entry_p:,.2f}",
                            "Exit": f"${tp_p:,.2f}",
                            "Points": f"+{pts_gain:,.1f} pts",
                            "PnL_Pct": round(pnl_pct, 2),
                            "Result": "TP HIT 🎯"
                        })
                        in_pos = False
                    elif curr['close'] <= sl_p:
                        pts_loss = entry_p - curr['close']
                        pnl_pct = -(pts_loss / entry_p) * 100 * leverage
                        trades.append({
                            "Date": str(entry_time.date()),
                            "Entry_Time": entry_time.strftime("%d-%b %H:%M"),
                            "Exit_Time": curr['time'].strftime("%d-%b %H:%M"),
                            "Strategy": "BTC Battle" if "BTC" in symbol else "ETH Battle",
                            "Side": "BUY",
                            "Entry": f"${entry_p:,.2f}",
                            "Exit": f"${curr['close']:,.2f}",
                            "Points": f"-{pts_loss:,.1f} pts",
                            "PnL_Pct": round(pnl_pct, 2),
                            "Result": "SL HIT 🛑"
                        })
                        in_pos = False

                elif pos_side == "SELL":
                    if curr['low'] <= tp_p:
                        pts_gain = entry_p - tp_p
                        pnl_pct = (pts_gain / entry_p) * 100 * leverage
                        trades.append({
                            "Date": str(entry_time.date()),
                            "Entry_Time": entry_time.strftime("%d-%b %H:%M"),
                            "Exit_Time": curr['time'].strftime("%d-%b %H:%M"),
                            "Strategy": "BTC Battle" if "BTC" in symbol else "ETH Battle",
                            "Side": "SELL",
                            "Entry": f"${entry_p:,.2f}",
                            "Exit": f"${tp_p:,.2f}",
                            "Points": f"+{pts_gain:,.1f} pts",
                            "PnL_Pct": round(pnl_pct, 2),
                            "Result": "TP HIT 🎯"
                        })
                        in_pos = False
                    elif curr['close'] >= sl_p:
                        pts_loss = curr['close'] - entry_p
                        pnl_pct = -(pts_loss / entry_p) * 100 * leverage
                        trades.append({
                            "Date": str(entry_time.date()),
                            "Entry_Time": entry_time.strftime("%d-%b %H:%M"),
                            "Exit_Time": curr['time'].strftime("%d-%b %H:%M"),
                            "Strategy": "BTC Battle" if "BTC" in symbol else "ETH Battle",
                            "Side": "SELL",
                            "Entry": f"${entry_p:,.2f}",
                            "Exit": f"${curr['close']:,.2f}",
                            "Points": f"-{pts_loss:,.1f} pts",
                            "PnL_Pct": round(pnl_pct, 2),
                            "Result": "SL HIT 🛑"
                        })
                        in_pos = False

        return pd.DataFrame(trades)
    except Exception: return pd.DataFrame()

def run_hft_backtest_simulation(symbol="BTCUSDT", interval="5m", days=90, leverage=50, tp_pct=2.0, sl_pct=1.0):
    try:
        end_ms = int(time.time() * 1000)
        start_ms = end_ms - (days * 24 * 60 * 60 * 1000)
        all_candles = []
        cur_start = start_ms

        while cur_start < end_ms:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&startTime={cur_start}&endTime={end_ms}&limit=1000"
            res = requests.get(url, timeout=5).json()
            if not res or not isinstance(res, list) or len(res) == 0: break
            all_candles.extend(res)
            cur_start = res[-1][0] + 1
            if len(res) < 1000: break
            time.sleep(0.04)

        if not all_candles: return pd.DataFrame()

        df = pd.DataFrame(all_candles, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'ct', 'qav', 't', 'tbv', 'tqv', 'ig'])
        df['time'] = pd.to_datetime(df['time'], unit='ms') + timedelta(hours=5, minutes=30)
        for col in ['open', 'high', 'low', 'close', 'vol']: df[col] = df[col].astype(float)
        df.drop_duplicates(subset=['time'], inplace=True)
        df.sort_values(by='time', inplace=True)

        df['EMA_Fast'] = df['close'].ewm(span=20, adjust=False).mean()
        df['EMA_Slow'] = df['close'].ewm(span=50, adjust=False).mean()

        trades = []
        in_pos = False
        entry_price = 0
        entry_time = None

        for i in range(1, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i-1]

            if not in_pos and prev['EMA_Fast'] <= prev['EMA_Slow'] and row['EMA_Fast'] > row['EMA_Slow']:
                in_pos = True
                entry_price = row['close']
                entry_time = row['time']
            elif in_pos:
                high_gain = ((row['high'] - entry_price) / entry_price) * 100
                low_drop = ((entry_price - row['low']) / entry_price) * 100

                if high_gain >= tp_pct:
                    trades.append({
                        "Date": str(entry_time.date()),
                        "Entry_Time": entry_time.strftime("%d-%b %H:%M"),
                        "Exit_Time": row['time'].strftime("%d-%b %H:%M"),
                        "Strategy": "HFT Surfer",
                        "Side": "BUY",
                        "Entry": f"${entry_price:,.2f}",
                        "Exit": f"${entry_price * (1 + tp_pct/100):,.2f}",
                        "PnL_Pct": round(tp_pct * leverage, 2),
                        "Result": "TP HIT 🎯"
                    })
                    in_pos = False
                elif low_drop >= sl_pct:
                    trades.append({
                        "Date": str(entry_time.date()),
                        "Entry_Time": entry_time.strftime("%d-%b %H:%M"),
                        "Exit_Time": row['time'].strftime("%d-%b %H:%M"),
                        "Strategy": "HFT Surfer",
                        "Side": "BUY",
                        "Entry": f"${entry_price:,.2f}",
                        "Exit": f"${entry_price * (1 - sl_pct/100):,.2f}",
                        "PnL_Pct": round(-sl_pct * leverage, 2),
                        "Result": "SL HIT 🛑"
                    })
                    in_pos = False

        return pd.DataFrame(trades)
    except Exception: return pd.DataFrame()

# ==============================================================================
# 3. AUTHENTICATION & LOGIN GATEWAY
# ==============================================================================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["user_data"] = None
    st.session_state["username"] = None

def render_login_page():
    st.markdown("""
    <div style="max-width: 440px; margin: 60px auto 20px auto; padding: 30px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); text-align: center;">
        <div style="font-size: 42px; margin-bottom: 8px;">⚡</div>
        <h2 style="margin: 0; color: #0f172a; font-weight: 800;">Stockimyze AlgoTrade</h2>
        <p style="color: #64748b; font-size: 13px; margin-top: 4px; margin-bottom: 24px;">Institutional Algorithmic Platform</p>
    </div>
    """, unsafe_allow_html=True)

    _, col2, _ = st.columns([1, 1.2, 1])
    with col2:
        with st.form("login_form"):
            st.markdown("<div style='font-weight:700; font-size:14px; margin-bottom:6px;'>Sign In</div>", unsafe_allow_html=True)
            u_in = st.text_input("Username / Client ID", placeholder="admin or client1")
            p_in = st.text_input("Password", type="password", placeholder="Password")
            sub = st.form_submit_button("🔐 Sign In", type="primary", use_container_width=True)

            if sub:
                db = load_json(USERS_FILE)
                uname = u_in.strip().lower()
                user = db.get(uname)
                if user and user.get("status") == "Active" and user.get("password") == hash_password(p_in.strip()):
                    st.session_state["authenticated"] = True
                    st.session_state["user_data"] = user
                    st.session_state["username"] = uname
                    st.session_state["current_page"] = "Dashboard"
                    log_audit(uname, "LOGIN_SUCCESS", "User authenticated successfully")
                    st.rerun()
                else:
                    st.error("Invalid credentials or account suspended.")
        st.caption("Admin: **admin** / **admin123** • Client: **client1** / **client123**")

if not st.session_state["authenticated"]:
    render_login_page()
    st.stop()

users_db = load_json(USERS_FILE)
logged_username = st.session_state["username"]
logged_user = users_db.get(logged_username, st.session_state["user_data"])
is_admin = (logged_user.get("role") == "admin")
allowed_strats = logged_user.get("allowed_strategies", ["BTCUSDT HFT", "ETHUSDT HFT", "BTC Battle", "ETH Battle"])
client_brokers = logged_user.get("brokers", {})

# ==============================================================================
# 4. LIVE MARKET TICKERS & CLIENT ENGINE
# ==============================================================================
@st.cache_data(ttl=5)
def get_live_tickers():
    prices = {"NIFTY": 25390.40, "BANKNIFTY": 52120.15, "SENSEX": 83140.80, "BTC": 76480.00, "ETH": 2645.00}
    try:
        url_in = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=^NSEI,^NSEBANK,^BSESN"
        res_in = requests.get(url_in, headers={"User-Agent": "Mozilla/5.0"}, timeout=2).json()
        for item in res_in.get("quoteResponse", {}).get("result", []):
            sym = item.get("symbol")
            price = item.get("regularMarketPrice")
            if sym == "^NSEI" and price: prices["NIFTY"] = float(price)
            elif sym == "^NSEBANK" and price: prices["BANKNIFTY"] = float(price)
            elif sym == "^BSESN" and price: prices["SENSEX"] = float(price)
    except Exception: pass
    try:
        res_cr = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=2).json()
        ticker_map = {item['symbol']: float(item['price']) for item in res_cr if item['symbol'] in ['BTCUSDT', 'ETHUSDT']}
        if 'BTCUSDT' in ticker_map: prices["BTC"] = ticker_map['BTCUSDT']
        if 'ETHUSDT' in ticker_map: prices["ETH"] = ticker_map['ETHUSDT']
    except Exception: pass
    return prices

live_prices = get_live_tickers()
is_cosmic_connected = (client_brokers.get("Cosmic Trade", {}).get("status") == "CONNECTED")

class CosmicTradeClient:
    def __init__(self, username):
        u = load_json(USERS_FILE).get(username, {})
        b_info = u.get("brokers", {}).get("Cosmic Trade", {})
        self.api_key = b_info.get("raw_key", os.getenv("COSMIC_API_KEY", "DEMO_KEY"))
        self.api_secret = b_info.get("secret", os.getenv("COSMIC_API_SECRET", "DEMO_SECRET"))
        self.base_url = "https://api.cosmictrade.com"

    def execute_bracket_trade(self, symbol, side, qty, leverage, sl_price, tp_price, current_price):
        order_result = {
            "symbol": symbol,
            "side": side.upper(),
            "leverage": f"{leverage}x",
            "qty": qty,
            "entry": current_price,
            "tp": round(tp_price, 2),
            "sl": round(sl_price, 2),
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        return True, order_result

cosmic_engine = CosmicTradeClient(logged_username)

# UI Styles
st.markdown("""
<style>
    .block-container { padding-top: 0.5rem !important; padding-bottom: 2rem !important; padding-left: 2rem !important; }
    header[data-testid="stHeader"] { background: transparent !important; height: 1.2rem !important; }
    .stApp { background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    section[data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; padding-top: 10px !important; }
    section[data-testid="stSidebar"] .stButton > button { border: none !important; background: transparent !important; color: #475569 !important; font-weight: 500 !important; font-size: 14px !important; padding: 8px 12px !important; border-radius: 8px !important; text-align: left !important; justify-content: flex-start !important; width: 100% !important; margin-bottom: 2px !important; }
    section[data-testid="stSidebar"] .stButton > button:hover { background-color: #f1f5f9 !important; color: #0f172a !important; }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] { background-color: #eff6ff !important; color: #2563eb !important; font-weight: 600 !important; border-left: 3px solid #2563eb !important; border-radius: 0 8px 8px 0 !important; }
    .sidebar-section { font-size: 11px; font-weight: 700; color: #94a3b8; letter-spacing: 0.08em; margin-top: 14px; margin-bottom: 6px; padding-left: 8px; text-transform: uppercase; }
    .ticker-matrix-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 8px 14px; display: flex; flex-direction: column; gap: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.03); }
    .ticker-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .row-badge { font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.06em; padding: 3px 8px; border-radius: 6px; min-width: 60px; text-align: center; }
    .badge-in { background: #e0f2fe; color: #0369a1; }
    .badge-global { background: #fef3c7; color: #b45309; }
    .market-chip { display: inline-flex; align-items: center; gap: 6px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 4px 10px; border-radius: 7px; }
    .market-chip .symbol { font-size: 12px; font-weight: 700; color: #475569; }
    .market-chip .val { font-size: 14px; font-weight: 800; color: #0f172a; }
    .status-pill { padding: 4px 10px; border-radius: 16px; font-size: 11px; font-weight: 700; display: inline-flex; align-items: center; gap: 4px; }
    .pill-green { background: #dcfce7; color: #15803d; }
    .pill-red { background: #fee2e2; color: #b91c1c; }
    .stat-box { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); margin-bottom: 10px; }
    .stat-title { color: #64748b; font-size: 12px; font-weight: 600; display: flex; justify-content: space-between; }
    .stat-val { color: #0f172a; font-size: 24px; font-weight: 800; margin: 4px 0; }
    .broker-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 16px; margin-bottom: 10px; }
    .broker-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .broker-meta { display: flex; align-items: center; gap: 10px; }
    .broker-logo { width: 38px; height: 38px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 13px; color: white; }
    .broker-info-row { display: flex; background: #f8fafc; border-radius: 8px; padding: 9px 11px; border: 1px solid #f1f5f9; margin-bottom: 12px; justify-content: space-between; }
    .info-label { font-size: 11px; color: #94a3b8; font-weight: 600; }
    .info-val { font-size: 12px; color: #1e293b; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

if "current_page" not in st.session_state: st.session_state["current_page"] = "Dashboard"

if "btc_algo_active" not in st.session_state: st.session_state["btc_algo_active"] = False
if "eth_algo_active" not in st.session_state: st.session_state["eth_algo_active"] = False
if "btc_cfg" not in st.session_state:
    st.session_state["btc_cfg"] = {"leverage": min(50, logged_user.get("max_leverage", 50)), "qty": 0.005, "tp_price": 78000.0, "sl_price": 75000.0, "tp_pct": 2.5, "sl_pct": 1.5}
if "eth_cfg" not in st.session_state:
    st.session_state["eth_cfg"] = {"leverage": min(30, logged_user.get("max_leverage", 50)), "qty": 0.100, "tp_price": 2750.0, "sl_price": 2580.0, "tp_pct": 3.0, "sl_pct": 2.0}

if "btc_battle_active" not in st.session_state: st.session_state["btc_battle_active"] = False
if "eth_battle_active" not in st.session_state: st.session_state["eth_battle_active"] = False
if "btc_battle_cfg" not in st.session_state:
    st.session_state["btc_battle_cfg"] = {"leverage": 50, "qty": 0.010, "target_pts": 400.0, "timeframe": "5m"}
if "eth_battle_cfg" not in st.session_state:
    st.session_state["eth_battle_cfg"] = {"leverage": 50, "qty": 0.200, "target_pts": 10.0, "timeframe": "5m"}

if "live_logs" not in st.session_state: st.session_state["live_logs"] = []

# ----------------- SIDEBAR -----------------
with st.sidebar:
    logo_file = next((f for f in ["logo.png", "logo.jpg", "logo.jpeg"] if os.path.exists(f)), None)
    img_tag = f'<img src="data:image/png;base64,{base64.b64encode(open(logo_file, "rb").read()).decode()}" style="width: 55px; height: 55px; object-fit: contain; margin-bottom: 4px;">' if logo_file else '<div style="font-size: 28px;">⚡</div>'

    st.markdown(f"""
    <div style="margin-bottom: 12px;">
        {img_tag}
        <div style="font-weight: 800; font-size: 17px; color: #0b192c; line-height: 1.2;">Stockimyze AlgoTrade</div>
        <div style="color: #627289; font-size: 10px; font-weight: 700; text-transform: uppercase; margin-top: 2px;">MULTI-STRATEGY PLATFORM</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">TRADING</div>', unsafe_allow_html=True)
    trading_nav = [
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
        ("Reports", "📋  Reports")
    ]
    for key, label in trading_nav:
        is_active = (st.session_state["current_page"] == key)
        if st.button(label, key=f"nav_{key}", type="primary" if is_active else "secondary", use_container_width=True):
            st.session_state["current_page"] = key
            st.rerun()

    if is_admin:
        st.markdown('<div class="sidebar-section">ADMIN</div>', unsafe_allow_html=True)
        admin_nav = [
            ("Admin_Users", "👥  Users"),
            ("Admin_Subscriptions", "🛡️  Subscriptions"),
            ("Admin_Payments", "💵  Payments"),
            ("Admin_Strategies", "📚  Strategies Master"),
            ("Admin_BrokerMgmt", "🔌  Broker Management"),
            ("Admin_Tickets", "🎫  Support Tickets"),
            ("Admin_AuditLogs", "📜  Audit Logs"),
            ("Admin_SystemHealth", "⚡  System Health"),
            ("Admin_MacroAlerts", "🔔  Macro Alerts"),
            ("Admin_AOCData", "🗄️  AOC Data")
        ]
        for key, label in admin_nav:
            is_active = (st.session_state["current_page"] == key)
            if st.button(label, key=f"nav_{key}", type="primary" if is_active else "secondary", use_container_width=True):
                st.session_state["current_page"] = key
                st.rerun()

    st.markdown('<div class="sidebar-section">ACCOUNT</div>', unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:12px; padding-left:8px; margin-bottom:8px;'>User: <b>{logged_user.get('name')}</b><br><span style='font-size:10px; font-weight:800; color:#2563eb;'>{'👑 ADMIN' if is_admin else '👤 CLIENT'}</span></div>", unsafe_allow_html=True)
    if st.button("🚪 Logout", key="btn_logout_sb", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["user_data"] = None
        st.session_state["username"] = None
        st.rerun()

# ----------------- TOP TICKER BAR -----------------
col_strip, col_usr = st.columns([4.2, 1.1])
with col_strip:
    st.markdown(f"""
    <div class="ticker-matrix-card">
        <div class="ticker-row">
            <span class="row-badge badge-in">INDIAN</span>
            <div class="market-chip" style="border-left: 3px solid #0284c7;"><span class="symbol" style="color:#0284c7;">🇮🇳 NIFTY</span><span class="val">{live_prices['NIFTY']:,.2f}</span></div>
            <div class="market-chip" style="border-left: 3px solid #7c3aed;"><span class="symbol" style="color:#7c3aed;">🏦 BANK NIFTY</span><span class="val">{live_prices['BANKNIFTY']:,.2f}</span></div>
            <span class="status-pill pill-green" style="margin-left: auto;">● NSE Live</span>
        </div>
        <div class="ticker-row">
            <span class="row-badge badge-global">GLOBAL</span>
            <div class="market-chip" style="border-left: 3px solid #f59e0b;"><span class="symbol" style="color:#d97706;">₿ BTC/USDT</span><span class="val">${live_prices['BTC']:,.2f}</span></div>
            <div class="market-chip" style="border-left: 3px solid #4f46e5;"><span class="symbol" style="color:#4f46e5;">⟠ ETH/USDT</span><span class="val">${live_prices['ETH']:,.2f}</span></div>
            <span class="status-pill {'pill-green' if is_cosmic_connected else 'pill-red'}" style="margin-left: auto;">
                {'● Cosmic Connected' if is_cosmic_connected else '○ Cosmic Disconnected'}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_usr:
    with st.popover(f"👤 {logged_user.get('name')}", use_container_width=True):
        st.markdown(f"**{logged_user.get('name')}** (@{logged_username})")
        st.caption(f"Role: {logged_user.get('role').capitalize()}")
        st.markdown(f"🔹 **Cosmic Broker:** {'Connected ✅' if is_cosmic_connected else 'Not Linked ❌'}")
        if st.button("🚪 Logout Account", key="u_out_pop", type="primary", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state["user_data"] = None
            st.session_state["username"] = None
            st.rerun()

selected_page = st.session_state["current_page"]

# ==============================================================================
# ROUTE: DASHBOARD
# ==============================================================================
if selected_page == "Dashboard":
    st.markdown(f"""
    <div style="background:#ffffff; border:1px solid #e2e8f0; border-left:5px solid #2563eb; border-radius:12px; padding:12px 18px; margin-top:14px; margin-bottom:14px; display:flex; justify-content:space-between; align-items:center;">
        <div>
            <div style="font-size:18px; font-weight:800; color:#0f172a;">✨ Welcome, {logged_user.get('name')}</div>
            <div style="font-size:12px; color:#64748b;">Active Engines: HFT Trend Surfer & Pure Body Engulfing Battle</div>
        </div>
        <div style="font-size:12px; font-weight:700; color:#2563eb; background:#eff6ff; border:1px solid #bfdbfe; padding:5px 14px; border-radius:20px;">
            ⚡ Status: {'Ready To Trade' if is_cosmic_connected else 'Setup Broker API First'}
        </div>
    </div>
    """, unsafe_allow_html=True)

    df_logs = load_trade_logs()
    user_trades = df_logs[df_logs["User"] == logged_username] if not df_logs.empty and "User" in df_logs.columns else pd.DataFrame()
    realized_pnl = user_trades["PnL_$"].sum() if not user_trades.empty else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="stat-box"><div class="stat-title">BTC Battle Target</div><div class="stat-val" style="color:#16a34a;">400 Pts</div><div style="font-size:11px;color:#64748b;">Candle High/Low SL</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="stat-box"><div class="stat-title">ETH Battle Target</div><div class="stat-val" style="color:#2563eb;">10 Pts</div><div style="font-size:11px;color:#64748b;">Candle High/Low SL</div></div>', unsafe_allow_html=True)
    with c3:
        running_bots = sum([
            1 if st.session_state["btc_algo_active"] else 0,
            1 if st.session_state["eth_algo_active"] else 0,
            1 if st.session_state["btc_battle_active"] else 0,
            1 if st.session_state["eth_battle_active"] else 0
        ])
        st.markdown(f'<div class="stat-box"><div class="stat-title">Running Bots</div><div class="stat-val">{running_bots} Active</div><div style="font-size:11px;color:#16a34a;">● Pure Body Engulfing</div></div>', unsafe_allow_html=True)
    with c4:
        pnl_col = "#16a34a" if realized_pnl >= 0 else "#dc2626"
        st.markdown(f'<div class="stat-box"><div class="stat-title">Realized PnL</div><div class="stat-val" style="color:{pnl_col};">${realized_pnl:+,.2f}</div><div style="font-size:11px;color:#16a34a;">↗ All Strategies</div></div>', unsafe_allow_html=True)

    try:
        url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=60"
        res = requests.get(url, timeout=2).json()
        df_m = pd.DataFrame(res, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'ct', 'qav', 't', 'tbv', 'tqv', 'ig'])
        df_m['time'] = pd.to_datetime(df_m['time'], unit='ms') + timedelta(hours=5, minutes=30)
        for c in ['open', 'high', 'low', 'close']: df_m[c] = df_m[c].astype(float)
        df_m['EMA20'] = df_m['close'].ewm(span=20, adjust=False).mean()

        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df_m['time'], open=df_m['open'], high=df_m['high'], low=df_m['low'], close=df_m['close'], name="BTC 5m (IST)", increasing_line_color='#10b981', increasing_fillcolor='#10b981', decreasing_line_color='#ef4444', decreasing_fillcolor='#ef4444'))
        fig.add_trace(go.Scatter(x=df_m['time'], y=df_m['EMA20'], mode='lines', line=dict(color='#2563eb', width=1.5), name='Trend Push EMA 20'))
        fig.update_layout(xaxis_rangeslider_visible=False, height=360, margin=dict(l=10, r=40, t=10, b=10), plot_bgcolor="#ffffff", paper_bgcolor="#ffffff", font=dict(color="#64748b", size=11), yaxis=dict(side="right", showgrid=True, gridcolor='#f8fafc', zeroline=False), xaxis=dict(showgrid=True, gridcolor='#f8fafc', zeroline=False))
        st.markdown('<div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:10px; box-shadow:0 1px 3px rgba(0,0,0,0.02); margin-top: 10px;">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    except Exception: pass

# ==============================================================================
# ROUTE: STRATEGIES (4 TABS)
# ==============================================================================
elif selected_page == "Strategies":
    st.markdown("<h2 style='margin-top: 10px; margin-bottom: 2px; color: #0f172a;'>Algorithmic Strategy Operations</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 14px; margin-bottom: 16px;'>Switch between original HFT Trend Surfer strategies and Pure Trend-Aligned Engulfing Battle strategies.</p>", unsafe_allow_html=True)

    tab_btc_hft, tab_eth_hft, tab_btc_battle, tab_eth_battle = st.tabs([
        "₿ Bitcoin Engine (BTCUSDT HFT)",
        "⟠ Ethereum Engine (ETHUSDT HFT)",
        "⚔️ BTC Battle (400 Pts Target)",
        "⚔️ ETH Battle (10 Pts Target)"
    ])

    def render_hft_strategy(symbol, live_price, is_active_key, cfg_key):
        cfg = st.session_state[cfg_key]
        c_left, c_right = st.columns([1.7, 1.3])

        pos_key = f"open_pos_{symbol}_{logged_username}"
        if pos_key in st.session_state and st.session_state[pos_key]:
            pos = st.session_state[pos_key]
            entry_p = pos["entry"]
            tp_p = pos["tp"]
            sl_p = pos["sl"]
            notional = pos["qty"] * entry_p * pos["leverage"]

            if live_price >= tp_p:
                gain_pct = ((live_price - entry_p) / entry_p) * 100
                pnl_usd = notional * (gain_pct / 100)
                log_trade(f"HFT-{int(time.time())}", datetime.now().strftime("%Y-%m-%d"), pos["time"], datetime.now().strftime("%H:%M:%S"), symbol, f"{symbol} HFT", pos["side"], pos["leverage"], pos["qty"], entry_p, live_price, "TAKE_PROFIT_LIMIT", pnl_usd, gain_pct * pos["leverage"], "CLOSED (PROFIT)")
                del st.session_state[pos_key]
                st.toast(f"🎉 {symbol} Target Hit! Profit +${pnl_usd:,.2f} booked.", icon="✅")
                st.rerun()

            elif live_price <= sl_p:
                loss_pct = ((entry_p - live_price) / entry_p) * 100
                loss_usd = notional * (loss_pct / 100)
                log_trade(f"HFT-{int(time.time())}", datetime.now().strftime("%Y-%m-%d"), pos["time"], datetime.now().strftime("%H:%M:%S"), symbol, f"{symbol} HFT", pos["side"], pos["leverage"], pos["qty"], entry_p, live_price, "STOP_LOSS_MARKET", -loss_usd, -(loss_pct * pos["leverage"]), "CLOSED (STOP_LOSS)")
                del st.session_state[pos_key]
                st.toast(f"🛑 {symbol} Stop Loss Triggered! Loss -${loss_usd:,.2f} recorded.", icon="⚠️")
                st.rerun()

        with c_left:
            is_active = st.session_state[is_active_key]
            status_text = "● RUNNING" if is_active else "○ STOPPED"
            status_color = "#16a34a" if is_active else "#64748b"
            bg_badge = "#dcfce7" if is_active else "#f1f5f9"
            accent_col = "#f59e0b" if symbol == "BTCUSDT" else "#6366f1"

            st.markdown(f"""
            <div style="background:#ffffff; border:1px solid #e2e8f0; border-left: 4px solid {accent_col}; border-radius:14px; padding:18px; margin-bottom:15px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div style="display:flex; align-items:center; gap:12px;">
                        <div style="width:40px; height:40px; background:#eff6ff; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:20px;">{"₿" if symbol=="BTCUSDT" else "⟠"}</div>
                        <div>
                            <div style="font-weight:800; font-size:16px; color:#0f172a;">{symbol} Cosmic Auto-HFT</div>
                            <div style="font-size:12px; color:#64748b;">Live Exchange: <b>${live_price:,.2f}</b> • Linked: <b>@{logged_username}</b></div>
                        </div>
                    </div>
                    <span style="background:{bg_badge}; color:{status_color}; font-weight:700; font-size:11px; padding:4px 10px; border-radius:20px;">{status_text}</span>
                </div>
                <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:10px; background:#f8fafc; padding:12px; border-radius:10px;">
                    <div><div style="font-size:11px; color:#94a3b8; font-weight:600;">Timeframe</div><div style="font-weight:700; font-size:13px;">1m / 5m</div></div>
                    <div><div style="font-size:11px; color:#94a3b8; font-weight:600;">Active Leverage</div><div style="font-weight:700; font-size:13px; color:#dc2626;">{cfg['leverage']}x</div></div>
                    <div><div style="font-size:11px; color:#94a3b8; font-weight:600;">Take Profit</div><div style="font-weight:700; font-size:13px; color:#16a34a;">${cfg['tp_price']:,.2f}</div></div>
                    <div><div style="font-size:11px; color:#94a3b8; font-weight:600;">Stop Loss</div><div style="font-weight:700; font-size:13px; color:#dc2626;">${cfg['sl_price']:,.2f}</div></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            b1, b2 = st.columns(2)
            with b1:
                if is_active:
                    if st.button(f"⏹ Stop {symbol} Auto-Pilot", key=f"stop_{symbol}", type="secondary", use_container_width=True):
                        st.session_state[is_active_key] = False
                        st.rerun()
                else:
                    if st.button(f"▶ Start {symbol} Auto-Pilot", key=f"start_{symbol}", type="primary", use_container_width=True):
                        st.session_state[is_active_key] = True
                        st.rerun()
            with b2:
                if st.button(f"🚀 Fire Instant Setup ({symbol})", key=f"fire_{symbol}", use_container_width=True):
                    ok, res = cosmic_engine.execute_bracket_trade(symbol, "BUY", cfg["qty"], cfg["leverage"], cfg["sl_price"], cfg["tp_price"], live_price)
                    st.session_state[pos_key] = {"time": res["timestamp"], "entry": res["entry"], "tp": res["tp"], "sl": res["sl"], "qty": res["qty"], "leverage": cfg["leverage"], "side": "BUY"}
                    st.toast(f"⚡ Cosmic Trade: {symbol} Bracket Order Placed!", icon="🚀")
                    st.rerun()

            st.markdown(f"<div style='margin-top: 15px; font-weight:700; font-size:14px; color:#0f172a;'>⚡ {symbol} Terminal Logs:</div>", unsafe_allow_html=True)
            st.info(f"Execution gateway running for @{logged_username}.")

        with c_right:
            max_allowed_lev = int(logged_user.get("max_leverage", 50))
            with st.form(key=f"form_{symbol}"):
                f_lev = st.slider(f"{symbol} Leverage (Max: {max_allowed_lev}x)", min_value=1, max_value=max_allowed_lev, value=min(int(cfg["leverage"]), max_allowed_lev))
                cq1, cq2 = st.columns(2)
                with cq1: f_qty = st.number_input("Order Quantity", value=float(cfg["qty"]), step=0.001 if symbol=="BTCUSDT" else 0.01, format="%.3f")
                with cq2:
                    notional = f_qty * live_price * f_lev
                    st.markdown(f"<div style='font-size:11px; color:#64748b; margin-top:24px;'>Position: <b>${notional:,.0f}</b><br>Margin: <b>${(f_qty*live_price):,.2f}</b></div>", unsafe_allow_html=True)

                st.markdown("<div style='font-weight:700; font-size:13px; margin-top:6px;'>Target & Cutoff Price ($):</div>", unsafe_allow_html=True)
                ctp, csl = st.columns(2)
                with ctp: f_tp_price = st.number_input("Take Profit ($)", value=float(cfg["tp_price"]), step=10.0 if symbol=="BTCUSDT" else 1.0, format="%.2f")
                with csl: f_sl_price = st.number_input("Stop Loss ($)", value=float(cfg["sl_price"]), step=10.0 if symbol=="BTCUSDT" else 1.0, format="%.2f")

                if st.form_submit_button(f"💾 Save {symbol} Settings", type="primary", use_container_width=True):
                    st.session_state[cfg_key] = {"leverage": f_lev, "qty": f_qty, "tp_price": f_tp_price, "sl_price": f_sl_price, "tp_pct": 2.0, "sl_pct": 1.0}
                    st.success(f"{symbol} settings saved!")
                    st.rerun()

    def render_battle_strategy(strat_name, symbol, live_price, active_key, cfg_key):
        cfg = st.session_state[cfg_key]
        c_left, c_right = st.columns([1.7, 1.3])

        pos_k = f"battle_pos_{symbol}_{logged_username}"
        if pos_k in st.session_state and st.session_state[pos_k]:
            pos = st.session_state[pos_k]

            if pos["side"] == "BUY":
                if live_price >= pos["tp"]:
                    pnl_d = (pos["tp"] - pos["entry"]) * pos["qty"] * pos["leverage"]
                    log_trade(f"BTL-{int(time.time())}", datetime.now().strftime("%Y-%m-%d"), pos["time"], datetime.now().strftime("%H:%M:%S"), symbol, strat_name, "BUY", pos["leverage"], pos["qty"], pos["entry"], pos["tp"], "TARGET_REACHED", pnl_d, ((pos['tp']-pos['entry'])/pos['entry'])*100*pos['leverage'], "CLOSED (PROFIT)")
                    del st.session_state[pos_k]
                    st.toast(f"🎯 {strat_name} Target Hit! Profit +${pnl_d:,.2f} booked.", icon="✅")
                    st.rerun()
                elif live_price <= pos["sl"]:
                    loss_d = (pos["entry"] - pos["sl"]) * pos["qty"] * pos["leverage"]
                    log_trade(f"BTL-{int(time.time())}", datetime.now().strftime("%Y-%m-%d"), pos["time"], datetime.now().strftime("%H:%M:%S"), symbol, strat_name, "BUY", pos["leverage"], pos["qty"], pos["entry"], pos["sl"], "CANDLE_LOW_SL", -loss_d, -((pos['entry']-pos['sl'])/pos['entry'])*100*pos['leverage'], "CLOSED (STOP_LOSS)")
                    del st.session_state[pos_k]
                    st.toast(f"🛑 {strat_name} Candle Low SL Triggered! Loss -${loss_d:,.2f} recorded.", icon="⚠️")
                    st.rerun()

            elif pos["side"] == "SELL":
                if live_price <= pos["tp"]:
                    pnl_d = (pos["entry"] - pos["tp"]) * pos["qty"] * pos["leverage"]
                    log_trade(f"BTL-{int(time.time())}", datetime.now().strftime("%Y-%m-%d"), pos["time"], datetime.now().strftime("%H:%M:%S"), symbol, strat_name, "SELL", pos["leverage"], pos["qty"], pos["entry"], pos["tp"], "TARGET_REACHED", pnl_d, ((pos['entry']-pos['tp'])/pos['entry'])*100*pos['leverage'], "CLOSED (PROFIT)")
                    del st.session_state[pos_k]
                    st.toast(f"🎯 {strat_name} Target Hit! Profit +${pnl_d:,.2f} booked.", icon="✅")
                    st.rerun()
                elif live_price >= pos["sl"]:
                    loss_d = (pos["sl"] - pos["entry"]) * pos["qty"] * pos["leverage"]
                    log_trade(f"BTL-{int(time.time())}", datetime.now().strftime("%Y-%m-%d"), pos["time"], datetime.now().strftime("%H:%M:%S"), symbol, strat_name, "SELL", pos["leverage"], pos["qty"], pos["entry"], pos["sl"], "CANDLE_HIGH_SL", -loss_d, -((pos['sl']-pos['entry'])/pos['entry'])*100*pos['leverage'], "CLOSED (STOP_LOSS)")
                    del st.session_state[pos_k]
                    st.toast(f"🛑 {strat_name} Candle High SL Triggered! Loss -${loss_d:,.2f} recorded.", icon="⚠️")
                    st.rerun()

        with c_left:
            is_act = st.session_state[active_key]
            st_text = "● RUNNING (TREND ALIGNED ENGULF)" if is_act else "○ STOPPED"
            st_color = "#16a34a" if is_act else "#64748b"
            bg_col = "#dcfce7" if is_act else "#f1f5f9"
            accent = "#f59e0b" if "BTC" in symbol else "#6366f1"
            target_val = cfg["target_pts"]

            st.markdown(f"""
            <div style="background:#ffffff; border:1px solid #e2e8f0; border-left:4px solid {accent}; border-radius:14px; padding:18px; margin-bottom:15px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div>
                        <div style="font-weight:800; font-size:17px; color:#0f172a;">{strat_name}</div>
                        <div style="font-size:12px; color:#64748b;">Market: <b>${live_price:,.2f}</b> • Rule: <b>Trend Aligned + Pure Body Engulfing</b></div>
                    </div>
                    <span style="background:{bg_col}; color:{st_color}; font-weight:700; font-size:11px; padding:4px 10px; border-radius:20px;">{st_text}</span>
                </div>
                <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:10px; background:#f8fafc; padding:12px; border-radius:10px;">
                    <div><div style="font-size:11px; color:#94a3b8; font-weight:600;">Timeframe</div><div style="font-weight:700; font-size:13px;">5 Minutes (IST)</div></div>
                    <div><div style="font-size:11px; color:#94a3b8; font-weight:600;">Target</div><div style="font-weight:700; font-size:13px; color:#16a34a;">{target_val} Points</div></div>
                    <div><div style="font-size:11px; color:#94a3b8; font-weight:600;">Stop Loss</div><div style="font-weight:700; font-size:13px; color:#dc2626;">Candle High/Low</div></div>
                    <div><div style="font-size:11px; color:#94a3b8; font-weight:600;">Trend Protection</div><div style="font-weight:700; font-size:13px; color:#2563eb;">EMA 200 + R:R</div></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            b1, b2, b3 = st.columns(3)
            with b1:
                if is_act:
                    if st.button(f"⏹ Stop {strat_name}", key=f"stop_{symbol}_btl", type="secondary", use_container_width=True):
                        st.session_state[active_key] = False
                        st.rerun()
                else:
                    if st.button(f"▶ Start {strat_name}", key=f"start_{symbol}_btl", type="primary", use_container_width=True):
                        st.session_state[active_key] = True
                        st.toast(f"{strat_name} Auto-Pilot Armed!", icon="🚀")
                        st.rerun()
            with b2:
                if st.button(f"🔴 Test Bearish Sell", key=f"fire_sell_{symbol}_btl", use_container_width=True):
                    candle_high = live_price + (60.0 if "BTC" in symbol else 2.5)
                    tp_price = live_price - target_val
                    st.session_state[pos_k] = {
                        "side": "SELL", "entry": live_price, "sl": candle_high, "tp": tp_price,
                        "qty": cfg["qty"], "leverage": cfg["leverage"], "time": datetime.now().strftime("%H:%M:%S")
                    }
                    st.session_state["live_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] {strat_name} BEARISH ENGULF SELL @ ${live_price:,.2f} | SL: ${candle_high:,.2f} | TP: ${tp_price:,.2f}")
                    st.toast(f"⚡ {strat_name}: Bearish Engulfing Sell Fired!", icon="🔴")
                    st.rerun()
            with b3:
                if st.button(f"🟢 Test Bullish Buy", key=f"fire_buy_{symbol}_btl", use_container_width=True):
                    candle_low = live_price - (60.0 if "BTC" in symbol else 2.5)
                    tp_price = live_price + target_val
                    st.session_state[pos_k] = {
                        "side": "BUY", "entry": live_price, "sl": candle_low, "tp": tp_price,
                        "qty": cfg["qty"], "leverage": cfg["leverage"], "time": datetime.now().strftime("%H:%M:%S")
                    }
                    st.session_state["live_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] {strat_name} BULLISH ENGULF BUY @ ${live_price:,.2f} | SL: ${candle_low:,.2f} | TP: ${tp_price:,.2f}")
                    st.toast(f"⚡ {strat_name}: Bullish Engulfing Buy Fired!", icon="🟢")
                    st.rerun()

            st.markdown(f"<div style='margin-top: 15px; font-weight:700; font-size:14px; color:#0f172a;'>⚡ {strat_name} Terminal Feed:</div>", unsafe_allow_html=True)
            f_logs = [l for l in st.session_state["live_logs"] if strat_name in l]
            if f_logs:
                for l in reversed(f_logs[-5:]):
                    st.markdown(f"<div style='background:#ffffff; border:1px solid #e2e8f0; padding:8px 12px; border-radius:8px; font-family:monospace; font-size:12px; color:#1e293b; margin-bottom:5px;'>🟢 {l}</div>", unsafe_allow_html=True)
            else:
                st.info(f"{strat_name} active and scanning 5m candles for trend-aligned pure body engulfing patterns.")

        with c_right:
            st.markdown(f"""
            <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:16px 18px; margin-bottom:12px;">
                <div style="font-weight:800; font-size:15px; color:#0f172a;">⚙️ {strat_name} Settings</div>
            </div>
            """, unsafe_allow_html=True)

            with st.form(key=f"form_{symbol}_btl"):
                max_l = int(logged_user.get("max_leverage", 50))
                s_lev = st.slider("Execution Leverage", 1, max_l, min(int(cfg["leverage"]), max_l))
                s_qty = st.number_input("Order Quantity", value=float(cfg["qty"]), step=0.001 if "BTC" in symbol else 0.01, format="%.3f")
                s_pts = st.number_input("Fixed Target Points", value=float(cfg["target_pts"]), disabled=True)
                st.caption(f"Rule: Target is locked to {target_val} pts. Stop loss is automatically anchored to the Engulfing Candle High (Sell) / Low (Buy).")

                if st.form_submit_button("💾 Save Settings", type="primary", use_container_width=True):
                    st.session_state[cfg_key]["leverage"] = s_lev
                    st.session_state[cfg_key]["qty"] = s_qty
                    st.success(f"{strat_name} parameters locked successfully!")
                    st.rerun()

    with tab_btc_hft:
        render_hft_strategy("BTCUSDT", live_prices["BTC"], "btc_algo_active", "btc_cfg")
    with tab_eth_hft:
        render_hft_strategy("ETHUSDT", live_prices["ETH"], "eth_algo_active", "eth_cfg")
    with tab_btc_battle:
        render_battle_strategy("BTC Battle", "BTCUSDT", live_prices["BTC"], "btc_battle_active", "btc_battle_cfg")
    with tab_eth_battle:
        render_battle_strategy("ETH Battle", "ETHUSDT", live_prices["ETH"], "eth_battle_active", "eth_battle_cfg")

# ==============================================================================
# ROUTE: BACKTESTING (HFT 90-DAYS + TREND-ALIGNED BATTLE 30-DAYS)
# ==============================================================================
elif selected_page == "Backtesting":
    st.markdown("<h2 style='margin-top: 10px; margin-bottom: 2px; color: #0f172a;'>⏳ Historical Backtest Simulator</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 14px; margin-bottom: 18px;'>Test both HFT Trend Surfer (Up to 3 Months) and Trend-Aligned Engulfing Battle Strategies (Up to 1 Month) on historical Binance data.</p>", unsafe_allow_html=True)

    tab_bt_battle, tab_bt_hft = st.tabs(["⚔️ Battle Strategy Backtest (1 Month)", "📈 HFT Surfer Backtest (3 Months)"])

    with tab_bt_battle:
        b1, b2, b3 = st.columns(3)
        with b1: bt_pair = st.selectbox("Battle Trading Pair", ["BTCUSDT (BTC Battle)", "ETHUSDT (ETH Battle)"])
        with b2: bt_d = st.selectbox("Battle Horizon", [30, 15, 7], index=0, format_func=lambda x: f"Last {x} Days ({'1 Month' if x==30 else str(x)+' Days'})")
        with b3: bt_l = st.slider("Battle Leverage", 1, int(logged_user.get("max_leverage", 50)), 50, key="btl_lev_slider")

        sym_pick = "BTCUSDT" if "BTC" in bt_pair else "ETHUSDT"
        if st.button("🚀 Run 1-Month Battle Backtest", type="primary", use_container_width=True):
            with st.spinner(f"Pulling {bt_d} days of 5m candles & testing trend-aligned engulfing setups (IST Clock)..."):
                res_btl = run_engulfing_battle_backtest(sym_pick, bt_d, bt_l)
                if not res_btl.empty:
                    tc = len(res_btl)
                    wc = len(res_btl[res_btl["Result"].str.contains("TP")])
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Simulated Battle Trades", tc)
                    m2.metric("Win Rate", f"{(wc/tc)*100:.1f}%", f"{wc} TP / {tc-wc} SL")
                    m3.metric("Projected Cumulative PnL", f"{res_btl['PnL_Pct'].sum():+,.2f}%")
                    m4.metric("Strategy Target", "400 Pts (BTC) / 10 Pts (ETH)")
                    st.dataframe(res_btl.iloc[::-1], use_container_width=True, hide_index=True)
                else:
                    st.warning("No confirmed high-probability setups found in this window.")

    with tab_bt_hft:
        h1, h2, h3, h4 = st.columns(4)
        with h1: h_sym = st.selectbox("HFT Pair", ["BTCUSDT", "ETHUSDT"], key="hft_sym")
        with h2: h_tf = st.selectbox("HFT Timeframe", ["5m", "15m", "1h"], index=0, key="hft_tf")
        with h3: h_days = st.selectbox("HFT Horizon", [90, 60, 30], index=0, format_func=lambda x: f"Last {x} Days", key="hft_days")
        with h4: h_lev = st.slider("HFT Leverage", 1, int(logged_user.get("max_leverage", 50)), 50, key="hft_lev")

        p1, p2 = st.columns(2)
        with p1: h_tp = st.number_input("Target Profit TP (%)", value=2.0, step=0.1, key="hft_tp")
        with p2: h_sl = st.number_input("Stop Loss SL (%)", value=1.0, step=0.1, key="hft_sl")

        if st.button("🚀 Run 3-Month HFT Backtest", type="primary", use_container_width=True):
            with st.spinner(f"Pulling {h_days} days of historical candles from Binance..."):
                res_hft = run_hft_backtest_simulation(h_sym, h_tf, h_days, h_lev, h_tp, h_sl)
                if not res_hft.empty:
                    tc_h = len(res_hft)
                    wc_h = len(res_hft[res_hft["Result"].str.contains("TP")])
                    m1, m2, m3 = st.columns(3)
                    m1.metric("HFT Trades", tc_h)
                    m2.metric("Win Rate", f"{(wc_h/tc_h)*100:.1f}%", f"{wc_h} Won")
                    m3.metric("Projected Total Return", f"{res_hft['PnL_Pct'].sum():+,.2f}%")
                    st.dataframe(res_hft.iloc[::-1], use_container_width=True, hide_index=True)
                else:
                    st.warning("No crossover setups found.")

# ==============================================================================
# ROUTE: BROKER CONNECTIONS
# ==============================================================================
elif selected_page == "Broker Connections":
    st.markdown("<h2 style='margin-top: 10px; margin-bottom: 2px; color: #0f172a;'>Broker Connections</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 14px; margin-bottom: 20px;'>Link your live trading account to enable automated execution.</p>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        ct_info = client_brokers.get("Cosmic Trade", {"status": "DISCONNECTED", "key": "-", "expiry": "-"})
        c_status = ct_info.get("status", "DISCONNECTED")
        st.markdown(f"""
        <div class="broker-card" style="border: 2px solid {'#22c55e' if c_status=='CONNECTED' else '#cbd5e1'};">
            <div class="broker-top">
                <div class="broker-meta">
                    <div class="broker-logo" style="background:#0f172a;">CO</div>
                    <div><div style="font-weight:700; font-size:15px; color:#0f172a;">Cosmic Trade</div><div style="font-size:12px; color:#64748b;">Crypto HFT Direct API</div></div>
                </div>
                <span class="status-pill {'pill-green' if c_status=='CONNECTED' else 'pill-red'}">● {c_status}</span>
            </div>
            <div class="broker-info-row">
                <div><div class="info-label">Linked API Key</div><div class="info-val">{ct_info.get('key', '-')}</div></div>
                <div><div class="info-label">Expiry</div><div class="info-val">{ct_info.get('expiry', '-')}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if c_status == "CONNECTED":
            if st.button("Disconnect Cosmic API", use_container_width=True):
                u_db = load_json(USERS_FILE)
                u_db[logged_username]["brokers"]["Cosmic Trade"] = {"status": "DISCONNECTED", "key": "-", "secret": "", "expiry": "-"}
                save_json(USERS_FILE, u_db)
                st.session_state["user_data"] = u_db[logged_username]
                st.rerun()
        else:
            k = st.text_input("Cosmic API Key", placeholder="Enter API Key")
            s = st.text_input("Cosmic Secret", type="password", placeholder="Enter Secret")
            if st.button("Connect Cosmic API", type="primary", use_container_width=True):
                if k and s:
                    u_db = load_json(USERS_FILE)
                    u_db[logged_username].setdefault("brokers", {})["Cosmic Trade"] = {
                        "status": "CONNECTED", "key": f"{k[:4]}••••{k[-4:]}", "raw_key": k, "secret": s, "expiry": "Permanent"
                    }
                    save_json(USERS_FILE, u_db)
                    st.rerun()

    with c2:
        st.markdown("""
        <div class="broker-card">
            <div class="broker-top">
                <div class="broker-meta"><div class="broker-logo" style="background:#f59e0b;">BI</div><div><div style="font-weight:700; font-size:15px;">Binance Futures</div><div style="font-size:12px; color:#64748b;">Crypto</div></div></div>
                <span class="status-pill pill-red">● DISCONNECTED</span>
            </div>
            <div class="broker-info-row"><div><div class="info-label">API Key</div><div class="info-val">-</div></div><div><div class="info-label">Status</div><div class="info-val">Standby</div></div></div>
        </div>
        """, unsafe_allow_html=True)

# ==============================================================================
# ROUTE: TRADE HISTORY
# ==============================================================================
elif selected_page == "Trade History":
    st.markdown("<h2 style='margin-top: 10px; margin-bottom: 2px; color: #0f172a;'>📜 Execution Trade Ledger</h2>", unsafe_allow_html=True)
    df_h = load_trade_logs()
    if not df_h.empty and "User" in df_h.columns:
        if not is_admin: df_h = df_h[df_h["User"] == logged_username]
        st.dataframe(df_h.iloc[::-1], use_container_width=True, hide_index=True)
    else: st.info("No trades executed yet.")

# ==============================================================================
# FALLBACK: OTHER ROUTES (LIVE TRADING, PAPER, ORDERS, POSITIONS, ADMIN, REPORTS)
# ==============================================================================
elif selected_page in ["Live Trading", "Paper Trading", "Orders", "Positions", "Portfolio", "PnL Analytics", "Reports"]:
    st.markdown(f"<h2 style='margin-top: 10px; color: #0f172a;'>{selected_page}</h2>", unsafe_allow_html=True)
    st.caption(f"Real-time console for @{logged_username}.")
    if selected_page == "Positions":
        pos_b = st.session_state.get(f"open_pos_BTCUSDT_{logged_username}")
        pos_e = st.session_state.get(f"open_pos_ETHUSDT_{logged_username}")
        pos_b_btl = st.session_state.get(f"battle_pos_BTCUSDT_{logged_username}")
        pos_e_btl = st.session_state.get(f"battle_pos_ETHUSDT_{logged_username}")

        active_pos = []
        if pos_b: active_pos.append({**pos_b, "Symbol": "BTCUSDT", "Strategy": "BTC HFT", "Live": live_prices["BTC"]})
        if pos_e: active_pos.append({**pos_e, "Symbol": "ETHUSDT", "Strategy": "ETH HFT", "Live": live_prices["ETH"]})
        if pos_b_btl: active_pos.append({**pos_b_btl, "Symbol": "BTCUSDT", "Strategy": "BTC Battle", "Live": live_prices["BTC"]})
        if pos_e_btl: active_pos.append({**pos_e_btl, "Symbol": "ETHUSDT", "Strategy": "ETH Battle", "Live": live_prices["ETH"]})

        if active_pos: st.dataframe(pd.DataFrame(active_pos), use_container_width=True, hide_index=True)
        else: st.info("No active positions currently open.")
    else:
        st.info(f"{selected_page} engine active.")

elif selected_page.startswith("Admin_") and is_admin:
    st.markdown(f"<h2 style='color:#0f172a;'>{selected_page.replace('Admin_', 'Admin ')}</h2>", unsafe_allow_html=True)
    st.caption("Master administration route active.")
    if selected_page == "Admin_Users":
        u_db = load_json(USERS_FILE)
        st.dataframe(pd.DataFrame([{"User": k, "Name": v.get("name"), "Role": v.get("role"), "Status": v.get("status"), "Strategies": ", ".join(v.get("allowed_strategies", []))} for k, v in u_db.items()]), use_container_width=True, hide_index=True)
    elif selected_page == "Admin_MacroAlerts":
        st.info("Macro Alerts and SNIPER controls active.")
    else:
        st.info(f"{selected_page} master console active.")

else:
    st.markdown(f"## {selected_page}")
    st.info(f"{selected_page} execution route is active.")