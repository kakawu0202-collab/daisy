"""Recalculate K1 + Daily cache from DB data, write to BOTH engine and portal DBs."""
import sys, os, json, sqlite3
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data-engine'))
from storage.db import get_db, put_cache
from processor.k1 import compute as k1_compute
from processor.daily import compute as daily_compute
from processor.risk import compute as risk_compute
from processor.kpi import compute as kpi_compute

ROOT = os.path.dirname(os.path.abspath(__file__))

# Compute from engine DB
conn = get_db()
rows = [dict(r) for r in conn.execute('SELECT * FROM orders').fetchall()]
print(f'Loaded {len(rows)} records')

k1 = k1_compute(rows)
print(f'K1: {k1["total_qty"]:,} total, {k1["shipped"]:,} shipped, {k1["unshipped"]:,} unshipped')
ut = k1['cto_p1_unshipped'] + k1['fga_unshipped'] + k1['rtl_unshipped'] + k1['cto_p2_unshipped']
print(f'  Sum type unshipped: {ut:,} (card: {k1["unshipped"]:,}) Match: {ut == k1["unshipped"]}')

daily = daily_compute(rows)
# Preserve ASN/SN/fwd data from existing portal cache (recalc lacks raw ASN data)
portal_db = os.path.join(ROOT, 'data', 'portal.db')
pconn_ro = sqlite3.connect(portal_db)
row_old = pconn_ro.execute("SELECT data FROM cache WHERE key='daily_summary'").fetchone()
pconn_ro.close()
if row_old:
    old_daily = json.loads(row_old[0])
    if old_daily.get('date') == daily.get('date'):
        for k in ('asn', 'sn', 'fwd_dist', 'progress'):
            new_v = daily.get(k)
            old_v = old_daily.get(k)
            if old_v and (not new_v or (isinstance(new_v, dict) and not any(new_v.values()))):
                daily[k] = old_v
print(f'Daily: {daily.get("date")}, new orders: {daily.get("new_orders",{}).get("qty",0)}, ASN: {daily.get("asn",{}).get("s",0)}S/{daily.get("asn",{}).get("n",0)}N')

risks = risk_compute(rows)
kpi = kpi_compute(rows)

# Write to engine DB
for key, data in [('k1_summary', k1), ('daily_summary', daily), ('risks', risks), ('kpi', kpi)]:
    put_cache(conn, key, data)
conn.close()

# Write to portal DB
portal_db = os.path.join(ROOT, 'data', 'portal.db')
pconn = sqlite3.connect(portal_db)
pconn.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, data TEXT NOT NULL, computed_at TEXT NOT NULL)")
now = datetime.now().isoformat()
for key, data in [('k1_summary', k1), ('daily_summary', daily), ('risks', risks), ('kpi', kpi)]:
    pconn.execute('INSERT OR REPLACE INTO cache (key,data,computed_at) VALUES (?,?,?)',
        (key, json.dumps(data, ensure_ascii=False, default=str), now))
pconn.commit(); pconn.close()
print('Both engine and portal caches updated.')
