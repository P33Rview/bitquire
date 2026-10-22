import os
from dotenv import load_dotenv
from scraping_200_wma import supabase_connection, get_200_wma

import pandas as pd
import numpy as np
import resend
import requests

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from html import escape

load_dotenv()
BASE_URL = "https://pro-api.coinmarketcap.com"

# Setting the min and max buy amounts
min_buy = 750
max_buy = 1500

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
    min_buy=min_buy,
    max_buy=max_buy,
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

    buy_amount = int(round(max_buy - position * (max_buy - min_buy), 0))
    usd_amount = round(buy_amount / get_czk_usd_exchange(), 2)
    btc_amount = round(usd_amount / btc_price, 7)

    return {"czk_amount": buy_amount,
            "usd_amount": usd_amount,
            "btc_amount": btc_amount}


def supabase_data_import(df):
    """Import calculated BTC buy amounts into Supabase."""

    columns = [
        "symbol",
        "pct_change_7d",
        "last_updated",
        "price",
        "200WMA",
        "fear_greed_index",
        "czk_amount",
        "usd_amount",
        "btc_amount"
    ]

    # Select the columns to upload
    data = df[columns].copy()

    # Convert datetime values to ISO format
    data["last_updated"] = pd.to_datetime(
        data["last_updated"]
    ).dt.strftime("%Y-%m-%dT%H:%M:%S%z")

    # Replace NaN values with None (JSON null)
    data = data.astype(object).where(pd.notna(data), None)

    # Convert DataFrame into list of dictionaries
    rows = data.to_dict(orient="records")

    # Insert data into Supabase
    response = (
        supabase_connection()
        .table("calculated_amount_to_buy")
        .insert(rows)
        .execute()
    )

    return response


def send_weekly_dca_email(df):
    """Send an HTML email with the weekly BTC DCA recommendation."""

    if df.empty:
        raise ValueError("No BTC data available to email.")

    row = df.iloc[0]

    price = float(row["price"])
    wma = float(row["200WMA"])
    fear_greed = float(row["fear_greed_index"])
    czk_amount = float(row["czk_amount"])
    usd_amount = float(row["usd_amount"])
    btc_amount = float(row["btc_amount"])

    ratio = price / wma

    report_date = datetime.now(
        ZoneInfo("Europe/Prague")
    ).strftime("%d %B %Y")

    def metric(label, value):
        return f"""
        <tr>
          <td style="padding:12px 0;color:#64748b;">
            {escape(label)}
          </td>
          <td style="padding:12px 0;text-align:right;
                     font-weight:600;color:#0f172a;">
            {escape(value)}
          </td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:32px 12px;
                 background:#f1f5f9;
                 font-family:Arial,sans-serif;">

      <table role="presentation" cellpadding="0" cellspacing="0"
             style="width:100%;max-width:520px;margin:auto;
                    background:white;border-radius:16px;">

        <tr>
          <td style="padding:32px;">

            <h1 style="font-size:24px;color:#0f172a;
                       margin:0 0 8px;">
              &#8383; Weekly DCA
            </h1>

            <p style="color:#64748b;margin:0 0 24px;">
              {report_date} · Weekly investment summary
            </p>

            <table role="presentation"
                   style="width:100%;border-collapse:collapse;">
              {metric("BTC Price", f"${price:,.2f}")}
              {metric("200-Week Moving Average", f"${wma:,.2f}")}
              {metric("BTC / 200 WMA Ratio", f"{ratio:.2f}x")}
              {metric("Fear & Greed Index", f"{fear_greed:.0f} / 100")}
            </table>

            <div style="background:#ecfdf5;border-radius:12px;
                        padding:24px;margin-top:24px;">

              <p style="color:#475569;margin:0 0 8px;">
                Recommended BTC Purchase
              </p>

              <h2 style="color:#059669;font-size:32px;
                           margin:0 0 3px;line-height:1.2;">
                  {czk_amount:,.2f} Kč
              </h2>
                
              <p style="color:#64748b;font-size:13px;
                          margin:0 0 24px;line-height:1.4;">
                  Purchase range: {min_buy:,.2f} – {max_buy:,.2f} Kč
              </p>
              
              <table role="presentation"
                     style="width:100%;border-collapse:collapse;">
                <tr>
                  <td style="padding:6px 0;">Amount in USD</td>
                  <td style="text-align:right;font-weight:bold;">
                    ${usd_amount:,.2f}
                  </td>
                </tr>
                <tr>
                  <td style="padding:6px 0;">BTC to buy</td>
                  <td style="text-align:right;font-weight:bold;">
                    {btc_amount:.8f} BTC
                  </td>
                </tr>
              </table>

            </div>

            <p style="font-size:12px;color:#94a3b8;
                      margin-top:24px;">
              Automatically generated using your
              BTC 200 WMA DCA strategy. <br> 
              Not financial advice.
            </p>

          </td>
        </tr>
      </table>

    </body>
    </html>
    """

    resend.api_key = os.environ["RESEND_API_KEY"]

    response = resend.Emails.send({
        "from": os.environ["EMAIL_FROM"],
        "to": os.environ["EMAIL_TO"],
        "subject": f"bitquire | {report_date}",
        "html": html
    })

    return response


if __name__ == "__main__":
    df = get_listings(1)
    df["fear_greed_index"] = fear_greed_index()
    df["200WMA"] = get_200_wma()

    # Adding calculated buy amount (CZK, USD and BTC)
    result = calculate_buy_amount()
    df = df.assign(**result)

    # Print calculated values
    with pd.option_context(
            "display.max_columns", None,
            "display.width", None
    ):
        print(df[[
            "symbol",
            "pct_change_7d",
            "last_updated",
            "price",
            "200WMA",
            "fear_greed_index",
            "czk_amount",
            "usd_amount",
            "btc_amount"
        ]])

    # Upload the same data to Supabase
    response = supabase_data_import(df)

    # Send email notification
    email_sending = send_weekly_dca_email(df)

    print("Data successfully uploaded to Supabase and sent to email!")
