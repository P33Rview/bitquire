const czk = n => new Intl.NumberFormat('cs-CZ',{style:'currency',currency:'CZK',maximumFractionDigits:0}).format(n);
const num = (n, digits=8) => Number(n).toFixed(digits);
const el = id => document.getElementById(id);
async function refresh() {
  try {
    const res = await fetch('/api/portfolio', {cache:'no-store'});
    if (!res.ok) throw new Error(res.status===401 ? 'Sign in to see your portfolio.' : `Unable to load data (${res.status}).`);
    const p = await res.json();
    el('value').textContent = czk(p.portfolio_value_czk);
    el('invested').textContent = czk(p.invested_czk);
    el('btc').textContent = `${num(p.btc_holdings)} BTC`;
    el('price').textContent = czk(p.btc_price_czk);
    el('average').textContent = p.btc_holdings ? czk(p.invested_czk / p.btc_holdings) : '—';
    const perf = el('performance');
    perf.className = p.profit_czk >= 0 ? 'positive' : 'negative';
    perf.textContent = `${p.profit_czk>=0?'+':''}${czk(p.profit_czk)} (${p.return_pct>=0?'+':''}${p.return_pct.toFixed(2)}%)`;
    const list = el('purchases'); list.replaceChildren();
    if (!p.purchases.length) list.textContent = 'No purchases recorded yet.';
    for (const purchase of p.purchases) {
      const row = document.createElement('div'); row.className='purchase';
      const left = document.createElement('div'); left.textContent='BTC purchase';
      const date = document.createElement('small'); date.textContent=new Date(purchase.purchased_at).toLocaleDateString('cs-CZ'); left.append(date);
      const right = document.createElement('div'); right.className='right'; right.textContent=czk(Number(purchase.czk_spent));
      const amount=document.createElement('small'); amount.textContent=`+${num(purchase.btc_amount)} BTC`; right.append(amount);
      row.append(left,right);list.append(row);
    }
    el('updated').textContent=`Updated ${new Date(p.as_of).toLocaleTimeString('cs-CZ')} · Refreshes every 60 seconds while open`;
  } catch(e) { el('updated').textContent=e.message; }
}
el('refresh').addEventListener('click',refresh);
refresh();
setInterval(()=>{if(!document.hidden) refresh()},60000);
