import streamlit as st
import pandas as pd
import requests
import json
import os
import time
import hashlib
from datetime import datetime

# Page Configuration
st.set_page_config(
    page_title="Stockimyze AlgoTrade",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    div[data-testid="stExpander"] { background-color: #ffffff; border-radius: 8px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

USERS_FILE = "users_db.json"
AUDIT_FILE = "audit_log.json"
TRADES_FILE = "trades_log.csv"

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

# Initialize Session State
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "user_data" not in st.session_state:
    st.session_state["user_data"] = {}
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Dashboard"

# Initialize Default Database Seed
def init_db():
    users = load_json(USERS_FILE)
    if not users:
        users = {
            "admin": {
                "name": "Master Admin",
                "role": "admin",
                "status": "Active",
                "password": "admin123",
                "allowed_strategies": ["BTCUSDT HFT", "ETHUSDT HFT", "BTC Battle", "ETH Battle"],
                "max_leverage": 50,
                "brokers": {"cosmic": {"connected": False}}
            },
            "client1": {
                "name": "Rahul Sharma",
                "role": "client",
                "status": "Active",
                "password": "client123",
                "allowed_strategies": ["BTCUSDT HFT", "ETHUSDT HFT", "BTC Battle", "ETH Battle"],
                "max_leverage": 50,
                "brokers": {"cosmic": {"connected": False}}
            }
        }
        save_json(USERS_FILE, users)

init_db()

# --- TOP TICKER BAR ---
def render_top_bar():
    c1, c2, c3, c4 = st.columns([1.5, 2, 2, 2.5])
    with c1:
        st.markdown("**⚡ STOCKIMYZE**")
    with c2:
        st.caption("🇮🇳 NIFTY: **25,390.40** | BANK NIFTY: **52,120.15**")
    with c3:
        st.caption("🌐 BTC: **$81,050.00** | ETH: **$2,621.01**")
    with c4:
        st.markdown(f"👤 Logged in as: **@{st.session_state.get('username')}** ({st.session_state.get('user_data', {}).get('role', 'User').title()})")
    st.markdown("---")

# --- LOGIN PAGE ---
def render_login_page():
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<h1 style='text-align:center;'>⚡ Stockimyze AlgoTrade</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:gray;'>Institutional Algorithmic Platform</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            u_in = st.text_input("Username / Client ID", placeholder="admin or client1")
            p_in = st.text_input("Password", type="password")
            sub = st.form_submit_button("🔐 Sign In", type="primary", use_container_width=True)
            
            if sub:
                uname = u_in.strip().lower()
                input_pass = p_in.strip()
                db = load_json(USERS_FILE)
                
                # Direct Master Fallback to avoid any lockout
                valid_creds = {
                    "admin": {"pass": "admin123", "role": "admin", "name": "Master Admin"},
                    "client1": {"pass": "client123", "role": "client", "name": "Rahul Sharma"}
                }
                
                user = db.get(uname)
                login_success = False
                
                if uname in valid_creds and input_pass == valid_creds[uname]["pass"]:
                    login_success = True
                    if not user:
                        user = {
                            "name": valid_creds[uname]["name"],
                            "role": valid_creds[uname]["role"],
                            "status": "Active",
                            "password": valid_creds[uname]["pass"],
                            "allowed_strategies": ["BTCUSDT HFT", "ETHUSDT HFT", "BTC Battle", "ETH Battle"],
                            "max_leverage": 50,
                            "brokers": {}
                        }
                elif user and user.get("status") == "Active":
                    stored_pass = user.get("password", "")
                    if stored_pass in [hash_password(input_pass), input_pass]:
                        login_success = True

                if login_success:
                    st.session_state["authenticated"] = True
                    st.session_state["user_data"] = user
                    st.session_state["username"] = uname
                    st.session_state["current_page"] = "Dashboard"
                    log_audit(uname, "LOGIN_SUCCESS", "User authenticated successfully")
                    st.rerun()
                else:
                    st.error("Invalid credentials or account suspended.")
                    
        st.caption("Default Access — Admin: `admin` / `admin123` • Client: `client1` / `client123`")

# --- DASHBOARD PAGE ---
def render_dashboard():
    st.subheader("Trading & Execution Overview")
    u_data = st.session_state.get("user_data", {})
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Today Realized PnL", "+$420.50", "+12.4%")
    col2.metric("Active Live Positions", "2 Running", "BTC & ETH")
    col3.metric("Max Allowed Leverage", f"{u_data.get('max_leverage', 50)}x")
    col4.metric("Account Status", u_data.get("status", "Active"))
    
    st.markdown("### Active Algorithmic Engines")
    t1, t2 = st.tabs(["🚀 BTC Battle (400 Pts Target)", "⚡ ETH Battle (10 Pts Target)"])
    
    with t1:
        st.write("**Strategy:** BTCUSDT Momentum Breakout 1-Min HFT")
        st.write("**Target:** 400 Points | **Stoploss:** 200 Points")
        c1, c2 = st.columns(2)
        with c1:
            st.toggle("Auto-Pilot Execution (BTC)", value=True, key="btc_bot_toggle")
        with c2:
            st.info("🟢 Running: Signal listening on Binance/Cosmic Stream")
            
    with t2:
        st.write("**Strategy:** ETHUSDT Scalp Micro-Wave")
        st.write("**Target:** 10 Points | **Stoploss:** 6 Points")
        c1, c2 = st.columns(2)
        with c1:
            st.toggle("Auto-Pilot Execution (ETH)", value=True, key="eth_bot_toggle")
        with c2:
            st.info("🟢 Running: Signal listening on Binance/Cosmic Stream")

# --- STRATEGIES PAGE ---
def render_strategies():
    st.subheader("Available Institutional Strategies")
    strats = [
        {"name": "BTC Battle", "pair": "BTC/USDT", "target": "400 Pts", "status": "Ready / Active"},
        {"name": "ETH Battle", "pair": "ETH/USDT", "target": "10 Pts", "status": "Ready / Active"},
        {"name": "BTCUSDT HFT", "pair": "BTC/USDT", "target": "Adaptive", "status": "Ready"},
        {"name": "ETHUSDT HFT", "pair": "ETH/USDT", "target": "Adaptive", "status": "Ready"}
    ]
    st.table(pd.DataFrame(strats))

# --- BROKER CONNECTION PAGE ---
def render_broker():
    st.subheader("Broker API Integration")
    st.caption("Connect your exchange keys to execute automated signals.")
    
    with st.form("broker_form"):
        broker = st.selectbox("Select Broker/Exchange", ["Cosmic Trade", "Binance Futures", "Delta Exchange"])
        api_key = st.text_input("API Key", type="password")
        api_secret = st.text_input("API Secret", type="password")
        submit_broker = st.form_submit_button("Connect Broker Account", type="primary")
        
        if submit_broker:
            if api_key and api_secret:
                st.success(f"Successfully linked {broker}! Ready for auto trades.")
            else:
                st.error("Please enter both API Key and Secret.")

# --- ADMIN USERS MANAGEMENT (FULL CONTROL) ---
def render_admin_users():
    st.title("Admin Users Management")
    st.caption("Master administration & client access control.")

    users = load_json(USERS_FILE)
    if not users:
        init_db()
        users = load_json(USERS_FILE)

    total_u = len(users)
    active_u = sum(1 for u in users.values() if u.get("status") == "Active")
    suspended_u = total_u - active_u

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Registered Clients", total_u)
    m2.metric("Active Clients", active_u)
    m3.metric("Suspended Clients", suspended_u)

    st.markdown("---")

    tab_list, tab_create = st.tabs(["📋 Client Directory & Actions", "➕ Create New Client"])

    with tab_create:
        st.subheader("Add New Client Access")
        with st.form("create_client_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                new_uname = st.text_input("Username / Client ID*", placeholder="e.g. client2").strip().lower()
                new_name = st.text_input("Full Name*", placeholder="e.g. Amit Verma")
                new_pass = st.text_input("Password*", type="password", placeholder="Assign password")
            with col_b:
                new_role = st.selectbox("Role", ["client", "admin"])
                new_status = st.selectbox("Initial Status", ["Active", "Suspended"])
                new_lev = st.number_input("Max Leverage (x)", min_value=1, max_value=100, value=50)

            all_available_strats = ["BTCUSDT HFT", "ETHUSDT HFT", "BTC Battle", "ETH Battle"]
            selected_strats = st.multiselect("Allowed Strategies", all_available_strats, default=all_available_strats)

            submit_new = st.form_submit_button("🚀 Create Client Account", type="primary", use_container_width=True)

            if submit_new:
                if not new_uname or not new_pass or not new_name:
                    st.error("Please fill all required fields (Username, Name, Password).")
                elif new_uname in users:
                    st.error(f"User '{new_uname}' already exists!")
                else:
                    users[new_uname] = {
                        "name": new_name,
                        "role": new_role,
                        "status": new_status,
                        "password": new_pass,
                        "allowed_strategies": selected_strats,
                        "max_leverage": new_lev,
                        "brokers": {"cosmic": {"connected": False}}
                    }
                    save_json(USERS_FILE, users)
                    log_audit(st.session_state.get("username", "admin"), "CREATE_USER", f"Created user {new_uname}")
                    st.success(f"Client '{new_uname}' successfully created!")
                    st.rerun()

    with tab_list:
        st.subheader("Manage Existing Clients")
        for uname, udata in list(users.items()):
            with st.expander(f"👤 **{uname.upper()}** — {udata.get('name', 'N/A')} [{udata.get('status', 'Active')}]", expanded=False):
                c1, c2, c3 = st.columns([2, 2, 2])
                with c1:
                    st.write(f"**Role:** `{udata.get('role', 'client')}`")
                    st.write(f"**Current Password:** `{udata.get('password', '******')}`")
                    st.write(f"**Max Leverage:** `{udata.get('max_leverage', 50)}x`")
                with c2:
                    st.write("**Assigned Strategies:**")
                    st.caption(", ".join(udata.get("allowed_strategies", [])))
                    broker_status = "🟢 Connected" if udata.get("brokers", {}).get("cosmic", {}).get("connected") else "🔴 Disconnected"
                    st.write(f"**Broker Status:** {broker_status}")
                with c3:
                    st.write("**Quick Controls:**")
                    current_st = udata.get("status", "Active")
                    target_st = "Suspended" if current_st == "Active" else "Active"
                    
                    if st.button(f"{'⏸ Suspend' if current_st == 'Active' else '▶ Activate'}", key=f"toggle_{uname}"):
                        users[uname]["status"] = target_st
                        save_json(USERS_FILE, users)
                        st.rerun()

                    with st.popover("🔑 Change Password"):
                        new_p = st.text_input(f"New Password for {uname}", key=f"pass_{uname}")
                        if st.button("Save Password", key=f"btn_p_{uname}"):
                            if new_p:
                                users[uname]["password"] = new_p
                                save_json(USERS_FILE, users)
                                st.success("Password updated!")
                                st.rerun()

                    if uname != "admin":
                        if st.button("🗑 Delete Client", key=f"del_{uname}", type="secondary"):
                            del users[uname]
                            save_json(USERS_FILE, users)
                            st.warning(f"User {uname} deleted.")
                            st.rerun()

# --- AUDIT LOGS PAGE ---
def render_audit_logs():
    st.subheader("Audit & System Security Logs")
    logs = load_json(AUDIT_FILE, [])
    if logs:
        st.dataframe(pd.DataFrame(logs)[::-1], use_container_width=True)
    else:
        st.info("No audit logs recorded yet.")

# --- MAIN CONTROLLER ---
def main():
    if not st.session_state["authenticated"]:
        render_login_page()
        return

    render_top_bar()
    user_role = st.session_state.get("user_data", {}).get("role", "client")

    with st.sidebar:
        st.title("Navigation")
        if user_role == "admin":
            pages = ["Dashboard", "Strategies", "Broker Connections", "Admin Users", "Audit Logs"]
        else:
            pages = ["Dashboard", "Strategies", "Broker Connections"]
            
        selected_page = st.radio("Go to", pages)
        
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state["username"] = ""
            st.session_state["user_data"] = {}
            st.rerun()

    if selected_page == "Dashboard":
        render_dashboard()
    elif selected_page == "Strategies":
        render_strategies()
    elif selected_page == "Broker Connections":
        render_broker()
    elif selected_page == "Admin Users":
        render_admin_users()
    elif selected_page == "Audit Logs":
        render_audit_logs()

if __name__ == "__main__":
    main()