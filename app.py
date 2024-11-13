import streamlit as st
import pandas as pd
import datetime
import os
import base64

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


# CSV filename constant
CSV_FILENAME = "transaction_history.csv"
TRANSACTION_FEE = 10

# Function to check if transaction history exists and has data
def has_transaction_history():
    if os.path.exists(CSV_FILENAME):
        df = pd.read_csv(CSV_FILENAME)
        return not df.empty
    return False

# Function to load transaction history and initialize state
def load_transaction_history():
    if os.path.exists(CSV_FILENAME):
        df = pd.read_csv(CSV_FILENAME)
        
        # Initialize transactions from CSV
        st.session_state.transactions = df.to_dict('records')
        
        # Initialize available cash from the last transaction
        if not df.empty:
            st.session_state.available_cash = float(df['Available Cash'].iloc[-1])
        else:
            # If CSV exists but is empty, use default or user-set initial fund
            st.session_state.available_cash = st.session_state.get('initial_fund', 10000)
            
        # Initialize shares by symbol from the latest state for each symbol
        shares_dict = {}
        for symbol in df['Stock Symbol'].unique():
            symbol_df = df[df['Stock Symbol'] == symbol]
            if not symbol_df.empty:
                shares = int(symbol_df.iloc[-1]['Shares Owned'])
                if shares > 0:  # Only add if there are shares owned
                    shares_dict[symbol] = shares
        st.session_state.shares_by_symbol = shares_dict
    else:
        # Initialize with default values if no CSV exists
        st.session_state.transactions = []
        st.session_state.available_cash = st.session_state.get('initial_fund', 10000)
        st.session_state.shares_by_symbol = {}

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = False

st.title("Stock Transaction Tracker")

# Check if transaction history exists
has_history = has_transaction_history()

# Initial Fund Setup - only show if no transaction history exists
if not has_history:
    if not st.session_state.initialized:
        st.header("Initial Fund Setup")
        default_fund = 10000
        if 'initial_fund' not in st.session_state:
            st.session_state.initial_fund = default_fund
        
        new_initial_fund = st.number_input(
            "Set your initial fund amount ($)", 
            min_value=100.0, 
            value=float(st.session_state.initial_fund),
            step=100.0,
            format="%.2f"
        )
        
        if st.button("Set Initial Fund"):
            st.session_state.initial_fund = new_initial_fund
            st.session_state.initialized = True
            load_transaction_history()
            st.success(f"Initial fund set to ${new_initial_fund:,.2f}")
            st.rerun()

# Load transaction history if not already initialized
if has_history and not st.session_state.initialized:
    load_transaction_history()
    st.session_state.initialized = True

# Main app interface
if st.session_state.initialized or has_history:
    # Display current portfolio summary
    st.header("Current Portfolio")
    st.write(f"Available Cash: ${st.session_state.available_cash:.2f}")
    if st.session_state.shares_by_symbol:
        st.write("Shares Owned:")
        for symbol, shares in st.session_state.shares_by_symbol.items():
            st.write(f"{symbol}: {shares} shares")
    else:
        st.write("No shares currently owned")

    # Input fields for transaction details
    st.header("Add New Transaction")
    transaction_type = st.selectbox("Transaction Type", ["Buy", "Sell"])
    stock_symbol = st.text_input("Stock Symbol", value="AAPL")
    shares = st.number_input("Number of Shares", min_value=1, value=10)
    price_per_share = st.number_input("Price per Share", min_value=0.01, value=150.00)

    # Calculate total cost/revenue of transaction
    total_cost = shares * price_per_share
    net_amount = total_cost + TRANSACTION_FEE if transaction_type == "Buy" else total_cost - TRANSACTION_FEE

    # Transaction form
    if st.button("Record Transaction"):
        if transaction_type == "Buy":
            if st.session_state.available_cash < net_amount:
                st.error("Insufficient funds for this transaction.")
            else:
                # Update available cash and shares for the specific stock symbol
                st.session_state.available_cash -= net_amount
                if stock_symbol in st.session_state.shares_by_symbol:
                    st.session_state.shares_by_symbol[stock_symbol] += shares
                else:
                    st.session_state.shares_by_symbol[stock_symbol] = shares
                # Record the transaction
                transaction = {
                    "Date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Type": transaction_type,
                    "Stock Symbol": stock_symbol,
                    "Shares": shares,
                    "Price per Share": price_per_share,
                    "Transaction Fee": TRANSACTION_FEE,
                    "Total Amount": net_amount,
                    "Available Cash": st.session_state.available_cash,
                    "Shares Owned": st.session_state.shares_by_symbol[stock_symbol]
                }
                st.session_state.transactions.append(transaction)
                
                # Update CSV file
                df = pd.DataFrame([transaction])
                df.to_csv(CSV_FILENAME, mode='a', header=not os.path.exists(CSV_FILENAME), index=False)
                st.success("Transaction recorded successfully!")
                st.rerun()
                
        elif transaction_type == "Sell":
            if stock_symbol not in st.session_state.shares_by_symbol or st.session_state.shares_by_symbol[stock_symbol] < shares:
                st.error(f"You do not have enough shares of {stock_symbol} to sell. You have {st.session_state.shares_by_symbol.get(stock_symbol, 0)} shares.")
            else:
                # Update available cash and shares for the specific stock symbol
                st.session_state.available_cash += net_amount
                st.session_state.shares_by_symbol[stock_symbol] -= shares
                if st.session_state.shares_by_symbol[stock_symbol] == 0:
                    del st.session_state.shares_by_symbol[stock_symbol]  # Remove stock symbol if shares are 0
                # Record the transaction
                transaction = {
                    "Date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Type": transaction_type,
                    "Stock Symbol": stock_symbol,
                    "Shares": shares,
                    "Price per Share": price_per_share,
                    "Transaction Fee": TRANSACTION_FEE,
                    "Total Amount": net_amount,
                    "Available Cash": st.session_state.available_cash,
                    "Shares Owned": st.session_state.shares_by_symbol.get(stock_symbol, 0)
                }
                st.session_state.transactions.append(transaction)
                
                # Update CSV file
                df = pd.DataFrame([transaction])
                df.to_csv(CSV_FILENAME, mode='a', header=not os.path.exists(CSV_FILENAME), index=False)
                st.success("Transaction recorded successfully!")
                st.rerun()

    # Display transaction history
    st.header("Transaction History")
    if st.session_state.transactions:
        df = pd.DataFrame(st.session_state.transactions)
        st.dataframe(df)
    else:
        st.write("No transactions recorded yet.")