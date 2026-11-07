import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from bitquire import get_listings, get_czk_usd_exchange
from scraping_200_wma import supabase_connection

from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv()

st.set_page_config(
    page_title="bitquire",
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

@st.cache_resource
def get_portfolio_snapshot():
    response = (
        supabase_connection()
        .table("calculated_amount_to_buy")
        .select("last_updated, price, czk_amount")
        .order("last_updated")
        .execute()
    )

    df = pd.DataFrame(response.data)

    if not df.empty:
        df["last_updated"] = pd.to_datetime(df["last_updated"])
        df["price"] = pd.to_numeric(df["price"])
        df["czk_amount"] = pd.to_numeric(df["czk_amount"])

        df = df.sort_values("last_updated")

        # Total invested CZK
        df["total_invested_czk"] = df["czk_amount"].cumsum()

        # BTC purchased each week
        df["btc_bought"] = df["czk_amount"] / df["price"]

        # Cumulative BTC holdings
        df["total_btc"] = df["btc_bought"].cumsum()

        # Portfolio value at each historical date
        df["portfolio_value_czk"] = df["total_btc"] * df["price"]

    return df

@st.fragment(run_every="180s") # Increased from 60 secs to 180 secs to preserve API limit rates
def show_portfolio():
    df = get_purchases()

    # Header
    col1, col2 = st.columns([3, 1], vertical_alignment="center")

    with col1:
        st.title("BTC Portfolio Tracker")

    with col2:
        timestamp = datetime.now(ZoneInfo("Europe/Prague"))
        st.markdown(
            f"<div style='text-align: right; color: gray; font-size: 12px;'>"
            f"↻ Last refreshed: {timestamp:%H:%M:%S}"
            f"</div>",
            unsafe_allow_html=True)

    if df.empty:
        st.info("No purchases recorded yet.")
        return

    btc_price = get_listings(1)["price"].iloc[0]
    btc_price_CZK = btc_price * get_czk_usd_exchange()
    avg_btc_price_USD = df["price"].mean()
    avg_btc_price_CZK = avg_btc_price_USD * get_czk_usd_exchange()

    avg_czk_buy = df["czk_amount"].mean()
    avg_btc_buy = df["btc_amount"].mean()

    total_btc = pd.to_numeric(df["btc_amount"]).sum()
    invested = pd.to_numeric(df["czk_amount"]).sum()

    current_value_CZK = total_btc * btc_price_CZK # CZK price
    # current_value_USD = total_btc * btc_price # USD price
    profit = current_value_CZK - invested
    return_pct = profit / invested * 100

    # Profit/loss widget
    color = "#16A34A" if profit >= 0 else "#DC2626"
    formatted_profit = f"{profit:+,.0f}".replace(",", " ")

    st.markdown(
        f"""
        <div style="padding: 0; margin-bottom: 30px;">
            <div style="font-size: 14px; color: gray; margin-bottom: 0; line-height: 1;">
                Unrealized P/L
            </div>
            <div style="display: flex; align-items: baseline; gap: 14px;">
                <span style="font-size: 75px; font-weight: 700; line-height: 1.1;">
                    {formatted_profit} Kč
                </span>
                <span style="font-size: 25px; font-weight: 600; color: {color};">
                    {return_pct:+.2f}%
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Metrics with
    c1, c2, c3, c4 = st.columns(4)
    height_val = 135

    with c1:
        with st.container(border=True, height=height_val):
            st.metric(
                "BTC Holdings",
                f"{total_btc:.8f} BTC")

            st.html("""
                            <style>
                                div[data-testid="stMetric"] {
                                    margin-bottom: -12px;
                                }
                            </style>
                        """)

            st.caption(f"**{avg_btc_buy:,.8f} BTC** (Average weekly BTC)")

    with c2:
        with st.container(border=True, height=height_val):
            st.metric(
                "Average BTC buy price",
                f"${avg_btc_price_USD:,.0f}".replace(",", " "))

            st.html("""
                            <style>
                                div[data-testid="stMetric"] {
                                    margin-bottom: -12px;
                                }
                            </style>
                        """)

            st.caption(f"**${btc_price:,.0f}** (Current BTC price)".replace(",", " "))

    with c3:
        with st.container(border=True, height=height_val):
            st.metric(
                "Total Invested",
                f"{invested:,.0f} Kč".replace(",", " "))

            st.html("""
                <style>
                    div[data-testid="stMetric"] {
                        margin-bottom: -12px;
                    }
                </style>
            """)

            st.caption(f"{f'**{avg_czk_buy:,.0f}'.replace(",", " ")} Kč** (Average weekly buy)")

    with c4:
        with st.container(border=True, height=height_val):
            st.metric(
                "Portfolio Value",
                f"{current_value_CZK:,.0f} Kč".replace(",", " "),
                f"{current_value_CZK - invested:,.0f} Kč")

    #Line chart with purchase history
    df_line = get_portfolio_snapshot()

    if not df.empty:
        st.line_chart(
            df_line,
            x="last_updated",
            y=["total_invested_czk", "portfolio_value_czk"],
            color=["#94A3B8", "#F7931A"],
            height=400
        )

    # Container with tabular purchase history
    with st.expander("Click for detailed purchase history"):
        st.subheader("Purchase History")
        st.dataframe(df[["last_updated", "price", "czk_amount", "btc_amount", "lower_buy_limit", "upper_buy_limit"]], use_container_width=True)

show_portfolio()
