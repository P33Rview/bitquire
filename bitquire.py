import os
from dotenv import load_dotenv
from scraping_200_wma import supabase_data_import, return_supabase_wma, get_200_wma

import pandas as pd
import numpy as np
from datetime import datetime, timezone
import matplotlib.pyplot as plt
import seaborn as sns

import requests

load_dotenv()
BASE_URL = "https://pro-api.coinmarketcap.com"


def get_session(api_key=None):
    """Build a requests session with the CoinMarketCap auth headers."""
    api_key = api_key or os.getenv("CMC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "No API key. Set the CMC_API_KEY environment variable or pass api_key=..."
        )

    session = requests.Session()
    session.headers.update({
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": api_key,
    })
    return session


def request(endpoint, params=None, api_key=None, session=None):
    """Call a CoinMarketCap endpoint and return the parsed `data` payload."""
    session = session or get_session(api_key)
    response = session.get(BASE_URL + endpoint, params=params, timeout=30)

    payload = response.json()
    status = payload.get("status", {})
    # v1 sends error_code as an int, v3 as a string — normalise before testing.
    error_code = str(status.get("error_code") or 0)
    if error_code != "0":
        raise RuntimeError(
            f"CoinMarketCap error {error_code}: {status.get('error_message')}"
        )
    response.raise_for_status()

    return payload["data"]


def to_frame(coins, convert="USD"):
    """Flatten the nested quote block into a tidy DataFrame."""
    rows = []
    for coin in coins:
        quote = coin["quote"][convert]
        rows.append({
            "symbol": coin["symbol"],
            "name": coin["name"],
            "rank": coin.get("cmc_rank"),
            "price": quote["price"],
            "volume_24h": quote["volume_24h"],
            "pct_change_1h": quote["percent_change_1h"],
            "pct_change_24h": quote["percent_change_24h"],
            "pct_change_7d": quote["percent_change_7d"],
            "market_cap": quote["market_cap"],
            "last_updated": pd.to_datetime(quote["last_updated"]),
        })

    return pd.DataFrame(rows)


def get_czk_usd_exchange():
    """Returns the CZK Exchange rate for CZK/USD pair."""

    api_key = os.getenv("EXCHANGE_API_KEY")
    EXCHANGE_URL = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/USD"

    response = requests.get(EXCHANGE_URL)
    data = response.json()

    return data["conversion_rates"]["CZK"]


def get_listings(limit=100, convert="USD", api_key=None, session=None):
    """Latest market data for the top `limit` coins by market cap."""
    data = request(
        "/v1/cryptocurrency/listings/latest",
        params={"start": 1, "limit": limit, "convert": convert},
        api_key=api_key,
        session=session,
    )
    return to_frame(data, convert)


def fear_greed_index(api_key=None, session=None):
    """Last fear and greed index value"""
    data = request(
        "/v3/fear-and-greed/latest",
        api_key=api_key,
        session=session,
    )
    return data["value"]


def calculate_buy_amount(
    btc_price=None,
    wma_200=None,
    fgi=None,
    min_buy=750,
    max_buy=1500,
    min_ratio=1.0,
    max_ratio=2.0,
    fgi_weight=0.3):
    """Calculates an amount of CZK to be spend on BTC weighted by fear and greed index."""

    if btc_price is None:
        btc_price = get_listings(1)["price"].iloc[0]
    if wma_200 is None:
        wma_200 = get_200_wma()
    if fgi is None:
        fgi = fear_greed_index()

    # Position 0..1 from price vs 200WMA (0 = cheap, 1 = expensive)
    ratio = btc_price / wma_200
    wma_position = np.clip((ratio - min_ratio) / (max_ratio - min_ratio), 0, 1)

    # Position 0..1 from sentiment (0 = extreme fear, 1 = extreme greed)
    fgi_position = np.clip(float(fgi) / 100, 0, 1)

    # Weighted blend of the two signals
    position = (1 - fgi_weight) * wma_position + fgi_weight * fgi_position

    buy_amount = round(max_buy - position * (max_buy - min_buy), 2)
    usd_amount = round(buy_amount / get_czk_usd_exchange(), 2)
    btc_amount = round(usd_amount / btc_price, 7)

    return {"czk_amount": buy_amount,
            "usd_amount": usd_amount,
            "btc_amount": btc_amount}


if __name__ == "__main__":
    df = get_listings(1)
    df["fear_greed_index"] = fear_greed_index()
    df["200WMA"] = return_supabase_wma()["200WMA"].reset_index(drop=True)

    # Adding calculated buy amount (CZK, USD and BTC)
    result = calculate_buy_amount()
    df = df.assign(**result)

    with pd.option_context("display.max_columns", None, "display.width", None):
        print(df[["symbol", "pct_change_7d", "last_updated",
                  "price", "200WMA", "fear_greed_index",
                  "czk_amount", "usd_amount", "btc_amount"]])
