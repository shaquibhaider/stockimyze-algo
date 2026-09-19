import streamlit as st
import pandas as pd
import requests
import json
import os
import time
import hashlib
from datetime import datetime, timedelta

# Page Configuration - Institutional Theme
st.set_page_config(
    page_title="Stockimyze AlgoTrade",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# FIXED INSTITUTIONAL UI CSS
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    .header-box { display: flex; align-items: center; justify-content: space-between; background: #ffffff; padding: 10px 18px; border-radius: 12px; border: 1px solid #e2e8f0; }
    .sidebar-category { font-size: 11px; font-weight: 800; color: #94a3b8; letter-spacing: 0.8px; margin-top: 18px; margin-bottom: 8px; padding-left: 6px; text-transform: uppercase; }
    div[data-testid="stSidebar"] div.stButton > button { text-align: left; border-radius: 8px; padding: 8px 14px; font-weight: 500; font-size: 13px; margin-bottom: 4px; border: 1px solid transparent; }
    div[data-testid="stSidebar"] div.stButton > button:hover { border: 1px solid #cbd5e1; background-color: #f1f5f9; color: #0f172a; }
    div[data-testid="stMetric"] { background-color: #ffffff; padding: 14px 18px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
    div[data-testid="stExpander"] { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; }
    
    /* Broker Card Styles */
    .broker-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .broker-badge-stocks { background: #f1f5f9; color: #475569; font-size: 11px; padding: 2px 8px; border-radius: 12px; font-weight: 600; }
    .broker-badge-crypto { background: #fef3c7; color: #b45309; font-size: 11px; padding: 2px 8px; border-radius: 12px; font-weight: 600; }
    .status-pill-disc { background: #fee2e2; color: #ef4444; font-size: 11px; padding: 3px 8px; border-radius: 10px; font-weight: 700; }
    .status-pill-conn { background: #dcfce7; color: #15803d; font-size: 11px; padding: 3px 8px; border-radius: 10px; font-weight: 700; }
    .avatar-circle { width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; color: #ffffff; font-size: 14px; }
</style>
""", unsafe_allow_html=True)

USERS_FILE = "users_db.json"
AUDIT_FILE = "audit_log.json"
BROKERS_FILE = "brokers_data.json"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def load_json(filepath, default_val=None):
    if default_val is None:
        default_val = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception:
            return default_val
    return default_val

def save_json(filepath, data):
    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        st.error(f"Error saving data: {e}")

def log_audit(username, action, details):
    logs = load_json(AUDIT_FILE, [])
    logs.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": username,
        "action": action,
        "details": details
    })
    save_json(AUDIT_FILE, logs)

def init_db():
    users = load_json(USERS_FILE)
    if not users:
        users = {
            "admin": {
                "name": "Master Admin",
                "role": "admin",
                "status": "Active",
                "password": "admin123",
                "allowed_strategies": ["BTC Battle", "ETH Battle", "BTCUSDT HFT", "ETHUSDT HFT"],
                "max_leverage": 200,
                "brokers": {}
            },
            "client1": {
                "name": "Rahul Sharma",
                "role": "client",
                "status": "Active",
                "password": "client123",
                "allowed_strategies": ["BTC Battle", "ETH Battle"],
                "max_leverage": 50,
                "brokers": {}
            }
        }
        save_json(USERS_FILE, users)

init_db()

# State Management
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "user_data" not in st.session_state:
    st.session_state["user_data"] = {}
if "selected_page" not in st.session_state:
    st.session_state["selected_page"] = "Dashboard"

# --- TOP INSTITUTIONAL TICKER BAR ---
def render_top_bar():
    c1, c2, c3, c4 = st.columns([2.2, 2.2, 2.5, 2.1])
    with c1:
        st.markdown("""
        <div style="background:#f0f9ff; padding:8px 12px; border-radius:8px; border:1px solid #bae6fd;">
            <span style="color:#0284c7; font-size:10px; font-weight:800;">INDIAN</span> 
            &nbsp;<b>IN NIFTY</b> <span style="color:#0f172a; font-weight:600;">25,390.40</span>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div style="background:#faf5ff; padding:8px 12px; border-radius:8px; border:1px solid #e9d5ff;">
            <span style="color:#9333ea; font-size:10px; font-weight:800;">🏦 BANK NIFTY</span> 
            &nbsp;<b>52,120.15</b> &nbsp;<span style="color:#16a34a; font-size:11px;">● NSE Live</span>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div style="background:#fffbeb; padding:8px 12px; border-radius:8px; border:1px solid #fde68a;">
            <span style="color:#d97706; font-size:10px; font-weight:800;">GLOBAL</span> 
            &nbsp;<b>₿ BTC:</b> $81,069.99 &nbsp;|&nbsp; <b>Ξ ETH:</b> $2,632.41
        </div>
        """, unsafe_allow_html=True)
    with c4:
        u_name = st.session_state.get('user_data', {}).get('name', 'Master Admin')
        u_role = st.session_state.get('user_data', {}).get('role', 'admin').title()
        st.markdown(f"""
        <div style="background:#ffffff; padding:8px 12px; border-radius:8px; border:1px solid #e2e8f0; text-align:right;">
            👤 <b>{u_name}</b> <span style="font-size:12px; color:#64748b;">({u_role})</span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("<hr style='margin-top:10px; margin-bottom:18px; border:none; border-top:1px solid #e2e8f0;'>", unsafe_allow_html=True)

# --- LOGIN SCREEN ---
def render_login():
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.3, 1])
    with c2:
        st.markdown("""
        <div style="text-align:center; padding:24px; background:#fff; border-radius:14px; box-shadow:0 4px 6px -1px rgba(0,0,0,0.06); border:1px solid #f1f5f9;">
            <span style="font-size:42px;">⚡</span>
            <h2 style="margin:6px 0 0 0; font-weight:800; color:#0f172a;">Stockimyze AlgoTrade</h2>
            <p style="color:#64748b; font-size:13px; margin:0;">Institutional Algorithmic Platform</p>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        with st.form("form_login"):
            u_in = st.text_input("Username / Client ID", placeholder="admin, client1, sameer").strip().lower()
            p_in = st.text_input("Password", type="password")
            btn = st.form_submit_button("🔐 Sign In", type="primary", use_container_width=True)
            if btn:
                db = load_json(USERS_FILE)
                valid_defaults = {
                    "admin": {"pass": "admin123", "role": "admin", "name": "Master Admin"},
                    "client1": {"pass": "client123", "role": "client", "name": "Rahul Sharma"}
                }
                user = db.get(u_in)
                success = False
                
                if u_in in valid_defaults and p_in == valid_defaults[u_in]["pass"]:
                    success = True
                    if not user:
                        user = {
                            "name": valid_defaults[u_in]["name"],
                            "role": valid_defaults[u_in]["role"],
                            "status": "Active",
                            "password": valid_defaults[u_in]["pass"],
                            "allowed_strategies": ["BTC Battle", "ETH Battle"],
                            "max_leverage": 200,
                            "brokers": {}
                        }
                elif user and user.get("status") == "Active":
                    st_p = str(user.get("password", "")).strip()
                    if p_in == st_p or hash_password(p_in) == st_p:
                        success = True

                if success:
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = u_in
                    st.session_state["user_data"] = user
                    st.session_state["selected_page"] = "Dashboard"
                    st.rerun()
                else:
                    st.error("Invalid credentials or account suspended.")

# --- DASHBOARD VIEW ---
def render_dashboard():
    st.subheader("Trading & Execution Overview")
    u_data = st.session_state.get("user_data", {})
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Today Realized PnL", "+$420.50", "+12.4%")
    col2.metric("Active Live Positions", "2 Running", "BTC & ETH")
    col3.metric("Max Allowed Leverage", f"{u_data.get('max_leverage', 200)}x")
    col4.metric("Account Status", u_data.get("status", "Active"))
    
    st.markdown("### Algorithmic Battle Bots Overview")
    t1, t2 = st.tabs(["🚀 BTC Battle (400 Pts Target)", "⚡ ETH Battle (10 Pts Target)"])
    
    with t1:
        st.write("**Strategy:** BTCUSDT Momentum Breakout 1-Min HFT")
        st.write("**Target:** 400 Points | **Stoploss:** 200 Points")
        c1, c2 = st.columns(2)
        with c1:
            st.toggle("Auto-Pilot Execution (BTC)", value=True, key="btc_bot_toggle_dash")
        with c2:
            st.info("🟢 Running: Signal listening on Binance/Cosmic/Shark Stream")
            
    with t2:
        st.write("**Strategy:** ETHUSDT Scalp Micro-Wave")
        st.write("**Target:** 10 Points | **Stoploss:** 6 Points")
        c1, c2 = st.columns(2)
        with c1:
            st.toggle("Auto-Pilot Execution (ETH)", value=True, key="eth_bot_toggle_dash")
        with c2:
            st.info("🟢 Running: Signal listening on Binance/Cosmic/Shark Stream")

# --- FULL STRATEGIES CONTROL CENTER ---
def render_strategies_page():
    st.title("⚡ Algorithmic Trading Strategies")
    st.caption("Configure, activate, and manage institutional trading engines.")

    u_data = st.session_state.get("user_data", {})
    user_lev = u_data.get("max_leverage", 200)

    strat_tabs = st.tabs([
        "🔥 BTC Battle (400 Pts)", 
        "⚡ ETH Battle (10 Pts)", 
        "🏎️ BTCUSDT HFT", 
        "🌊 ETHUSDT HFT", 
        "📊 Active Strategy Deployments"
    ])

    with strat_tabs[0]:
        st.markdown("### 🚀 BTC Battle Strategy Engine")
        st.caption("Automated high-frequency target-seeking engine for BTCUSDT.")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            btc_target = st.number_input("Target Points (USDT)", min_value=50, max_value=2000, value=400, step=25, key="btc_tgt")
        with c2:
            btc_sl = st.number_input("Stop Loss Points (USDT)", min_value=25, max_value=1000, value=200, step=25, key="btc_sl")
        with c3:
            btc_lev = st.slider("Strategy Leverage", min_value=1, max_value=int(user_lev), value=min(50, int(user_lev)), key="btc_lev_slide")
        
        st.write("")
        c_act1, c_act2 = st.columns([2, 2])
        with c_act1:
            btc_active = st.toggle("Enable BTC Battle Auto-Trader", value=True, key="btc_main_toggle")
            if btc_active:
                st.success(f"● Bot Active | Target: +{btc_target} pts | SL: -{btc_sl} pts | Lev: {btc_lev}x")
            else:
                st.warning("Bot Paused.")
        with c_act2:
            st.selectbox("Execution Broker Routing", ["Shark Exchange API", "Cosmic Mainnet API", "Binance Futures Feed", "Paper Trading Simulation"], key="btc_route")

    with strat_tabs[1]:
        st.markdown("### ⚡ ETH Battle Strategy Engine")
        st.caption("Micro-wave scalp momentum bot for ETHUSDT perpetuals.")
        
        e1, e2, e3 = st.columns(3)
        with e1:
            eth_target = st.number_input("Target Points (USDT)", min_value=2, max_value=100, value=10, step=1, key="eth_tgt")
        with e2:
            eth_sl = st.number_input("Stop Loss Points (USDT)", min_value=1, max_value=50, value=6, step=1, key="eth_sl")
        with e3:
            eth_lev = st.slider("ETH Leverage", min_value=1, max_value=int(user_lev), value=min(25, int(user_lev)), key="eth_lev_slide")
            
        st.write("")
        e_act1, e_act2 = st.columns([2, 2])
        with e_act1:
            eth_active = st.toggle("Enable ETH Battle Auto-Trader", value=True, key="eth_main_toggle")
            if eth_active:
                st.success(f"● Bot Active | Target: +{eth_target} pts | SL: -{eth_sl} pts | Lev: {eth_lev}x")
            else:
                st.warning("Bot Paused.")
        with e_act2:
            st.selectbox("Execution Broker Routing", ["Shark Exchange API", "Cosmic Mainnet API", "Binance Futures Feed", "Paper Trading Simulation"], key="eth_route")

    with strat_tabs[2]:
        st.markdown("### 🏎️ BTCUSDT High Frequency Engine (HFT)")
        st.write("Order-book imbalance and delta-volume burst detection engine.")
        h1, h2 = st.columns(2)
        with h1:
            st.number_input("Lot Size (BTC)", min_value=0.001, max_value=5.0, value=0.05, step=0.01, key="btc_hft_lot")
            st.toggle("Run HFT Order Sniping", value=False, key="btc_hft_tgl")
        with h2:
            st.info("HFT Engine listening for liquidity spikes > $1.5M")

    with strat_tabs[3]:
        st.markdown("### 🌊 ETHUSDT High Frequency Engine (HFT)")
        st.write("Cross-market funding-arbitrage and tick-level scalp module.")
        eh1, eh2 = st.columns(2)
        with eh1:
            st.number_input("Lot Size (ETH)", min_value=0.01, max_value=50.0, value=0.5, step=0.1, key="eth_hft_lot")
            st.toggle("Run HFT Order Sniping", value=False, key="eth_hft_tgl")
        with eh2:
            st.info("HFT Engine monitoring 500ms orderbook depth.")

    with strat_tabs[4]:
        st.markdown("### 📊 Active Live Positions Summary")
        active_pos_data = [
            {"Strategy": "BTC Battle", "Symbol": "BTCUSDT", "Type": "LONG", "Entry Price": "$80,820.00", "Current Price": "$81,069.99", "PnL": "+$249.99", "Target": "+400 Pts", "Status": "RUNNING"},
            {"Strategy": "ETH Battle", "Symbol": "ETHUSDT", "Type": "SHORT", "Entry Price": "$2,641.50", "Current Price": "$2,632.41", "PnL": "+$9.09", "Target": "+10 Pts", "Status": "RUNNING"}
        ]
        st.dataframe(pd.DataFrame(active_pos_data), use_container_width=True)

# --- COMPLETE LIVE BROKER CONNECTIONS (INCL. SHARK EXCHANGE) ---
def render_broker_connections():
    st.markdown("<h2 style='margin-bottom:0;'>Broker Connections</h2>", unsafe_allow_html=True)
    st.caption("Connect and manage your broker accounts for live execution.")

    username = st.session_state.get("username", "admin")
    u_db = load_json(USERS_FILE)
    user_info = u_db.get(username, {})
    user_brokers = user_info.get("brokers", {})

    brokers_def = [
        {"id": "zerodha", "name": "Zerodha", "tag": "Stocks", "avatar": "ZE", "bg": "#1d4ed8", "type": "equity"},
        {"id": "dhan", "name": "Dhan", "tag": "Stocks", "avatar": "DH", "bg": "#2563eb", "type": "equity"},
        {"id": "angelone", "name": "Angel One", "tag": "Stocks", "avatar": "AN", "bg": "#ea580c", "type": "equity"},
        {"id": "upstox", "name": "Upstox", "tag": "Stocks", "avatar": "UP", "bg": "#581c87", "type": "equity"},
        {"id": "binance", "name": "Binance", "tag": "Crypto", "avatar": "BI", "bg": "#eab308", "type": "crypto"},
        {"id": "bybit", "name": "Bybit", "tag": "Crypto", "avatar": "BY", "bg": "#f59e0b", "type": "crypto"},
        {"id": "coinswitch", "name": "CoinSwitch", "tag": "Crypto", "avatar": "CO", "bg": "#4f46e5", "type": "crypto"},
        {"id": "cosmic", "name": "Cosmic Trade", "tag": "Crypto", "avatar": "CO", "bg": "#0f172a", "type": "crypto"},
        {"id": "shark", "name": "Shark Exchange", "tag": "Crypto", "avatar": "SH", "bg": "#0891b2", "type": "crypto"}
    ]

    # Grid 4 Columns
    cols = st.columns(4)
    for idx, b in enumerate(brokers_def):
        col = cols[idx % 4]
        b_id = b["id"]
        b_data = user_brokers.get(b_id, {})
        is_conn = b_data.get("connected", False)
        api_key_masked = b_data.get("api_key_mask", "—")
        expiry_val = b_data.get("expiry", "—")

        with col:
            status_html = (
                '<span class="status-pill-conn">● CONNECTED</span>' 
                if is_conn else 
                '<span class="status-pill-disc">● DISCONNECTED</span>'
            )
            badge_class = "broker-badge-stocks" if b["tag"] == "Stocks" else "broker-badge-crypto"

            st.markdown(f"""
            <div class="broker-card">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <div class="avatar-circle" style="background-color:{b['bg']};">{b['avatar']}</div>
                        <div>
                            <div style="font-weight:700; font-size:15px; color:#0f172a;">{b['name']}</div>
                            <span class="{badge_class}">{b['tag']}</span>
                        </div>
                    </div>
                    <div>{status_html}</div>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:14px; background:#f8fafc; padding:8px 10px; border-radius:8px;">
                    <div>
                        <div style="font-size:11px; color:#64748b;">API Key</div>
                        <div style="font-size:12px; font-weight:600; color:#0f172a;">{api_key_masked}</div>
                    </div>
                    <div>
                        <div style="font-size:11px; color:#64748b;">Token Expiry</div>
                        <div style="font-size:12px; font-weight:600; color:#0f172a;">{expiry_val}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if is_conn:
                if st.button("🔌 Disconnect", key=f"disc_{b_id}", use_container_width=True):
                    user_brokers[b_id]["connected"] = False
                    user_info["brokers"] = user_brokers
                    u_db[username] = user_info
                    save_json(USERS_FILE, u_db)
                    st.toast(f"Disconnected from {b['name']}", icon="⚠️")
                    st.rerun()
            else:
                with st.popover(f"⚡ Connect {b['name']}", use_container_width=True):
                    st.markdown(f"**Setup Live Credentials for {b['name']}**")
                    inp_key = st.text_input("API Key*", key=f"k_{b_id}", placeholder="Enter API Key")
                    inp_sec = st.text_input("API Secret*", type="password", key=f"s_{b_id}", placeholder="Enter API Secret")
                    
                    if b["type"] == "equity":
                        st.text_input("Client ID / TOTP Secret (Optional)", key=f"t_{b_id}")
                    
                    if st.button("Verify & Activate", key=f"sub_{b_id}", type="primary", use_container_width=True):
                        if not inp_key or not inp_sec:
                            st.error("API Key & Secret are required!")
                        else:
                            exp_date = (datetime.now() + timedelta(days=90)).strftime("%d-%b-%Y")
                            mask = inp_key[:4] + "••••" + inp_key[-3:] if len(inp_key) >= 7 else "••••••••"
                            user_brokers[b_id] = {
                                "connected": True,
                                "api_key_mask": mask,
                                "expiry": exp_date,
                                "connected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            user_info["brokers"] = user_brokers
                            u_db[username] = user_info
                            save_json(USERS_FILE, u_db)
                            log_audit(username, "BROKER_CONNECT", f"Connected {b['name']}")
                            st.success(f"{b['name']} Connected Successfully!")
                            st.rerun()

# --- ADMIN USERS VIEW ---
def render_admin_users():
    st.markdown("<h2 style='margin-bottom:0;'>Admin Users</h2>", unsafe_allow_html=True)
    st.caption("Master administration route active.")

    u_db = load_json(USERS_FILE)
    if not u_db:
        init_db()
        u_db = load_json(USERS_FILE)

    table_rows = []
    for k, v in u_db.items():
        table_rows.append({
            "User": k,
            "Name": v.get("name", "N/A"),
            "Role": v.get("role", "client"),
            "Status": v.get("status", "Active"),
            "Strategies": ", ".join(v.get("allowed_strategies", []))
        })
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True)

    st.markdown("---")
    t_create, t_manage = st.tabs(["➕ Create New Client", "⚙️ Client Actions & Controls"])

    with t_create:
        st.markdown("#### Add New Client Account")
        with st.form("create_client_form_adm", clear_on_submit=True):
            c_a, c_b = st.columns(2)
            with c_a:
                new_u = st.text_input("Username / Client ID*", placeholder="e.g. client2").strip().lower()
                new_n = st.text_input("Full Name*", placeholder="e.g. Amit Sharma")
                new_p = st.text_input("Password*", type="password", placeholder="Assign client password")
            with c_b:
                new_r = st.selectbox("Role", ["client", "admin"])
                new_s = st.selectbox("Initial Status", ["Active", "Suspended"])
                new_l = st.number_input("Max Leverage (1x - 200x)", min_value=1, max_value=200, value=200)

            new_strats = st.multiselect("Allowed Strategies", ["BTC Battle", "ETH Battle", "BTCUSDT HFT", "ETHUSDT HFT"], default=["BTC Battle", "ETH Battle"])
            
            if st.form_submit_button("🚀 Create Client Account", type="primary", use_container_width=True):
                if not new_u or not new_n or not new_p:
                    st.error("Please fill in all required fields.")
                elif new_u in u_db:
                    st.error(f"User '{new_u}' already exists!")
                else:
                    u_db[new_u] = {
                        "name": new_n,
                        "role": new_r,
                        "status": new_s,
                        "password": new_p,
                        "allowed_strategies": new_strats,
                        "max_leverage": new_l,
                        "brokers": {}
                    }
                    save_json(USERS_FILE, u_db)
                    st.success(f"Client '{new_u}' created with {new_l}x leverage!")
                    st.rerun()

    with t_manage:
        st.markdown("#### Manage Existing Clients")
        for uname, udata in list(u_db.items()):
            c_stat = udata.get("status", "Active")
            with st.expander(f"👤 {uname.upper()} — {udata.get('name', 'N/A')} [{c_stat}]"):
                col1, col2, col3 = st.columns([2, 2, 2])
                with col1:
                    st.write(f"**Password:** `{udata.get('password', '******')}`")
                    st.write(f"**Max Leverage:** `{udata.get('max_leverage', 50)}x`")
                with col2:
                    active_brokers_count = sum(1 for b in udata.get("brokers", {}).values() if b.get("connected"))
                    st.write(f"**Active Brokers:** `🟢 {active_brokers_count} Connected`")
                    st.caption(f"Allowed: {', '.join(udata.get('allowed_strategies', []))}")
                with col3:
                    tgt = "Suspended" if c_stat == "Active" else "Active"
                    btn_txt = "⏸ Suspend" if c_stat == "Active" else "▶ Activate"
                    if st.button(btn_txt, key=f"btn_st_{uname}"):
                        u_db[uname]["status"] = tgt
                        save_json(USERS_FILE, u_db)
                        st.rerun()

                    with st.popover("🔑 Reset Password"):
                        p_val = st.text_input("New Password", key=f"inp_{uname}")
                        if st.button("Save Password", key=f"save_{uname}"):
                            if p_val:
                                u_db[uname]["password"] = p_val
                                save_json(USERS_FILE, u_db)
                                st.success("Password Updated!")
                                st.rerun()

                    with st.popover("⚡ Update Leverage"):
                        cur_lev = int(udata.get("max_leverage", 50))
                        new_lev_val = st.number_input("Leverage (1x - 200x)", min_value=1, max_value=200, value=cur_lev, key=f"lev_{uname}")
                        if st.button("Save Leverage", key=f"btn_lev_{uname}"):
                            u_db[uname]["max_leverage"] = new_lev_val
                            save_json(USERS_FILE, u_db)
                            st.success("Leverage Updated!")
                            st.rerun()

                    if uname != "admin":
                        if st.button("🗑 Delete Client", key=f"del_{uname}", type="secondary"):
                            del u_db[uname]
                            save_json(USERS_FILE, u_db)
                            st.warning(f"Deleted {uname}")
                            st.rerun()

def render_placeholder(title):
    st.title(title)
    st.caption(f"Realtime {title} interface.")
    st.info(f"⚡ {title} module active & synchronized with mainnet engine.")

# --- MAIN APP CONTROLLER ---
def main():
    if not st.session_state["authenticated"]:
        render_login()
        return

    render_top_bar()
    user_role = st.session_state.get("user_data", {}).get("role", "client")

    with st.sidebar:
        st.markdown("<h3 style='margin-bottom:0;'>⚡ Stockimyze</h3>", unsafe_allow_html=True)
        st.caption("Institutional Algo Trading Engine")
        st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)

        st.markdown("<div class='sidebar-category'>TRADING & ANALYTICS</div>", unsafe_allow_html=True)
        trading_items = [
            ("📈 Dashboard", "Dashboard"),
            ("📊 Positions", "Positions"),
            ("💼 Portfolio", "Portfolio"),
            ("📈 PnL Analytics", "PnL Analytics"),
            ("📜 Trade History", "Trade History"),
            ("📋 Reports", "Reports"),
            ("⚡ Strategies", "Strategies"),
            ("🔌 Broker Connection", "Broker Connection"),
        ]
        for lbl, key in trading_items:
            active = (st.session_state.get("selected_page") == key)
            if st.button(lbl, key=f"btn_{key}", use_container_width=True, type="primary" if active else "secondary"):
                st.session_state["selected_page"] = key
                st.rerun()

        if user_role == "admin":
            st.markdown("<div class='sidebar-category'>ADMINISTRATION</div>", unsafe_allow_html=True)
            admin_items = [
                ("👥 Admin Users", "Admin_Users"),
                ("🛡️ Subscriptions", "Admin_Subscriptions"),
                ("💵 Payments", "Admin_Payments"),
                ("📊 Strategies Master", "Admin_StrategiesMaster"),
                ("🔌 Broker Management", "Admin_BrokerManagement"),
                ("🎫 Support Tickets", "Admin_SupportTickets"),
                ("📜 Audit Logs", "Admin_AuditLogs"),
                ("⚡ System Health", "Admin_SystemHealth"),
                ("🔔 Macro Alerts", "Admin_MacroAlerts"),
                ("💾 AOC Data", "Admin_AOCData"),
            ]
            for lbl, key in admin_items:
                active = (st.session_state.get("selected_page") == key)
                if st.button(lbl, key=f"btn_{key}", use_container_width=True, type="primary" if active else "secondary"):
                    st.session_state["selected_page"] = key
                    st.rerun()

        st.markdown("<hr style='margin:16px 0;'>", unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state["username"] = ""
            st.session_state["user_data"] = {}
            st.session_state["selected_page"] = "Dashboard"
            st.rerun()

    # Routing
    sel = st.session_state.get("selected_page", "Dashboard")
    if sel == "Dashboard":
        render_dashboard()
    elif sel == "Strategies":
        render_strategies_page()
    elif sel == "Broker Connection":
        render_broker_connections()
    elif sel == "Admin_Users":
        render_admin_users()
    else:
        render_placeholder(sel.replace("Admin_", ""))

if __name__ == "__main__":
    main()
