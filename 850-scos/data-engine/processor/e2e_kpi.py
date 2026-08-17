"""
E2E KPI Engine — centralized KPI calculation per SCOS spec.
Reads E2E records + merged records, applies kpi_config.json.
Produces KPIs + exceptions + quarterly/monthly/weekly summaries.
"""
import json, os
from datetime import datetime, timedelta

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kpi_config.json')
# Hold codes that mark a PO as "unclean" (had hold history)
UNCLEAN_HOLDS = {'A01','A02','A03','A04','A05','A06','A07','A09','A11','A12','A13','A14',
                 'A21','A22','A23','A24','A27','A32','A35','D01','D04','D05'}

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def dell_week(dt):
    if isinstance(dt, str):
        try: dt = datetime.strptime(dt[:19], '%Y-%m-%dT%H:%M:%S')
        except:
            try: dt = datetime.strptime(dt[:10], '%Y-%m-%d')
            except: return None
    wk1 = datetime(2026, 1, 31)
    if dt < wk1: return None
    return f'WK{(dt.date() - wk1.date()).days // 7 + 1:02d}'

def dell_month(dt):
    """Dell months: aligned to Dell weeks. Return 'Jul', 'Aug' etc."""
    if isinstance(dt, str):
        try: dt = datetime.strptime(dt[:10], '%Y-%m-%d')
        except: return None
    return dt.strftime('%b')

def dell_quarter(dt):
    """Dell quarter: Q1=Feb-Apr, Q2=May-Jul, Q3=Aug-Oct, Q4=Nov-Jan."""
    if isinstance(dt, str):
        try: dt = datetime.strptime(dt[:10], '%Y-%m-%d')
        except: return None
    m = dt.month
    if 2 <= m <= 4: return 'Q1'
    if 5 <= m <= 7: return 'Q2'
    if 8 <= m <= 10: return 'Q3'
    return 'Q4'

def parse_dt(val):
    if not val: return None
    s = str(val).strip()
    if s.endswith('Z'): s = s[:-1]
    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try: return datetime.strptime(s[:19] if len(s) > 19 else s, fmt)
        except: pass
    return None

def hours_between(start, end):
    a, b = parse_dt(start), parse_dt(end)
    if not a or not b or b < a: return None
    return round((b - a).total_seconds() / 3600, 2)

def _has_hold(po, merged_map):
    """Check if a PO has unclean hold history."""
    r = merged_map.get(po)
    if not r: return False
    hc = str(r.get('hold_code', '') or '').strip().upper()
    ih = str(r.get('is_hold', '') or '').strip().upper()
    return hc in UNCLEAN_HOLDS or ih == 'Y'

