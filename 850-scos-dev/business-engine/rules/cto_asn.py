"""CTO P1 已入库未开 ASN — 提醒清单（Business Engine 规则）。

口径（对应风险规则 R5 第二分支）：
- cto_p1='Y' AND 有 STOCKIN_CDT（已入库）AND 无 CREATEASN_CDT（未开立 ASN）AND 未出货
- 每笔附带 28H 目标出货时间（PO_RECEIVE + 28H）与已入库时长
- 按 28H 目标时间升序（最紧急在前），无 PO_RECEIVE 的排最后
纯计算、零存储副作用。
"""
from datetime import datetime, timedelta, timezone


def _parse_dt(s):
    if not s:
        return None
    s = str(s).strip()
    try:
        return datetime.strptime(s[:19], '%Y-%m-%dT%H:%M:%S')
    except Exception:
        try:
            return datetime.strptime(s[:10], '%Y-%m-%d')
        except Exception:
            return None


def compute(records):
    vn_tz = timezone(timedelta(hours=7))
    now = datetime.now(vn_tz).replace(tzinfo=None)
    items = []
    for r in records:
        if r.get('cto_p1') != 'Y':
            continue
        if not r.get('stockin_cdt'):
            continue
        if r.get('createasn_cdt'):
            continue
        if r.get('actual_shipped'):
            continue

        prd = _parse_dt(r.get('po_received'))
        fg = _parse_dt(r.get('stockin_cdt'))
        target = prd + timedelta(hours=28) if prd else None
        items.append({
            'po': r.get('po'), 'po_line': r.get('po_line', '1'),
            'so': r.get('dell_so') or '', 'mcid': r.get('mcid') or '',
            'dpn': r.get('dpn') or '', 'ipn': r.get('ipn') or '',
            'region': r.get('region') or '', 'priority': r.get('priority') or '',
            'po_qty': r.get('po_qty', 0) or 0,
            'status': r.get('status') or '', 'is_hold': r.get('is_hold') or '',
            'hold_code': r.get('hold_code') or '',
            'stockin_cdt': str(r.get('stockin_cdt'))[:19],
            'po_received': str(r.get('po_received') or '')[:19],
            'target_28h': target.strftime('%m/%d %H:%M') if target else '',
            'target_passed': bool(target and target < now),
            'hours_since_fg': round((now - fg).total_seconds() / 3600, 1) if fg else None,
        })

    items.sort(key=lambda x: (x['target_28h'] == '', x['target_28h']))
    return {
        'count': len(items),
        'qty': sum(i['po_qty'] for i in items),
        'overdue': sum(1 for i in items if i['target_passed']),
        'items': items,
    }
