import requests
import pandas as pd
from datetime import datetime, timezone
from supabase import create_client, Client


def get_btc_weekly_data():
    """Extracting the 200-week data of Bitcoin from Yahoo Finance"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD"
    params = {
        "period1": 0,
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


def calculate_200_wma():
    """Calculate the 200-week moving average BTC price"""
    df_btc = get_btc_weekly_data()

    # Calculate 200-week moving average
    df_btc["200WMA"] = df_btc["Close"].rolling(
        window=200,
        min_periods=200
    ).mean()

    result = (df_btc.dropna(subset=["200WMA"])[["Date", "200WMA"]]).tail(1)

    return result


def supabase_connection():
    """Establishing a supabase connection"""
    SUPABASE_URL = "https://mzhomnjkelxmwlhafisp.supabase.co"
    SUPABASE_KEY = "sb_publishable_fELh3_L2GsNTRbM-Pzdaxg_Xfk5bXXL"

    # Establishing a supabase connection
    supabase: Client = create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )

    return supabase


def supabase_data_import():
    """Importing data into supabase"""
    row = calculate_200_wma().iloc[0].to_dict()
    row["Date"] = row["Date"].isoformat()

    response = (
        supabase_connection()
        .table("200_wma_btc")
        .insert(row)
        .execute()
    )

    return response


def return_supabase_wma():
    """Returning the latest 200-week moving average BTC price from supabase"""
    response = (
        supabase_connection()
        .table("200_wma_btc")
        .select("*")
        .execute()
        )

    df = pd.DataFrame(response.data).sort_values(by="Date", ascending=False).head(1)

    return df