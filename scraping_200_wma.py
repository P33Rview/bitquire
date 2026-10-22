import requests
import pandas as pd
import os
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def get_btc_weekly_data():
    """Extracting the 200-week data of Bitcoin from Yahoo Finance"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD"
    params = {
        "period1": int((datetime.now(timezone.utc) - timedelta(weeks=200)).timestamp()),
        "period2": int(datetime.now(timezone.utc).timestamp()),
        "interval": "1wk",
        "events": "history",
    }

    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=30
    )
    response.raise_for_status()
    data = response.json()["chart"]["result"][0]

    df = pd.DataFrame({
        "Date": pd.to_datetime(data["timestamp"], unit="s", utc=True),
        "Close": data["indicators"]["quote"][0]["close"]
    })
    return df


def get_200_wma():
    """Calculate the 200-week moving average BTC price"""
    df_btc = get_btc_weekly_data()

    # Calculate 200-week moving average
    df_btc["200WMA"] = df_btc["Close"].rolling(
        window=200,
        min_periods=200
    ).mean()

    result = (df_btc.dropna(subset=["200WMA"])["200WMA"]).iloc[-1]

    return result


def supabase_connection():
    """Establishing a supabase connection"""
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    # Establishing a supabase connection
    supabase: Client = create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )

    return supabase