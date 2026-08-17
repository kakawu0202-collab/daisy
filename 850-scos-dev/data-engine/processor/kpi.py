"""CTO P1 28H KPI — daily/weekly statistics. Week = Saturday to Friday."""
from datetime import datetime, timedelta, timezone

def compute(records):
    """Compute CTO P1 28H KPI for daily and weekly windows.
    Returns {daily: {date: {total, ok, pct}}, weekly: {week_start: {total, ok, pct, orders}}}"""
    vn_tz = timezone(timedelta(hours=7))
    now = datetime.now(vn_tz)

    cto_recs = [r for r in records if r['cto_p1'] == 'Y' and r['po_received'] and r['sn_cdt']]

    daily = {}
    weekly = {}

    for r in cto_recs:
        try: prd = datetime.strptime(r['po_received'][:19], '%Y-%m-%dT%H:%M:%S')
        except:
            try: prd = datetime.strptime(r['po_received'][:10], '%Y-%m-%d')
            except: continue
        try: sn_dt = datetime.strptime(r['sn_cdt'][:19], '%Y-%m-%dT%H:%M:%S')
        except:
            try: sn_dt = datetime.strptime(r['sn_cdt'][:10], '%Y-%m-%d')
            except: continue

        hours = (sn_dt - prd).total_seconds() / 3600
        ok = hours <= 28
        ship_date = sn_dt.date()

        # Daily
        dk = ship_date.strftime('%Y-%m-%d')
        daily.setdefault(dk, {'total': 0, 'ok': 0, 'qty': 0})
        daily[dk]['total'] += 1
        daily[dk]['qty'] += r['po_qty']
        if ok: daily[dk]['ok'] += 1

        # Weekly (Saturday to Friday)
        wk = _week_start(ship_date)
        weekly.setdefault(wk, {'total': 0, 'ok': 0, 'qty': 0, 'ok_qty': 0})
        weekly[wk]['total'] += 1
        weekly[wk]['qty'] += r['po_qty']
        if ok: weekly[wk]['ok'] += 1; weekly[wk]['ok_qty'] += r['po_qty']

    # Add percentages
    for d in daily.values(): d['pct'] = round(d['ok'] / max(d['total'], 1) * 100, 1)
    for w in weekly.values(): w['pct'] = round(w['ok'] / max(w['total'], 1) * 100, 1)

    # Get this week
    this_week = _week_start(now.date())
    tw = weekly.get(this_week, {'total': 0, 'ok': 0, 'qty': 0, 'ok_qty': 0, 'pct': 0})

    return {
        'daily': {k: daily[k] for k in sorted(daily.keys())[-14:]},
        'weekly': {k: weekly[k] for k in sorted(weekly.keys())[-8:]},
        'this_week': this_week,
        'this_week_start': this_week,
        'target_75': tw['pct'] >= 75,
        'target_90': tw['pct'] >= 90,
    }


def _week_start(date):
    """Return the Saturday that starts this week (Sat-Fri week)."""
    # weekday(): Mon=0, Tue=1, ..., Fri=4, Sat=5, Sun=6
    # Saturday = 5. Days since last Saturday:
    days_since_sat = (date.weekday() - 5) % 7
    sat = date - timedelta(days=days_since_sat)
    return sat.strftime('%Y-%m-%d')
