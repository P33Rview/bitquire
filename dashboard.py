
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from bitquire import get_listings, get_czk_usd_exchange
from scraping_200_wma import supabase_connection

load_dotenv()

st.set_page_config(
    page_title="BTC Portfolio",
    page_icon="₿",
    layout="wide"
)

@st.cache_resource
def get_purchases():
    response = (
        supabase_connection()
        .table("calculated_amount_to_buy")
        .select("*")
        .order("last_updated")
        .execute()
    )
    return pd.DataFrame(response.data)

st.title("₿ BTC Portfolio Tracker")

@st.fragment(run_every="60s")
def show_portfolio():
    df = get_purchases()

    if df.empty:
        st.info("No purchases recorded yet.")
        return

    btc_price = get_listings(1)["price"].iloc[0] * get_czk_usd_exchange()
    avg_btc_price = df["price"].mean() * get_czk_usd_exchange()

    total_btc = pd.to_numeric(df["btc_amount"]).sum()
    invested = pd.to_numeric(df["czk_amount"]).sum()

    current_value = total_btc * btc_price
    profit = current_value - invested
    return_pct = profit / invested * 100

    c1, c2, c3 = st.columns(3)

    c1.metric("Portfolio Value", f"{current_value:,.0f} Kč")
    c2.metric("Total Invested", f"{invested:,.0f} Kč")
    c3.metric(
        "Unrealized P/L",
        f"{profit:+,.0f} Kč",
        f"{return_pct:+.2f}%"
    )

    c4, c5 = st.columns(2)

    c4.metric("BTC Holdings", f"{total_btc:.8f} BTC")
    c5.metric("Average BTC Price", f"{avg_btc_price:,.0f} Kč")

    st.subheader("Purchase History")
    st.dataframe(df, use_container_width=True)

show_portfolio()
