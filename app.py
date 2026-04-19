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
st.set_page_config(page_title="Trading Dashboard", layout="wide")

USERS_FILE = "users.json"
PORTFOLIO_FILE = "portfolio_data.json"
HISTORY_FILE = "portfolio_history.json"

# =============================
# SECURITY
# =============================
def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

# =============================
# LOAD / SAVE USERS
# =============================
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

users = load_users()

# =============================
# LOAD / SAVE PORTFOLIO
# =============================
def load_portfolios():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_portfolios(data):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

portfolios = load_portfolios()

# =============================
# LOAD / SAVE HISTORY
# =============================
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_history(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

history = load_history()

# =============================
# PRICE FETCH
# =============================
@st.cache_data(ttl=60)
def get_price(ticker):
    try:
        data = yf.Ticker(ticker).history(period="5d")
        if data.empty:
            return None
        return float(data["Close"].iloc[-1])
    except:
        return None

# =============================
# SESSION STATE
# =============================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = ""
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

# =============================
# LOGIN SYSTEM
# =============================
def login_page():
    st.title("Login System")

    mode = st.radio("Choose", ["Login", "Register"])

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if mode == "Register":
        if st.button("Create Account"):
            if username in users:
                st.error("User already exists")
            else:
                users[username] = hash_password(password)
                save_users(users)
                st.success("Account created!")

    if mode == "Login":
        if st.button("Login"):
            if username in users and users[username] == hash_password(password):
                st.session_state.logged_in = True
                st.session_state.user = username
                st.session_state.portfolio = portfolios.get(username, [])
                st.rerun()
            else:
                st.error("Invalid login")

# =============================
# APP START
# =============================
if not st.session_state.logged_in:
    login_page()
    st.stop()

st.title("🚀 Trading Dashboard")
st.write(f"Welcome {st.session_state.user}")

if st.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# =============================
# STOCK CHART VIEWER (NEW ADDITION)
# =============================
st.subheader("📈 Stock Chart Viewer")

chart_ticker = st.text_input("Enter ticker for chart (e.g. AAPL)")

if chart_ticker:
    data = yf.Ticker(chart_ticker).history(period="6mo")

    if not data.empty:
        st.line_chart(data["Close"])
    else:
        st.error("No data found for this ticker")

# =============================
# STOCK DATA
# =============================
company_names = {
    "AAPL": "Apple Inc",
    "AMZN": "Amazon.com Inc",
    "AMD": "Advanced Micro Devices Inc",
    "MSFT": "Microsoft Corp",
    "META": "Meta Platforms Inc",
    "TSLA": "Tesla Inc",
    "GOOGL": "Alphabet Inc",
    "NVDA": "NVIDIA Corp",
    "NFLX": "Netflix Inc",
    "INTC": "Intel Corp",
    "UBER": "Uber Technologies Inc",
    "DIS": "Walt Disney Co",
    "SHOP": "Shopify Inc",
    "PYPL": "PayPal Holdings Inc",
    "BABA": "Alibaba Group"
}

popular = list(company_names.keys())

# =============================
# ADD TRADE
# =============================
st.sidebar.header("Add Trade")

search = st.sidebar.text_input("Search Stock").upper()
matches = [t for t in popular if t.startswith(search)] if search else popular

options = []

for t in matches:
    price = get_price(t)
    name = company_names.get(t, "Unknown")

    if price:
        options.append(f"{t} — {name} (${price:.2f})")
    else:
        options.append(f"{t} — {name} (N/A)")

selection = st.sidebar.selectbox("Select Stock", options)
ticker = selection.split(" — ")[0]

amount = st.sidebar.number_input("Amount ($)", value=100.0)

if st.sidebar.button("Add Trade"):
    price = get_price(ticker)

    if price:
        trade = {
            "Ticker": ticker,
            "Amount": amount,
            "Price": price,
            "Shares": amount / price
        }

        st.session_state.portfolio.append(trade)

        portfolios[st.session_state.user] = st.session_state.portfolio
        save_portfolios(portfolios)

        st.success(f"Added {ticker}")

# =============================
# PORTFOLIO VALUE
# =============================
def get_portfolio_value(portfolio):
    total = 0
    for p in portfolio:
        price = get_price(p["Ticker"])
        if price:
            total += price * p["Shares"]
    return total

# =============================
# PORTFOLIO DISPLAY
# =============================
st.subheader("Portfolio")

df = pd.DataFrame(st.session_state.portfolio)

if not df.empty:
    st.dataframe(df)

    invested = df["Amount"].sum()
    current = get_portfolio_value(st.session_state.portfolio)
    profit = current - invested

    st.subheader("Summary")
    st.write(f"Invested: ${invested:.2f}")
    st.write(f"Current Value: ${current:.2f}")

    if profit >= 0:
        st.success(f"Profit: +${profit:.2f}")
    else:
        st.error(f"Loss: -${abs(profit):.2f}")
else:
    st.info("No trades yet")

# =============================
# MARKET WATCH
# =============================
st.subheader("Market Watch")

for t in popular:
    price = get_price(t)
    if price:
        st.write(f"{t}: ${price:.2f}")

# =============================
# HISTORY
# =============================
st.subheader("Portfolio History")

user = st.session_state.user

if user not in history:
    history[user] = []

current_value = get_portfolio_value(st.session_state.portfolio)

history[user].append({
    "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "value": current_value
})

save_history(history)

df_hist = pd.DataFrame(history[user])

if not df_hist.empty:
    st.line_chart(df_hist.set_index("time")["value"])