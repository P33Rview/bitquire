import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from supabase import create_client

BASE = Path(__file__).parent
app = FastAPI(title="BTC Portfolio")
security = HTTPBasic()
app.mount('/static', StaticFiles(directory=BASE / 'static'), name='static')

load_dotenv()

def require_login(credentials: HTTPBasicCredentials = Depends(security)):
    username = os.environ.get('APP_USERNAME')
    password = os.environ.get('APP_PASSWORD')
    if not username or not password:
        raise HTTPException(503, 'APP_USERNAME and APP_PASSWORD must be configured')
    if not (secrets.compare_digest(credentials.username, username)
            and secrets.compare_digest(credentials.password, password)):
        raise HTTPException(401, 'Invalid credentials', headers={'WWW-Authenticate': 'Basic'})


@app.get('/')
def index():
    return FileResponse(BASE / 'static' / 'index.html')


@app.get('/api/portfolio', dependencies=[Depends(require_login)])
async def portfolio():
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_KEY')
    if not url or not key:
        raise HTTPException(503, 'Supabase environment variables are missing')

    client = create_client(url, key)
    # Page through all purchases to avoid Supabase's default row limit.
    purchases = []
    offset = 0
    while True:
        batch = (client.table('btc_purchases')
                 .select('purchased_at,btc_amount,czk_spent')
                 .order('purchased_at', desc=True)
                 .range(offset, offset + 499).execute().data)
        purchases.extend(batch)
        if len(batch) < 500:
            break
        offset += 500

    async with httpx.AsyncClient(timeout=12) as http:
        try:
            response = await http.get(
                'https://api.coingecko.com/api/v3/simple/price',
                params={'ids': 'bitcoin', 'vs_currencies': 'czk'},
            )
            response.raise_for_status()
            price = float(response.json()['bitcoin']['czk'])
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise HTTPException(502, 'BTC market price temporarily unavailable') from exc

    invested = sum(float(p['czk_spent']) for p in purchases)
    btc = sum(float(p['btc_amount']) for p in purchases)
    value = btc * price
    profit = value - invested
    return {
        'as_of': datetime.now(timezone.utc).isoformat(),
        'btc_price_czk': price,
        'btc_holdings': round(btc, 8),
        'invested_czk': round(invested, 2),
        'portfolio_value_czk': round(value, 2),
        'profit_czk': round(profit, 2),
        'return_pct': round(profit / invested * 100, 2) if invested else 0,
        'purchases': purchases[:20],
    }
