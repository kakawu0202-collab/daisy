"""Daily summary — output matches dashboard JS expectations (old field names)."""
from datetime import datetime, timedelta, timezone

def _fwd_dist(ship_data, ship_date):
    fd = {}
    for s in ship_data:
        if str(s.get('SHIP_DATE',''))[:10] != ship_date: continue
        scac = str(s.get('SCAC','') or s.get('Ship mode','')).strip()
        if scac: fd[scac] = fd.get(scac, 0) + (s.get('SHIP_QTY', 0) or 0)
    return fd

def _compute_asn(asn_data, ship_date):
    n=s=ack=nack=0
    for a in asn_data:
        sd = str(a.get('SHIP_DATE',''))[:10]
        if sd != ship_date: continue
        sns = str(a.get('SN_STATUS','')).upper()
        asns = str(a.get('ASN_STATUS','')).upper()
        if sns in ('S','SN ACK'): s += 1
        else: n += 1
        if 'NACK' in asns: nack += 1
        elif 'ACK' in asns: ack += 1
    return {'n': n, 's': s, 'ack': ack, 'nack': nack}


def compute(records, raw_ship=None, raw_asn=None):
    if raw_ship is None: raw_ship = []
    if raw_asn is None: raw_asn = []
    vn_tz = timezone(timedelta(hours=7))
    now = datetime.now(vn_tz).replace(tzinfo=None)
    today_5am = now.replace(hour=5, minute=0, second=0, microsecond=0)
    if now.hour < 5: today_5am -= timedelta(days=1)
    tomorrow_5am = today_5am + timedelta(days=1)
    disp_date = today_5am.strftime('%Y-%m-%d')
    ship_date = now.strftime('%Y-%m-%d')

    # Today new orders (PO received in VN 5am-5am)
    today_orders = []
    for r in records:
        prd = r['po_received']
        if not prd: continue
        s = str(prd).strip()
        try:
            if len(s) >= 19: dt = datetime.strptime(s[:19], '%Y-%m-%dT%H:%M:%S')
            else: dt = datetime.strptime(s[:10], '%Y-%m-%d').replace(hour=12)
        except: continue
        if today_5am <= dt < tomorrow_5am: today_orders.append(r)

    by_type, by_region, by_type_region = {}, {}, {}
    for r in today_orders:
        t = 'CTO_P1' if r['cto_p1'] == 'Y' else (r['sub_type'] or '?')
        reg = r['region'] or '?'
        by_type[t] = by_type.get(t, 0) + r['po_qty']
        by_region[reg] = by_region.get(reg, 0) + r['po_qty']
        if t not in by_type_region: by_type_region[t] = {}
        by_type_region[t][reg] = by_type_region[t].get(reg, 0) + r['po_qty']

    # Today shipped — use raw shipment SHIP_QTY by SHIP_DATE (not sn_cdt)
    sh_qty = sh_cnt = cto_sh = 0
    today_sxr = {}
    # Normalize: handle dict-wrapped data from OMS API
    if isinstance(raw_ship, dict):
        raw_ship = raw_ship.get('data', raw_ship.get('ResultData', [])) or []
    ship_data = raw_ship or []
    if isinstance(raw_asn, dict):
        raw_asn = raw_asn.get('data', raw_asn.get('ResultData', [])) or []
    asn_data = raw_asn or []
    po_ship_today = {}
    for s in ship_data:
        sd = str(s.get('SHIP_DATE', '')).strip()[:10]
        if sd != ship_date: continue
        po = str(s.get('PO', '')).strip()
        sq = s.get('SHIP_QTY', 0) or 0
        po_ship_today[po] = po_ship_today.get(po, 0) + sq

    for r in records:
        po = r['po']
        if po not in po_ship_today: continue
        sq = po_ship_today[po]
        sh_qty += sq; sh_cnt += 1
        if r['cto_p1'] == 'Y': cto_sh += sq
        t = 'CTO_P1' if r['cto_p1'] == 'Y' else (r['sub_type'] or '?')
        reg = r['region'] or '?'
        if t not in today_sxr: today_sxr[t] = {}
        today_sxr[t][reg] = today_sxr[t].get(reg, 0) + sq

    # CTO P1 28H today
    plan, done = 0, 0
    for r in records:
        if r['cto_p1'] != 'Y' or not r['po_received']: continue
        try: dt = datetime.strptime(str(r['po_received'])[:19], '%Y-%m-%dT%H:%M:%S')
        except:
            try: dt = datetime.strptime(str(r['po_received'])[:10], '%Y-%m-%d')
            except: continue
        if (dt + timedelta(hours=28)).date() == now.date():
            plan += r['po_qty']
            if r['actual_shipped']: done += min(r['shipped_qty'], r['po_qty'])

    # MSBD/CTO 28H today (for plan_msbd and plan_cto28h cards)
    def plan_status(sub):
        return {'stbl': sum(r['stbl'] for r in sub), 'atb': sum(r['atb'] for r in sub),
                'wip': sum(r['wip'] for r in sub), 'fg': sum(r['fg'] for r in sub),
                'sn': sum(r['sn'] for r in sub), 'count': len(sub),
                'qty': sum(r['po_qty'] for r in sub)}

    msbd_today = [r for r in records if r['cto_p1'] != 'Y' and r['msbd'] and str(r['msbd'])[:10] == disp_date]
    cto28h_today = []
    for r in records:
        if r['cto_p1'] != 'Y' or not r['po_received']: continue
        try: dt = datetime.strptime(str(r['po_received'])[:19], '%Y-%m-%dT%H:%M:%S')
        except:
            try: dt = datetime.strptime(str(r['po_received'])[:10], '%Y-%m-%d')
            except: continue
        if (dt + timedelta(hours=28)).strftime('%Y-%m-%d') == disp_date:
            cto28h_today.append(r)

    # 30-day trends
    # PO → type/ship_mode lookup for enrichment
    po_type = {}
    po_mode = {}
    for r in records:
        po = str(r.get('po','')).strip()
        t = 'CTO_P1' if r['cto_p1'] == 'Y' else (r['sub_type'] or 'OTHER')
        po_type[po] = t
        po_mode[po] = r.get('ship_mode','') or ''

    ot, st = {}, {}
    for i in range(30):
        ds_day = today_5am - timedelta(days=i)
        ds = ds_day.strftime('%m/%d')
        day_str = ds_day.strftime('%Y-%m-%d')
        oq = {'cto_p1':0,'fga':0,'rtl':0,'cto_p2':0}
        by_mode = {}
        cnt = 0
        for r in records:
            prd = r['po_received']
            if not prd: continue
            s = str(prd).strip()
            try:
                if len(s) >= 19: dt = datetime.strptime(s[:19], '%Y-%m-%dT%H:%M:%S')
                else: dt = datetime.strptime(s[:10], '%Y-%m-%d')
            except: continue
            if ds_day <= dt < ds_day + timedelta(days=1):
                cnt += 1
                q = r['po_qty']
                if r['cto_p1'] == 'Y': oq['cto_p1'] += q
                elif r['sub_type'] == 'FGA': oq['fga'] += q
                elif r['sub_type'] == 'RTL': oq['rtl'] += q
                elif r['sub_type'] == 'CTO': oq['cto_p2'] += q
                m = r.get('ship_mode','') or 'OTHER'
                by_mode[m] = by_mode.get(m, 0) + q
        ot[ds] = {'total': cnt, 'qty': sum(oq.values()), 'by_mode': by_mode, **oq}

        # Ship trend: raw shipment SHIP_QTY enriched with type + scac
        by_type = {'CTO_P1':0,'FGA':0,'RTL':0,'CTO_P2':0,'OTHER':0}
        by_scac = {}
        st_total = 0
        if ship_data:
            for s in ship_data:
                sd = str(s.get('SHIP_DATE','')).strip()[:10]
                if sd != day_str: continue
                q = s.get('SHIP_QTY', 0) or 0
                st_total += q
                po = str(s.get('PO','')).strip()
                t = po_type.get(po, 'OTHER')
                by_type[t] = by_type.get(t, 0) + q
                scac = str(s.get('SCAC','') or '').strip() or 'OTHER'
                by_scac[scac] = by_scac.get(scac, 0) + q
        else:
            st_total = sum(
                min(r['shipped_qty'], r['po_qty']) for r in records
                if r['sn_cdt'] and str(r['sn_cdt'])[:10] == day_str and r['actual_shipped']
            )
        st[ds] = {'total': st_total, 'by_type': by_type, 'by_scac': by_scac}

    return {
        'date': disp_date,
        'new_orders': {'count': len(today_orders), 'qty': sum(r['po_qty'] for r in today_orders),
                       'by_type': by_type, 'by_region': by_region,
                       'by_type_region': by_type_region},
        # Old field names for dashboard JS compat:
        'shipped': {'count': sh_cnt, 'qty': sh_qty},
        'shipped_cto_p1': cto_sh,
        'shipped_xreg': today_sxr,
        'nack_count': sum(1 for r in records if r['ack_status'] == 'REJECT'),
        'zc_count': sum(1 for r in records if r['status'] == 'ZC'),
        'open_count': 0,
        'asn': _compute_asn(asn_data, ship_date),
        'sn': {'s': sum(1 for a in asn_data if str(a.get('SN_STATUS','')).upper() in ('S','SN ACK') and str(a.get('SHIP_DATE',''))[:10] == ship_date)},
        'asn_pending_qty': sum(r['po_qty'] for r in records if r['asn'] and not r['actual_shipped']),
        'order_trend': ot,
        'ship_trend': st,
        'plan_msbd': plan_status(msbd_today),
        'plan_cto28h': plan_status(cto28h_today),
        'progress': {'asn_qty': sh_qty, 'asn_count': len(set(str(s.get('ASN','')).strip() for s in ship_data if str(s.get('SHIP_DATE',''))[:10] == ship_date)), 'pps_done': sh_cnt, 'truck_count': len(set(str(s.get('TRUCK_NO','')).strip() for s in ship_data if str(s.get('SHIP_DATE',''))[:10] == ship_date and str(s.get('TRUCK_NO','')).strip()))},
        'fwd_dist': _fwd_dist(ship_data, ship_date),
        # New fields for SCOS:
        'cto_p1_28h': {'today_plan': plan, 'today_done': done, 'miss_risk': max(0, plan - done)},
    }
