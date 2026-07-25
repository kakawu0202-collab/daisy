import json
from datetime import datetime, timedelta, timezone

d = json.load(open('d:/workspace/850-toolbox/data/oms_cache.json', 'r', encoding='utf-8'))
po = d.get('rpt_850_po', [])
if isinstance(po, dict): po = po.get('data', po.get('ResultData', []))

# CTO P1 unshipped
cto_p1 = [p for p in po if p.get('MASTER_TYPE') == 'PRD' and p.get('SUB_TYPE') == 'CTO' and str(p.get('PRIORITY','')) == '1']
unshipped = [p for p in cto_p1 if (p.get('PO_QTY',0) or 0) > (p.get('SHIP_QTY',0) or 0)]

vn_tz = timezone(timedelta(hours=7))
now_vn = datetime.now(vn_tz)
today = now_vn.date()
window_start = today - timedelta(days=3)
window_end = today + timedelta(days=5)

print(f'Today: {today}')
print(f'28H window: {window_start} to {window_end}')
print(f'CTO P1 unshipped: {len(unshipped)} records')

# Check each unshipped CTO P1
no_prd = 0
outside_window = []
inside_window = []

for p in unshipped:
    prd = p.get('PO_RECEIVE_DATE')
    if not prd:
        no_prd += (p.get('PO_QTY',0) or 0)
        continue
    try:
        dt = datetime.strptime(str(prd)[:19], '%Y-%m-%dT%H:%M:%S')
    except:
        continue
    due = (dt + timedelta(hours=28)).date()
    unshipped_qty = (p.get('PO_QTY',0) or 0) - (p.get('SHIP_QTY',0) or 0)

    if due < window_start:
        outside_window.append((due, 'before', unshipped_qty, p.get('PO')))
    elif due > window_end:
        outside_window.append((due, 'after', unshipped_qty, p.get('PO')))
    else:
        inside_window.append((due, unshipped_qty, p.get('PO')))

print(f'\nNo PO_RECEIVE_DATE: {no_prd} pcs')
print(f'Inside window: {sum(x[1] for x in inside_window)} pcs ({len(inside_window)} orders)')
print(f'Outside window: {sum(x[2] for x in outside_window)} pcs')

print(f'\n=== Outside window ({len(outside_window)} orders) ===')
from collections import defaultdict
before_by_date = defaultdict(int)
after_by_date = defaultdict(int)
for due, cat, qty, po_id in outside_window:
    if cat == 'before':
        before_by_date[str(due)] += qty
    else:
        after_by_date[str(due)] += qty

print('Before window (expired):')
for d, q in sorted(before_by_date.items())[-10:]:
    print(f'  {d}: {q} pcs')

print('After window (future):')
for d, q in sorted(after_by_date.items())[:10]:
    print(f'  {d}: {q} pcs')
