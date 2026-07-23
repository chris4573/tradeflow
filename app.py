import streamlit as st
import json
import os
import hashlib
import uuid
import secrets
import smtplib
from urllib.parse import urlparse
from datetime import datetime
from email.message import EmailMessage

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

from streamlit_autorefresh import st_autorefresh

from market_engine import SCAN_UNIVERSE, ASSET_LABELS, analyze_market_frame
from alerts_store import (
    load_alert_store,
    save_alert_store,
    update_price_and_generate_alerts,
    get_recent_events,
)
from insights_engine import (
    safe_pct_change,
    best_category_label,
    trend_label_from_history,
    compare_asset_strength,
    performance_score,
    trade_win_rate,
    best_and_worst_assets_from_portfolio_rows,
    portfolio_change_summary,
    consistency_ratio_from_history,
    risk_level_from_behavior,
)
from ai_engine import score_trade_idea

# =============================
# CONFIG
# =============================
st.set_page_config(
    page_title="TradeFlow",
    layout="wide",
    initial_sidebar_state="expanded"
)

USERS_FILE = "users.json"
PORTFOLIO_FILE = "portfolio_data.json"
HISTORY_FILE = "portfolio_history.json"
SALES_FILE = "sales_history.json"
ALERTS_FILE = "alerts_store.json"

SUGGESTION_SCORE_THRESHOLD = 0.35

# =============================
# EMAIL RESET CONFIG
# REPLACE THESE WITH YOUR REAL GMAIL DETAILS
# =============================
SMTP_EMAIL = "YOUR_GMAIL@gmail.com"
SMTP_APP_PASSWORD = "YOUR_16_CHAR_APP_PASSWORD"

# =============================
# STYLING
# =============================
st.markdown("""
<style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(31,100,255,0.10), transparent 30%),
            radial-gradient(circle at top right, rgba(18,184,134,0.08), transparent 25%),
            linear-gradient(180deg, #eef3fb 0%, #e4ecf8 100%);
    }

    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        background-image:
            linear-gradient(rgba(16,42,67,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(16,42,67,0.03) 1px, transparent 1px);
        background-size: 32px 32px;
        opacity: 0.35;
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
    }

    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 1.2rem;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #031b4e 0%, #02153c 100%);
    }

    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] h5,
    section[data-testid="stSidebar"] h6,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span {
        color: white !important;
    }

    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea {
        background-color: white !important;
        color: #102a43 !important;
        border-radius: 10px !important;
    }

    section[data-testid="stSidebar"] [data-testid="stNumberInput"] input {
        background-color: white !important;
        color: #102a43 !important;
    }

    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: white !important;
        color: #102a43 !important;
        border-radius: 10px !important;
    }

    section[data-testid="stSidebar"] div[data-baseweb="select"] * {
        color: #102a43 !important;
    }

    .stButton > button {
        border-radius: 12px;
        font-weight: 700;
        width: 100%;
        padding: 0.75rem 1rem;
        border: none;
        background: linear-gradient(135deg, #1f64ff 0%, #1456eb 100%);
        color: white;
        box-shadow: 0 10px 24px rgba(20, 86, 235, 0.2);
    }

    .stButton > button:hover {
        filter: brightness(1.04);
    }

    .main-title {
        font-size: 2rem;
        font-weight: 800;
        color: #102a43;
        margin-bottom: 0.2rem;
    }

    .subtitle {
        font-size: 1rem;
        color: #627d98;
        margin-bottom: 1rem;
    }

    .card {
        background: white;
        border-radius: 18px;
        padding: 20px;
        box-shadow: 0 8px 24px rgba(16, 42, 67, 0.08);
        border: 1px solid #e6edf5;
    }

    .metric-card {
        border-radius: 18px;
        padding: 20px;
        color: white;
        min-height: 130px;
        box-shadow: 0 8px 24px rgba(16, 42, 67, 0.12);
    }

    .metric-blue {
        background: linear-gradient(135deg, #123d9b 0%, #0f57d5 100%);
    }

    .metric-green {
        background: linear-gradient(135deg, #089981 0%, #12b886 100%);
    }

    .metric-white {
        background: white;
        color: #102a43;
        border: 1px solid #e6edf5;
    }

    .metric-label {
        font-size: 0.9rem;
        font-weight: 700;
        opacity: 0.9;
        margin-bottom: 12px;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        line-height: 1.1;
    }

    .metric-sub {
        font-size: 1rem;
        font-weight: 600;
        margin-top: 10px;
    }

    .section-title {
        font-size: 1.35rem;
        font-weight: 800;
        color: #102a43;
        margin-bottom: 12px;
    }

    .ticker-bar {
        background: white;
        border-radius: 18px;
        padding: 14px 18px;
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        margin-bottom: 24px;
        box-shadow: 0 8px 24px rgba(16, 42, 67, 0.08);
        border: 1px solid #e6edf5;
    }

    .ticker-item {
        color: #102a43;
        text-align: center;
        font-weight: 800;
        font-size: 0.98rem;
    }

    .login-wrap {
        max-width: 760px;
        margin: 0 auto;
    }

    .login-card {
        background: rgba(255,255,255,0.94);
        border: 1px solid #dfe8f5;
        border-radius: 24px;
        padding: 26px;
        box-shadow: 0 18px 50px rgba(16, 42, 67, 0.10);
    }

    .login-brand {
        text-align: center;
        margin-bottom: 1rem;
    }

    .login-brand-name {
        font-size: 3rem;
        font-weight: 900;
        color: #102a43;
        line-height: 1;
    }

    .login-brand-name span {
        color: #1f64ff;
    }

    .login-brand-tag {
        font-size: 0.95rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        color: #2f5bea;
        margin-top: 6px;
    }

    .portfolio-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 14px 0;
        border-bottom: 1px solid #edf2f7;
        gap: 12px;
    }

    .portfolio-left {
        display: flex;
        align-items: center;
        gap: 12px;
        min-width: 0;
    }

    .portfolio-icon {
        width: 42px;
        height: 42px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        font-weight: 700;
        color: white;
        flex-shrink: 0;
    }

    .icon-blue { background: #2f5bea; }

    .portfolio-name {
        font-size: 1rem;
        font-weight: 700;
        color: #102a43;
        word-break: break-word;
    }

    .portfolio-meta {
        font-size: 0.85rem;
        color: #627d98;
    }

    .portfolio-value {
        text-align: right;
    }

    .portfolio-money {
        font-size: 1.1rem;
        font-weight: 800;
        color: #102a43;
    }

    .portfolio-pct-up {
        font-size: 0.95rem;
        font-weight: 700;
        color: #12b886;
    }

    .portfolio-pct-down {
        font-size: 0.95rem;
        font-weight: 700;
        color: #ef4444;
    }

    .watch-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 0;
        border-bottom: 1px solid #edf2f7;
        gap: 12px;
    }

    .watch-left {
        display: flex;
        align-items: center;
        gap: 12px;
        min-width: 0;
    }

    .watch-logo {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        background: white;
        border: 1px solid #e6edf5;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        color: #102a43;
        flex-shrink: 0;
    }

    .watch-name {
        font-size: 1rem;
        font-weight: 700;
        color: #102a43;
    }

    .watch-sub {
        font-size: 0.85rem;
        color: #627d98;
        word-break: break-word;
    }

    .watch-price {
        text-align: right;
        font-weight: 800;
        color: #102a43;
    }

    .watch-change-up {
        color: #12b886;
        font-size: 0.9rem;
        font-weight: 700;
    }

    .watch-change-down {
        color: #ef4444;
        font-size: 0.9rem;
        font-weight: 700;
    }

    @media (max-width: 900px) {
        .ticker-bar {
            grid-template-columns: repeat(2, 1fr);
        }

        .login-brand-name {
            font-size: 2.3rem;
        }
    }

    @media (max-width: 768px) {
        .block-container {
            padding-top: 0rem !important;
            padding-left: 0.7rem;
            padding-right: 0.7rem;
            padding-bottom: 1rem;
        }

        .main-title {
            font-size: 1.5rem;
        }

        .subtitle {
            font-size: 0.95rem;
        }

        .card,
        .metric-card,
        .login-card {
            padding: 14px;
            border-radius: 14px;
        }

        .metric-value {
            font-size: 1.35rem;
        }

        .metric-label,
        .metric-sub {
            font-size: 0.85rem;
        }

        .section-title {
            font-size: 1.1rem;
        }

        .portfolio-row,
        .watch-row {
            flex-direction: column;
            align-items: flex-start;
        }

        .portfolio-value,
        .watch-price {
            text-align: left;
            width: 100%;
        }
    }
</style>
""", unsafe_allow_html=True)
# =============================
# FILE HELPERS
# =============================
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# =============================
# BASE DATA
# =============================
users = load_json(USERS_FILE, {})
portfolios = load_json(PORTFOLIO_FILE, {})
history = load_json(HISTORY_FILE, {})
sales_history = load_json(SALES_FILE, {})


