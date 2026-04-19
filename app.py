import streamlit as st
import json
import os
import hashlib
import yfinance as yf
import pandas as pd
from datetime import datetime

# =============================
# CONFIG
# =============================
st.set_page_config(
    page_title="TradeFlow",
    layout="wide",
    initial_sidebar_state="collapsed"
)

USERS_FILE = "users.json"
PORTFOLIO_FILE = "portfolio_data.json"
HISTORY_FILE = "portfolio_history.json"
SALES_FILE = "sales_history.json"

# =============================
# STYLING
# =============================
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #eef3fb 0%, #e4ecf8 100%);
    }

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 1.2rem;
    }

    /* Hide sidebar on login screen feel */
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
        font-weight: 700;
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
        font-weight: 600;
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
        font-size: 1.4rem;
        font-weight: 700;
        color: #102a43;
        margin-bottom: 12px;
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
    .icon-purple { background: #7c3aed; }
    .icon-gold { background: #d4a72c; }
    .icon-green { background: #089981; }

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
        object-fit: contain;
        background: white;
        border: 1px solid #e6edf5;
        padding: 3px;
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

    .stDataFrame, .stTable {
        font-size: 0.9rem;
    }

    /* LOGIN PAGE */
    .auth-shell {
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1.5rem 0;
    }

    .auth-grid {
        width: 100%;
        max-width: 1180px;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 28px;
        align-items: stretch;
    }

    .auth-left {
        position: relative;
        overflow: hidden;
        border-radius: 28px;
        padding: 42px 34px;
        background:
            linear-gradient(180deg, rgba(255,255,255,0.55), rgba(255,255,255,0.35)),
            linear-gradient(135deg, #edf3ff 0%, #dde8fb 100%);
        border: 1px solid rgba(255,255,255,0.75);
        box-shadow: 0 18px 50px rgba(16, 42, 67, 0.10);
        min-height: 720px;
    }

    .auth-left::after {
        content: "";
        position: absolute;
        inset: 0;
        background:
            linear-gradient(to right, rgba(31,100,255,0.06) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(31,100,255,0.06) 1px, transparent 1px);
        background-size: 40px 40px;
        opacity: 0.45;
        pointer-events: none;
    }

    .auth-chart {
        position: absolute;
        left: 0;
        right: 0;
        bottom: 0;
        height: 55%;
        opacity: 0.22;
        pointer-events: none;
    }

    .chart-line {
        position: absolute;
        left: 4%;
        right: 4%;
        bottom: 16%;
        height: 3px;
        background: linear-gradient(90deg, #7aa7ff, #2f5bea);
        transform: rotate(-18deg);
        border-radius: 999px;
        box-shadow: 0 0 18px rgba(47,91,234,0.18);
    }

    .chart-dot {
        position: absolute;
        width: 14px;
        height: 14px;
        border-radius: 50%;
        background: #7aa7ff;
        box-shadow: 0 0 0 5px rgba(122,167,255,0.15);
    }

    .c1 { left: 6%; bottom: 6%; }
    .c2 { left: 19%; bottom: 14%; }
    .c3 { left: 33%; bottom: 10%; }
    .c4 { left: 47%; bottom: 22%; }
    .c5 { left: 60%; bottom: 17%; }
    .c6 { left: 74%; bottom: 31%; }
    .c7 { left: 88%; bottom: 46%; }

    .candle {
        position: absolute;
        bottom: 0;
        width: 12px;
        border-radius: 10px;
        opacity: 0.30;
    }

    .green { background: linear-gradient(180deg, #7de3c8 0%, #12b886 100%); }
    .red { background: linear-gradient(180deg, #ffc3cc 0%, #ef4444 100%); }

    .ca1 { left: 8%; height: 80px; }
    .ca2 { left: 16%; height: 130px; }
    .ca3 { left: 24%; height: 90px; }
    .ca4 { left: 34%; height: 170px; }
    .ca5 { left: 44%; height: 110px; }
    .ca6 { left: 54%; height: 190px; }
    .ca7 { left: 64%; height: 150px; }
    .ca8 { left: 74%; height: 220px; }
    .ca9 { left: 84%; height: 250px; }

    .ticker-bar {
        background: linear-gradient(180deg, #031b4e 0%, #02153c 100%);
        border-radius: 20px;
        padding: 14px 18px;
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        margin-bottom: 34px;
        box-shadow: 0 8px 24px rgba(16, 42, 67, 0.14);
    }

    .ticker-item {
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        font-weight: 700;
        font-size: 0.98rem;
    }

    .ticker-up { color: #12d39a; }
    .ticker-down { color: #ff5f73; }

    .brand-logo {
        font-size: 3.2rem;
        font-weight: 900;
        color: #1f64ff;
        line-height: 1;
        margin-bottom: 8px;
        position: relative;
        z-index: 2;
    }

    .brand-name {
        font-size: 3.5rem;
        font-weight: 900;
        line-height: 1;
        color: #102a43;
        margin-bottom: 8px;
        position: relative;
        z-index: 2;
    }

    .brand-name span {
        color: #1f64ff;
    }

    .brand-tag {
        font-size: 1rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        color: #2f5bea;
        margin-bottom: 44px;
        position: relative;
        z-index: 2;
    }

    .hero-title {
        font-size: 4rem;
        line-height: 1.04;
        font-weight: 900;
        color: #102a43;
        margin-bottom: 18px;
        position: relative;
        z-index: 2;
    }

    .hero-title span {
        color: #2f5bea;
    }

    .hero-sub {
        font-size: 1.35rem;
        color: #486581;
        max-width: 500px;
        margin-bottom: 34px;
        position: relative;
        z-index: 2;
    }

    .feature-list {
        display: grid;
        gap: 18px;
        position: relative;
        z-index: 2;
    }

    .feature-item {
        display: flex;
        align-items: flex-start;
        gap: 16px;
    }

    .feature-icon {
        width: 62px;
        height: 62px;
        border-radius: 18px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.6rem;
        font-weight: 800;
        flex-shrink: 0;
    }

    .feature-blue { background: #dce7ff; color: #2f5bea; }
    .feature-green { background: #dcf7ef; color: #12b886; }
    .feature-purple { background: #ece6ff; color: #7c3aed; }

    .feature-title {
        font-size: 1.55rem;
        font-weight: 800;
        color: #102a43;
        margin-bottom: 2px;
    }

    .feature-sub {
        font-size: 1.1rem;
        color: #486581;
    }

    .auth-right {
        background: rgba(255,255,255,0.88);
        border: 1px solid rgba(255,255,255,0.85);
        border-radius: 28px;
        padding: 34px 28px 0 28px;
        box-shadow: 0 18px 50px rgba(16, 42, 67, 0.10);
        backdrop-filter: blur(8px);
        display: flex;
        flex-direction: column;
        min-height: 720px;
    }

    .auth-pill {
        background: #dde5f3;
        border-radius: 999px;
        padding: 6px;
        display: flex;
        gap: 6px;
        margin: 0 auto 26px auto;
        width: fit-content;
    }

    .auth-pill-active {
        background: linear-gradient(135deg, #1f64ff 0%, #1456eb 100%);
        color: white;
        border-radius: 999px;
        padding: 12px 28px;
        font-weight: 800;
    }

    .auth-pill-inactive {
        color: #4a5d7a;
        padding: 12px 28px;
        font-weight: 800;
    }

    .auth-title {
        font-size: 2.8rem;
        line-height: 1.1;
        font-weight: 900;
        color: #102a43;
        text-align: center;
        margin-bottom: 10px;
    }

    .auth-subtitle {
        text-align: center;
        color: #627d98;
        font-size: 1.25rem;
        margin-bottom: 22px;
    }

    .mini-market {
        background: #e8eefb;
        border-radius: 20px;
        padding: 18px 20px;
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 14px;
        margin-bottom: 22px;
    }

    .mini-stock {
        text-align: center;
    }

    .mini-stock-name {
        font-size: 1.05rem;
        font-weight: 800;
        color: #102a43;
    }

    .mini-stock-price {
        font-size: 1.9rem;
        font-weight: 900;
        color: #102a43;
    }

    .mini-stock-change-up {
        color: #12b886;
        font-weight: 800;
        font-size: 1rem;
    }

    .mini-stock-change-down {
        color: #ef4444;
        font-weight: 800;
        font-size: 1rem;
    }

    .auth-form-label {
        font-size: 1rem;
        font-weight: 800;
        color: #344966;
        margin-bottom: 6px;
        margin-top: 8px;
    }

    .auth-footer-box {
        margin-top: auto;
        background: linear-gradient(180deg, #031b4e 0%, #02153c 100%);
        color: white;
        border-bottom-left-radius: 28px;
        border-bottom-right-radius: 28px;
        margin-left: -28px;
        margin-right: -28px;
        padding: 26px 28px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
    }

    .auth-footer-title {
        font-size: 1.35rem;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .auth-footer-sub {
        font-size: 1rem;
        color: #c8d6ea;
    }

    .auth-lock {
        font-size: 2rem;
        font-weight: 800;
    }

    .auth-note {
        text-align: center;
        color: #627d98;
        margin-top: 16px;
        margin-bottom: 20px;
        font-size: 1rem;
    }

    .stRadio > div {
        gap: 0.5rem;
    }

    .stTextInput > div > div > input,
    .stPasswordInput > div > div > input {
        border-radius: 14px !important;
        padding-top: 0.9rem !important;
        padding-bottom: 0.9rem !important;
    }

    @media (max-width: 900px) {
        .auth-grid {
            grid-template-columns: 1fr;
        }

        .auth-left {
            min-height: auto;
            padding: 24px 20px 220px 20px;
        }

        .auth-right {
            min-height: auto;
        }

        .ticker-bar {
            grid-template-columns: repeat(2, 1fr);
        }

        .hero-title {
            font-size: 2.4rem;
        }

        .brand-name {
            font-size: 2.5rem;
        }

        .auth-title {
            font-size: 2rem;
        }

        .mini-market {
            grid-template-columns: 1fr;
        }
    }

    @media (max-width: 768px) {
        .block-container {
            padding-top: 0.8rem;
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
        .metric-card {
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

        .feature-title {
            font-size: 1.2rem;
        }

        .feature-sub,
        .hero-sub,
        .auth-subtitle {
            font-size: 1rem;
        }

        .hero-title {
            font-size: 2rem;
        }

        .auth-footer-box {
            flex-direction: column;
            align-items: flex-start;
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
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

users = load_json(USERS_FILE, {})
portfolios = load_json(PORTFOLIO_FILE, {})
history = load_json(HISTORY_FILE, {})
sales_history = load_json(SALES_FILE, {})

@st.cache_data(ttl=60)
def get_price(ticker):
    try:
        data = yf.Ticker(ticker).history(period="5d")
        if data.empty:
            return None
        return float(data["Close"].iloc[-1])
    except Exception:
        return None

@st.cache_data(ttl=300)
def get_price_and_change(ticker):
    try:
        data = yf.Ticker(ticker).history(period="5d")
        if data.empty:
            return None, None
        close = data["Close"].dropna()
        current = float(close.iloc[-1])
        previous = float(close.iloc[-2]) if len(close) > 1 else current
        pct_change = ((current - previous) / previous) * 100 if previous else 0
        return current, pct_change
    except Exception:
        return None, None

@st.cache_data(ttl=86400)
def load_stock_universe():
    nasdaq_url = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
    other_url = "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"

    try:
        nasdaq_df = pd.read_csv(nasdaq_url, sep="|")
        other_df = pd.read_csv(other_url, sep="|")

        nasdaq_df = nasdaq_df[nasdaq_df["Symbol"] != "File Creation Time"]
        other_df = other_df[other_df["ACT Symbol"] != "File Creation Time"]

        nasdaq_df = nasdaq_df[["Symbol", "Security Name"]].copy()
        nasdaq_df.columns = ["Ticker", "Name"]

        other_df = other_df[["ACT Symbol", "Security Name"]].copy()
        other_df.columns = ["Ticker", "Name"]

        stocks_df = pd.concat([nasdaq_df, other_df], ignore_index=True)
        stocks_df["Ticker"] = stocks_df["Ticker"].astype(str).str.upper().str.strip()
        stocks_df["Name"] = stocks_df["Name"].astype(str).str.strip()
        stocks_df = stocks_df.drop_duplicates(subset=["Ticker"])
        stocks_df = stocks_df[stocks_df["Ticker"].str.len() > 0]

        return stocks_df.sort_values("Ticker").reset_index(drop=True)
    except Exception:
        return pd.DataFrame(columns=["Ticker", "Name"])

stocks_df = load_stock_universe()
company_names = dict(zip(stocks_df["Ticker"], stocks_df["Name"]))

logo_domains = {
    "AAPL": "apple.com",
    "TSLA": "tesla.com",
    "NVDA": "nvidia.com",
    "GOOGL": "google.com",
    "MSFT": "microsoft.com",
    "AMZN": "amazon.com",
    "META": "meta.com",
    "NFLX": "netflix.com",
    "UBER": "uber.com",
    "SPOT": "spotify.com"
}

def get_logo_url(ticker):
    domain = logo_domains.get(ticker)
    if domain:
        return f"https://logo.clearbit.com/{domain}"
    return None

# =============================
# SESSION
# =============================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = ""
if "selected_portfolio" not in st.session_state:
    st.session_state.selected_portfolio = None
if "page" not in st.session_state:
    st.session_state.page = "Home"

# =============================
# LOGIN
# =============================
def login_page():
    st.markdown("""
    <div class="auth-shell">
        <div class="auth-grid">
            <div class="auth-left">
                <div class="ticker-bar">
                    <div class="ticker-item">AAPL <span>$192.33</span> <span class="ticker-up">▲ 1.24%</span></div>
                    <div class="ticker-item">TSLA <span>$245.12</span> <span class="ticker-down">▼ -0.87%</span></div>
                    <div class="ticker-item">NVDA <span>$875.44</span> <span class="ticker-up">▲ 2.58%</span></div>
                    <div class="ticker-item">SPY <span>$528.19</span> <span class="ticker-up">▲ 0.31%</span></div>
                </div>

                <div class="brand-logo">📈</div>
                <div class="brand-name">Trade<span>Flow</span></div>
                <div class="brand-tag">TRACK. TRADE. GROW.</div>

                <div class="hero-title">Your Portfolio.<br><span>Your Advantage.</span></div>
                <div class="hero-sub">
                    Track stocks, manage trades, and see your performance all in one place.
                </div>

                <div class="feature-list">
                    <div class="feature-item">
                        <div class="feature-icon feature-blue">📊</div>
                        <div>
                            <div class="feature-title">Real-Time Prices</div>
                            <div class="feature-sub">Stay updated with live market data</div>
                        </div>
                    </div>

                    <div class="feature-item">
                        <div class="feature-icon feature-green">📈</div>
                        <div>
                            <div class="feature-title">Smart Tracking</div>
                            <div class="feature-sub">Monitor your investments easily</div>
                        </div>
                    </div>

                    <div class="feature-item">
                        <div class="feature-icon feature-purple">🕘</div>
                        <div>
                            <div class="feature-title">Trade History</div>
                            <div class="feature-sub">Review and learn from every move</div>
                        </div>
                    </div>
                </div>

                <div class="auth-chart">
                    <div class="chart-line"></div>
                    <div class="chart-dot c1"></div>
                    <div class="chart-dot c2"></div>
                    <div class="chart-dot c3"></div>
                    <div class="chart-dot c4"></div>
                    <div class="chart-dot c5"></div>
                    <div class="chart-dot c6"></div>
                    <div class="chart-dot c7"></div>

                    <div class="candle green ca1"></div>
                    <div class="candle red ca2"></div>
                    <div class="candle green ca3"></div>
                    <div class="candle green ca4"></div>
                    <div class="candle red ca5"></div>
                    <div class="candle green ca6"></div>
                    <div class="candle red ca7"></div>
                    <div class="candle green ca8"></div>
                    <div class="candle green ca9"></div>
                </div>
            </div>
    """, unsafe_allow_html=True)

    mode = st.radio("Account", ["Login", "Register"], horizontal=True, label_visibility="collapsed")

    st.markdown("""
            <div class="auth-right">
    """, unsafe_allow_html=True)

    if mode == "Login":
        st.markdown("""
            <div class="auth-pill">
                <div class="auth-pill-active">Login</div>
                <div class="auth-pill-inactive">Register</div>
            </div>
        """, unsafe_allow_html=True)
        title_text = "Welcome back"
        subtitle_text = "Sign in to access your dashboard"
    else:
        st.markdown("""
            <div class="auth-pill">
                <div class="auth-pill-inactive">Login</div>
                <div class="auth-pill-active">Register</div>
            </div>
        """, unsafe_allow_html=True)
        title_text = "Create your account"
        subtitle_text = "Start tracking your portfolio with TradeFlow"

    st.markdown(f"""
        <div class="auth-title">{title_text}</div>
        <div class="auth-subtitle">{subtitle_text}</div>
        <div class="mini-market">
            <div class="mini-stock">
                <div class="mini-stock-name">AAPL</div>
                <div class="mini-stock-price">$192.33</div>
                <div class="mini-stock-change-up">▲ 1.24%</div>
            </div>
            <div class="mini-stock">
                <div class="mini-stock-name">TSLA</div>
                <div class="mini-stock-price">$245.12</div>
                <div class="mini-stock-change-down">▼ -0.87%</div>
            </div>
            <div class="mini-stock">
                <div class="mini-stock-name">NVDA</div>
                <div class="mini-stock-price">$875.44</div>
                <div class="mini-stock-change-up">▲ 2.58%</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="auth-form-label">USERNAME</div>', unsafe_allow_html=True)
    username = st.text_input(
        "Username",
        placeholder="Enter your username",
        label_visibility="collapsed",
        key="auth_username"
    )

    st.markdown('<div class="auth-form-label">PASSWORD</div>', unsafe_allow_html=True)
    password = st.text_input(
        "Password",
        type="password",
        placeholder="Enter your password",
        label_visibility="collapsed",
        key="auth_password"
    )

    if mode == "Register":
        if st.button("Create Account", key="register_button"):
            if username in users:
                st.error("User already exists")
            elif not username or not password:
                st.error("Enter a username and password")
            else:
                users[username] = hash_password(password)
                save_json(USERS_FILE, users)

                portfolios[username] = {"Main": []}
                history[username] = {"Main": []}
                sales_history[username] = {"Main": []}

                save_json(PORTFOLIO_FILE, portfolios)
                save_json(HISTORY_FILE, history)
                save_json(SALES_FILE, sales_history)

                st.success("Account created. You can log in now.")

    if mode == "Login":
        if st.button("Login to TradeFlow", key="login_button"):
            if username in users and users[username] == hash_password(password):
                st.session_state.logged_in = True
                st.session_state.user = username

                if username not in portfolios:
                    portfolios[username] = {"Main": []}
                elif isinstance(portfolios[username], list):
                    portfolios[username] = {"Main": portfolios[username]}

                if username not in history:
                    history[username] = {"Main": []}
                elif isinstance(history[username], list):
                    history[username] = {"Main": history[username]}

                if username not in sales_history:
                    sales_history[username] = {"Main": []}
                elif isinstance(sales_history[username], list):
                    sales_history[username] = {"Main": sales_history[username]}

                save_json(PORTFOLIO_FILE, portfolios)
                save_json(HISTORY_FILE, history)
                save_json(SALES_FILE, sales_history)

                portfolio_names = list(portfolios[username].keys())
                st.session_state.selected_portfolio = portfolio_names[0] if portfolio_names else "Main"
                st.rerun()
            else:
                st.error("Invalid login")

    st.markdown("""
        <div class="auth-note">New to TradeFlow? Create your account and start tracking smarter.</div>

        <div class="auth-footer-box">
            <div>
                <div class="auth-footer-title">Secure & Private</div>
                <div class="auth-footer-sub">Your data is encrypted and protected</div>
            </div>
            <div class="auth-lock">🔒</div>
        </div>
    </div>
    </div>
    </div>
    """, unsafe_allow_html=True)

# =============================
# DATA HELPERS
# =============================
def get_user_portfolios(user):
    if user not in portfolios:
        portfolios[user] = {"Main": []}
    elif isinstance(portfolios[user], list):
        portfolios[user] = {"Main": portfolios[user]}
    return portfolios[user]

def get_current_portfolio():
    user = st.session_state.user
    current_name = st.session_state.selected_portfolio
    user_portfolios = get_user_portfolios(user)

    if current_name not in user_portfolios:
        user_portfolios[current_name] = []

    return user_portfolios[current_name]

def save_current_portfolio(updated_portfolio):
    user = st.session_state.user
    current_name = st.session_state.selected_portfolio
    user_portfolios = get_user_portfolios(user)
    user_portfolios[current_name] = updated_portfolio
    portfolios[user] = user_portfolios
    save_json(PORTFOLIO_FILE, portfolios)

def get_current_history():
    user = st.session_state.user
    current_name = st.session_state.selected_portfolio

    if user not in history:
        history[user] = {}
    if current_name not in history[user]:
        history[user][current_name] = []

    return history[user][current_name]

def save_current_history(updated_history):
    user = st.session_state.user
    current_name = st.session_state.selected_portfolio
    if user not in history:
        history[user] = {}
    history[user][current_name] = updated_history
    save_json(HISTORY_FILE, history)

def get_current_sales():
    user = st.session_state.user
    current_name = st.session_state.selected_portfolio

    if user not in sales_history:
        sales_history[user] = {}
    if current_name not in sales_history[user]:
        sales_history[user][current_name] = []

    return sales_history[user][current_name]

def save_current_sales(updated_sales):
    user = st.session_state.user
    current_name = st.session_state.selected_portfolio
    if user not in sales_history:
        sales_history[user] = {}
    sales_history[user][current_name] = updated_sales
    save_json(SALES_FILE, sales_history)

def get_portfolio_value(portfolio):
    total = 0.0
    for trade in portfolio:
        current_price = get_price(trade["Ticker"])
        if current_price is not None:
            total += current_price * trade["Shares"]
    return total

def build_portfolio_df(portfolio):
    if not portfolio:
        return pd.DataFrame()

    rows = []
    for idx, trade in enumerate(portfolio):
        current_price = get_price(trade["Ticker"])
        market_value = None
        unrealized = None

        if current_price is not None:
            market_value = current_price * trade["Shares"]
            unrealized = market_value - trade["Amount"]

        rows.append({
            "ID": idx,
            "Ticker": trade["Ticker"],
            "Name": company_names.get(trade["Ticker"], trade["Ticker"]),
            "Amount": round(trade["Amount"], 2),
            "Buy Price": round(trade["Price"], 2),
            "Current Price": round(current_price, 2) if current_price is not None else None,
            "Shares": round(trade["Shares"], 4),
            "Market Value": round(market_value, 2) if market_value is not None else None,
            "Unrealized P/L": round(unrealized, 2) if unrealized is not None else None,
            "Time": trade.get("Time", "Older trade")
        })

    return pd.DataFrame(rows)

def update_history_snapshot():
    current_history = get_current_history()
    current_portfolio = get_current_portfolio()
    current_value_now = get_portfolio_value(current_portfolio)
    now_key = datetime.now().strftime("%Y-%m-%d %H:%M")

    if not current_history or current_history[-1]["time"] != now_key:
        current_history.append({
            "time": now_key,
            "value": current_value_now
        })
        save_current_history(current_history)

# =============================
# APP START
# =============================
if not st.session_state.logged_in:
    login_page()
    st.stop()

user = st.session_state.user
user_portfolios = get_user_portfolios(user)

if not st.session_state.selected_portfolio or st.session_state.selected_portfolio not in user_portfolios:
    st.session_state.selected_portfolio = list(user_portfolios.keys())[0]

update_history_snapshot()
current_portfolio = get_current_portfolio()
portfolio_df = build_portfolio_df(current_portfolio)

# =============================
# SIDEBAR
# =============================
st.sidebar.markdown("## TradeFlow")

page = st.sidebar.radio(
    "Navigation",
    ["Home", "Stock Viewer", "Manage Trades", "History"],
    index=["Home", "Stock Viewer", "Manage Trades", "History"].index(st.session_state.page)
)
st.session_state.page = page

st.sidebar.markdown("---")
st.sidebar.markdown("### Portfolios")

portfolio_names = list(user_portfolios.keys())
selected_portfolio = st.sidebar.radio(
    "Select Portfolio",
    portfolio_names,
    index=portfolio_names.index(st.session_state.selected_portfolio)
)
st.session_state.selected_portfolio = selected_portfolio
current_portfolio = get_current_portfolio()
portfolio_df = build_portfolio_df(current_portfolio)

new_portfolio_name = st.sidebar.text_input("New Portfolio Name").strip()
if st.sidebar.button("Create Portfolio"):
    if not new_portfolio_name:
        st.sidebar.error("Enter a portfolio name")
    elif new_portfolio_name in user_portfolios:
        st.sidebar.error("Portfolio already exists")
    else:
        user_portfolios[new_portfolio_name] = []
        portfolios[user] = user_portfolios
        save_json(PORTFOLIO_FILE, portfolios)

        if user not in history:
            history[user] = {}
        history[user][new_portfolio_name] = []
        save_json(HISTORY_FILE, history)

        if user not in sales_history:
            sales_history[user] = {}
        sales_history[user][new_portfolio_name] = []
        save_json(SALES_FILE, sales_history)

        st.session_state.selected_portfolio = new_portfolio_name
        st.sidebar.success(f"Created {new_portfolio_name}")
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### Quick Add Trade")

search = st.sidebar.text_input("Search Stock").strip()
matches_df = pd.DataFrame()

if search and not stocks_df.empty:
    q = search.upper()
    matches_df = stocks_df[
        stocks_df["Ticker"].str.contains(q, na=False) |
        stocks_df["Name"].str.upper().str.contains(q, na=False)
    ].head(25)
else:
    matches_df = stocks_df.head(25)

options = []
for _, row in matches_df.iterrows():
    t = row["Ticker"]
    name = row["Name"]
    price = get_price(t)

    if price:
        options.append(f"{t} - {name} (${price:.2f})")
    else:
        options.append(f"{t} - {name} (N/A)")

if options:
    selection = st.sidebar.selectbox("Select Stock", options)
    ticker = selection.split(" - ", 1)[0].strip()
else:
    selection = None
    ticker = None
    st.sidebar.warning("No matching stocks found.")

amount = st.sidebar.number_input("Amount ($)", value=100.0)

if st.sidebar.button("Add Trade"):
    if not ticker:
        st.sidebar.error("Choose a stock first.")
    else:
        price = get_price(ticker)

        if price:
            trade = {
                "Ticker": ticker,
                "Amount": float(amount),
                "Price": float(price),
                "Shares": float(amount / price),
                "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            current_portfolio.append(trade)
            save_current_portfolio(current_portfolio)
            st.sidebar.success(f"Added {ticker}")
            st.rerun()
        else:
            st.sidebar.error("Could not fetch price for that stock.")

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.user = ""
    st.session_state.selected_portfolio = None
    st.session_state.page = "Home"
    st.rerun()

# =============================
# HOME PAGE
# =============================
if st.session_state.page == "Home":
    invested = float(portfolio_df["Amount"].sum()) if not portfolio_df.empty else 0.0
    current_value = float(portfolio_df["Market Value"].fillna(0).sum()) if not portfolio_df.empty else 0.0
    unrealized_profit = current_value - invested
    pnl_pct = (unrealized_profit / invested * 100) if invested > 0 else 0.0
    portfolio_count = len(user_portfolios)

    st.markdown(f"<div class='main-title'>Welcome back, {user}</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Here’s how your investments are doing today.</div>", unsafe_allow_html=True)

    row1_col1, row1_col2 = st.columns(2)
    row2_col1, row2_col2 = st.columns(2)

    with row1_col1:
        st.markdown(f"""
        <div class="metric-card metric-blue">
            <div class="metric-label">INVESTED</div>
            <div class="metric-value">${invested:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with row1_col2:
        st.markdown(f"""
        <div class="metric-card metric-green">
            <div class="metric-label">CURRENT VALUE</div>
            <div class="metric-value">${current_value:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with row2_col1:
        color_class = "metric-white"
        pnl_sign = "+" if unrealized_profit >= 0 else ""
        pct_sign = "+" if pnl_pct >= 0 else ""
        st.markdown(f"""
        <div class="metric-card {color_class}">
            <div class="metric-label">PROFIT / LOSS</div>
            <div class="metric-value">{pnl_sign}${unrealized_profit:,.2f}</div>
            <div class="metric-sub">{pct_sign}{pnl_pct:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with row2_col2:
        st.markdown(f"""
        <div class="metric-card metric-blue">
            <div class="metric-label">PORTFOLIOS</div>
            <div class="metric-value">{portfolio_count}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    hist_data = get_current_history()
    hist_df = pd.DataFrame(hist_data)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Portfolio Overview</div>", unsafe_allow_html=True)
    if not hist_df.empty:
        st.line_chart(hist_df.set_index("time")["value"], use_container_width=True)
    else:
        st.info("No portfolio history yet")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    left, right = st.columns([1.15, 0.85], gap="large")

    with left:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Your Portfolios</div>", unsafe_allow_html=True)

        icon_classes = ["icon-blue", "icon-purple", "icon-gold", "icon-green"]

        for i, (p_name, p_trades) in enumerate(user_portfolios.items()):
            p_df = build_portfolio_df(p_trades)
            p_invested = float(p_df["Amount"].sum()) if not p_df.empty else 0.0
            p_current = float(p_df["Market Value"].fillna(0).sum()) if not p_df.empty else 0.0
            p_profit = p_current - p_invested
            p_pct = (p_profit / p_invested * 100) if p_invested > 0 else 0.0
            holdings = len(p_trades)

            pct_class = "portfolio-pct-up" if p_pct >= 0 else "portfolio-pct-down"
            pct_sign = "+" if p_pct >= 0 else ""
            money_sign = "+" if p_profit >= 0 else ""

            st.markdown(f"""
            <div class="portfolio-row">
                <div class="portfolio-left">
                    <div class="portfolio-icon {icon_classes[i % len(icon_classes)]}">
                        {p_name[:1].upper()}
                    </div>
                    <div>
                        <div class="portfolio-name">{p_name}</div>
                        <div class="portfolio-meta">{holdings} holdings</div>
                    </div>
                </div>
                <div class="portfolio-value">
                    <div class="portfolio-money">${p_current:,.2f}</div>
                    <div class="{pct_class}">{money_sign}${p_profit:,.2f} • {pct_sign}{p_pct:.2f}%</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Watchlist</div>", unsafe_allow_html=True)

        watchlist = ["AAPL", "TSLA", "NVDA", "GOOGL", "MSFT"]

        for ticker in watchlist:
            price, change = get_price_and_change(ticker)
            name = company_names.get(ticker, ticker)
            logo_url = get_logo_url(ticker)
            change_class = "watch-change-up" if (change is not None and change >= 0) else "watch-change-down"
            change_sign = "+" if (change is not None and change >= 0) else ""

            if logo_url:
                logo_html = f"<img class='watch-logo' src='{logo_url}' onerror=\"this.style.display='none'\">"
            else:
                logo_html = f"<div class='watch-logo'>{ticker[:1]}</div>"

            price_text = f"${price:,.2f}" if price is not None else "N/A"
            change_text = f"{change_sign}{change:.2f}%" if change is not None else "N/A"

            st.markdown(f"""
            <div class="watch-row">
                <div class="watch-left">
                    {logo_html}
                    <div>
                        <div class="watch-name">{ticker}</div>
                        <div class="watch-sub">{name}</div>
                    </div>
                </div>
                <div class="watch-price">
                    <div>{price_text}</div>
                    <div class="{change_class}">{change_text}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.subheader("Recent Trades")
    if not portfolio_df.empty:
        recent_df = portfolio_df.sort_values("Time", ascending=False).head(8)
        st.dataframe(
            recent_df[["Ticker", "Name", "Shares", "Buy Price", "Amount", "Time"]],
            use_container_width=True
        )
    else:
        st.info("No trades yet in this portfolio")
 =============================

# =============================
# STOCK VIEWER PAGE
# =============================
elif st.session_state.page == "Stock Viewer":
    st.subheader("Stock Viewer")

    chart_search = st.text_input("Search stock (e.g. Tesla or AAPL)")
    chart_matches = pd.DataFrame()

    if chart_search and not stocks_df.empty:
        q = chart_search.strip().upper()
        chart_matches = stocks_df[
            stocks_df["Ticker"].str.contains(q, na=False) |
            stocks_df["Name"].str.upper().str.contains(q, na=False)
        ].head(25)

    if not chart_matches.empty:
        chart_options = [f"{row.Ticker} - {row.Name}" for _, row in chart_matches.iterrows()]
        chart_selection = st.selectbox("Choose stock", chart_options)
        chart_ticker = chart_selection.split(" - ", 1)[0].strip()
        chart_name = company_names.get(chart_ticker, chart_ticker)

        chart_data = yf.Ticker(chart_ticker).history(period="6mo")
        current_price = get_price(chart_ticker)

        st.write(f"Showing: {chart_ticker} - {chart_name}")

        if not chart_data.empty:
            st.line_chart(chart_data["Close"], use_container_width=True)
        else:
            st.error("No chart data found.")

        if current_price is not None:
            st.write(f"Current price: ${current_price:.2f}")

            buy_col, sell_col = st.columns(2)

            with buy_col:
                st.markdown("### Buy")
                buy_amount = st.number_input(
                    f"Buy amount for {chart_ticker} ($)",
                    min_value=1.0,
                    value=100.0,
                    step=10.0,
                    key=f"buy_amount_{chart_ticker}"
                )

                if st.button(f"Buy {chart_ticker}", key=f"buy_btn_{chart_ticker}"):
                    buy_trade = {
                        "Ticker": chart_ticker,
                        "Amount": float(buy_amount),
                        "Price": float(current_price),
                        "Shares": float(buy_amount / current_price),
                        "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }

                    current_portfolio.append(buy_trade)
                    save_current_portfolio(current_portfolio)
                    st.success(f"Bought {chart_ticker} for ${buy_amount:.2f}")
                    st.rerun()

            with sell_col:
                st.markdown("### Sell")

                owned_trades = [
                    (i, t) for i, t in enumerate(current_portfolio)
                    if t["Ticker"] == chart_ticker
                ]

                if owned_trades:
                    sell_options = [
                        f"ID {i} | {t['Shares']:.4f} shares | bought at ${t['Price']:.2f} | {t.get('Time', 'Older trade')}"
                        for i, t in owned_trades
                    ]

                    selected_sell = st.selectbox(
                        f"Select {chart_ticker} trade to sell",
                        sell_options,
                        key=f"sell_select_{chart_ticker}"
                    )

                    selected_id = int(selected_sell.split("|")[0].replace("ID", "").strip())
                    selected_trade = current_portfolio[selected_id]
                    max_shares = float(selected_trade["Shares"])

                    sell_shares = st.number_input(
                        f"Shares to sell ({chart_ticker})",
                        min_value=0.0001,
                        max_value=max_shares,
                        value=max_shares,
                        step=0.0001,
                        format="%.4f",
                        key=f"sell_shares_{chart_ticker}"
                    )

                    estimated_sale_value = sell_shares * current_price
                    estimated_cost_basis = sell_shares * float(selected_trade["Price"])
                    estimated_pl = estimated_sale_value - estimated_cost_basis

                    st.write(f"Sale value: ${estimated_sale_value:.2f}")

                    if estimated_pl >= 0:
                        st.success(f"Estimated profit: ${estimated_pl:.2f}")
                    else:
                        st.error(f"Estimated loss: ${abs(estimated_pl):.2f}")

                    if st.button(f"Sell {chart_ticker}", key=f"sell_btn_{chart_ticker}"):
                        realized_sale_value = sell_shares * current_price
                        realized_cost_basis = sell_shares * float(selected_trade["Price"])
                        realized_pl = realized_sale_value - realized_cost_basis

                        sale_record = {
                            "Ticker": chart_ticker,
                            "Shares Sold": round(sell_shares, 4),
                            "Sell Price": round(current_price, 2),
                            "Sale Value": round(realized_sale_value, 2),
                            "Cost Basis": round(realized_cost_basis, 2),
                            "Realized P/L": round(realized_pl, 2),
                            "Sold At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }

                        remaining_shares = selected_trade["Shares"] - sell_shares

                        if remaining_shares <= 0.0000001:
                            current_portfolio.pop(selected_id)
                        else:
                            current_portfolio[selected_id]["Shares"] = remaining_shares
                            current_portfolio[selected_id]["Amount"] = remaining_shares * float(selected_trade["Price"])

                        save_current_portfolio(current_portfolio)

                        current_sales = get_current_sales()
                        current_sales.append(sale_record)
                        save_current_sales(current_sales)

                        st.success(f"Sold {sell_shares:.4f} shares of {chart_ticker}")
                        st.rerun()
                else:
                    st.info(f"You do not own any {chart_ticker} trades in this portfolio.")
        else:
            st.error("Could not fetch current price.")
    elif chart_search:
        st.warning("No matching stocks found.")

# =============================
# MANAGE TRADES PAGE
# =============================
elif st.session_state.page == "Manage Trades":
    st.subheader(f"Manage Trades - {st.session_state.selected_portfolio}")

    if not portfolio_df.empty:
        st.dataframe(portfolio_df, use_container_width=True)

        trade_labels = [
            f"ID {row['ID']} | {row['Ticker']} | {row['Shares']:.4f} shares | bought {row['Time']}"
            for _, row in portfolio_df.iterrows()
        ]

        selected_label = st.selectbox("Select a trade", trade_labels)
        selected_id = int(selected_label.split("|")[0].replace("ID", "").strip())
        selected_trade = current_portfolio[selected_id]
        selected_current_price = get_price(selected_trade["Ticker"]) or 0.0

        c1, c2 = st.columns(2)

        with c1:
            st.markdown("### Delete Trade")
            if st.button("Delete Selected Trade"):
                deleted = current_portfolio.pop(selected_id)
                save_current_portfolio(current_portfolio)
                st.success(f"Deleted {deleted['Ticker']} trade")
                st.rerun()

        with c2:
            st.markdown("### Sell Trade")
            max_shares = float(selected_trade["Shares"])
            sell_shares = st.number_input(
                "Shares to sell",
                min_value=0.0001,
                max_value=max_shares,
                value=max_shares,
                step=0.0001,
                format="%.4f",
                key=f"manage_sell_{selected_id}"
            )

            avg_buy_price = float(selected_trade["Price"])
            estimated_sale_value = sell_shares * selected_current_price
            estimated_cost_basis = sell_shares * avg_buy_price
            estimated_pl = estimated_sale_value - estimated_cost_basis

            st.write(f"Current price: ${selected_current_price:.2f}")
            st.write(f"Estimated sale value: ${estimated_sale_value:.2f}")

            if estimated_pl >= 0:
                st.success(f"Estimated realized profit: ${estimated_pl:.2f}")
            else:
                st.error(f"Estimated realized loss: ${abs(estimated_pl):.2f}")

            if st.button("Sell Selected Shares"):
                realized_sale_value = sell_shares * selected_current_price
                realized_cost_basis = sell_shares * avg_buy_price
                realized_pl = realized_sale_value - realized_cost_basis

                sale_record = {
                    "Ticker": selected_trade["Ticker"],
                    "Shares Sold": round(sell_shares, 4),
                    "Sell Price": round(selected_current_price, 2),
                    "Sale Value": round(realized_sale_value, 2),
                    "Cost Basis": round(realized_cost_basis, 2),
                    "Realized P/L": round(realized_pl, 2),
                    "Sold At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                remaining_shares = selected_trade["Shares"] - sell_shares
                if remaining_shares <= 0.0000001:
                    current_portfolio.pop(selected_id)
                else:
                    current_portfolio[selected_id]["Shares"] = remaining_shares
                    current_portfolio[selected_id]["Amount"] = remaining_shares * avg_buy_price

                save_current_portfolio(current_portfolio)

                current_sales = get_current_sales()
                current_sales.append(sale_record)
                save_current_sales(current_sales)

                st.success(f"Sold {sell_shares:.4f} shares of {selected_trade['Ticker']}")
                st.rerun()
    else:
        st.info("No trades yet in this portfolio")

# =============================
# HISTORY PAGE
# =============================
elif st.session_state.page == "History":
    st.subheader(f"History - {st.session_state.selected_portfolio}")

    current_sales = get_current_sales()
    if current_sales:
        st.markdown("### Sales History")
        sales_df = pd.DataFrame(current_sales)
        st.dataframe(sales_df, use_container_width=True)

        total_realized = float(sales_df["Realized P/L"].sum())
        if total_realized >= 0:
            st.success(f"Total Realized Profit/Loss: ${total_realized:.2f}")
        else:
            st.error(f"Total Realized Profit/Loss: ${total_realized:.2f}")
    else:
        st.info("No sales yet in this portfolio")

    st.markdown("### Portfolio History")
    current_history = get_current_history()
    df_hist = pd.DataFrame(current_history)
    if not df_hist.empty:
        st.line_chart(df_hist.set_index("time")["value"], use_container_width=True)
    else:
        st.info("No portfolio history yet")