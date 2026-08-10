import os

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

import requests
import json


BASE_URL = "https://pro-api.coinmarketcap.com"


def get_session(api_key=None):
    """Build a requests session with the CoinMarketCap auth headers."""
    api_key = api_key or os.environ.get("CMC_API_KEY")
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
    if status.get("error_code"):
        raise RuntimeError(
            f"CoinMarketCap error {status['error_code']}: {status.get('error_message')}"
        )
    response.raise_for_status()

    return payload["data"]


def get_listings(limit=100, convert="USD", api_key=None, session=None):
    """Latest market data for the top `limit` coins by market cap."""
    data = request(
        "/v1/cryptocurrency/listings/latest",
        params={"start": 1, "limit": limit, "convert": convert},
        api_key=api_key,
        session=session,
    )
    return to_frame(data, convert)


def get_quotes(symbols, convert="USD", api_key=None, session=None):
    """Latest quotes for specific symbols, e.g. ["BTC", "ETH"]."""
    if isinstance(symbols, str):
        symbols = [symbols]

    data = request(
        "/v1/cryptocurrency/quotes/latest",
        params={"symbol": ",".join(symbols), "convert": convert},
        api_key=api_key,
        session=session,
    )
    return to_frame(list(data.values()), convert)


def to_frame(coins, convert="USD"):
    """Flatten the nested quote block into a tidy DataFrame."""
    rows = []
    for coin in coins:
        quote = coin["quote"][convert]
        rows.append({
            "id": coin["id"],
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


if __name__ == "__main__":
    df = get_listings(limit=10)
    print(df[["rank", "symbol", "name", "price", "pct_change_24h", "market_cap"]])
