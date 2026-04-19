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
# LOAD LARGE STOCK UNIVERSE
# =============================
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

    except:
        return pd.DataFrame(columns=["Ticker", "Name"])

stocks_df = load_stock_universe()
company_names = dict(zip(stocks_df["Ticker"], stocks_df["Name"]))
popular = stocks_df["Ticker"].tolist()

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
# STOCK CHART VIEWER
# =============================
st.subheader("📈 Stock Chart Viewer")

chart_search = st.text_input("Search stock (e.g. Tesla or AAPL)")

chart_matches = pd.DataFrame()

if chart_search and not stocks_df.empty:
    q = chart_search.strip().upper()
    chart_matches = stocks_df[
        stocks_df["Ticker"].str.contains(q, na=False) |
        stocks_df["Name"].str.upper().str.contains(q, na=False)
    ].head(25)

if not chart_matches.empty:
    chart_options = [
        f"{row.Ticker} - {row.Name}" for _, row in chart_matches.iterrows()
    ]

    chart_selection = st.selectbox("Choose stock for chart", chart_options)
    chart_ticker = chart_selection.split(" - ")[0]

    chart_data = yf.Ticker(chart_ticker).history(period="6mo")

    st.write(f"Showing: {chart_selection}")

    if not chart_data.empty:
        st.line_chart(chart_data["Close"])
    else:
        st.error("No chart data found.")
elif chart_search:
    st.warning("No matching stocks found.")

# =============================
# ADD TRADE
# =============================
st.sidebar.header("Add Trade")

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

if st.sidebar.button("Add Trade") and ticker:
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
    else:
        st.error("Could not fetch price for that stock.")

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

watchlist = ["AAPL", "MSFT", "TSLA", "NVDA", "AMZN", "GOOGL", "META"]

for t in watchlist:
    price = get_price(t)
    name = company_names.get(t, t)
    if price:
        st.write(f"{t} - {name}: ${price:.2f}")

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