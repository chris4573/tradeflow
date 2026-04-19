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
st.set_page_config(page_title="TradeFlow", layout="wide")

USERS_FILE = "users.json"
PORTFOLIO_FILE = "portfolio_data.json"
HISTORY_FILE = "portfolio_history.json"
SALES_FILE = "sales_history.json"

# =============================
# SECURITY
# =============================
def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

# =============================
# LOAD / SAVE HELPERS
# =============================
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
    except Exception:
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
    except Exception:
        return pd.DataFrame(columns=["Ticker", "Name"])

stocks_df = load_stock_universe()
company_names = dict(zip(stocks_df["Ticker"], stocks_df["Name"]))

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
    st.title("TradeFlow Login")

    mode = st.radio("Choose", ["Login", "Register"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if mode == "Register":
        if st.button("Create Account"):
            if username in users:
                st.error("User already exists")
            elif not username or not password:
                st.error("Enter a username and password")
            else:
                users[username] = hash_password(password)
                save_json(USERS_FILE, users)
                st.success("Account created")

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
# SAVE USER DATA
# =============================
def save_user_portfolio():
    portfolios[st.session_state.user] = st.session_state.portfolio
    save_json(PORTFOLIO_FILE, portfolios)

def save_user_sale(record):
    user = st.session_state.user
    if user not in sales_history:
        sales_history[user] = []
    sales_history[user].append(record)
    save_json(SALES_FILE, sales_history)

# =============================
# PORTFOLIO CALCS
# =============================
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
            "Time": trade["Time"]
        })

    return pd.DataFrame(rows)

# =============================
# APP START
# =============================
if not st.session_state.logged_in:
    login_page()
    st.stop()

st.title("TradeFlow")
st.write(f"Welcome {st.session_state.user}")

if st.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.user = ""
    st.session_state.portfolio = []
    st.rerun()

# =============================
# STOCK CHART VIEWER
# =============================
st.subheader("Stock Chart Viewer")

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
    chart_selection = st.selectbox("Choose stock for chart", chart_options)
    chart_ticker = chart_selection.split(" - ", 1)[0].strip()
    chart_data = yf.Ticker(chart_ticker).history(period="6mo")

    st.write(f"Showing: {chart_selection}")
    if not chart_data.empty:
        st.line_chart(chart_data["Close"])
    else:
        st.error("No chart data found.")
elif chart_search:
    st.warning("No matching stocks found.")

# =============================
# SIDEBAR - ADD TRADE
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

amount = st.sidebar.number_input("Amount ($)", min_value=1.0, value=100.0, step=10.0)

if st.sidebar.button("Add Trade") and ticker:
    price = get_price(ticker)
    if price:
        trade = {
            "Ticker": ticker,
            "Amount": float(amount),
            "Price": float(price),
            "Shares": float(amount / price),
            "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        st.session_state.portfolio.append(trade)
        save_user_portfolio()
        st.sidebar.success(f"Added {ticker}")
        st.rerun()
    else:
        st.sidebar.error("Could not fetch price for that stock.")

# =============================
# PORTFOLIO TABLE
# =============================
st.subheader("Portfolio")

portfolio_df = build_portfolio_df(st.session_state.portfolio)

if not portfolio_df.empty:
    st.dataframe(portfolio_df, use_container_width=True)

    invested = float(portfolio_df["Amount"].sum())
    current_value = float(portfolio_df["Market Value"].fillna(0).sum())
    unrealized_profit = current_value - invested

    col1, col2, col3 = st.columns(3)
    col1.metric("Invested", f"${invested:,.2f}")
    col2.metric("Current Value", f"${current_value:,.2f}")
    col3.metric("Unrealized P/L", f"${unrealized_profit:,.2f}")
else:
    st.info("No trades yet")

# =============================
# MANAGE TRADES
# =============================
st.subheader("Manage Trades")

if not portfolio_df.empty:
    trade_labels = [
        f"ID {row['ID']} | {row['Ticker']} | {row['Shares']:.4f} shares | bought {row['Time']}"
        for _, row in portfolio_df.iterrows()
    ]

    selected_label = st.selectbox("Select a trade", trade_labels)
    selected_id = int(selected_label.split("|")[0].replace("ID", "").strip())
    selected_trade = st.session_state.portfolio[selected_id]
    selected_current_price = get_price(selected_trade["Ticker"]) or 0.0

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### Delete Trade")
        if st.button("Delete Selected Trade"):
            deleted = st.session_state.portfolio.pop(selected_id)
            save_user_portfolio()
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
            key=f"sell_{selected_id}"
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
                st.session_state.portfolio.pop(selected_id)
            else:
                remaining_amount = remaining_shares * avg_buy_price
                st.session_state.portfolio[selected_id]["Shares"] = remaining_shares
                st.session_state.portfolio[selected_id]["Amount"] = remaining_amount

            save_user_portfolio()
            save_user_sale(sale_record)
            st.success(f"Sold {sell_shares:.4f} shares of {selected_trade['Ticker']}")
            st.rerun()
else:
    st.info("Add trades to manage them")

# =============================
# SALES HISTORY
# =============================
st.subheader("Sales History")

user_sales = sales_history.get(st.session_state.user, [])
if user_sales:
    sales_df = pd.DataFrame(user_sales)
    st.dataframe(sales_df, use_container_width=True)

    total_realized = float(sales_df["Realized P/L"].sum())
    if total_realized >= 0:
        st.success(f"Total Realized Profit/Loss: ${total_realized:.2f}")
    else:
        st.error(f"Total Realized Profit/Loss: ${total_realized:.2f}")
else:
    st.info("No sales yet")

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
# PORTFOLIO HISTORY
# =============================
st.subheader("Portfolio History")

user = st.session_state.user
if user not in history:
    history[user] = []

current_value_now = get_portfolio_value(st.session_state.portfolio)

history[user].append({
    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "value": current_value_now
})
save_json(HISTORY_FILE, history)

df_hist = pd.DataFrame(history[user])
if not df_hist.empty:
    st.line_chart(df_hist.set_index("time")["value"])