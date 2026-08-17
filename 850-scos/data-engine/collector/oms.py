"""OMS data collector — stateless pull, no business logic."""
import os, json, requests

OMS_URL = 'http://luxoms-vn-prod.luxshare-ict.com'
OMS_IP  = 'http://10.177.20.61'

REPORTS = [
    ('0848012288', 'po'), ('1593920512', 'e2e'), ('0320073728', 'gpp'),
    ('0886717440', 'asn'), ('1780017152', 'ship'),
]


class OMSClient:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({'Content-Type': 'application/json;charset=UTF-8'})
        self.token = None

    def login(self, account='31000161', password=None):
        pw = password or os.environ.get('OMS_PASSWORD', '')
        if not pw:
            creds_path = os.environ.get('OMS_CREDS_PATH',
                os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'oms_creds.json'))
            if os.path.exists(creds_path):
                pw = json.load(open(creds_path)).get('password', '')
        if not pw: return False
        for url in (OMS_URL, OMS_IP):
            try:
                r = self.s.post(f'{url}/api/auth/login', json={'account': account, 'password': pw}, timeout=30)
                if r.ok:
                    d = r.json()
                    self.token = d.get('token') or (d.get('data', {}) or {}).get('token')
                    return bool(self.token)
            except: continue
        return False

    def _api(self, method, path, body=None, timeout=60):
        h = {'token': self.token} if self.token else {}
        for url in (OMS_URL, OMS_IP):
            try:
                if method == 'GET':
                    r = self.s.get(f'{url}{path}', headers=h, timeout=timeout)
                else:
                    r = self.s.post(f'{url}{path}', json=body, headers=h, timeout=timeout)
                if r.ok: return r.json()
                return {'error': f'HTTP {r.status_code}'}
            except requests.ConnectionError: continue
        return {'error': 'OMS unreachable'}

    def fetch_report(self, report_id):
        cfg = self._api('GET', f'/api/ReportSetting/GetReportByID?report_id={report_id}')
        if 'error' in cfg:
            print(f'    Config error for {report_id}: {cfg["error"][:80]}')
            return []
        data = cfg.get('data', {})
        rname = data.get('REPORT_NAME', '')
        try: details = json.loads(data.get('REPORT_DETAILS', '{}'))
        except: details = {}
        sql = (details.get('mainReport', {}) or {}).get('sql', '')
        fields = (details.get('mainReport', {}) or {}).get('fields', [])
        body = {'report_id': report_id, 'reportName': rname,
                'pagination': {'page': 1, 'pageSize': 50000},
                'parameters': {}, 'parentContext': None, 'sql': sql, 'fields': fields}
        resp = self._api('POST', '/api/ReportSetting/QueryDynamicReport', body)
        if 'error' in resp:
            print(f'    Query error for {report_id}: {resp["error"][:80]}')
            return []
        return resp.get('data', {}).get('ResultData', resp.get('ResultData', []))

    def pull_all(self):
        result = {}
        for rid, key in REPORTS:
            rows = self.fetch_report(rid)
            result[key] = rows
            print(f'  {key}: {len(rows)} rows')
        return result
