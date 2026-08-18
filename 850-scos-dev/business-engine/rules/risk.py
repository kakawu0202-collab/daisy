"""Risk engine — implements R1-R7 business rules. Runs on Data Engine, results cached."""
from datetime import datetime, timedelta, timezone

def compute(records):
    """Generate risk/warning items from merged records.
    Returns list of risk dicts, each with: {type, severity, po, detail, qty}"""
    vn_tz = timezone(timedelta(hours=7))
    now = datetime.now(vn_tz).replace(tzinfo=None)
    today = now.date()
    risks = []

    for r in records:
        po = r['po']
        cto = r['cto_p1'] == 'Y'
        msbd = r['msbd']
        msbd_date = None
        if msbd:
            try: msbd_date = datetime.strptime(msbd[:10], '%Y-%m-%d').date()
            except: pass

        # R1: CTO P1 28H miss
        if cto and r['po_received']:
            try:
                dt = datetime.strptime(r['po_received'][:19], '%Y-%m-%dT%H:%M:%S')
            except:
                try: dt = datetime.strptime(r['po_received'][:10], '%Y-%m-%d')
                except: dt = None
            if dt:
                due = dt + timedelta(hours=28)
                if due < now and not r['actual_shipped']:
                    risks.append({'type': 'CTO_P1_28H_MISS', 'severity': 'high', 'po': po,
                        'detail': f'28H deadline {due.strftime("%m/%d %H:%M")}', 'qty': r['po_qty']})

        # R2: MSBD expired, not shipped (non-CTO P1)
        if not cto and msbd_date and msbd_date <= today and not r['actual_shipped']:
            risks.append({'type': 'MSBD_MISS', 'severity': 'high' if msbd_date < today else 'mid',
                'po': po, 'detail': f'MSBD {msbd[:10]}', 'qty': r['po_qty']})

        # R3: STBL > 0 is abnormal
        if r['stbl'] > 0:
            qty = r['stbl'] if r['sub_type'] == 'FGA' else r['po_qty']
            risks.append({'type': 'STBL_ABNORMAL', 'severity': 'mid', 'po': po,
                'detail': f'STBL {r["stbl"]} pcs', 'qty': qty})

        # R4: ATB + MSBD within 2 days → warning
        if r['atb'] > 0 and msbd_date and msbd_date <= today + timedelta(days=2) and not r['actual_shipped']:
            risks.append({'type': 'ATB_MSBD_WARN', 'severity': 'mid', 'po': po,
                'detail': f'ATB {r["atb"]} pcs, MSBD {msbd[:10]}', 'qty': r['atb']})

        # R5: CTO P1 Shuttle — must create ASN within 1H after FG
        if cto and r['stockin_cdt'] and r['createasn_cdt']:
            try:
                fg_dt = datetime.strptime(r['stockin_cdt'][:19], '%Y-%m-%dT%H:%M:%S')
                asn_dt = datetime.strptime(r['createasn_cdt'][:19], '%Y-%m-%dT%H:%M:%S')
                if (asn_dt - fg_dt).total_seconds() > 3600:
                    risks.append({'type': 'CTO_ASN_DELAY', 'severity': 'mid', 'po': po,
                        'detail': f'ASN {round((asn_dt-fg_dt).total_seconds()/3600,1)}H after FG', 'qty': r['po_qty']})
            except: pass
        elif cto and r['stockin_cdt'] and not r['createasn_cdt'] and not r['actual_shipped']:
            try:
                fg_dt = datetime.strptime(r['stockin_cdt'][:19], '%Y-%m-%dT%H:%M:%S')
                if now - fg_dt > timedelta(hours=1):
                    risks.append({'type': 'CTO_ASN_MISSING', 'severity': 'high', 'po': po,
                        'detail': f'{(now-fg_dt).total_seconds()/3600:.1f}H since FG, no ASN', 'qty': r['po_qty']})
            except: pass

        # R6: Per-segment over-target by 1H → warning
        if cto and r['po_received'] and r['input_cdt']:
            try:
                prd = datetime.strptime(r['po_received'][:19], '%Y-%m-%dT%H:%M:%S')
                inp = datetime.strptime(r['input_cdt'][:19], '%Y-%m-%dT%H:%M:%S')
                h = (inp - prd).total_seconds() / 3600
                if h > 12: risks.append({'type': 'PLANNING_OVER', 'severity': 'mid', 'po': po,
                    'detail': f'Planning {round(h,1)}H (target <=11H)', 'qty': r['po_qty']})
            except: pass
        if cto and r['input_cdt'] and r['stockin_cdt']:
            try:
                inp = datetime.strptime(r['input_cdt'][:19], '%Y-%m-%dT%H:%M:%S')
                stk = datetime.strptime(r['stockin_cdt'][:19], '%Y-%m-%dT%H:%M:%S')
                h = (stk - inp).total_seconds() / 3600
                if h > 13: risks.append({'type': 'BUILD_OVER', 'severity': 'mid', 'po': po,
                    'detail': f'Build {round(h,1)}H (target <=12H)', 'qty': r['po_qty']})
            except: pass
        if cto and r['stockin_cdt'] and r['sn_cdt']:
            try:
                stk = datetime.strptime(r['stockin_cdt'][:19], '%Y-%m-%dT%H:%M:%S')
                sn_dt = datetime.strptime(r['sn_cdt'][:19], '%Y-%m-%dT%H:%M:%S')
                h = (sn_dt - stk).total_seconds() / 3600
                if h > 6: risks.append({'type': 'SHUTTLE_OVER', 'severity': 'mid', 'po': po,
                    'detail': f'Shuttle {round(h,1)}H (target <=5H)', 'qty': r['po_qty']})
            except: pass

    return risks


def summarize(risks):
    """Aggregate risks into summary counts by type."""
    s = {}
    for r in risks:
        k = r['type']
        s.setdefault(k, {'count': 0, 'qty': 0, 'high': 0, 'mid': 0})
        s[k]['count'] += 1
        s[k]['qty'] += r['qty']
        if r['severity'] == 'high': s[k]['high'] += 1
        else: s[k]['mid'] += 1
    return s
