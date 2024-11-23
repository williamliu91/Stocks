import streamlit as st
import yfinance as yf
import pandas as pd
import os
import datetime
import base64

# Page Configuration
st.set_page_config(page_title="Stock Lookup & Paper Trading", page_icon="📈", layout="wide")

# Title and Header
st.title("📊 Real-Time Stock Lookup & Paper Trading")

# Function to load the image and convert it to base64
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Path to the locally stored QR code image
qr_code_path = "qrcode.png"  # Ensure the image is in your app directory

# Convert image to base64
qr_code_base64 = get_base64_of_bin_file(qr_code_path)

# Custom CSS to position the QR code close to the top-right corner under the "Deploy" area
st.markdown(
    f"""
    <style>
    .qr-code {{
        position: fixed;  /* Keeps the QR code fixed in the viewport */
        top: 10px;       /* Sets the distance from the top of the viewport */
        right: 10px;     /* Sets the distance from the right of the viewport */
        width: 200px;    /* Adjusts the width of the QR code */
        z-index: 100;    /* Ensures the QR code stays above other elements */
    }}
    </style>
    <img src="data:image/png;base64,{qr_code_base64}" class="qr-code">
    """,
    unsafe_allow_html=True
)


# Portfolio CSV File
PORTFOLIO_FILE = "portfolio.csv"

# Initialize Session State
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["Symbol", "Shares", "Purchase Price"])
if 'balance' not in st.session_state:
    st.session_state.balance = 100000  # Default balance if no file exists

# Load Portfolio and Balance from CSV
def load_portfolio_and_balance():
    if os.path.exists(PORTFOLIO_FILE):
        data = pd.read_csv(PORTFOLIO_FILE)
        if "Balance" in data.columns:
            balance = data["Balance"].iloc[0]
            portfolio = data.drop(columns=["Balance"])
            return portfolio, balance
    return pd.DataFrame(columns=["Symbol", "Shares", "Purchase Price"]), 100000

# Save Portfolio and Balance to CSV
def save_portfolio_and_balance(portfolio, balance):
    portfolio["Balance"] = [balance] + [None] * (len(portfolio) - 1)
    portfolio.to_csv(PORTFOLIO_FILE, index=False)

