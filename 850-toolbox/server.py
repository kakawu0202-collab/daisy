"""
850 Toolbox Server — 统一工具箱平台
启动: python server.py
访问: http://localhost:8500
"""
import sys, os, io, json, time, hashlib, secrets, sqlite3
from datetime import datetime, timedelta, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
import requests
from concurrent.futures import ThreadPoolExecutor
import threading

_oms_lock = threading.Lock()

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in separate threads."""
    daemon_threads = True
import urllib.request
import urllib.parse
import threading

if sys.platform == 'win32' and sys.stdout:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PORT = 8500
SESSION_DAYS = 30
ADMIN_PW = os.environ.get('TOOLBOX_ADMIN', 'admin850')  # admin password for /admin

# ── User Database ──────────────────────────────────────────
USER_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'users.db')
_sessions = {}  # token -> {'user': username, 'expires': datetime}

def _init_db():
    db = sqlite3.connect(USER_DB)
    db.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')
    db.commit(); db.close()

def _hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def _check_auth(handler):
    """Return username if authenticated, None otherwise."""
    cookies = handler.headers.get('Cookie', '')
    token = ''
    for c in cookies.split(';'):
        c = c.strip()
        if c.startswith('tb_token='):
            token = c[9:]
    if token and token in _sessions:
        sess = _sessions[token]
        if datetime.now() < sess['expires']:
            # Also verify user is still active in DB
            try:
                db = sqlite3.connect(USER_DB)
                row = db.execute('SELECT status FROM users WHERE username=?', (sess['user'],)).fetchone()
                db.close()
                if row and row[0] == 'active':
                    return sess['user']
            except: pass
        del _sessions[token]
    return None

def _require_auth(handler):
    """Check auth; if not logged in, redirect to login."""
    user = _check_auth(handler)
    if not user:
        handler.send_response(302)
        handler.send_header('Location', '/login.html')
        handler.end_headers()
        return None
    return user

OMS_URL = 'http://luxoms-vn-prod.luxshare-ict.com'
TOOLBOX_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(TOOLBOX_DIR, 'static')
DATA_DIR = os.path.join(TOOLBOX_DIR, 'data')
CACHE_FILE = os.path.join(DATA_DIR, 'oms_cache.json')
FGA_HOLD_FILE = os.path.join(DATA_DIR, 'fga_hold.csv')
FGA_STATUS_FILE = os.path.join(DATA_DIR, 'fga_status.csv')

os.makedirs(DATA_DIR, exist_ok=True)
_init_db()
os.makedirs(STATIC_DIR, exist_ok=True)

# 870 FGA 分配（同目录模块）
try:
    from fga870_loader import run_allocation
except Exception as _e:
    run_allocation = None
    print(f'  [warn] fga870_loader 未加载: {_e}')

# ── OMS Client ─────────────────────────────────────────────
class OMSClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({'Content-Type': 'application/json;charset=UTF-8',
                                     'User-Agent': 'Mozilla/5.0'})
        self.token = None
        self.cached_data = None
        self._load_cache()

    def _load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    self.cached_data = json.load(f)
            except: pass

    def _save_cache(self, data):
        self.cached_data = data
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except: pass

    def _get(self, path):
        h = {} if not self.token else {'token': self.token}
        try:
            r = self.session.get(OMS_URL + path, headers=h, timeout=30)
            return r.json() if r.ok else {'error': f'HTTP {r.status_code}'}
        except requests.exceptions.ConnectionError:
            return {'error': f'连接 OMS 失败。请确认 VPN 已连接。'}
        except Exception as e:
            return {'error': str(e)}

    def _post(self, path, body):
        h = {} if not self.token else {'token': self.token}
        try:
            r = self.session.post(OMS_URL + path, json=body, headers=h, timeout=60)
            return r.json() if r.ok else {'error': f'HTTP {r.status_code}: {r.text[:200]}'}
        except requests.exceptions.ConnectionError:
            return {'error': f'连接 OMS 失败。请确认 VPN 已连接。'}
        except Exception as e:
            return {'error': str(e)}

    def login(self, account, password):
        resp = self._post('/api/auth/login', {'account': account, 'password': password})
        token = resp.get('token') or (resp.get('data', {}) or {}).get('token')
        if token: self.token = token
        return token is not None

    def fetch_one_report(self, report_id):
        """Fetch a single report (config + data)."""
        cfg = self._get(f'/api/ReportSetting/GetReportByID?report_id={report_id}')
        if 'error' in cfg: return ('error', cfg['error'], report_id)

        data = cfg.get('data', {})
        report_name = data.get('REPORT_NAME', '') or data.get('reportName', '')
        details_str = data.get('REPORT_DETAILS', '{}')
        try: details = json.loads(details_str)
        except: details = details_str if isinstance(details_str, dict) else {}
        sql = (details.get('mainReport', {}) or {}).get('sql', '') if isinstance(details, dict) else ''
        fields = (details.get('mainReport', {}) or {}).get('fields', []) if isinstance(details, dict) else []

        body = {'report_id': report_id, 'reportName': report_name,
                'pagination': {'page': 1, 'pageSize': 50000},
                'parameters': {}, 'parentContext': None,
                'sql': sql, 'fields': fields}
        resp = self._post('/api/ReportSetting/QueryDynamicReport', body)
        if 'error' in resp: return ('error', resp['error'], report_id)
        rows = resp.get('data', {}).get('ResultData', resp.get('ResultData', []))
        return ('ok', rows, report_id)

    def fetch_all(self, account, password):
        ok = self.login(account, password)
        if not ok: return {'error': 'OMS 登录失败', 'account': account}

        result = {'time': datetime.now().isoformat(), 'account': account}
        print('  Login OK, fetching reports...')

        # Sequential fetch (more reliable than nested threading)
        for rid, key in [('0848012288','rpt_850_po'), ('1593920512','rpt_e2e'), ('0320073728','rpt_gpp'),
                         ('0886717440','rpt_asn'), ('1780017152','rpt_shipment')]:
            try:
                status, data, rid2 = self.fetch_one_report(rid)
                if status == 'ok':
                    result[key] = data
                    # Map to expected count keys
                    cnt_key = {'rpt_850_po':'po_count','rpt_e2e':'e2e_count','rpt_gpp':'gpp_count'}.get(key, key+'_count')
                    result[cnt_key] = len(data)
                    print(f'  {key}: {len(data)} rows OK')
                else:
                    print(f'  {key}: ERROR - {data}')
                    result[key] = []
            except Exception as e:
                print(f'  {key}: EXCEPTION - {e}')
                result[key] = []

        self._save_cache(result)
        return result

oms = OMSClient()

# ── Auto-pull scheduler ────────────────────────────────────
AUTO_PULL_INTERVAL = 600  # 10 minutes
def _creds_path():
    return os.path.join(DATA_DIR, 'oms_creds.json')

def load_creds():
    path = _creds_path()
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {}

def save_creds(account, password):
    try:
        with open(_creds_path(), 'w', encoding='utf-8') as f:
            json.dump({'account': account, 'password': password}, f)
    except: pass

def auto_pull():
    creds = load_creds()
    if not creds.get('password'):
        return
    try:
        result = oms.fetch_all(creds.get('account', '31000161'), creds['password'])
        if 'error' not in result:
            print(f'Auto-pull OK: {result.get("po_count",0)} PO, {result.get("e2e_count",0)} E2E')
        else:
            print(f'Auto-pull FAIL: {result.get("error","")}')
    except Exception as e:
        print(f'Auto-pull ERR: {e}')

def start_auto_pull():
    import threading
    creds = load_creds()
    if not creds.get('password'):
        return
    def run():
        while True:
            time.sleep(AUTO_PULL_INTERVAL)
            try: auto_pull()
            except: pass
    t = threading.Thread(target=run, daemon=True)
    t.start()
    print(f'Auto-pull enabled (every {AUTO_PULL_INTERVAL//60}min)')


# ── Auto-Pull Background Thread ─────────────────────────────
AUTO_PULL_INTERVAL = 10 * 60  # 10 minutes between OMS pulls
_auto_pull_state = {'running': False, 'last_pull': None, 'last_result': '', 'next_pull': None}

def _auto_pull_loop():
    account = '31000161'
    password = os.environ.get('OMS_PASSWORD', '')
    if not password:
        _auto_pull_state['last_result'] = 'OMS_PASSWORD 环境变量未设置'
        print('[auto-pull] OMS_PASSWORD not set in env — auto-pull disabled')
        return
    _auto_pull_state['running'] = True
    print(f'[auto-pull] Started — every {AUTO_PULL_INTERVAL//60} min')
    # Do an initial pull immediately on startup
    time.sleep(3)  # brief delay to let server fully start
    try:
        print(f'[auto-pull] Initial pull from OMS...')
        result = oms.fetch_all(account, password)
        _auto_pull_state['last_pull'] = datetime.now().isoformat()
        if 'error' in result:
            _auto_pull_state['last_result'] = f'FAIL: {result["error"]}'
            print(f'[auto-pull] Initial FAILED: {result["error"]}')
        else:
            cnt = result.get('po_count', 0)
            _auto_pull_state['last_result'] = f'OK: {cnt} PO rows'
            print(f'[auto-pull] Initial OK — {cnt} PO rows')
    except Exception as e:
        _auto_pull_state['last_pull'] = datetime.now().isoformat()
        _auto_pull_state['last_result'] = f'ERROR: {e}'
        print(f'[auto-pull] Initial ERROR: {e}')
    while True:
        _auto_pull_state['next_pull'] = (datetime.now() + timedelta(seconds=AUTO_PULL_INTERVAL)).isoformat()
        time.sleep(AUTO_PULL_INTERVAL)
        try:
            print(f'[auto-pull] Pulling from OMS...')
            result = oms.fetch_all(account, password)
            _auto_pull_state['last_pull'] = datetime.now().isoformat()
            if 'error' in result:
                _auto_pull_state['last_result'] = f'FAIL: {result["error"]}'
                print(f'[auto-pull] FAILED: {result["error"]}')
            else:
                cnt = result.get('po_count', 0)
                _auto_pull_state['last_result'] = f'OK: {cnt} PO rows'
                print(f'[auto-pull] OK — {cnt} PO rows')
        except Exception as e:
            _auto_pull_state['last_pull'] = datetime.now().isoformat()
            _auto_pull_state['last_result'] = f'ERROR: {e}'
            print(f'[auto-pull] ERROR: {e}')

_auto_pull_thread = threading.Thread(target=_auto_pull_loop, daemon=True)
_auto_pull_thread.start()

# ── Helper: merge data for tools ───────────────────────────
DIRTY_DATES = {"0001-01-01T00:00:00Z","0001-01-01T06:00:00Z","1900-01-01T00:00:00Z","1900-01-01T06:00:00Z","0001-01-01","1900-01-01"}

def cd(v):
    if v is None: return None
    s = str(v).strip()
    if not s or s in DIRTY_DATES: return None
    return s[:10]

def merge_records(data, include_all=False):
    po_data = data.get('rpt_850_po', [])
    e2e_data = data.get('rpt_e2e', [])
    gpp_data = data.get('rpt_gpp', [])
    asn_data = data.get('rpt_asn', [])
    ship_data = data.get('rpt_shipment', [])

    if isinstance(po_data, dict): po_data = po_data.get('data', po_data.get('ResultData', []))
    if isinstance(e2e_data, dict): e2e_data = e2e_data.get('data', e2e_data.get('ResultData', []))
    if isinstance(gpp_data, dict): gpp_data = gpp_data.get('data', gpp_data.get('ResultData', []))
    if isinstance(asn_data, dict): asn_data = asn_data.get('data', asn_data.get('ResultData', []))
    if isinstance(ship_data, dict): ship_data = ship_data.get('data', ship_data.get('ResultData', []))

    po_all = po_data if include_all else [p for p in po_data if p.get('MASTER_TYPE') == 'PRD']

    e2e_map = {}
    for e in (e2e_data or []):
        e2e_map[f"{e.get('PO','')}_{e.get('PO_LINE','')}"] = e

    gpp_map = {}
    for g in (gpp_data or []):
        gpp_map[f"{g.get('PO','')}_{g.get('PO_LINE','')}"] = g

    # Build ASN → SN_STATUS lookup
    asn_status_map = {}
    for a in (asn_data or []):
        asn_id = str(a.get('ASN','')).strip()
        sn_status = str(a.get('SN_STATUS','')).strip().upper()
        if asn_id:
            # Keep best status: S > SN ACK > others
            prev = asn_status_map.get(asn_id, '')
            if sn_status == 'S' or (prev != 'S' and sn_status):
                asn_status_map[asn_id] = sn_status

    # Build PO → SN_STATUS via Shipment.ASN → ASN.SN_STATUS chain
    po_sn_map = {}
    for s in (ship_data or []):
        po = str(s.get('PO','')).strip()
        asn_id = str(s.get('ASN','')).strip()
        if po and asn_id:
            sn = asn_status_map.get(asn_id, '')
            if sn:
                prev = po_sn_map.get(po, '')
                if sn == 'S' or (prev != 'S' and sn):
                    po_sn_map[po] = sn

    records = []
    for p in po_all:
        e = e2e_map.get(f"{p.get('PO','')}_{p.get('PO_LINE','')}", {})
        g = gpp_map.get(f"{p.get('PO','')}_{p.get('PO_LINE','')}", {})
        sub = p.get('SUB_TYPE','')
        pri = str(p.get('PRIORITY',''))
        cto_p1 = 'Y' if (sub == 'CTO' and pri == '1') else ''
        po_qty = p.get('PO_QTY',0) or 0
        sn_qty = int(e.get('SN_QTY') or 0)
        sn_cdt_val = cd(e.get('SN_CDT'))
        po_str = str(p.get('PO','')).strip()
        po_sn = po_sn_map.get(po_str, '')
        # Shipped: S or SN ACK (NONE → ... → S → SN ACK)
        actual_shipped = po_sn in ('S', 'SN ACK')
        asn_pending = bool(po_sn) and not actual_shipped  # ASN exists but SN is NONE etc

        # Computed status label
        raw_status = p.get('STATUS','')
        ack = p.get('ACK_STATUS','')
        if ack == 'REJECT':
            status_label = 'NACK (被拒绝)'
        elif raw_status == 'ZC':
            status_label = 'ZC (已取消)'
        elif raw_status == 'Close':
            status_label = 'CLOSE (正常关闭)'
        elif raw_status == 'Open':
            status_label = 'OPEN (Backlog)' if not sn_cdt_val else 'OPEN'
        elif raw_status == 'E':
            status_label = 'V (校验中未pass)'
        else:
            status_label = raw_status

        # Compute production status from E2E station dates
        # SN: has SN_CDT → shipped
        # FG: has STOCKIN_CDT but no SN_CDT → finished goods in warehouse
        # WIP: has INPUT_CDT but no STOCKIN_CDT → in production line
        # ATB: has WIP/FG activity but no INPUT_CDT → material ready, not yet on line
        # STBL: no activity at all → waiting for material
        stockin_cdt = e.get('STOCKIN_CDT')
        input_cdt = e.get('INPUT_CDT')
        aft_cdt = e.get('AFT_CDT')

        if sn_cdt_val:
            e2e_sn = sn_qty  # Shipped
        else:
            e2e_sn = 0

        if stockin_cdt and not sn_cdt_val:
            e2e_fg = int(e.get('STOCKIN_QTY') or 0) or (po_qty - e2e_sn)  # FG: stocked in
        else:
            e2e_fg = 0

        if input_cdt and not stockin_cdt:
            # WIP: from input to before stockin
            e2e_wip = po_qty - e2e_sn - e2e_fg
        else:
            e2e_wip = 0

        if not input_cdt and (stockin_cdt or aft_cdt):
            # ATB: material complete but not yet input to line
            e2e_atb = po_qty - e2e_sn - e2e_fg - e2e_wip
        else:
            e2e_atb = 0

        # STBL: no activity at all
        e2e_stbl = po_qty - e2e_sn - e2e_fg - e2e_wip - e2e_atb
        if e2e_stbl < 0: e2e_stbl = 0
        if e2e_atb < 0: e2e_atb = 0
        if e2e_wip < 0: e2e_wip = 0

        # Prefer GPP data if available, otherwise use E2E-derived
        has_gpp = g and (g.get('WIP') or g.get('FG') or g.get('SN') or g.get('STBL') or g.get('ATB'))

        r = {
            'PO': str(p.get('PO','')).strip(),
            'PO_LINE': str(p.get('PO_LINE','')),
            'DELL_SO': p.get('DELL_SO'), 'DPN': p.get('DPN'), 'IPN': p.get('IPN'),
            'REGION': p.get('REGION'), 'SHIP_MODE': p.get('SHIP_MODE'),
            'SCAC': p.get('SCAC'), 'MCID': p.get('MCID'),
            'MASTER_TYPE': p.get('MASTER_TYPE'),
            'SUB_TYPE': sub, 'PRIORITY': pri,
            'CTO_P1': cto_p1,
            'PO_QTY': po_qty,
            'REMAIN_QTY': p.get('REMAIN_QTY',0) or 0,
            'SHIP_QTY': p.get('SHIP_QTY',0) or 0,
            'MSBD': cd(p.get('MSBD')), 'PSD': cd(p.get('PSD')),
            'FINAL_MSBD': cd(p.get('FINAL_MSBD')),
            'PO_RECEIVE_DATE': cd(p.get('PO_RECEIVE_DATE')),
            'STATUS': p.get('STATUS'), 'STATUS_LABEL': status_label,
            'ACK_STATUS': p.get('ACK_STATUS'),
            'IS_HOLD': p.get('IS_HOLD'), 'HOLD_CODE': p.get('HOLD_CODE'),
            'ASN': str(p.get('ASN','')) if p.get('ASN') else '',
            'HAWB': str(p.get('HAWB','')) if p.get('HAWB') else '',
            'DESCRIPTION': str(p.get('DESCRIPTION',''))[:80] if p.get('DESCRIPTION') else '',
            'SHIP_TO_COUNTRY': p.get('SHIP_TO_COUNTRY'),
            'PALLET_QTY': p.get('PALLET_QTY',0) or 0,
            'CARTON_QTY': p.get('CARTON_QTY',0) or 0,
            'STBL': (int(g.get('STBL') or 0) if has_gpp else e2e_stbl),
            'ATB': (int(g.get('ATB') or 0) if has_gpp else e2e_atb),
            'WIP': (int(g.get('WIP') or 0) if has_gpp else e2e_wip),
            'FG': (int(g.get('FG') or 0) if has_gpp else e2e_fg),
            'SN': (int(g.get('SN') or 0) if has_gpp else e2e_sn),
            'SN_CDT': sn_cdt_val,
            'ACTUAL_SHIPPED': actual_shipped,
            'ASN_STATUS': po_sn if not actual_shipped else '',  # SN_STATUS for backlog records
            'ASN_PENDING': asn_pending,
        }
        records.append(r)
    return records

# ── HTTP Handler ──────────────────────────────────────────
def fga_po_rows():
    """从缓存取 850 原始行（供 FGA 分配）。"""
    if not oms.cached_data:
        return []
    rows = oms.cached_data.get('rpt_850_po', [])
    if isinstance(rows, dict):
        rows = rows.get('data', rows.get('ResultData', []))
    return rows or []


class ToolboxHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        # Auth check for protected pages
        protected = ['/k1.html','/shipped.html','/sort.html','/fga870.html','/a2.html','/index.html','/']
        if path in protected or (path.endswith('.html') and path not in ['/login.html','/admin.html','/offline.html']):
            user = _require_auth(self)
            if not user: return

        if path == '/api/logout':
            cookies = self.headers.get('Cookie', '')
            token = ''
            for c in cookies.split(';'):
                c = c.strip()
                if c.startswith('tb_token='):
                    token = c[9:]
            if token in _sessions:
                del _sessions[token]
            self.send_response(302)
            self.send_header('Location', '/login.html')
            self.send_header('Set-Cookie', 'tb_token=; Path=/; Max-Age=0')
            self.end_headers()

        elif path == '/api/health':
            # Health check + data freshness for PWA auto-refresh
            now = datetime.now().isoformat()
            cached_time = oms.cached_data.get('time','') if oms.cached_data else ''
            oms_ok = False
            try:
                test = oms._get('/api/Dashboard/Get850ForDashboard')
                oms_ok = 'error' not in test
            except: pass
            self._json_response({
                'status': 'ok',
                'server_time': now,
                'data_cached': oms.cached_data is not None,
                'data_time': cached_time,
                'oms_reachable': oms_ok,
                'version': '3.3.0-pwa',
                'auto_pull': {
                    'running': _auto_pull_state['running'],
                    'interval_min': AUTO_PULL_INTERVAL // 60,
                    'last_pull': _auto_pull_state['last_pull'],
                    'last_result': _auto_pull_state['last_result'],
                    'next_pull': _auto_pull_state['next_pull'],
                },
            })

        elif path == '/api/cache':
            self._json_response({
                'cached': oms.cached_data is not None,
                'time': oms.cached_data.get('time','') if oms.cached_data else '',
                'po_count': oms.cached_data.get('po_count',0) if oms.cached_data else 0,
                'e2e_count': oms.cached_data.get('e2e_count',0) if oms.cached_data else 0,
                'gpp_count': oms.cached_data.get('gpp_count',0) if oms.cached_data else 0,
            })

        elif path == '/api/sort-data':
            if not oms.cached_data:
                self._json_response({'error': 'No cached data. Pull OMS first.'}, 400)
                return
            records = merge_records(oms.cached_data, include_all=True)
            # Filter params
            qs = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(qs)
            for key in ['REGION','SUB_TYPE','STATUS','ACK_STATUS','SHIP_MODE','SCAC','MCID','CTO_P1']:
                v = (params.get(key.lower(),[''])[0]).strip()
                if v:
                    records = [r for r in records if str(r.get(key,'')) == v]
            msbd_val = (params.get('msbd',[''])[0]).strip()
            if msbd_val:
                records = [r for r in records if r.get('MSBD','') and str(r.get('MSBD',''))[:10] == msbd_val]
            sn_val = (params.get('sn',[''])[0]).strip()
            if sn_val:
                records = [r for r in records if r.get('SN_CDT','') and str(r.get('SN_CDT',''))[:10] == sn_val]
            shipped = (params.get('shipped',[''])[0]).strip()
            if shipped == '1':
                records = [r for r in records if r.get('ACTUAL_SHIPPED')]
            elif shipped == '0':
                records = [r for r in records if not r.get('ACTUAL_SHIPPED')]
            gpp_status = (params.get('gpp',[''])[0]).strip().upper()
            if gpp_status in ['STBL','ATB','WIP','FG','SN']:
                records = [r for r in records if int(r.get(gpp_status) or 0) > 0]
            po_list = params.get('po', [])
            if po_list:
                records = [r for r in records if str(r.get('PO','')).strip() in po_list]
            po_f = (params.get('po_from',[''])[0]).strip()
            po_t = (params.get('po_to',[''])[0]).strip()
            if po_f or po_t:
                def in_range(r):
                    prd = r.get('PO_RECEIVE_DATE','')
                    if not prd: return False
                    try: d = datetime.strptime(str(prd)[:10], '%Y-%m-%d').date()
                    except: return False
                    if po_f and d < datetime.strptime(po_f, '%Y-%m-%d').date(): return False
                    if po_t and d > datetime.strptime(po_t, '%Y-%m-%d').date(): return False
                    return True
                records = [r for r in records if in_range(r)]
            limit = int((params.get('limit',['500'])[0]) or '500')
            records = records[:limit]
            self._json_response({'records': records, 'total': len(records)})

        elif path == '/api/daily-summary':
            if not oms.cached_data:
                self._json_response({'error': 'No cached data'}, 400)
                return
            try:
                records = merge_records(oms.cached_data, include_all=False)
            except Exception as _e:
                self._json_response({'error': 'merge_records failed: '+str(_e)}, 500)
                return
            # Support date parameter for historical review
            qs2 = urllib.parse.urlparse(self.path).query
            params2 = urllib.parse.parse_qs(qs2)
            date_str = (params2.get('date', [''])[0]).strip()
            vn_tz = timezone(timedelta(hours=7))
            now_vn = datetime.now(vn_tz)
            if date_str:
                try:
                    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    today_5am = datetime(target_date.year, target_date.month, target_date.day, 5, 0, 0, tzinfo=vn_tz)
                except:
                    today_5am = now_vn.replace(hour=5, minute=0, second=0, microsecond=0)
            else:
                today_5am = now_vn.replace(hour=5, minute=0, second=0, microsecond=0)
            if not date_str and now_vn.hour < 5: today_5am -= timedelta(days=1)
            tomorrow_5am = today_5am + timedelta(days=1)
            display_date = today_5am.strftime('%Y-%m-%d')
            # Shipment date: natural day (midnight-midnight VN), not 5am window
            if date_str:
                ship_date_str = date_str
            else:
                ship_date_str = now_vn.strftime('%Y-%m-%d')

            # Today's orders (PO received in VN 5am-5am window)
            today = []
            for r in records:
                prd = r.get('PO_RECEIVE_DATE')
                if not prd: continue
                try: dt = datetime.strptime(str(prd)[:19], '%Y-%m-%dT%H:%M:%S'); dt = dt.replace(tzinfo=vn_tz)
                except:
                    try: dt = datetime.strptime(str(prd)[:10], '%Y-%m-%d'); dt = dt.replace(hour=12, tzinfo=vn_tz)
                    except: continue
                if today_5am <= dt < tomorrow_5am: today.append(r)

            # Today's ASN data
            asn_data = oms.cached_data.get('rpt_asn', [])
            if isinstance(asn_data, dict): asn_data = asn_data.get('data', asn_data.get('ResultData', []))
            today_asn = {'n':0, 's':0, 'ack':0, 'nack':0, 's_no_ack':0}
            for a in (asn_data or []):
                ship_date = a.get('SHIP_DATE','')
                if ship_date and str(ship_date)[:10] == ship_date_str:
                    sns = str(a.get('SN_STATUS','')).upper()
                    asns = str(a.get('ASN_STATUS','')).upper()
                    # SN S = S or SN ACK (both are shipped)
                    if sns in ('S', 'SN ACK'): today_asn['s'] += 1
                    else: today_asn['n'] += 1
                    # ACK/NACK from ASN_STATUS
                    if 'NACK' in asns: today_asn['nack'] += 1
                    elif 'ACK' in asns: today_asn['ack'] += 1
                    # Alert: S sent but no ACK response yet
                    if sns in ('S', 'SN ACK') and 'ACK' not in asns and 'NACK' not in asns:
                        today_asn['s_no_ack'] += 1

            # Today's shipped: from Shipment report (natural day)
            ship_data = oms.cached_data.get('rpt_shipment', [])
            if isinstance(ship_data, dict): ship_data = ship_data.get('data', ship_data.get('ResultData', []))
            today_shipped = {'count':0, 'qty':0}
            for s_ in (ship_data or []):
                sd = s_.get('SHIP_DATE','')
                if sd and str(sd)[:10] == ship_date_str:
                    today_shipped['count'] += 1
                    today_shipped['qty'] += s_.get('SHIP_QTY',0) or 0

            # SN S = ASN records with SN_STATUS in (S, SN ACK) and SHIP_DATE=today
            today_sn = {'s': sum(1 for a in (asn_data or []) if str(a.get('SN_STATUS','')).upper() in ('S','SN ACK') and str(a.get('SHIP_DATE',''))[:10]==ship_date_str)}

            # Today breakdowns
            by_type = {}; by_region = {}
            for r in today:
                t = 'CTO_P1' if r.get('CTO_P1')=='Y' else r.get('SUB_TYPE','?')
                by_type[t] = by_type.get(t,0) + r.get('PO_QTY',0)
                reg = r.get('REGION','?')
                by_region[reg] = by_region.get(reg,0) + r.get('PO_QTY',0)

            nack_today = [r for r in today if r.get('ACK_STATUS')=='REJECT']
            zc_today = [r for r in today if r.get('STATUS')=='ZC']
            open_today = [r for r in today if r.get('STATUS')=='Open' and r.get('ACK_STATUS')!='REJECT']

            # Historical order trends (last 30 days, by type)
            order_trend = {}
            _d = today_5am
            for i in range(30):
                day_start = _d - timedelta(days=i); day_end = day_start + timedelta(days=1)
                ds = day_start.strftime('%m/%d')
                day_recs = []
                for r in records:
                    prd = r.get('PO_RECEIVE_DATE')
                    if not prd: continue
                    try: dt = datetime.strptime(str(prd)[:10], '%Y-%m-%d'); dt = dt.replace(tzinfo=vn_tz)
                    except: continue
                    if day_start <= dt < day_end: day_recs.append(r)
                order_trend[ds] = {
                    'total': len(day_recs), 'qty': sum(r.get('PO_QTY',0) for r in day_recs),
                    'cto_p1': sum(r.get('PO_QTY',0) for r in day_recs if r.get('CTO_P1')=='Y'),
                    'fga': sum(r.get('PO_QTY',0) for r in day_recs if r.get('SUB_TYPE')=='FGA'),
                    'rtl': sum(r.get('PO_QTY',0) for r in day_recs if r.get('SUB_TYPE')=='RTL'),
                    'cto_p2': sum(r.get('PO_QTY',0) for r in day_recs if r.get('SUB_TYPE')=='CTO' and r.get('CTO_P1')!='Y'),
                }

            # Historical shipment trends (last 30 days, by type, from shipment report)
            ship_trend = {}
            for i in range(30):
                day_start = _d - timedelta(days=i); day_end = day_start + timedelta(days=1)
                ds = day_start.strftime('%m/%d')
                day_ships = [s_ for s_ in (ship_data or []) if s_.get('SHIP_DATE') and str(s_.get('SHIP_DATE',''))[:10] == day_start.strftime('%Y-%m-%d')]
                ship_trend[ds] = {
                    'total': sum(s_.get('SHIP_QTY',0) or 0 for s_ in day_ships),
                    'count': len(day_ships),
                }

            # MSBD today (non-CTO P1) + CTO P1 28H today
            today_msbd = [r for r in records if r.get('CTO_P1')!='Y' and r.get('MSBD') and str(r.get('MSBD',''))[:10]==display_date]
            today_cto28h = []
            for r in records:
                if r.get('CTO_P1')!='Y': continue
                prd = r.get('PO_RECEIVE_DATE')
                if not prd: continue
                try: dt = datetime.strptime(str(prd)[:19], '%Y-%m-%dT%H:%M:%S')
                except: continue
                if (dt + timedelta(hours=28)).strftime('%Y-%m-%d') == display_date:
                    today_cto28h.append(r)
            def plan_status(subset):
                return {
                    'stbl': sum(int(r.get('STBL') or 0) for r in subset),
                    'atb': sum(int(r.get('ATB') or 0) for r in subset),
                    'wip': sum(int(r.get('WIP') or 0) for r in subset),
                    'fg': sum(int(r.get('FG') or 0) for r in subset),
                    'sn': sum(int(r.get('SN') or 0) for r in subset),
                    'count': len(subset), 'qty': sum(r.get('PO_QTY',0) for r in subset),
                }

            # Shipment progress tracking
            today_shipments = [s_ for s_ in (ship_data or []) if s_.get('SHIP_DATE') and str(s_.get('SHIP_DATE',''))[:10]==ship_date_str]
            pps_done = today_shipped['count']  # match shipment count
            asn_s_total = sum(1 for a in (asn_data or []) if str(a.get('SN_STATUS','')).upper()=='S')
            truck_count = len(set(str(s_.get('TRUCK_NO','')) for s_ in today_shipments if str(s_.get('TRUCK_NO','')).strip()))
            # Forwarder distribution from shipment report
            fwd_dist = {}
            for s_ in today_shipments:
                scac = str(s_.get('SCAC','') or s_.get('Ship mode','')).strip()
                if scac:
                    fwd_dist[scac] = fwd_dist.get(scac,0) + (s_.get('SHIP_QTY',0) or 0)

            # Today's shipped type×region distribution (from Shipment report, matches today_shipped)
            po_data_xr = oms.cached_data.get('rpt_850_po', [])
            if isinstance(po_data_xr, dict): po_data_xr = po_data_xr.get('data', po_data_xr.get('ResultData', []))
            po_lookup_xr = {}
            for p in (po_data_xr or []):
                po_lookup_xr[str(p.get('PO','')).strip()] = p
            shipped_xreg_daily = {}
            cto_p1_shipped_qty = 0
            for s_ in today_shipments:
                po = str(s_.get('PO','')).strip()
                p = po_lookup_xr.get(po, {})
                if not p: continue
                sub = p.get('SUB_TYPE','?')
                pri = str(p.get('PRIORITY',''))
                t = 'CTO_P1' if (sub == 'CTO' and pri == '1') else sub
                reg = p.get('REGION','?')
                sq = s_.get('SHIP_QTY',0) or 0
                if t not in shipped_xreg_daily: shipped_xreg_daily[t] = {}
                shipped_xreg_daily[t][reg] = shipped_xreg_daily[t].get(reg,0) + sq
                if t == 'CTO_P1': cto_p1_shipped_qty += sq

            self._json_response({
                'date': display_date,
                'new_orders': {'count': len(today), 'qty': sum(r.get('PO_QTY',0) for r in today),
                              'by_type': by_type, 'by_region': by_region},
                'nack_count': len(nack_today),
                'zc_count': len(zc_today),
                'open_count': len(open_today),
                'shipped': today_shipped,
                'shipped_cto_p1': cto_p1_shipped_qty,
                'shipped_xreg': shipped_xreg_daily,
                'asn': today_asn,
                'sn': today_sn,
                'order_trend': order_trend,
                'ship_trend': ship_trend,
                'plan_msbd': plan_status(today_msbd),
                'plan_cto28h': plan_status(today_cto28h),
                'progress': {
                    'asn_qty': sum(s_.get('SHIP_QTY',0) or 0 for s_ in today_shipments),
                    'asn_count': len(set(str(s_.get('ASN','')).strip() for s_ in today_shipments if str(s_.get('ASN','')).strip())),
                    'pps_done': pps_done,
                    'truck_count': truck_count,
                },
                'fwd_dist': fwd_dist,
            })

        elif path == '/api/k1-summary':
            if not oms.cached_data:
                self._json_response({'error': 'No cached data'}, 400)
                return
            # Parse date params (MSBD + PO received)
            qs = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(qs)
            from_str = (params.get('from',[''])[0]).strip()
            to_str = (params.get('to',[''])[0]).strip()
            po_from_str = (params.get('po_from',[''])[0]).strip()
            po_to_str = (params.get('po_to',[''])[0]).strip()
            date_from = datetime.strptime(from_str, '%Y-%m-%d').date() if from_str else None
            date_to = datetime.strptime(to_str, '%Y-%m-%d').date() if to_str else None
            po_from = datetime.strptime(po_from_str, '%Y-%m-%d').date() if po_from_str else None
            po_to = datetime.strptime(po_to_str, '%Y-%m-%d').date() if po_to_str else None

            # Don't cache filtered results
            if date_from or date_to or po_from or po_to:
                try:
                    self._json_response(self._k1_summary(date_from, date_to, po_from, po_to))
                except Exception as e:
                    self._json_response({'error': str(e), 'total_qty':0}, 500)
            else:
                cached = oms.cached_data
                if cached and cached.get('k1_summary'):
                    self._json_response(cached['k1_summary'])
                else:
                    try:
                        s = self._k1_summary()
                        if oms.cached_data:
                            oms.cached_data['k1_summary'] = s
                            oms._save_cache(oms.cached_data)
                        self._json_response(s)
                    except Exception as e:
                        self._json_response({'error': '计算K1失败: '+str(e), 'total_qty':0, 'total_pcs':0}, 500)

        elif path == '/api/shipped-history':
            if not oms.cached_data:
                self._json_response({'error': 'No cached data'}, 400)
                return
            qs = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(qs)
            granularity = (params.get('granularity',['month'])[0]).strip()
            records = merge_records(oms.cached_data, include_all=False)
            shipped = [r for r in records if r.get('ACTUAL_SHIPPED')]
            _asn_ship = oms.cached_data.get('rpt_asn', [])
            if isinstance(_asn_ship, dict): _asn_ship = _asn_ship.get('data', _asn_ship.get('ResultData', []))

            buckets = {}
            for r in shipped:
                sn = r.get('SN_CDT')
                if not sn: continue
                try: d = datetime.strptime(str(sn)[:10], '%Y-%m-%d')
                except: continue
                if granularity == 'day': key = d.strftime('%m/%d')
                elif granularity == 'week': key = d.strftime('%Y-W%W')
                elif granularity == 'quarter': key = d.strftime('%Y-Q') + str((d.month-1)//3+1)
                elif granularity == 'year': key = d.strftime('%Y')
                else: key = d.strftime('%Y-%m')  # month
                if key not in buckets: buckets[key] = {'label':key,'qty':0,'count':0}
                buckets[key]['qty'] += (r.get('SHIP_QTY',0) or 0)
                buckets[key]['count'] += 1

            result = sorted(buckets.values(), key=lambda x: x['label'])
            self._json_response({'data': result, 'total_shipped': len(shipped),
                                'total_qty': sum(a.get('QTY',0) or 0 for a in (_asn_ship or []) if str(a.get('SN_STATUS','')).upper() in ('S','SN ACK'))})

        elif path == '/api/shipped-summary':
            if not oms.cached_data:
                self._json_response({'error': 'No cached data'}, 400)
                return
            records = merge_records(oms.cached_data, include_all=False)
            shipped = [r for r in records if r.get('ACTUAL_SHIPPED')]
            now = datetime.now()
            this_month = sum(r.get('SHIP_QTY',0) or 0 for r in shipped
                           if r.get('SN_CDT') and str(r['SN_CDT'])[:7] == now.strftime('%Y-%m'))
            last_month = sum(r.get('SHIP_QTY',0) or 0 for r in shipped
                           if r.get('SN_CDT') and str(r['SN_CDT'])[:7] == (now.replace(day=1)-timedelta(days=1)).strftime('%Y-%m'))
            _asn_ss = oms.cached_data.get('rpt_asn', [])
            if isinstance(_asn_ss, dict): _asn_ss = _asn_ss.get('data', _asn_ss.get('ResultData', []))
            total_shipped = sum(a.get('QTY',0) or 0 for a in (_asn_ss or []) if str(a.get('SN_STATUS','')).upper() in ('S','SN ACK'))
            trend = 'up' if this_month > last_month else ('down' if this_month < last_month else 'flat')
            self._json_response({'this_month': this_month, 'last_month': last_month,
                                'total_shipped': total_shipped, 'trend': trend, 'count': len(shipped)})

        elif path == '/api/a2-fields':
            if not oms.cached_data:
                self._json_response({'error': 'No cached data'}, 400)
                return
            self._json_response(self._a2_data())

        elif path == '/api/fga-status':
            po_rows = fga_po_rows()
            self._json_response({
                'has_hold': os.path.exists(FGA_HOLD_FILE),
                'has_status': os.path.exists(FGA_STATUS_FILE),
                'has_850': bool(po_rows),
                'fga_count': sum(1 for r in po_rows
                                 if str(r.get('SUB_TYPE') or '').strip().upper() == 'FGA'),
                'cache_time': oms.cached_data.get('time', '') if oms.cached_data else '',
            })

        elif path == '/api/fga-allocate':
            if run_allocation is None:
                self._json_response({'error': 'FGA 分配模块未加载'}, 500); return
            po_rows = fga_po_rows()
            if not po_rows:
                self._json_response({'error': '无 850 数据，请先在首页刷新 OMS'}, 400); return
            if not (os.path.exists(FGA_HOLD_FILE) and os.path.exists(FGA_STATUS_FILE)):
                self._json_response({'error': '请先上传 T_HOLD_PO 与 T_STATUS_PO 两个文件'}, 400); return
            try:
                with open(FGA_HOLD_FILE, encoding='utf-8', errors='replace') as f:
                    hold_text = f.read()
                with open(FGA_STATUS_FILE, encoding='utf-8', errors='replace') as f:
                    status_text = f.read()
                self._json_response(run_allocation(po_rows, status_text, hold_text))
            except Exception as e:
                import traceback; traceback.print_exc()
                self._json_response({'error': str(e)}, 500)

        elif path == '/sw.js':
            # Service Worker must never be cached by browser
            self.send_response(200)
            self.send_header('Content-Type', 'application/javascript; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            sw_path = os.path.join(STATIC_DIR, 'sw.js')
            with open(sw_path, 'r', encoding='utf-8') as f:
                self.wfile.write(f.read().encode('utf-8'))

        elif path == '/manifest.json':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'public, max-age=86400')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            mf_path = os.path.join(STATIC_DIR, 'manifest.json')
            with open(mf_path, 'r', encoding='utf-8') as f:
                self.wfile.write(f.read().encode('utf-8'))

        else:
            # Fall back to static file serving
            if path == '/' or path == '':
                self.path = '/index.html'
            super().do_GET()

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path

        # ── User Auth APIs ─────────────────────────────────
        if path == '/api/register':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length > 0 else {}
            username = (body.get('username','')).strip()
            password = (body.get('password','')).strip()
            if not username or not password or len(username) < 2 or len(password) < 4:
                self._json_response({'error': '账号至少2位，密码至少4位'}, 400); return
            try:
                db = sqlite3.connect(USER_DB)
                db.execute('INSERT INTO users (username,password_hash) VALUES (?,?)',
                          (username, _hash_pw(password)))
                db.commit(); db.close()
                self._json_response({'ok': True, 'msg': '申请已提交，等待管理员审批'})
            except sqlite3.IntegrityError:
                self._json_response({'error': '账号已存在'}, 400)

        elif path == '/api/login':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length > 0 else {}
            username = (body.get('username','')).strip()
            password = (body.get('password','')).strip()
            db = sqlite3.connect(USER_DB)
            row = db.execute('SELECT password_hash,status FROM users WHERE username=?',
                           (username,)).fetchone()
            db.close()
            if not row:
                self._json_response({'error': '账号不存在'}, 401)
            elif row[0] != _hash_pw(password):
                self._json_response({'error': '密码错误'}, 401)
            elif row[1] == 'pending':
                self._json_response({'error': '账号待审批，请等待管理员通过'}, 403)
            elif row[1] == 'disabled':
                self._json_response({'error': '账号已被禁用'}, 403)
            else:
                token = secrets.token_hex(32)
                _sessions[token] = {
                    'user': username,
                    'expires': datetime.now() + timedelta(days=SESSION_DAYS)
                }
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Set-Cookie',
                    f'tb_token={token}; Path=/; Max-Age={SESSION_DAYS*86400}; HttpOnly; SameSite=Lax')
                self.end_headers()
                self.wfile.write(json.dumps({'ok': True, 'user': username}).encode('utf-8'))

        elif path == '/api/admin-action':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length > 0 else {}
            admin_pw = (body.get('admin_pw','')).strip()
            if admin_pw != ADMIN_PW:
                self._json_response({'error': '管理员密码错误'}, 403); return
            action = body.get('action','')
            target = (body.get('username','')).strip()
            db = sqlite3.connect(USER_DB)
            if action == 'approve':
                db.execute('UPDATE users SET status=? WHERE username=?', ('active', target))
            elif action == 'reject':
                db.execute('DELETE FROM users WHERE username=? AND status=?', (target, 'pending'))
            elif action == 'disable':
                db.execute('UPDATE users SET status=? WHERE username=?', ('disabled', target))
                # Clear all sessions for this user
                for t in list(_sessions.keys()):
                    if _sessions[t]['user'] == target:
                        del _sessions[t]
            elif action == 'enable':
                db.execute('UPDATE users SET status=? WHERE username=?', ('active', target))
            elif action == 'list':
                rows = db.execute('SELECT username,status,created_at FROM users ORDER BY created_at DESC').fetchall()
                db.close()
                self._json_response({'users': [{'username': r[0], 'status': r[1], 'created': r[2]} for r in rows]})
                return
            db.commit(); db.close()
            self._json_response({'ok': True})

        elif path == '/api/oms-pull':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length > 0 else {}
            account = body.get('account', '31000161')
            password = body.get('password', '')
            if not password:
                self._json_response({'error': 'Password required'}, 400)
                return
            result = oms.fetch_all(account, password)
            save_creds(account, password)
            self._json_response({
                'ok': 'error' not in result,
                'error': result.get('error',''),
                'po_count': result.get('po_count',0),
                'e2e_count': result.get('e2e_count',0),
                'gpp_count': result.get('gpp_count',0),
                'time': result.get('time',''),
            })

        elif path == '/api/k1-send':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length > 0 else {}
            msg = (
                f"📊 K1 PRD 看板  {datetime.now().strftime('%m/%d %H:%M')}\n"
                f"订单总数: {body.get('total',0):,} pcs\n"
                f"已出货: {body.get('shipped',0):,} | Backlog: {body.get('backlog',0):,} | NACK: {body.get('nack',0)}\n"
                f"CTO P1: {body.get('cto_p1',0):,} pcs (已出 {body.get('cto_shipped',0):,})\n"
                f"详情: http://localhost:8500/k1.html"
            )
            try:
                import subprocess
                r = subprocess.run(['python', os.path.join(os.path.dirname(TOOLBOX_DIR), 'ka_send.py'), 'text', msg],
                                   capture_output=True, text=True, timeout=15, cwd=os.path.dirname(TOOLBOX_DIR))
                ok = 'success' in r.stdout.lower() or 'code=0' in r.stdout
                self._json_response({'ok': ok, 'detail': r.stdout.strip()[:200]})
            except Exception as e:
                self._json_response({'ok': False, 'error': str(e)})

        elif path == '/api/fga-upload':
            try:
                length = int(self.headers.get('Content-Length', 0))
                raw = self.rfile.read(length) if length > 0 else b''
                body = json.loads(raw.decode('utf-8', 'replace'))
            except Exception as e:
                self._json_response({'error': 'body解析失败: ' + str(e)}, 400); return
            ftype = body.get('type', '')
            content = body.get('content', '')
            if ftype not in ('hold', 'status') or not content:
                self._json_response({'error': 'type 需为 hold/status 且 content 非空'}, 400); return
            target = FGA_HOLD_FILE if ftype == 'hold' else FGA_STATUS_FILE
            try:
                with open(target, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(content)
                import csv as _csv, io as _io
                rows = list(_csv.DictReader(_io.StringIO(content)))
                self._json_response({'ok': True, 'type': ftype, 'rows': len(rows)})
            except Exception as e:
                self._json_response({'error': str(e)}, 500)

        else:
            self._json_response({'error': 'Not found'}, 404)

    def _json_response(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode('utf-8'))

    def _k1_summary(self, date_from=None, date_to=None, po_from=None, po_to=None):
        records = merge_records(oms.cached_data, include_all=False)

        def in_range(d, f, t):
            if not d: return False
            try: dt = datetime.strptime(str(d)[:10], '%Y-%m-%d').date()
            except: return False
            if f and dt < f: return False
            if t and dt > t: return False
            return True

        # MSBD-filtered subset (for production status + MSBD/CTO P1 charts)
        msbd_records = records
        if date_from or date_to:
            msbd_records = [r for r in records if in_range(r.get('MSBD'), date_from, date_to)]

        # Combined filter (MSBD + PO received) for KPI/ship/region cards
        kpi_records = records
        if date_from or date_to or po_from or po_to:
            kpi_records = [r for r in records
                          if (not date_from and not date_to) or in_range(r.get('MSBD'), date_from, date_to)
                          or (po_from or po_to) and in_range(r.get('PO_RECEIVE_DATE'), po_from, po_to)]

        # Use msbd_records for production/charts, kpi_records for KPI/ship
        records = kpi_records  # default for KPI/ship/region calculations
        _msbd = msbd_records   # for production status and charts
        total_qty = sum(r['PO_QTY'] for r in records)

        # Today's orders: Vietnam time zone (UTC+7), 5am-5am window
        vn_tz = timezone(timedelta(hours=7))
        now_vn = datetime.now(vn_tz)
        today_5am = now_vn.replace(hour=5, minute=0, second=0, microsecond=0)
        if now_vn.hour < 5:
            today_5am -= timedelta(days=1)
        tomorrow_5am = today_5am + timedelta(days=1)

        today_orders = []
        for r in records:
            prd = r.get('PO_RECEIVE_DATE')
            if not prd: continue
            try:
                dt = datetime.strptime(str(prd)[:19], '%Y-%m-%dT%H:%M:%S')
                dt = dt.replace(tzinfo=vn_tz)
            except:
                try:
                    dt = datetime.strptime(str(prd)[:10], '%Y-%m-%d')
                    dt = dt.replace(hour=12, tzinfo=vn_tz)
                except:
                    continue
            if today_5am <= dt < tomorrow_5am:
                today_orders.append(r)

        today_summary = {
            'count': len(today_orders),
            'qty': sum(r['PO_QTY'] for r in today_orders),
            'cto_p1': sum(r['PO_QTY'] for r in today_orders if r.get('CTO_P1')=='Y'),
            'fga': sum(r['PO_QTY'] for r in today_orders if r.get('SUB_TYPE')=='FGA'),
            'rtl': sum(r['PO_QTY'] for r in today_orders if r.get('SUB_TYPE')=='RTL'),
            'cto': sum(r['PO_QTY'] for r in today_orders if r.get('SUB_TYPE')=='CTO'),
            'by_region': {},
        }
        for r in today_orders:
            reg = r.get('REGION','?')
            today_summary['by_region'][reg] = today_summary['by_region'].get(reg,0) + r['PO_QTY']
        # Shipped: from ASN report QTY (S + SN ACK), PRD only
        _asn_k1 = oms.cached_data.get('rpt_asn', []) if oms.cached_data else []
        if isinstance(_asn_k1, dict): _asn_k1 = _asn_k1.get('data', _asn_k1.get('ResultData', []))
        # Build PRD ASN set via Shipment
        _prd_pos = set(str(p.get('PO','')).strip() for p in (oms.cached_data.get('rpt_850_po', []) or []) if p.get('MASTER_TYPE')=='PRD')
        if isinstance(oms.cached_data.get('rpt_850_po'), dict):
            _po_tmp = oms.cached_data['rpt_850_po'].get('data', oms.cached_data['rpt_850_po'].get('ResultData', []))
            _prd_pos = set(str(p.get('PO','')).strip() for p in (_po_tmp or []) if p.get('MASTER_TYPE')=='PRD')
        _ship_tmp = oms.cached_data.get('rpt_shipment', [])
        if isinstance(_ship_tmp, dict): _ship_tmp = _ship_tmp.get('data', _ship_tmp.get('ResultData', []))
        _prd_asn = set()
        for s_ in (_ship_tmp or []):
            if str(s_.get('PO','')).strip() in _prd_pos:
                _prd_asn.add(str(s_.get('ASN','')).strip())
        shipped = sum(a.get('QTY', 0) or 0 for a in (_asn_k1 or []) if str(a.get('SN_STATUS','')).upper() in ('S','SN ACK') and str(a.get('ASN','')).strip() in _prd_asn)

        # Per-type shipped from ASN QTY (distribute by SHIP_QTY proportions)
        _type_shipped = {'CTO_P1': 0, 'FGA': 0, 'RTL': 0, 'CTO': 0}
        _asn_qty_map = {}
        for a in (_asn_k1 or []):
            if str(a.get('SN_STATUS','')).upper() in ('S','SN ACK'):
                _asn_qty_map[str(a.get('ASN','')).strip()] = a.get('QTY', 0) or 0
        # For each ASN, find linked POs and distribute
        _asn_type_qtys = {}
        for s_ in (_ship_tmp or []):
            aid = str(s_.get('ASN','')).strip()
            if aid not in _asn_qty_map: continue
            po = str(s_.get('PO','')).strip()
            if po not in _prd_pos: continue
            if aid not in _asn_type_qtys: _asn_type_qtys[aid] = {'total_ship': 0, 'types': {}}
            sq = s_.get('SHIP_QTY', 0) or 0
            _asn_type_qtys[aid]['total_ship'] += sq
            # Get PO type
            p = next((x for x in (_po_recs if '_po_recs' in dir() else []) if str(x.get('PO','')).strip() == po), None)
            if not p:
                for x in (oms.cached_data.get('rpt_850_po',[]) if isinstance(oms.cached_data.get('rpt_850_po',[]), list) else oms.cached_data.get('rpt_850_po',{}).get('data',[])):
                    if str(x.get('PO','')).strip() == po: p = x; break
            if not p: continue
            sub = p.get('SUB_TYPE','?')
            pri = str(p.get('PRIORITY',''))
            t = 'CTO_P1' if (sub == 'CTO' and pri == '1') else sub
            _asn_type_qtys[aid]['types'][t] = _asn_type_qtys[aid]['types'].get(t, 0) + sq
        # Distribute ASN QTY proportionally
        for aid, info in _asn_type_qtys.items():
            asn_qty = _asn_qty_map.get(aid, 0)
            total_sq = info['total_ship']
            if total_sq == 0: continue
            for t, sq in info['types'].items():
                ratio = sq / total_sq
                _type_shipped[t] = _type_shipped.get(t, 0) + round(asn_qty * ratio)

        cto_p1 = [r for r in records if r.get('CTO_P1') == 'Y']
        others = [r for r in records if r.get('CTO_P1') != 'Y']
        nack = [r for r in records if r.get('ACK_STATUS') == 'REJECT']

        # Type+Region cross (all, backlog, shipped)
        def build_xreg(subset, field='PO_QTY'):
            xr = {}
            for r in subset:
                t = r.get('SUB_TYPE','?') ; reg = r.get('REGION','?')
                if r.get('CTO_P1')=='Y': t = 'CTO_P1'
                if t not in xr: xr[t] = {}
                xr[t][reg] = xr[t].get(reg,0) + (r[field] or 0)
            return xr
        xreg = build_xreg(records)
        backlog_records = [r for r in records if not r.get('ACTUAL_SHIPPED')]
        shipped_records = [r for r in records if r.get('ACTUAL_SHIPPED')]
        backlog_xreg = build_xreg(backlog_records)
        shipped_xreg = build_xreg(shipped_records, 'SHIP_QTY')

        # GPP/E2E status breakdown
        def gpp_summary(subset):
            return {
                'stbl': sum(int(r.get('STBL') or 0) for r in subset),
                'atb': sum(int(r.get('ATB') or 0) for r in subset),
                'wip': sum(int(r.get('WIP') or 0) for r in subset),
                'fg': sum(int(r.get('FG') or 0) for r in subset),
                'sn': sum(int(r.get('SN') or 0) for r in subset),
            }
        cto_p1_msbd = [r for r in _msbd if r.get('CTO_P1')=='Y']
        others_msbd = [r for r in _msbd if r.get('CTO_P1')!='Y']
        cto_p1_gpp = gpp_summary(cto_p1_msbd)
        others_gpp = gpp_summary(others_msbd)

        # MSBD: show past incomplete + today + next 7 days
        today = datetime.now().date()
        cutoff_future = today + timedelta(days=7)
        # MSBD: exclude CTO P1 (they have their own 28H chart)
        msbd_plan = {}
        for r in _msbd:
            if r.get('CTO_P1') == 'Y': continue
            msbd = r.get('MSBD')
            if not msbd: continue
            try: d = datetime.strptime(msbd[:10], '%Y-%m-%d').date()
            except: continue
            # Include: past dates (before today) OR today + next 7 days
            if d <= cutoff_future:
                ds = d.strftime('%m/%d')
                if ds not in msbd_plan:
                    msbd_plan[ds] = {'planned':0,'actual':0,'date':ds,'incomplete': False}
                msbd_plan[ds]['planned'] += r['PO_QTY']
                # Actual: use ACTUAL_SHIPPED flag from merge_records
                if r.get('ACTUAL_SHIPPED'):
                    msbd_plan[ds]['actual'] += r['PO_QTY']
        # Mark past dates as incomplete if planned > actual
        for k in msbd_plan:
            p = msbd_plan[k]
            try:
                d = datetime.strptime('2026/'+p['date'], '%Y/%m/%d').date()
                if d < today and p['planned'] > p['actual']:
                    p['incomplete'] = True
            except: pass
        msbd_list = sorted(msbd_plan.values(), key=lambda x: x['date'])
        # Filter: past dates only show if incomplete
        msbd_list = [x for x in msbd_list if not (
            datetime.strptime('2026/'+x['date'], '%Y/%m/%d').date() < today
            and x['planned'] == x['actual'] and x['planned'] > 0
        )]

        # CTO P1 28H: PO received + 28 hours = expected ship
        # Find date range covering all unshipped CTO P1
        cto_unshipped_dates = []
        for r in cto_p1_msbd:
            if r.get('ACTUAL_SHIPPED'): continue
            prd = r.get('PO_RECEIVE_DATE')
            if not prd: continue
            try:
                dt = datetime.strptime(str(prd)[:10], '%Y-%m-%d')
                due = (dt + timedelta(hours=28)).date()
                cto_unshipped_dates.append(due)
            except: pass
        # Start from the earlier of: earliest unshipped, or 3 days ago
        _earliest = min(cto_unshipped_dates) if cto_unshipped_dates else today
        min_date = min(_earliest, today - timedelta(days=3))
        max_date = max(max(cto_unshipped_dates), today + timedelta(days=1)) if cto_unshipped_dates else today + timedelta(days=5)
        cto_timeline = []
        d = min_date
        while d <= max_date:
            ds = d.strftime('%m/%d')
            day_plan = 0; day_actual = 0
            for r in cto_p1_msbd:
                prd = r.get('PO_RECEIVE_DATE')
                if not prd: continue
                try:
                    dt = datetime.strptime(str(prd)[:19], '%Y-%m-%dT%H:%M:%S')
                except:
                    try: dt = datetime.strptime(str(prd)[:10], '%Y-%m-%d')
                    except: continue
                due_28h = (dt + timedelta(hours=28)).date()
                if due_28h == d:
                    day_plan += r['PO_QTY']
                    if r.get('ACTUAL_SHIPPED'):
                        day_actual += r['PO_QTY']
            cto_timeline.append({
                'date': ds, 'planned': day_plan, 'actual': day_actual,
                'past': d < today, 'today': d == today,
            })
            d += timedelta(days=1)
        # Filter: remove empty columns and past completed dates
        cto_timeline = [x for x in cto_timeline if not (
            (x['past'] and x['planned'] == x['actual'] and x['planned'] > 0)  # past completed
            or (x['planned'] == 0 and x['actual'] == 0)  # empty column
        )]

        # ASN pending: from ASN report QTY, not PO_QTY
        _asn_data = oms.cached_data.get('rpt_asn', []) if oms.cached_data else []
        if isinstance(_asn_data, dict): _asn_data = _asn_data.get('data', _asn_data.get('ResultData', []))
        _asn_none = [a for a in (_asn_data or []) if str(a.get('SN_STATUS','')).strip().upper() == 'NONE']

        return {
            'total_qty': total_qty, 'shipped': shipped,
            'unshipped': total_qty - shipped,
            'total_pcs': len(records),
            'nack_count': len(nack),
            'asn_pending_qty': sum(a.get('QTY', 0) or 0 for a in _asn_none),
            'asn_pending_count': len(_asn_none),
            'fga_count': len([r for r in records if r.get('SUB_TYPE')=='FGA']),
            'rtl_count': len([r for r in records if r.get('SUB_TYPE')=='RTL']),
            'cto_count': len([r for r in records if r.get('SUB_TYPE')=='CTO']),
            'cto_p1_qty': sum(r['PO_QTY'] for r in cto_p1),
            'cto_p1_count': len(cto_p1),
            'cto_p1_shipped': _type_shipped.get('CTO_P1', 0),
            'cto_p1_unshipped': sum(r['PO_QTY'] for r in cto_p1) - _type_shipped.get('CTO_P1', 0),
            'others_qty': sum(r['PO_QTY'] for r in others),
            'others_shipped': _type_shipped.get('FGA',0) + _type_shipped.get('RTL',0) + _type_shipped.get('CTO',0),
            'others_unshipped': sum(r['PO_QTY'] for r in others) - (_type_shipped.get('FGA',0) + _type_shipped.get('RTL',0) + _type_shipped.get('CTO',0)),
            # Per-type breakdown for "其他"
            'fga_qty': sum(r['PO_QTY'] for r in others if r.get('SUB_TYPE')=='FGA'),
            'fga_shipped': _type_shipped.get('FGA', 0),
            'fga_unshipped': sum(r['PO_QTY'] for r in others if r.get('SUB_TYPE')=='FGA') - _type_shipped.get('FGA', 0),
            'rtl_qty': sum(r['PO_QTY'] for r in others if r.get('SUB_TYPE')=='RTL'),
            'rtl_shipped': _type_shipped.get('RTL', 0),
            'rtl_unshipped': sum(r['PO_QTY'] for r in others if r.get('SUB_TYPE')=='RTL') - _type_shipped.get('RTL', 0),
            'cto_p2_qty': sum(r['PO_QTY'] for r in others if r.get('SUB_TYPE')=='CTO'),
            'cto_p2_shipped': _type_shipped.get('CTO', 0),
            'cto_p2_unshipped': sum(r['PO_QTY'] for r in others if r.get('SUB_TYPE')=='CTO') - _type_shipped.get('CTO', 0),
            'region_cnt': xreg.get('CTO_P1', {}),
            'type_cnt': {t: sum(xreg.get(t,{}).values()) for t in ['CTO_P1','FGA','RTL','CTO'] if t in xreg},
            'cross_region': xreg,
            'backlog_xreg': backlog_xreg,
            'asn_no_sn': sum(1 for r in backlog_records if r.get('ASN') and not r.get('SN')),
            'asn_pending_qty': sum(r.get('PO_QTY',0) for r in backlog_records if r.get('ASN') and not r.get('SN')),
            'shipped_xreg': shipped_xreg,
            'cto_p1_gpp': cto_p1_gpp,
            'others_gpp': others_gpp,
            'msbd_plan': msbd_list,
            'cto_timeline': cto_timeline,
        }

    def _a2_data(self):
        records = merge_records(oms.cached_data)
        fga = [r for r in records if r['SUB_TYPE']=='FGA']
        rtl = [r for r in records if r['SUB_TYPE']=='RTL' or
               (r['SUB_TYPE']=='CTO' and r['PRIORITY']=='2')]
        return {
            'fga': fga, 'fga_count': len(fga),
            'rtl': rtl, 'rtl_count': len(rtl),
        }

    def log_message(self, format, *args):
        pass  # suppress logs

# ── Main ──────────────────────────────────────────────────
def main():
    server = ThreadingHTTPServer(('0.0.0.0', PORT), ToolboxHandler)
    server.timeout = 120
    print(f"""
╔══════════════════════════════════════╗
║      Daisy 850 v1                    ║
║      http://localhost:{PORT}           ║
║                                      ║
║  📊 优先级排序 | 📈 K1 看板          ║
║  📋 A2 报告   | ⚡ OMS 数据刷新      ║
║                                      ║
║  Ctrl+C 停止                         ║
╚══════════════════════════════════════╝
""")
    start_auto_pull()
    server.serve_forever()

if __name__ == '__main__':
    main()
