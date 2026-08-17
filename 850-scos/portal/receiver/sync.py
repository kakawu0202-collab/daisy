"""Portal Receiver — accepts pushed data from Data Engine. Zero business logic."""
import os, json, sqlite3
from datetime import datetime

DB_PATH = os.environ.get('SCOS_PORTAL_DB') or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'portal.db')

SCHEMA = '''
CREATE TABLE IF NOT EXISTS orders (
    po TEXT NOT NULL, po_line TEXT NOT NULL DEFAULT '1',
    region TEXT, sub_type TEXT, priority TEXT, cto_p1 TEXT,
    mcid TEXT, ship_mode TEXT, scac TEXT, master_type TEXT,
    po_qty INTEGER DEFAULT 0, remain_qty INTEGER DEFAULT 0, ship_qty INTEGER DEFAULT 0,
    msbd TEXT, psd TEXT, final_msbd TEXT, po_received TEXT,
    status TEXT, ack_status TEXT, is_hold TEXT, hold_code TEXT, status_label TEXT,
    asn TEXT, hawb TEXT, dpn TEXT, ipn TEXT, dell_so TEXT,
    ship_to_country TEXT, description TEXT,
    input_cdt TEXT, stockin_cdt TEXT, sn_cdt TEXT, createasn_cdt TEXT,
    stbl INTEGER DEFAULT 0, atb INTEGER DEFAULT 0, wip INTEGER DEFAULT 0,
    fg INTEGER DEFAULT 0, sn INTEGER DEFAULT 0,
    actual_shipped INTEGER DEFAULT 0, shipped_qty INTEGER DEFAULT 0, asn_pending INTEGER DEFAULT 0,
    updated_at TEXT, hash TEXT,
    PRIMARY KEY (po, po_line)
);
CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, data TEXT NOT NULL, computed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, sync_time TEXT,
    added INTEGER DEFAULT 0, updated INTEGER DEFAULT 0, total INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_orders_cto_p1 ON orders(cto_p1);
'''

def _db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    try: conn.execute('ALTER TABLE orders ADD COLUMN shipped_qty INTEGER DEFAULT 0')
    except sqlite3.OperationalError: pass
    try: conn.execute('ALTER TABLE orders ADD COLUMN asn_pending INTEGER DEFAULT 0')
    except sqlite3.OperationalError: pass
    conn.commit()
    return conn

FIELDS = ['po','po_line','region','sub_type','priority','cto_p1','mcid','ship_mode','scac',
    'master_type','po_qty','remain_qty','ship_qty','msbd','psd','final_msbd','po_received',
    'status','ack_status','is_hold','hold_code','status_label','asn','hawb','dpn','ipn','dell_so',
    'ship_to_country','description','input_cdt','stockin_cdt','sn_cdt','createasn_cdt',
    'stbl','atb','wip','fg','sn','actual_shipped','shipped_qty','asn_pending','updated_at','hash']

def handle_sync(payload):
    """Store pushed data. Returns {ok, added, updated}."""
    records = payload.get('records', [])
    now = datetime.now().isoformat()
    conn = _db()

    added = updated = 0
    for r in records:
        h = str(hash('|'.join(str(r.get(k,'')) for k in sorted(r.keys()) if k not in ('updated_at','hash'))))
        r['hash'] = h; r['updated_at'] = now
        ex = conn.execute('SELECT hash FROM orders WHERE po=? AND po_line=?',
            (str(r.get('po','')), str(r.get('po_line','1')))).fetchone()
        vals = [r.get(f, '') for f in FIELDS]
        if ex:
            if ex['hash'] != h:
                conn.execute(f'UPDATE orders SET {",".join(f+"=?" for f in FIELDS)} WHERE po=? AND po_line=?',
                    vals + [str(r.get('po','')), str(r.get('po_line','1'))])
                updated += 1
        else:
            conn.execute(f'INSERT OR REPLACE INTO orders ({",".join(FIELDS)}) VALUES ({",".join("?" for _ in FIELDS)})', vals)
            added += 1

    # Store cache items (k1_summary, daily_summary, risks, kpi)
    for key in ('k1_summary', 'daily_summary', 'risks', 'risk_summary', 'kpi', 'e2e_kpi'):
        data = payload.get(key)
        if data:
            conn.execute('INSERT OR REPLACE INTO cache (key,data,computed_at) VALUES (?,?,?)',
                (key, json.dumps(data, ensure_ascii=False, default=str), now))

    conn.execute('INSERT INTO sync_log (sync_time,added,updated,total) VALUES (?,?,?,(SELECT COUNT(*) FROM orders))',
        [now, added, updated])
    conn.commit()
    conn.close()
    return {'ok': True, 'added': added, 'updated': updated}