# =============================
# USER / AUTH HELPERS
# =============================
def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def generate_unique_user_id():
    existing_ids = {
        value.get("user_id", "")
        for value in users.values()
        if isinstance(value, dict)
    }
    while True:
        new_id = f"TF-{uuid.uuid4().hex[:8].upper()}"
        if new_id not in existing_ids:
            return new_id


def send_reset_email(to_email, reset_code, username):
    try:
        msg = EmailMessage()
        msg["Subject"] = "TradeFlow Password Reset"
        msg["From"] = SMTP_EMAIL
        msg["To"] = to_email

        msg.set_content(
            f"""Hi {username},

You requested a password reset for your TradeFlow account.

Your reset code is:

{reset_code}

Enter this code in the TradeFlow app to set a new password.

If you did not request this, you can ignore this email.
"""
        )

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
            smtp.send_message(msg)

        return True, "Reset email sent"
    except Exception as e:
        return False, f"Could not send email: {e}"


def normalize_users():
    changed = False

    for username, value in list(users.items()):
        if isinstance(value, str):
            users[username] = {
                "password": value,
                "email": "",
                "visibility": "private",
                "user_id": generate_unique_user_id(),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            changed = True

        elif isinstance(value, dict):
            if "password" not in value:
                value["password"] = ""
                changed = True
            if "email" not in value:
                value["email"] = ""
                changed = True
            if "visibility" not in value:
                value["visibility"] = "private"
                changed = True
            if "user_id" not in value or not str(value["user_id"]).strip():
                value["user_id"] = generate_unique_user_id()
                changed = True
            if "created_at" not in value:
                value["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                changed = True

        else:
            users[username] = {
                "password": "",
                "email": "",
                "visibility": "private",
                "user_id": generate_unique_user_id(),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            changed = True

    if changed:
        save_json(USERS_FILE, users)


def normalize_portfolios():
    changed = False

    for username, value in list(portfolios.items()):
        if isinstance(value, list):
            portfolios[username] = {"Main": value}
            changed = True
        elif not isinstance(value, dict):
            portfolios[username] = {"Main": []}
            changed = True
        elif "Main" not in value:
            value["Main"] = []
            changed = True

    if changed:
        save_json(PORTFOLIO_FILE, portfolios)


def normalize_history_all():
    changed = False

    for username, value in list(history.items()):
        if isinstance(value, list):
            history[username] = {"Main": value}
            changed = True
        elif not isinstance(value, dict):
            history[username] = {"Main": []}
            changed = True
        elif "Main" not in value:
            value["Main"] = []
            changed = True

    if changed:
        save_json(HISTORY_FILE, history)


def normalize_sales_all():
    changed = False

    for username, value in list(sales_history.items()):
        if isinstance(value, list):
            sales_history[username] = {"Main": value}
            changed = True
        elif not isinstance(value, dict):
            sales_history[username] = {"Main": []}
            changed = True
        elif "Main" not in value:
            value["Main"] = []
            changed = True

    if changed:
        save_json(SALES_FILE, sales_history)


def email_exists(email):
    lowered = email.strip().lower()
    for _, info in users.items():
        if isinstance(info, dict) and str(info.get("email", "")).strip().lower() == lowered:
            return True
    return False


def get_username_from_email(email):
    lowered = email.strip().lower()
    for username, info in users.items():
        if isinstance(info, dict) and str(info.get("email", "")).strip().lower() == lowered:
            return username
    return None


def get_user_id(username):
    if username in users and isinstance(users[username], dict):
        return users[username].get("user_id", "")
    return ""


def find_username_by_name_or_id(search_value):
    if not search_value:
        return None

    cleaned = search_value.strip()
    lowered = cleaned.lower()

    if cleaned in users:
        return cleaned

    for username, info in users.items():
        if username.lower() == lowered:
            return username
        if isinstance(info, dict):
            user_id = str(info.get("user_id", "")).strip().lower()
            if user_id == lowered:
                return username

    return None


normalize_users()
normalize_portfolios()
normalize_history_all()
normalize_sales_all()


# =============================
# SESSION
# =============================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user" not in st.session_state:
    st.session_state.user = ""

if "selected_portfolio" not in st.session_state:
    st.session_state.selected_portfolio = "Main"

if "page" not in st.session_state:
    st.session_state.page = "Home"

if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["AAPL", "TSLA", "NVDA", "SPY"]

if "suggested_search_value" not in st.session_state:
    st.session_state.suggested_search_value = ""

if "reset_code" not in st.session_state:
    st.session_state.reset_code = ""

if "reset_user" not in st.session_state:
    st.session_state.reset_user = ""

if "reset_email" not in st.session_state:
    st.session_state.reset_email = ""

if "show_reset_form" not in st.session_state:
    st.session_state.show_reset_form = False


# =============================
# LOGIN / REGISTER PAGE
# =============================
def login_page():
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)

    st.markdown("""
    <div class="ticker-bar">
        <div class="ticker-item">AAPL ▲ 1.24%</div>
        <div class="ticker-item">TSLA ▼ -0.87%</div>
        <div class="ticker-item">NVDA ▲ 2.58%</div>
        <div class="ticker-item">BTC ▲ 0.31%</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-card">', unsafe_allow_html=True)

    st.markdown("""
    <div class="login-brand">
        <div class="login-brand-name">Trade<span>Flow</span></div>
        <div class="login-brand-tag">TRACK. TRADE. GROW.</div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["Login", "Register", "Forgot Password"])

    with tab1:
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login"):
            matched_username = get_username_from_email(login_email)

            if not matched_username:
                st.error("No account found with that email")
            else:
                stored_password = users[matched_username].get("password", "")

                valid_login = (
                    stored_password == login_password
                    or stored_password == hash_password(login_password)
                )

                if valid_login:
                    if stored_password == login_password:
                        users[matched_username]["password"] = hash_password(login_password)
                        save_json(USERS_FILE, users)

                    st.session_state.logged_in = True
                    st.session_state.user = matched_username
                    st.session_state.selected_portfolio = "Main"
                    st.success("Logged in successfully")
                    st.rerun()
                else:
                    st.error("Wrong password")

    with tab2:
        register_username = st.text_input("Username", key="register_username")
        register_email = st.text_input("Email", key="register_email")
        register_password = st.text_input("Password", type="password", key="register_password")

        if st.button("Create Account"):
            clean_username = register_username.strip()
            clean_email = register_email.strip().lower()
            clean_password = register_password.strip()

            if not clean_username or not clean_email or not clean_password:
                st.error("Fill in username, email, and password")
            elif "@" not in clean_email or "." not in clean_email:
                st.error("Enter a valid email")
            elif clean_username in users:
                st.error("Username already exists")
            elif email_exists(clean_email):
                st.error("Email already in use")
            else:
                users[clean_username] = {
                    "password": hash_password(clean_password),
                    "email": clean_email,
                    "visibility": "private",
                    "user_id": generate_unique_user_id(),
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                save_json(USERS_FILE, users)

                portfolios[clean_username] = {"Main": []}
                history[clean_username] = {"Main": []}
                sales_history[clean_username] = {"Main": []}

                save_json(PORTFOLIO_FILE, portfolios)
                save_json(HISTORY_FILE, history)
                save_json(SALES_FILE, sales_history)

                st.success("Account created. You can now log in.")

    with tab3:
        reset_email_input = st.text_input("Enter your account email", key="forgot_email")

        if st.button("Send Reset Code"):
            matched_username = get_username_from_email(reset_email_input)

            if not matched_username:
                st.error("No account found with that email")
            else:
                code = f"{secrets.randbelow(900000) + 100000}"
                st.session_state.reset_code = code
                st.session_state.reset_user = matched_username
                st.session_state.reset_email = reset_email_input.strip().lower()
                st.session_state.show_reset_form = True

                sent, message = send_reset_email(
                    to_email=st.session_state.reset_email,
                    reset_code=code,
                    username=matched_username
                )

                if sent:
                    st.success("Reset code sent to your email")
                else:
                    st.error(message)

        if st.session_state.show_reset_form:
            st.markdown("### Enter Reset Code")
            entered_code = st.text_input("Reset Code", key="entered_reset_code")
            new_password = st.text_input("New Password", type="password", key="new_reset_password")

            if st.button("Reset Password"):
                if not entered_code or not new_password:
                    st.error("Enter the reset code and a new password")
                elif entered_code != st.session_state.reset_code:
                    st.error("Invalid reset code")
                else:
                    reset_user = st.session_state.reset_user
                    users[reset_user]["password"] = hash_password(new_password)
                    save_json(USERS_FILE, users)

                    st.session_state.reset_code = ""
                    st.session_state.reset_user = ""
                    st.session_state.reset_email = ""
                    st.session_state.show_reset_form = False

                    st.success("Password updated. You can now log in.")

    st.markdown("</div></div>", unsafe_allow_html=True)
# =============================
# SEARCH / MARKET HELPERS
# =============================
@st.cache_data(ttl=3600)
def get_symbol_search_map():
    return {
        "apple": "AAPL",
        "aapl": "AAPL",
        "microsoft": "MSFT",
        "msft": "MSFT",
        "nvidia": "NVDA",
        "nvda": "NVDA",
        "amazon": "AMZN",
        "amzn": "AMZN",
        "meta": "META",
        "facebook": "META",
        "alphabet": "GOOGL",
        "google": "GOOGL",
        "googl": "GOOGL",
        "tesla": "TSLA",
        "tsla": "TSLA",
        "netflix": "NFLX",
        "nflx": "NFLX",
        "amd": "AMD",
        "intel": "INTC",
        "intc": "INTC",
        "palantir": "PLTR",
        "pltr": "PLTR",
        "uber": "UBER",
        "spy": "SPY",
        "qqq": "QQQ",
        "iwm": "IWM",
        "bitcoin": "BTC-USD",
        "btc": "BTC-USD",
        "btc-usd": "BTC-USD",
        "ethereum": "ETH-USD",
        "eth": "ETH-USD",
        "eth-usd": "ETH-USD",
        "solana": "SOL-USD",
        "sol": "SOL-USD",
        "sol-usd": "SOL-USD",
        "xrp": "XRP-USD",
        "xrp-usd": "XRP-USD",
        "cardano": "ADA-USD",
        "ada": "ADA-USD",
        "ada-usd": "ADA-USD",
    }


def resolve_ticker(user_input):
    if not user_input:
        return None

    cleaned = user_input.strip().lower()
    symbol_map = get_symbol_search_map()

    if cleaned in symbol_map:
        return symbol_map[cleaned]

    upper_value = user_input.strip().upper()
    if upper_value in SCAN_UNIVERSE:
        return upper_value

    return upper_value


def calculate_change(current, previous):
    if previous is None or previous <= 0:
        return 0.0
    return ((current - previous) / previous) * 100.0


# =============================
# PRICE / ANALYSIS HELPERS
# =============================
@st.cache_data(ttl=60)
def get_price(ticker):
    try:
        if not ticker:
            return None

        data = yf.Ticker(ticker).history(period="5d")
        if data is None or data.empty or "Close" not in data.columns:
            return None

        close = data["Close"].dropna()
        if close.empty:
            return None

        return float(close.iloc[-1])
    except Exception:
        return None


@st.cache_data(ttl=300)
def get_price_and_change(ticker):
    try:
        if not ticker:
            return None, None

        data = yf.Ticker(ticker).history(period="5d")
        if data is None or data.empty or "Close" not in data.columns:
            return None, None

        close = data["Close"].dropna()
        if close.empty:
            return None, None

        current = float(close.iloc[-1])
        previous = float(close.iloc[-2]) if len(close) > 1 else current
        pct_change = ((current - previous) / previous) * 100 if previous else 0.0
        return current, pct_change
    except Exception:
        return None, None


@st.cache_data(ttl=60)
def get_market_frame(ticker):
    try:
        if not ticker:
            return pd.DataFrame()

        df = yf.Ticker(ticker).history(period="5d", interval="5m")
        if df is None:
            return pd.DataFrame()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60)
def get_extended_market_frame(ticker):
    try:
        if not ticker:
            return pd.DataFrame()
        df = yf.Ticker(ticker).history(period="1mo", interval="1h")
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60)
def get_asset_analysis(ticker):
    df = get_market_frame(ticker)
    return analyze_market_frame(df)


def calculate_consistency_score(df):
    if df is None or df.empty or "Close" not in df.columns or len(df) < 6:
        return 0.0

    close = df["Close"].dropna()
    if len(close) < 6:
        return 0.0

    rises = 0
    falls = 0

    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i - 1]:
            rises += 1
        elif close.iloc[i] < close.iloc[i - 1]:
            falls += 1

    total = rises + falls
    return (max(rises, falls) / total) if total > 0 else 0.0