# Function to Fetch Stock Data
def get_stock_data(symbol):
    """Get latest stock data including price and basic info."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period='1d')
        if df.empty:
            return None
        current_price = df['Close'].iloc[-1]
        info = {
            'symbol': symbol,
            'current_price': current_price,
            'volume': df['Volume'].iloc[-1],
            'open': df['Open'].iloc[-1],
            'high': df['High'].iloc[-1],
            'low': df['Low'].iloc[-1]
        }
        try:
            info['name'] = ticker.info.get('longName', symbol)
        except:
            info['name'] = symbol
        return info
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {str(e)}")
        return None

# Load portfolio and balance at start
st.session_state.portfolio, st.session_state.balance = load_portfolio_and_balance()


st.markdown("""
Monitor real-time market prices and engage in paper trading. 
Start with a virtual balance of **$100,000**, and build your portfolio!
""")

# Sidebar Input for Stock Symbol
st.sidebar.header("Stock Lookup")
symbol = st.sidebar.text_input("Enter Stock Symbol (e.g., AAPL, MSFT, GOOGL)", "").upper()

if symbol:
    with st.spinner(f'Fetching data for {symbol}...'):
        stock_data = get_stock_data(symbol)

        if stock_data:
            st.header(f"{stock_data['name']} ({stock_data['symbol']})")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("💵 Current Price", f"${stock_data['current_price']:.2f}")
            with col2:
                st.metric("📈 Day High", f"${stock_data['high']:.2f}")
                st.metric("📉 Day Low", f"${stock_data['low']:.2f}")
            with col3:
                st.metric("🔄 Volume", f"{stock_data['volume']:,}")

            st.markdown("---")

           # Buy and Sell Sections in Columns
st.subheader("📋 Paper Trading")
col1, col2 = st.columns([1, 1])  # Adjust column proportions as needed

# Buy Section
with col1:
    buy_quantity = st.number_input(
        "Enter quantity to buy", min_value=0, step=1, value=0, key="buy_quantity"
    )
    buy_button = st.button("Buy", key="buy_button")

# Sell Section
with col2:
    sell_quantity = st.number_input(
        "Enter quantity to sell", min_value=0, step=1, value=0, key="sell_quantity"
    )
    sell_button = st.button("Sell", key="sell_button")

# Ensure stock data is fetched
if symbol:
    with st.spinner(f'Fetching data for {symbol}...'):
        stock_data = get_stock_data(symbol)

    if stock_data:  # Only proceed if stock data is available
        # Buy Button Logic
        if buy_button:
            cost = buy_quantity * stock_data["current_price"]
            transaction_fee = cost * 0.002  # 0.2% transaction fee
            total_cost = cost + transaction_fee  # Total cost with fee
            transaction_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Current date and time

            if total_cost <= st.session_state.balance:
                st.session_state.balance -= total_cost  # Deduct total cost with fee
                existing = st.session_state.portfolio[
                    st.session_state.portfolio["Symbol"] == symbol
                ]
                if not existing.empty:
                    st.session_state.portfolio.loc[existing.index, "Shares"] += buy_quantity
                    st.session_state.portfolio.loc[existing.index, "Transaction Fee"] += transaction_fee  # Add fee
                    st.session_state.portfolio.loc[existing.index, "Transaction Date"] = transaction_date  # Add date
                else:
                    st.session_state.portfolio = pd.concat(
                        [
                            st.session_state.portfolio,
                            pd.DataFrame(
                                {
                                    "Symbol": [symbol],
                                    "Shares": [buy_quantity],
                                    "Purchase Price": [stock_data["current_price"]],
                                    "Transaction Fee": [transaction_fee],  # Add fee to new row
                                    "Transaction Date": [transaction_date],  # Add date to new row
                                }
                            ),
                        ]
                    )
                save_portfolio_and_balance(st.session_state.portfolio, st.session_state.balance)
                st.success(f"Bought {buy_quantity} shares of {symbol} for ${cost:.2f} (Fee: ${transaction_fee:.2f}) on {transaction_date}")
            else:
                st.error("Insufficient balance!")

        # Sell Button Logic
        if sell_button:
            existing = st.session_state.portfolio[
                st.session_state.portfolio["Symbol"] == symbol
            ]
            if not existing.empty and existing["Shares"].iloc[0] >= sell_quantity:
                st.session_state.portfolio.loc[existing.index, "Shares"] -= sell_quantity
                proceeds = sell_quantity * stock_data["current_price"]
                transaction_fee = proceeds * 0.002  # 0.2% transaction fee
                net_proceeds = proceeds - transaction_fee  # Net proceeds after fee
                transaction_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Current date and time
                st.session_state.balance += net_proceeds
                st.session_state.portfolio.loc[existing.index, "Transaction Fee"] += transaction_fee  # Add fee
                st.session_state.portfolio.loc[existing.index, "Transaction Date"] = transaction_date  # Add date
                st.session_state.portfolio = st.session_state.portfolio[
                    st.session_state.portfolio["Shares"] > 0
                ]
                save_portfolio_and_balance(st.session_state.portfolio, st.session_state.balance)
                st.success(f"Sold {sell_quantity} shares of {symbol} for ${net_proceeds:.2f} (Fee: ${transaction_fee:.2f}) on {transaction_date}")
            else:
                st.error("Not enough shares to sell!")

        st.markdown("---")

# Portfolio Display Section
st.subheader("📂 Portfolio")
if not st.session_state.portfolio.empty:
    # Remove rows with NaN or invalid symbols from the portfolio
    valid_portfolio = st.session_state.portfolio.dropna(subset=["Symbol"])

    # Drop the "Balance" column before displaying the portfolio table
    valid_portfolio = valid_portfolio.drop(columns=["Balance"], errors="ignore")

    # Rename the columns as needed (make sure this happens first)
    valid_portfolio = valid_portfolio.rename(columns={
        "Transaction Date": "The Latest Transaction Date",  # Renaming "Transaction Date" column
        "Purchase Price": "The Latest Purchase Price",     # Renaming "Purchase Price" column
        "Transaction Fee": "Total Transaction Fee"         # Renaming "Transaction Fee" column
    })
    
    # Ensure no missing values in 'Symbol' and 'Shares'
valid_portfolio = valid_portfolio.dropna(subset=['Symbol', 'Shares'])

# Function to get current stock value
def get_current_value(symbol, shares):
    if pd.isna(symbol) or pd.isna(shares):  # Handle missing values
        return 0
    stock_data = get_stock_data(symbol)
    if stock_data is not None and 'current_price' in stock_data:
        return shares * stock_data['current_price']
    return 0  # Return 0 if stock data is unavailable or invalid

# Apply function to get current value
current_values = valid_portfolio.apply(
    lambda row: get_current_value(row['Symbol'], row['Shares']), axis=1
)

# Ensure no missing values in 'Symbol' and 'Shares'
valid_portfolio = valid_portfolio.dropna(subset=['Symbol', 'Shares'])

# Function to get current stock value
def get_current_value(symbol, shares):
    if pd.isna(symbol) or pd.isna(shares):  # Handle missing values
        return 0
    stock_data = get_stock_data(symbol)
    if stock_data is not None and 'current_price' in stock_data:
        return shares * stock_data['current_price']
    return 0  # Return 0 if stock data is unavailable or invalid

# Apply function to get current value
current_values = valid_portfolio.apply(
    lambda row: get_current_value(row['Symbol'], row['Shares']), axis=1
)

# Ensure the output length matches the DataFrame length
if len(current_values) == len(valid_portfolio):
    valid_portfolio['Current Value'] = current_values
else:
    print("Mismatch in lengths!")
    # Optionally, handle this case if needed

# Round all relevant columns to 2 decimal points to ensure correct display
valid_portfolio["The Latest Purchase Price"] = valid_portfolio["The Latest Purchase Price"].round(2)
valid_portfolio["Total Transaction Fee"] = valid_portfolio["Total Transaction Fee"].round(2)
valid_portfolio["Current Value"] = valid_portfolio["Current Value"].round(2)
valid_portfolio["Shares"] = valid_portfolio["Shares"].round(2)

# Ensure that figures are displayed with 2 decimal places using string formatting
valid_portfolio["The Latest Purchase Price"] = valid_portfolio["The Latest Purchase Price"].apply(lambda x: f"{x:.2f}")
valid_portfolio["Total Transaction Fee"] = valid_portfolio["Total Transaction Fee"].apply(lambda x: f"{x:.2f}")
valid_portfolio["Current Value"] = valid_portfolio["Current Value"].apply(lambda x: f"{x:.2f}")
valid_portfolio["Shares"] = valid_portfolio["Shares"].apply(lambda x: f"{x:.2f}")

# Display the portfolio
st.write(valid_portfolio)
