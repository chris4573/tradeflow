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
# STOCK UNIVERSE
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
if "selected_portfolio" not in st.session_state:
    st.session_state.selected_portfolio = None

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

                # create empty portfolio structure for new user
                portfolios[username] = {"Main": []}
                save_json(PORTFOLIO_FILE, portfolios)

                history[username] = {"Main": []}
                save_json(HISTORY_FILE, history)

                sales_history[username] = {"Main": []}
                save_json(SALES_FILE, sales_history)

                st.success("Account created")

    if mode == "Login":
        if st.button("Login"):
            if username in users and users[username] == hash_password(password):
                st.session_state.logged_in = True
                st.session_state.user = username

                # migrate old data if needed
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
            "Time": trade.get("Time", "Older trade")
        })

    return pd.DataFrame(rows)

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

# =============================
# SIDEBAR - PORTFOLIOS
# =============================
st.sidebar.header("Portfolios")

portfolio_names = list(user_portfolios.keys())

selected_portfolio = st.sidebar.radio(
    "Select Portfolio",
    portfolio_names,
    index=portfolio_names.index(st.session_state.selected_portfolio)
)

st.session_state.selected_portfolio = selected_portfolio

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

current_portfolio = get_current_portfolio()

# =============================
# HEADER
# =============================
st.title("TradeFlow")
st.write(f"Welcome {user}")
st.write(f"Current portfolio: **{st.session_state.selected_portfolio}**")

if st.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.user = ""
    st.session_state.selected_portfolio = None
    st.rerun()

# =============================
# STOCK VIEWER + BUY/SELL
# =============================
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
        st.line_chart(chart_data["Close"])
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
# SIDEBAR - ADD TRADE
# =============================
st.sidebar.header("Quick Add Trade")

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

# =============================
# PORTFOLIO DISPLAY
# =============================
st.subheader("Portfolio")

portfolio_df = build_portfolio_df(current_portfolio)

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
    st.info("No trades yet in this portfolio")

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
    st.info("Add trades to manage them")

# =============================
# SALES HISTORY
# =============================
st.subheader("Sales History")

current_sales = get_current_sales()
if current_sales:
    sales_df = pd.DataFrame(current_sales)
    st.dataframe(sales_df, use_container_width=True)

    total_realized = float(sales_df["Realized P/L"].sum())
    if total_realized >= 0:
        st.success(f"Total Realized Profit/Loss: ${total_realized:.2f}")
    else:
        st.error(f"Total Realized Profit/Loss: ${total_realized:.2f}")
else:
    st.info("No sales yet in this portfolio")

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

current_history = get_current_history()
current_value_now = get_portfolio_value(current_portfolio)

current_history.append({
    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "value": current_value_now
})
save_current_history(current_history)

df_hist = pd.DataFrame(current_history)
if not df_hist.empty:
    st.line_chart(df_hist.set_index("time")["value"])