def calculate_volume_score(df):
    if df is None or df.empty or "Volume" not in df.columns:
        return 0.0

    volume = df["Volume"].dropna()
    if len(volume) < 10:
        return 0.0

    recent = volume.tail(5).mean()
    base = volume.tail(20).mean() if len(volume) >= 20 else volume.mean()

    return (recent - base) / base if base > 0 else 0.0


def estimate_hold_window(change_1h, change_24h, change_7d, volatility_pct):
    if change_1h > 0 and change_24h > 0 and volatility_pct < 1.2:
        return "6–24 hours", "Short swing continuation likely"
    if change_24h > 0 and change_7d > 0 and volatility_pct < 2.2:
        return "1–3 days", "Momentum may continue over the next few sessions"
    if change_7d > 0:
        return "3–7 days", "Broader trend may keep pushing higher"
    return "Watch only", "Setup is weaker right now"


@st.cache_data(ttl=60)
def get_ai_trade_idea(ticker):
    extended = get_extended_market_frame(ticker)
    analysis = get_asset_analysis(ticker)

    change_1h = float(analysis.get("change_1h", 0))
    change_24h = float(analysis.get("change_24h", 0))
    volatility_pct = float(analysis.get("volatility_pct", 0))

    change_7d = 0.0
    try:
        if extended is not None and not extended.empty and "Close" in extended.columns:
            close = extended["Close"].dropna()
            if len(close) > 168:
                change_7d = ((close.iloc[-1] - close.iloc[-168]) / close.iloc[-168]) * 100
    except Exception:
        change_7d = 0.0

    consistency = calculate_consistency_score(extended)
    volume = calculate_volume_score(extended)

    idea = score_trade_idea(
        change_1h,
        change_24h,
        change_7d,
        volatility_pct,
        consistency,
        volume
    )

    hold_window, hold_reason = estimate_hold_window(
        change_1h,
        change_24h,
        change_7d,
        volatility_pct
    )

    return {
        "ticker": ticker,
        "asset": ASSET_LABELS.get(ticker, ticker),
        "price": get_price(ticker),
        "trend": analysis.get("trend", "Neutral ➖"),
        "volatility": analysis.get("volatility", "Low volatility 🟢"),
        "change_1h": round(change_1h, 2),
        "change_24h": round(change_24h, 2),
        "change_7d": round(change_7d, 2),
        "label": idea["label"],
        "confidence": idea["confidence"],
        "score": idea["score"],
        "reasons": idea["reasons"],
        "hold_window": hold_window,
        "hold_reason": hold_reason,
    }


