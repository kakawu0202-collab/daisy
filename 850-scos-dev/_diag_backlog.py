"""Diagnose backlog discrepancy — find exact diff source."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data-engine'))
from storage.db import get_db

conn = get_db()
rows = [dict(r) for r in conn.execute('SELECT * FROM orders').fetchall()]
print(f'{len(rows)} records\n')

# Compute per-type
types = {'CTO_P1': 0, 'FGA': 0, 'RTL': 0, 'CTO_P2': 0, 'OTHER': 0}
qty_by_type = {'CTO_P1': 0, 'FGA': 0, 'RTL': 0, 'CTO_P2': 0, 'OTHER': 0}
shipped_by_type = {'CTO_P1': 0, 'FGA': 0, 'RTL': 0, 'CTO_P2': 0, 'OTHER': 0}

for r in rows:
    po_qty = r.get('po_qty', 0) or 0
    sq = r.get('shipped_qty', 0) or 0
    t = 'CTO_P1' if r.get('cto_p1') == 'Y' else (r.get('sub_type') or 'OTHER')
    if t not in ('CTO_P1', 'FGA', 'RTL', 'CTO'):
        t = 'CTO_P2' if t == 'CTO' else 'OTHER'
    else:
        t = 'CTO_P2' if t == 'CTO' else t
    types[t] += 1
    qty_by_type[t] += po_qty
    shipped_by_type[t] += sq

total_qty = sum(qty_by_type.values())
total_shipped = sum(min(shipped_by_type[t], qty_by_type[t]) for t in qty_by_type)
total_unshipped = sum(max(0, qty_by_type[t] - shipped_by_type[t]) for t in qty_by_type)

print(f'Total qty: {total_qty:,}')
print(f'Total shipped (per-type capped): {total_shipped:,}')
print(f'Unshipped: {total_qty - total_shipped:,} (should = sum type unshipped = {total_unshipped:,})')

print(f'\n{"Type":<10} {"Count":>6} {"Qty":>10} {"Shipped":>10} {"Unshipped":>10} {"CappedSh":>10}')
for t in ['CTO_P1', 'FGA', 'RTL', 'CTO_P2', 'OTHER']:
    q = qty_by_type[t]; s = shipped_by_type[t]
    cs = min(s, q); us = max(0, q - s)
    print(f'{t:<10} {types[t]:>6} {q:>10,} {s:>10,} {us:>10,} {cs:>10,}')

# Also check: per-record shipped_qty exceeds po_qty?
over = [(r.get('po',''), r.get('po_qty',0), r.get('shipped_qty',0)) for r in rows if (r.get('shipped_qty',0) or 0) > (r.get('po_qty',0) or 0)]
print(f'\nRecords with shipped_qty > po_qty: {len(over)}')
if over:
    for po, q, s in over[:5]:
        print(f'  {po}: po_qty={q}, shipped_qty={s}, excess={s-q}')

# Re-check: if total_qty - total_shipped != total_unshipped, there's a bug
actual = total_qty - sum(min(shipped_by_type[t], qty_by_type[t]) for t in qty_by_type)
expected = sum(max(0, qty_by_type[t] - shipped_by_type[t]) for t in qty_by_type)
if actual != expected:
    print(f'\n*** BUG: actual unshipped {actual} != expected {expected} ***')
    # This should NEVER happen — the math is identity
else:
    print(f'\nMath checks: actual {actual} == expected {expected} (OK, this should never fail)')
