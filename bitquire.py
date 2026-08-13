import os
from dotenv import load_dotenv
from scraping_200_wma import supabase_data_import, return_supabase_wma

import pandas as pd
import numpy as np
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

if __name__ == "__main__":
    df = get_listings(1)
    df["fear_greed_index"] = fear_greed_index()
    df["200WMA"] = return_supabase_wma()["200WMA"].reset_index(drop=True)
    print(df[["symbol",
              "pct_change_24h", "pct_change_7d",
              "last_updated", "fear_greed_index",
              "price", "200WMA"]])