@st.cache_data(ttl=60)
def build_ai_trade_ideas():
    rows = []

    for ticker in SCAN_UNIVERSE:
        try:
            rows.append(get_ai_trade_idea(ticker))
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).sort_values("score", ascending=False).head(10)


@st.cache_data(ttl=60)
def build_suggested_assets():
    rows = []

    for ticker in SCAN_UNIVERSE:
        analysis = get_asset_analysis(ticker)
        score = float(analysis.get("suggestion_score", 0.0))

        if score < SUGGESTION_SCORE_THRESHOLD:
            continue

        if analysis.get("change_1h", 0) <= 0 and analysis.get("change_24h", 0) <= 0:
            continue

        rows.append({
            "Ticker": ticker,
            "Asset": ASSET_LABELS.get(ticker, ticker),
            "Score": round(score, 3),
            "Tag": analysis.get("suggestion_tag", "Momentum rising 📈"),
            "Trend": analysis.get("trend", "Neutral ➖"),
            "Volatility": analysis.get("volatility", "Low volatility 🟢"),
            "1H %": round(float(analysis.get("change_1h", 0.0)), 2),
            "24H %": round(float(analysis.get("change_24h", 0.0)), 2),
        })

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).sort_values("Score", ascending=False).head(8)


# =============================
# NEWS HELPERS
# =============================
@st.cache_data(ttl=120)
def get_ticker_news(ticker, limit=12):
    try:
        if not ticker:
            return []

        resolved = resolve_ticker(ticker)
        if not resolved:
            return []

        news_items = yf.Ticker(resolved).news
        if not news_items:
            return []

        cleaned_items = []
        for item in news_items[:limit]:
            content = item.get("content", {}) if isinstance(item, dict) else {}

            title = content.get("title") or item.get("title") or "Untitled headline"
            link = (
                content.get("canonicalUrl", {}).get("url")
                or content.get("clickThroughUrl", {}).get("url")
                or item.get("link")
                or ""
            )
            publisher = (
                content.get("provider", {}).get("displayName")
                or item.get("publisher")
                or "Unknown source"
            )
            published_at = content.get("pubDate") or item.get("providerPublishTime") or ""
            summary = content.get("summary") or item.get("summary") or ""

            cleaned_items.append({
                "title": title,
                "link": link,
                "publisher": publisher,
                "published_at": published_at,
                "summary": summary,
                "ticker": resolved,
            })

        return cleaned_items
    except Exception:
        return []


