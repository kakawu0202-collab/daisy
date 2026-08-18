"""K1 Summary computation — runs on Data Engine, result cached and pushed."""
from datetime import datetime, timedelta, timezone

def compute(records):
    """Return K1 dashboard dict from merged records. Portal reads this directly, no recomputation."""
    vn_tz = timezone(timedelta(hours=7))
    today = datetime.now(vn_tz).date()

    total_qty = sum(r['po_qty'] for r in records)
    cto_p1 = [r for r in records if r['cto_p1'] == 'Y']
    others = [r for r in records if r['cto_p1'] != 'Y']
    nack = [r for r in records if r['ack_status'] == 'REJECT']

    def qty(sub, typ=None, is_p1=False):
        if is_p1: return sum(r['po_qty'] for r in sub if r['cto_p1'] == 'Y')
        if typ: return sum(r['po_qty'] for r in sub if r['sub_type'] == typ)
        return sum(r['po_qty'] for r in sub)

    def shipped(sub, typ=None, is_p1=False):
        if is_p1: return sum(r['shipped_qty'] for r in sub if r['cto_p1'] == 'Y')
        if typ: return sum(r['shipped_qty'] for r in sub if r['sub_type'] == typ)
        return sum(r['shipped_qty'] for r in sub)

    def xreg(sub):
        x = {}
        for r in sub:
            t = 'CTO_P1' if r['cto_p1'] == 'Y' else (r['sub_type'] or '?')
            reg = r['region'] or '?'
            if t not in x: x[t] = {}
            x[t][reg] = x[t].get(reg, 0) + r['po_qty']
        return x

    def gpp(sub):
        # Exclude ZC (cancelled) and CLOSE+fully-shipped orders (GPP residue)
        active = []
        for r in sub:
            st = r.get('status')
            if st == 'ZC': continue
            if st == 'CLOSE' and r['shipped_qty'] >= r['po_qty'] and r['po_qty'] > 0: continue
            active.append(r)
        return {k: sum(r[k] for r in active) for k in ('stbl','atb','wip','fg','sn')}

    cto_p1_msbd = [r for r in cto_p1]
    others_msbd = [r for r in others]

    # MSBD plan (non-CTO P1)
    msbd_plan = {}
    for r in others:
        if not r['msbd']: continue
        try: d = datetime.strptime(r['msbd'][:10], '%Y-%m-%d').date()
        except: continue
        if d <= today + timedelta(days=7):
            ds = d.strftime('%m/%d')
            msbd_plan.setdefault(ds, {'planned':0,'actual':0,'date':ds,'incomplete':False})
            msbd_plan[ds]['planned'] += r['po_qty']
            if r['actual_shipped']: msbd_plan[ds]['actual'] += min(r['shipped_qty'], r['po_qty'])
    for k in msbd_plan:
        p = msbd_plan[k]
        try:
            d = datetime.strptime(f'2026/{p["date"]}', '%Y/%m/%d').date()
            if d < today and p['planned'] > p['actual']: p['incomplete'] = True
        except: pass
    msbd_list = sorted(msbd_plan.values(), key=lambda x: x['date'])
    msbd_list = [x for x in msbd_list if not (
        datetime.strptime(f'2026/{x["date"]}','%Y/%m/%d').date() < today and x['planned'] == x['actual'] and x['planned'] > 0)]

    # CTO P1 28H timeline
    unshipped_dates = []
    for r in cto_p1_msbd:
        if r['actual_shipped']: continue
        if not r['po_received']: continue
        try: dt = datetime.strptime(r['po_received'][:19], '%Y-%m-%dT%H:%M:%S'); unshipped_dates.append((dt + timedelta(hours=28)).date())
        except:
            try: dt = datetime.strptime(r['po_received'][:10], '%Y-%m-%d'); unshipped_dates.append((dt + timedelta(hours=28)).date())
            except: pass
    mn = min(unshipped_dates) if unshipped_dates else today
    mn, mx = min(mn, today - timedelta(days=3)), max(max(unshipped_dates) if unshipped_dates else today + timedelta(days=5), today + timedelta(days=1))
    cto_timeline = []
    d = mn
    while d <= mx:
        plan = act = 0
        for r in cto_p1_msbd:
            if not r['po_received']: continue
            try: dt = datetime.strptime(r['po_received'][:19], '%Y-%m-%dT%H:%M:%S')
            except:
                try: dt = datetime.strptime(r['po_received'][:10], '%Y-%m-%d')
                except: continue
            if (dt + timedelta(hours=28)).date() == d:
                plan += r['po_qty']
                if r['actual_shipped']: act += min(r['shipped_qty'], r['po_qty'])
        cto_timeline.append({'date': d.strftime('%m/%d'), 'planned': plan, 'actual': act, 'past': d < today, 'today': d == today})
        d += timedelta(days=1)
    cto_timeline = [x for x in cto_timeline if not (x['past'] and x['planned'] == x['actual'] and x['planned'] > 0) and not (x['planned'] == 0 and x['actual'] == 0)]

    # Per-record shipped/unshipped (consistent with backlog_xreg)
    bl_recs, sh_recs = [], []
    for r in records:
        u = max(0, r['po_qty'] - r['shipped_qty'])
        if u > 0: bl_recs.append({**r, 'po_qty': u})
        if r['shipped_qty'] > 0: sh_recs.append({**r, 'po_qty': min(r['shipped_qty'], r['po_qty'])})
    # shipped/unshipped totals from per-record split (consistent with type cards)
    shipped_total = 0
    unshipped_total = 0
    # Compute type totals from bl_recs/sh_recs first
    c1u = sum(r['po_qty'] for r in bl_recs if r['cto_p1'] == 'Y')
    fu = sum(r['po_qty'] for r in bl_recs if r['sub_type'] == 'FGA')
    ru = sum(r['po_qty'] for r in bl_recs if r['sub_type'] == 'RTL')
    c2u = sum(r['po_qty'] for r in bl_recs if r['sub_type'] == 'CTO' and r['cto_p1'] != 'Y')
    shipped_total = (sum(r['po_qty'] for r in sh_recs if r['cto_p1'] == 'Y') +
                     sum(r['po_qty'] for r in sh_recs if r['sub_type'] == 'FGA') +
                     sum(r['po_qty'] for r in sh_recs if r['sub_type'] == 'RTL') +
                     sum(r['po_qty'] for r in sh_recs if r['sub_type'] == 'CTO' and r['cto_p1'] != 'Y'))
    unshipped_total = c1u + fu + ru + c2u

    c1q, oq = qty(records, is_p1=True), qty(others)
    fq, rq, c2q = qty(others, 'FGA'), qty(others, 'RTL'), qty(others, 'CTO')

    # Per-type unshipped from backlog_records (NOT type-level capping)
    def bl_qty(sub, typ=None, is_p1=False):
        if is_p1: return sum(r['po_qty'] for r in bl_recs if r['cto_p1'] == 'Y')
        if typ: return sum(r['po_qty'] for r in bl_recs if r['sub_type'] == typ)
        return sum(r['po_qty'] for r in bl_recs)
    def sh_qty(sub, typ=None, is_p1=False):
        if is_p1: return sum(r['po_qty'] for r in sh_recs if r['cto_p1'] == 'Y')
        if typ: return sum(r['po_qty'] for r in sh_recs if r['sub_type'] == typ)
        return sum(r['po_qty'] for r in sh_recs)

    return dict(
        total_qty=total_qty, shipped=shipped_total, unshipped=unshipped_total,
        total_pcs=len(records), nack_count=len(nack),
        asn_pending_qty=sum(r['po_qty'] for r in bl_recs if r.get('asn_pending')),
        cto_p1_qty=c1q, cto_p1_count=len(cto_p1),
        cto_p1_shipped=c1q-c1u, cto_p1_unshipped=c1u,
        others_qty=oq, others_shipped=oq-(fu+ru+c2u), others_unshipped=fu+ru+c2u,
        fga_qty=fq, fga_shipped=fq-fu, fga_unshipped=fu,
        rtl_qty=rq, rtl_shipped=rq-ru, rtl_unshipped=ru,
        cto_p2_qty=c2q, cto_p2_shipped=c2q-c2u, cto_p2_unshipped=c2u,
        region_cnt=xreg(records).get('CTO_P1', {}),
        type_cnt={t: sum(xreg(records).get(t, {}).values()) for t in ('CTO_P1','FGA','RTL','CTO') if t in xreg(records)},
        cross_region=xreg(records), backlog_xreg=xreg(bl_recs), shipped_xreg=xreg(sh_recs),
        cto_p1_gpp=gpp(cto_p1_msbd), others_gpp=gpp(others_msbd),
        fga_gpp=gpp([r for r in others_msbd if r['sub_type'] == 'FGA']),
        rtl_gpp=gpp([r for r in others_msbd if r['sub_type'] == 'RTL']),
        cto_p2_gpp=gpp([r for r in others_msbd if r['sub_type'] == 'CTO' and r['cto_p1'] != 'Y']),
        msbd_plan=msbd_list, cto_timeline=cto_timeline,
    )