def compute_all(e2e_records, merged_records=None):
    config = load_config()
    merged = merged_records or []
    merged_map = {str(r.get('po','')).strip(): r for r in merged}

    # Common KPI population: Close + valid SN_CDT
    completed = []
    shipped_all = []
    for r in e2e_records:
        if r.get('SN_CDT') and parse_dt(r.get('SN_CDT')):
            po = str(r.get('PO','')).strip()
            r['_clean'] = not _has_hold(po, merged_map)
            shipped_all.append(r)
            if str(r.get('PO_STATUS','')).strip().upper() == 'CLOSE':
                completed.append(r)

    if not completed and not shipped_all:
        return {'error': 'No completed POs', 'kpis': {}, 'exceptions': [], 'weekly': {}}

    all_exceptions = []
    kpi_results = {}

    for kpi_key, cfg in config.items():
        pop_type = cfg.get('population', 'close')
        clean_only = cfg.get('clean_only')
        non_clean_only = cfg.get('non_clean_only')
        priority = cfg.get('priority_filter')
        kpi_type = cfg.get('type', 'hours')

        # Filter population
        pop = shipped_all if pop_type == 'shipped' else completed
        if priority:
            pop = [r for r in pop if str(r.get('PRIORITY','')).strip() == priority]
        if clean_only:
            pop = [r for r in pop if r.get('_clean')]
        if non_clean_only:
            pop = [r for r in pop if not r.get('_clean')]

        start_f, end_f = cfg['start'], cfg['end']
        sla = cfg['sla_hours']
        goal = cfg['goal']

        results = []
        qty_total = 0; qty_pass = 0; qty_fail = 0
        for r in pop:
            qty = int(r.get('PO_QTY', 0) or 0)
            qty_total += qty
            if kpi_type == 'datetime_compare':
                sn_dt = parse_dt(r.get(end_f))
                msbd_dt = parse_dt(r.get(start_f))
                if sn_dt and msbd_dt:
                    elapsed = round((sn_dt - msbd_dt).total_seconds() / 3600, 2)
                    status = 'PASS' if elapsed <= 0 else 'FAIL'
                    over = max(0, elapsed)
                else:
                    elapsed = None; status = 'OPEN'; over = 0
            else:
                elapsed = hours_between(r.get(start_f), r.get(end_f))
                status = 'OPEN' if elapsed is None else ('PASS' if elapsed <= sla else 'FAIL')
                over = max(0, round((elapsed or 0) - sla, 2)) if elapsed else 0
            if status == 'PASS': qty_pass += qty
            elif status == 'FAIL': qty_fail += qty
            sn = r.get('SN_CDT')
            dt = parse_dt(sn)
            results.append({
                'po': r.get('PO',''), 'po_line': r.get('PO_LINE','1'),
                'priority': r.get('PRIORITY',''), 'dpn': r.get('DPN',''), 'ipn': r.get('IPN',''),
                'po_qty': r.get('PO_QTY',0), 'clean': r.get('_clean'),
                'kpi': kpi_key, 'elapsed_hours': elapsed, 'sla_hours': sla,
                'status': status, 'over_hours': over,
                'week': dell_week(sn) if dt else None,
                'month': dell_month(sn) if dt else None,
                'quarter': dell_quarter(sn) if dt else None,
            })
            all_exceptions.append(results[-1])

        total = len(results)
        p = sum(1 for x in results if x['status'] == 'PASS')
        f = sum(1 for x in results if x['status'] == 'FAIL')
        o = sum(1 for x in results if x['status'] == 'OPEN')
        rate = round(p / max(total, 1), 4)

        qty_rate = round(qty_pass / max(qty_total, 1), 4)
        kpi_results[kpi_key] = {
            'name': cfg['name'], 'total': total, 'pass': p, 'fail': f, 'open': o,
            'pass_rate': rate, 'pass_pct': round(rate * 100, 1),
            'qty_total': qty_total, 'qty_pass': qty_pass, 'qty_fail': qty_fail,
            'qty_pass_pct': round(qty_rate * 100, 1),
            'goal': goal, 'gap': round((rate - goal) * 100, 1),
            'sla_hours': sla, 'above_goal': rate >= goal,
            'clean_only': clean_only, 'non_clean_only': non_clean_only,
        }

    # Weekly / Monthly / Quarterly aggregation
    weekly = _aggregate(all_exceptions, 'week')
    monthly = _aggregate(all_exceptions, 'month')
    quarterly = _aggregate(all_exceptions, 'quarter')

    dq = {'total_e2e': len(e2e_records), 'closed': len(completed),
          'non_closed': len(e2e_records) - len(completed)}

    # Bottleneck
    fc = {}
    for ex in all_exceptions:
        if ex['status'] == 'FAIL':
            fc[ex['kpi']] = fc.get(ex['kpi'], 0) + 1
    tf = sum(fc.values()) or 1
    bottleneck = {k: {'count': v, 'pct': round(v / tf * 100, 1)} for k, v in sorted(fc.items(), key=lambda x: -x[1])}

    return {'kpis': kpi_results, 'exceptions': all_exceptions,
            'weekly': weekly, 'monthly': monthly, 'quarterly': quarterly,
            'data_quality': dq, 'bottleneck': bottleneck}


def _aggregate(exceptions, period_key):
    agg = {}
    for ex in exceptions:
        p = ex.get(period_key)
        if not p: continue
        kpi = ex['kpi']
        agg.setdefault(p, {}).setdefault(kpi, {'total': 0, 'pass': 0, 'fail': 0, 'open': 0})
        agg[p][kpi]['total'] += 1
        agg[p][kpi][ex['status'].lower()] += 1
    for period, kpis in agg.items():
        for kpi, data in kpis.items():
            t = max(data['total'], 1)
            data['pass_rate'] = round(data['pass'] / t, 4)
            data['pass_pct'] = round(data['pass'] / t * 100, 1)
    return agg