@st.cache_data(ttl=120)
def get_multi_asset_news(tickers, limit_per_ticker=4, total_limit=16):
    all_news = []
    seen_links = set()

    for ticker in tickers:
        items = get_ticker_news(ticker, limit=limit_per_ticker)
        for item in items:
            link = item.get("link", "")
            if link and link not in seen_links:
                seen_links.add(link)
                all_news.append(item)

    all_news = sorted(all_news, key=lambda x: str(x.get("published_at", "")), reverse=True)
    return all_news[:total_limit]


def get_news_domain(link):
    try:
        if not link:
            return ""
        return urlparse(link).netloc.replace("www.", "")
    except Exception:
        return ""


def is_preferred_news_source(item):
    publisher = str(item.get("publisher", "")).lower()
    domain = get_news_domain(item.get("link", "")).lower()

    preferred_terms = [
        "reuters",
        "associated press",
        "ap news",
        "bloomberg",
        "cnbc",
        "marketwatch",
        "barrons",
        "financial times",
        "wsj",
        "the wall street journal",
        "investopedia",
        "yahoo finance",
    ]
    return any(term in publisher or term in domain for term in preferred_terms)


def split_news_by_quality(news_items):
    preferred = []
    other = []

    for item in news_items:
        if is_preferred_news_source(item):
            preferred.append(item)
        else:
            other.append(item)

    return preferred, other
# =============================
# SIDEBAR NAVIGATION (FIXED)
# =============================
def sidebar():
    with st.sidebar:
        st.markdown("## 📊 TradeFlow")

        st.session_state.page = st.radio(
            "Navigation",
            ["Home", "Portfolio", "AI Suggestions", "Market", "News", "Settings"]
        )

        st.markdown("---")

        user = st.session_state.user

        # =============================
        # MULTI-PORTFOLIO SUPPORT (FIXED)
        # =============================
        user_portfolios = portfolios.get(user, {"Main": []})

        portfolio_names = list(user_portfolios.keys())

        selected = st.selectbox(
            "Select Portfolio",
            portfolio_names,
            index=portfolio_names.index(st.session_state.selected_portfolio)
            if st.session_state.selected_portfolio in portfolio_names else 0
        )

        st.session_state.selected_portfolio = selected

        # ➕ Create new portfolio (THIS WAS MISSING)
        new_portfolio_name = st.text_input("New Portfolio Name")

        if st.button("➕ Add Portfolio"):
            if new_portfolio_name.strip():
                if new_portfolio_name not in user_portfolios:
                    portfolios[user][new_portfolio_name] = []
                    history[user][new_portfolio_name] = []
                    sales_history[user][new_portfolio_name] = []

                    save_json(PORTFOLIO_FILE, portfolios)
                    save_json(HISTORY_FILE, history)
                    save_json(SALES_FILE, sales_history)

                    st.success("Portfolio created")
                    st.rerun()
                else:
                    st.error("Portfolio already exists")

        st.markdown("---")

        # 👤 USER INFO
        user_info = users.get(user, {})
        st.markdown(f"👤 **{user}**")
        st.caption(f"ID: {user_info.get('user_id', '')}")

        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user = ""
            st.rerun()


# =============================
# PORTFOLIO HELPERS
# =============================
def get_current_portfolio():
    user = st.session_state.user
    portfolio_name = st.session_state.selected_portfolio

    return portfolios.get(user, {}).get(portfolio_name, [])


