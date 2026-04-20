import streamlit as st
import json
import os
import hashlib
import uuid
import yfinance as yf
import pandas as pd
from datetime import datetime
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
        background: linear-gradient(180deg, #031b4e 0%, #02153c 100%);
        border-radius: 20px;
        padding: 14px 18px;
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        margin-bottom: 24px;
        box-shadow: 0 8px 24px rgba(16, 42, 67, 0.14);
    }

    .ticker-item {
        color: white;
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
# HELPERS
# =============================
def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


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


users = load_json(USERS_FILE, {})
portfolios = load_json(PORTFOLIO_FILE, {})
history = load_json(HISTORY_FILE, {})
sales_history = load_json(SALES_FILE, {})


def normalize_users():
    changed = False
    for username, value in list(users.items()):
        if isinstance(value, str):
            users[username] = {
                "password": value,
                "visibility": "private",
                "user_id": f"TF-{uuid.uuid4().hex[:8].upper()}"
            }
            changed = True
        elif isinstance(value, dict):
            if "password" not in value:
                value["password"] = ""
                changed = True
            if "visibility" not in value:
                value["visibility"] = "private"
                changed = True
            if "user_id" not in value or not str(value["user_id"]).strip():
                value["user_id"] = f"TF-{uuid.uuid4().hex[:8].upper()}"
                changed = True
        else:
            users[username] = {
                "password": "",
                "visibility": "private",
                "user_id": f"TF-{uuid.uuid4().hex[:8].upper()}"
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


def get_user_id(username):
    if username in users and isinstance(users[username], dict):
        return users[username].get("user_id", "")
    return ""


def find_username_by_name_or_id(search_value):
    if not search_value:
        return None

    cleaned = search_value.strip()
    if cleaned in users:
        return cleaned

    lowered = cleaned.lower()
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

# =============================
# LOGIN
# =============================
def login_page():
    st.markdown("""
    <div class="login-wrap">
        <div class="ticker-bar">
            <div class="ticker-item">AAPL ▲ 1.24%</div>
            <div class="ticker-item">TSLA ▼ -0.87%</div>
            <div class="ticker-item">NVDA ▲ 2.58%</div>
            <div class="ticker-item">SPY ▲ 0.31%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-wrap"><div class="login-card">', unsafe_allow_html=True)

    st.markdown("""
    <div class="login-brand">
        <div class="login-brand-name">Trade<span>Flow</span></div>
        <div class="login-brand-tag">TRACK. TRADE. GROW.</div>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Welcome back")

    mode = st.radio("Select Mode", ["Login", "Register"], horizontal=True)

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if mode == "Register":
        if st.button("Create Account"):
            if username in users:
                st.error("User already exists")
            elif not username.strip() or not password.strip():
                st.error("Enter a username and password")
            else:
                users[username] = {
                    "password": hash_password(password),
                    "visibility": "private",
                    "user_id": generate_unique_user_id()
                }
                save_json(USERS_FILE, users)

                portfolios[username] = {"Main": []}
                history[username] = {"Main": []}
                sales_history[username] = {"Main": []}

                save_json(PORTFOLIO_FILE, portfolios)
                save_json(HISTORY_FILE, history)
                save_json(SALES_FILE, sales_history)

                st.success("Account created. You can now log in.")

    if mode == "Login":
        if st.button("Login"):
            if username in users and users[username]["password"] == hash_password(password):
                st.session_state.logged_in = True
                st.session_state.user = username
                st.session_state.selected_portfolio = "Main"
                st.rerun()
            else:
                st.error("Invalid login")

    st.markdown("</div></div>", unsafe_allow_html=True)

# =============================
# DATA HELPERS
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
def get_asset_analysis(ticker):
    df = get_market_frame(ticker)
    return analyze_market_frame(df)


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


def get_user_portfolios(user):
    if user not in portfolios:
        portfolios[user] = {"Main": []}
    elif isinstance(portfolios[user], list):
        portfolios[user] = {"Main": portfolios[user]}
    elif not isinstance(portfolios[user], dict):
        portfolios[user] = {"Main": []}

    if "Main" not in portfolios[user]:
        portfolios[user]["Main"] = []

    save_json(PORTFOLIO_FILE, portfolios)
    return portfolios[user]


def normalize_history_for_user(user):
    if user not in history:
        history[user] = {"Main": []}
    elif isinstance(history[user], list):
        history[user] = {"Main": history[user]}
    elif not isinstance(history[user], dict):
        history[user] = {"Main": []}

    if "Main" not in history[user]:
        history[user]["Main"] = []

    save_json(HISTORY_FILE, history)


def normalize_sales_for_user(user):
    if user not in sales_history:
        sales_history[user] = {"Main": []}
    elif isinstance(sales_history[user], list):
        sales_history[user] = {"Main": sales_history[user]}
    elif not isinstance(sales_history[user], dict):
        sales_history[user] = {"Main": []}

    if "Main" not in sales_history[user]:
        sales_history[user]["Main"] = []

    save_json(SALES_FILE, sales_history)


def get_current_portfolio():
    return get_user_portfolios(st.session_state.user).get(
        st.session_state.selected_portfolio, []
    )


def save_current_portfolio(updated):
    user = st.session_state.user
    portfolio_name = st.session_state.selected_portfolio

    if user not in portfolios:
        portfolios[user] = {}
    if portfolio_name not in portfolios[user]:
        portfolios[user][portfolio_name] = []

    portfolios[user][portfolio_name] = updated
    save_json(PORTFOLIO_FILE, portfolios)


def get_current_history():
    user = st.session_state.user
    portfolio_name = st.session_state.selected_portfolio
    normalize_history_for_user(user)
    return history[user].get(portfolio_name, [])


def save_current_history(updated):
    user = st.session_state.user
    portfolio_name = st.session_state.selected_portfolio
    normalize_history_for_user(user)
    history[user][portfolio_name] = updated
    save_json(HISTORY_FILE, history)


def get_current_sales():
    user = st.session_state.user
    portfolio_name = st.session_state.selected_portfolio
    normalize_sales_for_user(user)
    return sales_history[user].get(portfolio_name, [])


def save_current_sales(updated):
    user = st.session_state.user
    portfolio_name = st.session_state.selected_portfolio
    normalize_sales_for_user(user)
    sales_history[user][portfolio_name] = updated
    save_json(SALES_FILE, sales_history)


def get_portfolio_value(portfolio):
    total = 0.0
    for trade in portfolio:
        price = get_price(trade.get("Ticker"))
        if price is not None:
            total += price * trade.get("Shares", 0)
    return total


def build_portfolio_df(portfolio):
    rows = []

    for trade in portfolio:
        ticker = trade.get("Ticker")
        price = get_price(ticker)
        if price is None:
            continue

        shares = float(trade.get("Shares", 0))
        amount = float(trade.get("Amount", 0))
        buy_price = float(trade.get("Price", 0))

        value = price * shares
        pl = value - amount

        rows.append({
            "Ticker": ticker,
            "Shares": shares,
            "Buy Price": buy_price,
            "Amount": amount,
            "Market Value": value,
            "Unrealized P/L": pl,
            "Time": trade.get("Time", "")
        })

    return pd.DataFrame(rows)


def update_history_snapshot():
    current_history = get_current_history()
    current_value_now = get_portfolio_value(get_current_portfolio())
    now_key = datetime.now().strftime("%Y-%m-%d %H:%M")

    if not current_history or current_history[-1]["time"] != now_key:
        current_history.append({
            "time": now_key,
            "value": current_value_now
        })
        save_current_history(current_history)


def get_user_visibility(username):
    if username in users:
        return users[username].get("visibility", "private")
    return "private"


def set_user_visibility(username, visibility):
    users[username]["visibility"] = visibility
    save_json(USERS_FILE, users)


def build_public_portfolio_allocations(username):
    if username not in portfolios:
        return pd.DataFrame()

    user_all_portfolios = get_user_portfolios(username)
    allocation = {}

    for _, portfolio in user_all_portfolios.items():
        for trade in portfolio:
            ticker = trade.get("Ticker")
            price = get_price(ticker)
            if price is None:
                continue

            shares = float(trade.get("Shares", 0))
            value = price * shares
            allocation[ticker] = allocation.get(ticker, 0) + value

    if not allocation:
        return pd.DataFrame()

    total = sum(allocation.values())
    data = []

    for ticker, value in allocation.items():
        data.append({
            "Ticker": ticker,
            "Percent": (value / total) * 100
        })

    return pd.DataFrame(data).sort_values("Percent", ascending=False)


@st.cache_data(ttl=60)
def get_asset_comparison_metrics(ticker):
    analysis = get_asset_analysis(ticker)

    try:
        data = yf.Ticker(ticker).history(period="10d")
        if data is None or data.empty or "Close" not in data.columns:
            change_7d = 0.0
        else:
            close = data["Close"].dropna()
            if len(close) >= 2:
                current = float(close.iloc[-1])
                previous_7d = float(close.iloc[0])
                change_7d = safe_pct_change(current, previous_7d)
            else:
                change_7d = 0.0
    except Exception:
        change_7d = 0.0

    momentum_score = (
        float(analysis.get("change_1h", 0)) * 0.4
        + float(analysis.get("change_24h", 0)) * 0.4
        + float(change_7d) * 0.2
    )

    return {
        "ticker": ticker,
        "change_1h": float(analysis.get("change_1h", 0)),
        "change_24h": float(analysis.get("change_24h", 0)),
        "change_7d": float(change_7d),
        "volatility_pct": float(analysis.get("volatility_pct", 0)),
        "volatility_label": analysis.get("volatility", "Low volatility 🟢"),
        "trend": analysis.get("trend", "Neutral ➖"),
        "momentum_score": momentum_score,
    }


def build_portfolio_recap(portfolio_df, history_rows, sales_rows):
    daily_value_change, daily_pct_change = portfolio_change_summary(history_rows, lookback_points=1)
    weekly_value_change, weekly_pct_change = portfolio_change_summary(history_rows, lookback_points=7)

    portfolio_rows = portfolio_df.to_dict("records") if not portfolio_df.empty else []
    best_trade_text, worst_trade_text = best_and_worst_assets_from_portfolio_rows(portfolio_rows)

    wins, losses, win_rate = trade_win_rate(sales_rows)
    consistency = consistency_ratio_from_history(history_rows)

    overall_score = performance_score(
        total_change_pct=weekly_pct_change,
        win_rate_pct=win_rate,
        consistency_ratio=consistency,
    )

    return {
        "daily_value_change": daily_value_change,
        "daily_pct_change": daily_pct_change,
        "weekly_value_change": weekly_value_change,
        "weekly_pct_change": weekly_pct_change,
        "best_trade_text": best_trade_text,
        "worst_trade_text": worst_trade_text,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "consistency": consistency,
        "overall_score": overall_score,
    }


def build_public_profile_insights(username):
    public_df = build_public_portfolio_allocations(username)
    allocation_rows = public_df.to_dict("records") if not public_df.empty else []

    user_history = history.get(username, {})
    combined_history = []
    if isinstance(user_history, dict):
        for _, rows in user_history.items():
            if isinstance(rows, list):
                combined_history.extend(rows)
        combined_history = sorted(combined_history, key=lambda x: str(x.get("time", "")))

    user_sales = sales_history.get(username, {})
    combined_sales = []
    if isinstance(user_sales, dict):
        for _, rows in user_sales.items():
            if isinstance(rows, list):
                combined_sales.extend(rows)

    user_portfolios = get_user_portfolios(username)
    combined_portfolio = []
    for _, rows in user_portfolios.items():
        if isinstance(rows, list):
            combined_portfolio.extend(rows)

    public_portfolio_df = build_portfolio_df(combined_portfolio)
    public_rows = public_portfolio_df.to_dict("records") if not public_portfolio_df.empty else []

    wins, losses, win_rate = trade_win_rate(combined_sales)
    trend_text = trend_label_from_history(combined_history)
    category_text = best_category_label(allocation_rows)
    risk_text = risk_level_from_behavior(allocation_rows, combined_sales, public_rows)

    return {
        "win_rate": win_rate,
        "trend_text": trend_text,
        "category_text": category_text,
        "risk_text": risk_text,
    }

# =============================
# APP START
# =============================
if not st.session_state.logged_in:
    login_page()
    st.stop()

st_autorefresh(interval=60_000, key="tradeflow_live_refresh")

user = st.session_state.user
normalize_history_for_user(user)
normalize_sales_for_user(user)
user_portfolios = get_user_portfolios(user)

if st.session_state.selected_portfolio not in user_portfolios:
    st.session_state.selected_portfolio = "Main"

current_portfolio = get_current_portfolio()
update_history_snapshot()
portfolio_df = build_portfolio_df(current_portfolio)

alert_store = load_alert_store(ALERTS_FILE)

seen_tickers = sorted({trade["Ticker"] for trade in current_portfolio})
for ticker in seen_tickers:
    latest_price = get_price(ticker)
    if latest_price is not None:
        update_price_and_generate_alerts(
            store=alert_store,
            username=user,
            ticker=ticker,
            price=latest_price,
        )

save_alert_store(ALERTS_FILE, alert_store)
recent_alerts = get_recent_events(alert_store, user, limit=12)

current_history_rows = get_current_history()
current_sales_rows = get_current_sales()
current_recap = build_portfolio_recap(portfolio_df, current_history_rows, current_sales_rows)

# =============================
# SIDEBAR
# =============================
st.sidebar.title("TradeFlow")

page = st.sidebar.radio(
    "Navigation",
    ["Home", "Stock Viewer", "Compare Assets", "Profiles", "Settings", "History"]
)
st.session_state.page = page

st.sidebar.markdown("---")
st.sidebar.subheader("Portfolios")

portfolio_names = list(user_portfolios.keys())

selected_portfolio = st.sidebar.selectbox(
    "Select Portfolio",
    portfolio_names,
    index=portfolio_names.index(st.session_state.selected_portfolio)
)
st.session_state.selected_portfolio = selected_portfolio

current_portfolio = get_current_portfolio()
portfolio_df = build_portfolio_df(current_portfolio)

new_portfolio_name = st.sidebar.text_input("New Portfolio Name")

if st.sidebar.button("Create Portfolio"):
    clean_name = new_portfolio_name.strip()

    if not clean_name:
        st.sidebar.error("Enter a portfolio name")
    elif clean_name in user_portfolios:
        st.sidebar.error("Portfolio already exists")
    else:
        user_portfolios[clean_name] = []
        portfolios[user] = user_portfolios
        save_json(PORTFOLIO_FILE, portfolios)

        if user not in history or not isinstance(history[user], dict):
            history[user] = {"Main": []}
        history[user][clean_name] = []
        save_json(HISTORY_FILE, history)

        if user not in sales_history or not isinstance(sales_history[user], dict):
            sales_history[user] = {"Main": []}
        sales_history[user][clean_name] = []
        save_json(SALES_FILE, sales_history)

        st.session_state.selected_portfolio = clean_name
        st.rerun()

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.user = ""
    st.session_state.selected_portfolio = "Main"
    st.rerun()

# =============================
# HOME PAGE
# =============================
if st.session_state.page == "Home":
    invested = float(portfolio_df["Amount"].sum()) if not portfolio_df.empty else 0.0
    current_value = float(portfolio_df["Market Value"].sum()) if not portfolio_df.empty else 0.0
    unrealized_profit = current_value - invested
    pnl_pct = (unrealized_profit / invested * 100) if invested > 0 else 0.0
    portfolio_count = len(user_portfolios)

    st.markdown(f"<div class='main-title'>Welcome back, {user}</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Your trading dashboard overview</div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div class='card' style='margin-bottom:18px;'>
        <div class='section-title'>Market Snapshot</div>
        <div style='display:flex; gap:18px; flex-wrap:wrap;'>
            <div><strong>Profiles</strong><br><span style='color:#627d98;'>Public or private sharing</span></div>
            <div><strong>Selected Portfolio</strong><br><span style='color:#627d98;'>{st.session_state.selected_portfolio}</span></div>
            <div><strong>Profile Status</strong><br><span style='color:#627d98;'>{get_user_visibility(user).title()}</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    recap_col1, recap_col2, recap_col3, recap_col4 = st.columns(4)

    with recap_col1:
        st.markdown(f"""
        <div class="metric-card metric-blue">
            <div class="metric-label">TODAY</div>
            <div class="metric-value">{current_recap['daily_pct_change']:+.2f}%</div>
            <div class="metric-sub">{current_recap['daily_value_change']:+.2f}$</div>
        </div>
        """, unsafe_allow_html=True)

    with recap_col2:
        st.markdown(f"""
        <div class="metric-card metric-green">
            <div class="metric-label">THIS WEEK</div>
            <div class="metric-value">{current_recap['weekly_pct_change']:+.2f}%</div>
            <div class="metric-sub">{current_recap['weekly_value_change']:+.2f}$</div>
        </div>
        """, unsafe_allow_html=True)

    with recap_col3:
        st.markdown(f"""
        <div class="metric-card metric-white">
            <div class="metric-label">WIN RATE</div>
            <div class="metric-value">{current_recap['win_rate']:.1f}%</div>
            <div class="metric-sub">{current_recap['wins']} wins / {current_recap['losses']} losses</div>
        </div>
        """, unsafe_allow_html=True)

    with recap_col4:
        st.markdown(f"""
        <div class="metric-card metric-blue">
            <div class="metric-label">PERFORMANCE SCORE</div>
            <div class="metric-value">{current_recap['overall_score']}</div>
            <div class="metric-sub">Overall recap</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Performance Recap</div>", unsafe_allow_html=True)
    st.write(f"**Best performing asset:** {current_recap['best_trade_text']}")
    st.write(f"**Worst performing asset:** {current_recap['worst_trade_text']}")
    st.write(f"**Profitable trades:** {current_recap['wins']}")
    st.write(f"**Losing trades:** {current_recap['losses']}")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    left, right = st.columns([1.2, 1])

    with left:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Your Holdings</div>", unsafe_allow_html=True)

        if not portfolio_df.empty:
            for _, row in portfolio_df.iterrows():
                analysis = get_asset_analysis(row["Ticker"])
                pct_class = "portfolio-pct-up" if row["Unrealized P/L"] >= 0 else "portfolio-pct-down"

                st.markdown(f"""
                <div class="portfolio-row">
                    <div class="portfolio-left">
                        <div class="portfolio-icon icon-blue">{row['Ticker'][0]}</div>
                        <div>
                            <div class="portfolio-name">{row['Ticker']}</div>
                            <div class="portfolio-meta">
                                {row['Shares']:.4f} shares • {analysis['trend']} • {analysis['volatility']}
                            </div>
                        </div>
                    </div>
                    <div class="portfolio-value">
                        <div class="portfolio-money">${row['Market Value']:,.2f}</div>
                        <div class="{pct_class}">${row['Unrealized P/L']:,.2f}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No holdings yet. Buy a stock in Stock Viewer.")

        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Portfolio Alerts</div>", unsafe_allow_html=True)

        if recent_alerts:
            for event in recent_alerts:
                st.markdown(
                    f"**{event['ticker']}** — {event['message']} "
                    f"({event['pct_change']:+.2f}%)"
                )
        else:
            st.info("No portfolio alerts yet.")

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    bottom_left, bottom_right = st.columns([1.2, 1])

    with bottom_left:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Suggested for You</div>", unsafe_allow_html=True)

        suggested_df = build_suggested_assets()
        if not suggested_df.empty:
            for idx, row in suggested_df.iterrows():
                st.markdown(
                    f"**{row['Asset']} ({row['Ticker']})** — {row['Tag']}  \n"
                    f"{row['Trend']} • {row['Volatility']} • "
                    f"1H: {row['1H %']:+.2f}% • 24H: {row['24H %']:+.2f}%"
                )

                col_a, col_b = st.columns(2)

                with col_a:
                    if st.button(f"Search {row['Ticker']}", key=f"search_{idx}"):
                        st.session_state["suggested_search_value"] = row["Ticker"]
                        st.success(f"Go to Stock Viewer and search {row['Ticker']}")

                with col_b:
                    if st.button(f"Add {row['Ticker']}", key=f"add_{idx}"):
                        add_price = get_price(row["Ticker"])
                        if add_price is not None:
                            default_amount = 100.0
                            trade = {
                                "Ticker": row["Ticker"],
                                "Amount": default_amount,
                                "Price": add_price,
                                "Shares": default_amount / add_price,
                                "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            current_portfolio.append(trade)
                            save_current_portfolio(current_portfolio)
                            st.success(f"Added {row['Ticker']} to portfolio")
                            st.rerun()
                        else:
                            st.error("Could not fetch latest price.")

                st.markdown("---")
        else:
            st.info("No strong growth candidates right now.")

        st.markdown("### Quick Add to Portfolio")
        add_search = st.text_input(
            "Search a stock or crypto to add",
            placeholder="Example: Apple, Tesla, Bitcoin, AAPL",
            key="home_add_search"
        )
        add_ticker = resolve_ticker(add_search)

        if add_search and add_ticker:
            add_price = get_price(add_ticker)

            if add_price is not None:
                st.write(f"**Found:** {add_ticker} — ${add_price:.2f}")

                add_amount = st.number_input(
                    "Amount to invest ($)",
                    min_value=1.0,
                    value=100.0,
                    key="home_add_amount"
                )

                if st.button("Add to Current Portfolio", key="home_add_btn"):
                    trade = {
                        "Ticker": add_ticker,
                        "Amount": add_amount,
                        "Price": add_price,
                        "Shares": add_amount / add_price,
                        "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    current_portfolio.append(trade)
                    save_current_portfolio(current_portfolio)
                    st.success(f"Added {add_ticker} to {st.session_state.selected_portfolio}")
                    st.rerun()
            else:
                st.warning("Could not find that stock or crypto.")

        st.markdown("</div>", unsafe_allow_html=True)

    with bottom_right:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Watchlist</div>", unsafe_allow_html=True)

        watch_search = st.text_input(
            "Add to watchlist",
            placeholder="Type Apple, Tesla, Bitcoin, AAPL...",
            key="watchlist_search"
        )
        watch_ticker = resolve_ticker(watch_search)

        if st.button("Add to Watchlist", key="watchlist_add_btn"):
            if watch_ticker:
                if watch_ticker not in st.session_state.watchlist:
                    st.session_state.watchlist.append(watch_ticker)
                    st.success(f"Added {watch_ticker} to watchlist")
                    st.rerun()
                else:
                    st.info(f"{watch_ticker} is already in your watchlist")
            else:
                st.warning("Enter a stock or crypto name")

        for idx, ticker in enumerate(st.session_state.watchlist):
            price, change = get_price_and_change(ticker)
            change_class = "watch-change-up" if (change is not None and change >= 0) else "watch-change-down"
            change_sign = "+" if (change is not None and change >= 0) else ""
            price_text = f"${price:,.2f}" if price is not None else "N/A"
            change_text = f"{change_sign}{change:.2f}%" if change is not None else "N/A"

            row_left, row_right = st.columns([5, 1])

            with row_left:
                st.markdown(f"""
                <div class="watch-row">
                    <div class="watch-left">
                        <div class="watch-logo">{ticker[0]}</div>
                        <div>
                            <div class="watch-name">{ticker}</div>
                            <div class="watch-sub">Live price</div>
                        </div>
                    </div>
                    <div class="watch-price">
                        <div>{price_text}</div>
                        <div class="{change_class}">{change_text}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with row_right:
                if st.button("X", key=f"remove_watch_{idx}"):
                    st.session_state.watchlist.pop(idx)
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

# =============================
# STOCK VIEWER
# =============================
elif st.session_state.page == "Stock Viewer":
    st.subheader("Stock Viewer")

    default_search = st.session_state.get("suggested_search_value", "")
    search_input = st.text_input(
        "Enter stock or crypto name/ticker (e.g. Apple, AAPL, Bitcoin, BTC-USD)",
        value=default_search
    )

    ticker = resolve_ticker(search_input)

    if search_input:
        st.session_state["suggested_search_value"] = search_input

    if ticker:
        price = get_price(ticker)

        if price:
            analysis = get_asset_analysis(ticker)

            st.success(f"{ticker} Price: ${price:.2f}")
            st.write(f"**Trend:** {analysis['trend']}")
            st.write(f"**Volatility:** {analysis['volatility']}")
            st.write(f"**1H Change:** {analysis['change_1h']:+.2f}%")
            st.write(f"**24H Change:** {analysis['change_24h']:+.2f}%")

            spike_msg = None
            if analysis["change_5m"] >= 1.0:
                spike_msg = "Spike up 📈"
            elif analysis["change_5m"] <= -1.0:
                spike_msg = "Drop down 📉"

            if spike_msg:
                st.warning(f"{spike_msg} ({analysis['change_5m']:+.2f}% over ~5m)")

            amount = st.number_input("Amount to invest ($)", value=100.0, min_value=1.0)

            if st.button("Add to Portfolio"):
                trade = {
                    "Ticker": ticker,
                    "Amount": amount,
                    "Price": price,
                    "Shares": amount / price,
                    "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                current_portfolio.append(trade)
                save_current_portfolio(current_portfolio)
                st.success(f"Bought {ticker}")
                st.rerun()
        else:
            st.error("Invalid ticker or name")

# =============================
# COMPARE ASSETS
# =============================
elif st.session_state.page == "Compare Assets":
    st.subheader("Asset Comparison")

    col1, col2 = st.columns(2)

    with col1:
        left_input = st.text_input("Left asset", placeholder="BTC, Apple, AAPL, ETH-USD", key="compare_left")
    with col2:
        right_input = st.text_input("Right asset", placeholder="ETH, Tesla, TSLA, BTC-USD", key="compare_right")

    left_ticker = resolve_ticker(left_input)
    right_ticker = resolve_ticker(right_input)

    if left_ticker and right_ticker:
        left_price = get_price(left_ticker)
        right_price = get_price(right_ticker)

        if left_price is not None and right_price is not None:
            left_metrics = get_asset_comparison_metrics(left_ticker)
            right_metrics = get_asset_comparison_metrics(right_ticker)
            winner_text = compare_asset_strength(left_metrics, right_metrics)

            left_score = left_metrics["momentum_score"] - left_metrics["volatility_pct"] * 0.2
            right_score = right_metrics["momentum_score"] - right_metrics["volatility_pct"] * 0.2

            left_label = "🏆 Stronger recently" if left_score > right_score else ""
            right_label = "🏆 Stronger recently" if right_score > left_score else ""

            compare_left, compare_right = st.columns(2)

            with compare_left:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown(f"### {left_ticker} {left_label}")
                st.write(f"**1H:** {left_metrics['change_1h']:+.2f}%")
                st.write(f"**24H:** {left_metrics['change_24h']:+.2f}%")
                st.write(f"**7D:** {left_metrics['change_7d']:+.2f}%")
                st.write(f"**Volatility:** {left_metrics['volatility_label']}")
                st.write(f"**Trend:** {left_metrics['trend']}")
                st.write(f"**Momentum score:** {left_metrics['momentum_score']:+.2f}")
                st.markdown("</div>", unsafe_allow_html=True)

            with compare_right:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown(f"### {right_ticker} {right_label}")
                st.write(f"**1H:** {right_metrics['change_1h']:+.2f}%")
                st.write(f"**24H:** {right_metrics['change_24h']:+.2f}%")
                st.write(f"**7D:** {right_metrics['change_7d']:+.2f}%")
                st.write(f"**Volatility:** {right_metrics['volatility_label']}")
                st.write(f"**Trend:** {right_metrics['trend']}")
                st.write(f"**Momentum score:** {right_metrics['momentum_score']:+.2f}")
                st.markdown("</div>", unsafe_allow_html=True)

            st.info(winner_text)
        else:
            st.error("Could not find one or both assets.")

# =============================
# PROFILES
# =============================
elif st.session_state.page == "Profiles":
    st.subheader("Search Profiles")

    search_user = st.text_input("Search by username or user ID")

    if search_user:
        matched_username = find_username_by_name_or_id(search_user)

        if not matched_username:
            st.error("User not found")
        else:
            st.write(f"**Username:** {matched_username}")
            st.write(f"**User ID:** {get_user_id(matched_username)}")

            visibility = get_user_visibility(matched_username)

            if visibility == "private":
                st.warning("This account is private 🔒")
            else:
                st.success("📊 Public Portfolio")

                df = build_public_portfolio_allocations(matched_username)
                insights = build_public_profile_insights(matched_username)

                if not df.empty:
                    fig, ax = plt.subplots(figsize=(6, 6))
                    ax.pie(
                        df["Percent"],
                        labels=df["Ticker"],
                        autopct="%1.1f%%"
                    )
                    ax.set_title(f"{matched_username}'s Portfolio Allocation")
                    st.pyplot(fig)
                else:
                    st.info("No public portfolio data available")

                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown("<div class='section-title'>Performance Insights</div>", unsafe_allow_html=True)
                st.write(f"**Success rate:** {insights['win_rate']:.1f}% 📊")
                st.write(f"**Trend:** {insights['trend_text']}")
                st.write(f"**Sector strength:** {insights['category_text']}")
                st.write(f"**Risk level:** {insights['risk_text']}")
                st.markdown("</div>", unsafe_allow_html=True)

# =============================
# SETTINGS
# =============================
elif st.session_state.page == "Settings":
    st.subheader("Account Settings")

    visibility = get_user_visibility(user)
    st.write(f"Current visibility: **{visibility.title()}**")
    st.write(f"**Your user ID:** `{get_user_id(user)}`")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🌍 Make Public"):
            set_user_visibility(user, "public")
            st.success("Profile set to public")
            st.rerun()

    with col2:
        if st.button("🔒 Make Private"):
            set_user_visibility(user, "private")
            st.success("Profile set to private")
            st.rerun()

# =============================
# HISTORY
# =============================
elif st.session_state.page == "History":
    st.subheader("Trade History")

    current_sales = get_current_sales()
    if current_sales:
        sales_df = pd.DataFrame(current_sales)
        st.markdown("### Sales History")
        st.dataframe(sales_df, use_container_width=True)
    else:
        st.info("No sales yet")

    st.markdown("### Current Portfolio Snapshot")
    if not portfolio_df.empty:
        st.dataframe(portfolio_df, use_container_width=True)
    else:
        st.info("No trades yet")