def save_current_portfolio(data):
    user = st.session_state.user
    portfolio_name = st.session_state.selected_portfolio

    portfolios[user][portfolio_name] = data
    save_json(PORTFOLIO_FILE, portfolios)


# =============================
# HOME PAGE (FIXES BLANK MIDDLE)
# =============================
def home_page():
    st.markdown('<div class="main-title">Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Overview of your trading activity</div>', unsafe_allow_html=True)

    portfolio = get_current_portfolio()

    total_value = 0
    total_change = 0

    for item in portfolio:
        ticker = item.get("ticker")
        shares = item.get("shares", 0)

        price, change = get_price_and_change(ticker)

        if price:
            total_value += price * shares
        if change:
            total_change += change

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="metric-card metric-blue">
            <div class="metric-label">Portfolio Value</div>
            <div class="metric-value">${total_value:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card metric-green">
            <div class="metric-label">Avg Change</div>
            <div class="metric-value">{round(total_change,2)}%</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card metric-white">
            <div class="metric-label">Assets</div>
            <div class="metric-value">{len(portfolio)}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 🔥 THIS FIXES THE "EMPTY BLACK SPACE"
    st.markdown("## 🚀 Quick Actions")

    colA, colB = st.columns(2)

    with colA:
        ticker = st.text_input("Add Stock (Ticker)")
        shares = st.number_input("Shares", min_value=1, step=1)

        if st.button("➕ Add to Portfolio"):
            if ticker:
                portfolio.append({
                    "ticker": ticker.upper(),
                    "shares": shares
                })
                save_current_portfolio(portfolio)
                st.success("Added")
                st.rerun()

    with colB:
        st.markdown("### 📈 Quick Market View")

        for t in ["AAPL", "TSLA", "NVDA"]:
            price, change = get_price_and_change(t)
            if price:
                st.write(f"{t}: ${round(price,2)} ({round(change,2)}%)")

# =============================
# PORTFOLIO PAGE
# =============================
def portfolio_page():
    st.markdown('<div class="main-title">Portfolio</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="subtitle">Current portfolio: {st.session_state.selected_portfolio}</div>',
        unsafe_allow_html=True
    )

    portfolio = get_current_portfolio()
    df = build_portfolio_df(portfolio)

    if df.empty:
        st.info("No holdings yet in this portfolio.")
        return

    total_value = float(df["Value"].sum())
    total_profit = float(df["Profit"].sum())
    total_pct = (total_profit / (total_value - total_profit) * 100) if total_value > total_profit else 0.0

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="metric-card metric-blue">
            <div class="metric-label">Portfolio Value</div>
            <div class="metric-value">${total_value:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card metric-green">
            <div class="metric-label">Total Profit</div>
            <div class="metric-value">${total_profit:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card metric-white">
            <div class="metric-label">Return %</div>
            <div class="metric-value">{total_pct:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.dataframe(df, use_container_width=True)

    st.markdown("## Manage Holdings")

    for i, row in df.iterrows():
        st.markdown(f"### {row['Ticker']}")
        c1, c2 = st.columns(2)

        with c1:
            sell_shares = st.number_input(
                f"Sell shares of {row['Ticker']}",
                min_value=1,
                max_value=max(1, int(row["Shares"])),
                step=1,
                key=f"sell_qty_{i}"
            )

        with c2:
            if st.button(f"Sell {row['Ticker']}", key=f"sell_btn_{i}"):
                updated = []
                sold_ticker = row["Ticker"]

                for item in portfolio:
                    if item.get("ticker") == sold_ticker:
                        current_shares = float(item.get("shares", 0))
                        if current_shares > sell_shares:
                            item["shares"] = current_shares - sell_shares
                            updated.append(item)
                        elif current_shares == sell_shares:
                            pass
                        else:
                            updated.append(item)
                    else:
                        updated.append(item)

                save_current_portfolio(updated)
                st.success(f"Sold {sell_shares} share(s) of {sold_ticker}")
                st.rerun()

        if st.button(f"Remove {row['Ticker']} completely", key=f"remove_btn_{i}"):
            updated = [item for item in portfolio if item.get("ticker") != row["Ticker"]]
            save_current_portfolio(updated)
            st.success(f"Removed {row['Ticker']}")
            st.rerun()

        st.markdown("---")


# =============================
# AI SUGGESTIONS PAGE
# =============================
def ai_suggestions_page():
    st.markdown('<div class="main-title">AI Suggestions</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Ideas based on momentum, volatility, consistency, and volume</div>',
        unsafe_allow_html=True
    )

    ideas = build_ai_trade_ideas()

    if ideas.empty:
        st.warning("No AI ideas found right now.")
        return

    top = ideas.iloc[0]

    st.markdown(f"""
    <div class="card">
        <div class="section-title">Top Pick</div>
        <p><strong>{top['asset']} ({top['ticker']})</strong></p>
        <p>Signal: {top['label']}</p>
        <p>Confidence: {top['confidence']}%</p>
        <p>Trend: {top['trend']}</p>
        <p>Volatility: {top['volatility']}</p>
        <p>1H: {top['change_1h']:+.2f}% | 24H: {top['change_24h']:+.2f}% | 7D: {top['change_7d']:+.2f}%</p>
        <p>Hold window: {top['hold_window']}</p>
        <p>{top['hold_reason']}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("## Ranked Suggestions")

    portfolio = get_current_portfolio()

    for i, row in ideas.iterrows():
        st.markdown(f"""
        <div class="card">
            <div class="section-title">{row['asset']} ({row['ticker']})</div>
            <p><strong>Signal:</strong> {row['label']}</p>
            <p><strong>Confidence:</strong> {row['confidence']}%</p>
            <p><strong>Trend:</strong> {row['trend']}</p>
            <p><strong>Volatility:</strong> {row['volatility']}</p>
            <p><strong>1H:</strong> {row['change_1h']:+.2f}% |
               <strong>24H:</strong> {row['change_24h']:+.2f}% |
               <strong>7D:</strong> {row['change_7d']:+.2f}%</p>
            <p><strong>Hold:</strong> {row['hold_window']}</p>
            <p>{row['hold_reason']}</p>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)

        with c1:
            if st.button(f"Search {row['ticker']}", key=f"ai_search_{i}"):
                st.session_state.suggested_search_value = row["ticker"]
                st.session_state.page = "Market"
                st.rerun()

        with c2:
            if st.button(f"Buy $100 of {row['ticker']}", key=f"ai_buy_{i}"):
                price = get_price(row["ticker"])
                if price:
                    shares = round(100 / price, 6)
                    portfolio.append({
                        "ticker": row["ticker"],
                        "shares": shares,
                        "avg_price": price
                    })
                    save_current_portfolio(portfolio)
                    st.success(f"Bought ${100} of {row['ticker']}")
                    st.rerun()
                else:
                    st.error("Could not fetch latest price")

        with c3:
            custom_amount = st.number_input(
                f"Custom buy amount for {row['ticker']}",
                min_value=1.0,
                value=250.0,
                step=1.0,
                key=f"ai_custom_amount_{i}"
            )
            if st.button(f"Buy custom {row['ticker']}", key=f"ai_buy_custom_{i}"):
                price = get_price(row["ticker"])
                if price:
                    shares = round(custom_amount / price, 6)
                    portfolio.append({
                        "ticker": row["ticker"],
                        "shares": shares,
                        "avg_price": price
                    })
                    save_current_portfolio(portfolio)
                    st.success(f"Bought ${custom_amount:.2f} of {row['ticker']}")
                    st.rerun()
                else:
                    st.error("Could not fetch latest price")

        st.markdown("---")
# =============================
# MARKET PAGE
# =============================
def market_page():
    st.markdown('<div class="main-title">Market</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Search stocks and crypto, view price, and quick-buy</div>',
        unsafe_allow_html=True
    )

    default_search = st.session_state.get("suggested_search_value", "")
    search_input = st.text_input(
        "Search by name or ticker",
        value=default_search,
        placeholder="Apple, AAPL, Bitcoin, BTC-USD"
    )

    ticker = resolve_ticker(search_input)

    if search_input:
        st.session_state.suggested_search_value = search_input

    if not ticker:
        st.info("Enter a stock or crypto to begin.")
        return

    price, change = get_price_and_change(ticker)

    if price is None:
        st.error("Could not find that ticker.")
        return

    analysis = get_asset_analysis(ticker)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Ticker", ticker)
    with col2:
        st.metric("Price", f"${price:,.2f}")
    with col3:
        st.metric("24H Change", f"{change:+.2f}%" if change is not None else "N/A")

    st.markdown(f"""
    <div class="card">
        <div class="section-title">{ticker} Overview</div>
        <p><strong>Trend:</strong> {analysis.get('trend', 'Neutral')}</p>
        <p><strong>Volatility:</strong> {analysis.get('volatility', 'Unknown')}</p>
        <p><strong>1H Change:</strong> {analysis.get('change_1h', 0):+.2f}%</p>
        <p><strong>24H Change:</strong> {analysis.get('change_24h', 0):+.2f}%</p>
    </div>
    """, unsafe_allow_html=True)

    df = get_extended_market_frame(ticker)
    if not df.empty and "Close" in df.columns:
        st.markdown("### Price Chart")
        st.line_chart(df["Close"])

    st.markdown("### Quick Buy")
    amount = st.number_input("Amount to invest ($)", min_value=1.0, value=100.0, step=1.0, key="market_buy_amount")

    if st.button("Buy This Asset", key="market_buy_btn"):
        portfolio = get_current_portfolio()
        shares = round(amount / price, 6)
        portfolio.append({
            "ticker": ticker,
            "shares": shares,
            "avg_price": price
        })
        save_current_portfolio(portfolio)
        st.success(f"Bought ${amount:.2f} of {ticker}")
        st.rerun()


# =============================
# NEWS PAGE
# =============================
def news_page():
    st.markdown('<div class="main-title">News</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Latest market headlines from tracked assets</div>',
        unsafe_allow_html=True
    )

    news_mode = st.radio(
        "News Source",
        ["AI Picks", "Search Ticker"],
        horizontal=True
    )

    selected_news = []

    if news_mode == "AI Picks":
        ideas = build_ai_trade_ideas()
        ai_tickers = ideas["ticker"].tolist()[:6] if not ideas.empty else []
        selected_news = get_multi_asset_news(ai_tickers, limit_per_ticker=3, total_limit=18)

    elif news_mode == "Search Ticker":
        news_search = st.text_input("Search ticker for news", placeholder="AAPL, TSLA, BTC-USD")
        resolved = resolve_ticker(news_search)

        if news_search and resolved:
            st.write(f"Showing headlines for **{resolved}**")
            selected_news = get_ticker_news(resolved, limit=15)

    preferred_news, other_news = split_news_by_quality(selected_news)

    if selected_news:
        top_story = selected_news[0]
        st.markdown(f"""
        <div class="card">
            <div class="section-title">Top Story</div>
            <p><strong><a href="{top_story['link']}" target="_blank">{top_story['title']}</a></strong></p>
            <p>{top_story['publisher']} • {top_story.get('ticker', '')}</p>
            <p>{top_story.get('summary', '')}</p>
        </div>
        """, unsafe_allow_html=True)

    if preferred_news:
        st.markdown("### Preferred Sources")
        start_index = 1 if selected_news and preferred_news and preferred_news[0]["title"] == selected_news[0]["title"] else 0
        for item in preferred_news[start_index:]:
            st.markdown(f"""
            <div class="card">
                <p><strong><a href="{item['link']}" target="_blank">{item['title']}</a></strong></p>
                <p>{item['publisher']} • {item.get('ticker', '')}</p>
                <p>{item.get('summary', '')}</p>
            </div>
            """, unsafe_allow_html=True)

    if other_news:
        st.markdown("### More Headlines")
        for item in other_news:
            st.markdown(f"""
            <div class="card">
                <p><strong><a href="{item['link']}" target="_blank">{item['title']}</a></strong></p>
                <p>{item['publisher']} • {item.get('ticker', '')}</p>
                <p>{item.get('summary', '')}</p>
            </div>
            """, unsafe_allow_html=True)

    if not selected_news:
        st.info("No news found right now.")


# =============================
# PROFILES PAGE
# =============================
def profiles_page():
    st.markdown('<div class="main-title">Profiles</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Search users by username or user ID</div>',
        unsafe_allow_html=True
    )

    search_user = st.text_input("Search by username or user ID")

    if not search_user:
        st.info("Search for a user to view their public profile.")
        return

    matched_username = find_username_by_name_or_id(search_user)

    if not matched_username:
        st.error("User not found")
        return

    st.write(f"**Username:** {matched_username}")
    st.write(f"**User ID:** {get_user_id(matched_username)}")

    visibility = get_user_visibility(matched_username)

    if visibility == "private":
        st.warning("This account is private 🔒")
        return

    st.success("📊 Public Portfolio")

    insights = build_public_profile_insights(matched_username)
    public_portfolios = get_user_portfolios(matched_username)

    all_rows = []
    for rows in public_portfolios.values():
        all_rows.extend(rows)

    df = build_portfolio_df(all_rows)

    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No public portfolio data available")

    st.markdown("### Performance Insights")
    st.write(f"**Portfolio value:** ${insights['value']:,.2f}")
    st.write(f"**Profit:** ${insights['profit']:,.2f}")
    st.write(f"**Return %:** {insights['pct']:.2f}%")
    st.write(f"**Best asset:** {insights['best']}")
    st.write(f"**Worst asset:** {insights['worst']}")
    st.write(f"**Win rate:** {insights['win_rate']}")
    st.write(f"**Risk level:** {insights['risk']}")


# =============================
# SETTINGS PAGE
# =============================
def settings_page():
    st.markdown('<div class="main-title">Settings</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Manage your account and profile visibility</div>',
        unsafe_allow_html=True
    )

    user = st.session_state.user
    current_visibility = get_user_visibility(user)

    st.write(f"**Logged in as:** {user}")
    st.write(f"**Email:** {users[user].get('email', '')}")
    st.write(f"**User ID:** {get_user_id(user)}")
    st.write(f"**Current visibility:** {current_visibility}")

    new_visibility = st.selectbox(
        "Profile visibility",
        ["private", "public"],
        index=0 if current_visibility == "private" else 1
    )

    if st.button("Update Visibility"):
        set_user_visibility(user, new_visibility)
        st.success("Visibility updated")
        st.rerun()

    st.markdown("---")
    st.markdown("### Password Reset")
    st.caption("Use the Forgot Password tab on the login screen to send yourself a reset email.")
# =============================
# EXTRA PORTFOLIO / PROFILE HELPERS
# =============================
def get_user_portfolios(username):
    if username not in portfolios:
        portfolios[username] = {"Main": []}
        save_json(PORTFOLIO_FILE, portfolios)

    if isinstance(portfolios[username], list):
        portfolios[username] = {"Main": portfolios[username]}
        save_json(PORTFOLIO_FILE, portfolios)

    if "Main" not in portfolios[username]:
        portfolios[username]["Main"] = []
        save_json(PORTFOLIO_FILE, portfolios)

    return portfolios[username]


def build_portfolio_df(portfolio):
    rows = []

    for item in portfolio:
        ticker = item.get("ticker", "")
        shares = float(item.get("shares", 0))
        avg_price = float(item.get("avg_price", 0))

        if not ticker or shares <= 0:
            continue

        current_price = get_price(ticker)
        if current_price is None:
            continue

        value = shares * current_price
        invested = shares * avg_price
        profit = value - invested
        pct = (profit / invested * 100) if invested > 0 else 0.0

        rows.append({
            "Ticker": ticker,
            "Shares": round(shares, 6),
            "Avg Price": round(avg_price, 2),
            "Price": round(current_price, 2),
            "Value": round(value, 2),
            "Profit": round(profit, 2),
            "%": round(pct, 2),
        })

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def get_user_visibility(username):
    if username in users and isinstance(users[username], dict):
        return users[username].get("visibility", "private")
    return "private"


def set_user_visibility(username, visibility):
    if username in users and isinstance(users[username], dict):
        users[username]["visibility"] = visibility
        save_json(USERS_FILE, users)


def build_public_profile_insights(username):
    user_portfolios = get_user_portfolios(username)

    all_rows = []
    for portfolio_rows in user_portfolios.values():
        if isinstance(portfolio_rows, list):
            all_rows.extend(portfolio_rows)

    df = build_portfolio_df(all_rows)

    total_value = float(df["Value"].sum()) if not df.empty else 0.0
    total_profit = float(df["Profit"].sum()) if not df.empty else 0.0
    invested = total_value - total_profit
    total_pct = (total_profit / invested * 100) if invested > 0 else 0.0

    best_asset = "N/A"
    worst_asset = "N/A"

    if not df.empty:
        sorted_df = df.sort_values("%", ascending=False)
        best_asset = sorted_df.iloc[0]["Ticker"]
        worst_asset = sorted_df.iloc[-1]["Ticker"]

    return {
        "value": total_value,
        "profit": total_profit,
        "pct": total_pct,
        "best": best_asset,
        "worst": worst_asset,
        "win_rate": "N/A",
        "risk": "Medium",
    }
# =============================
# MAIN APP ROUTER (FULLY FIXED)
# =============================
def main_app():
    sidebar()

    if st.session_state.page == "Home":
        home_page()

    elif st.session_state.page == "Portfolio":
        portfolio_page()

    elif st.session_state.page == "AI Suggestions":
        ai_suggestions_page()

    elif st.session_state.page == "Market":
        market_page()

    elif st.session_state.page == "News":
        news_page()

    elif st.session_state.page == "Profiles":
        profiles_page()

    elif st.session_state.page == "Settings":
        settings_page()
# =============================
# APP ENTRY
# =============================
if not st.session_state.logged_in:
    login_page()
else:
    main_app()
