"""ST Validator — SHIP_STATUS 出货状态校验（Business Engine 规则）。

输入 PO 或 ASN，校验出货状态一致性。基于 merged records 现有字段的派生校验
（raw ship_status 由 merge 从出货报告映射，公司侧同步后才有值）。

校验规则（按 PO 逐条）：
- NACK：ack_status=REJECT → error
- 已出货无 SN：actual_shipped=1 且无 sn_cdt → error（数据异常）
- 未标记出货但有出货量：actual_shipped=0 且 shipped_qty>0 → warn
- 超发：shipped_qty > po_qty → warn
- Hold → warn
- 部分出货：0 < shipped_qty < po_qty → info
- raw ship_status 异常值（非空且不含已出货标记时结合 actual_shipped 提示）→ 观察项

verdict 优先级：NACK > ERROR(异常) > WARN > PARTIAL > OPEN > PASS
纯计算、零存储副作用。
"""


def _check_record(r):
    """返回 (verdict, checks) —— 单条 PO 的出货状态校验。"""
    checks = []
    q = r.get('po_qty', 0) or 0
    sq = r.get('shipped_qty', 0) or 0
    shipped = bool(r.get('actual_shipped'))
    nack = str(r.get('ack_status', '')).upper() == 'REJECT'
    hold = str(r.get('is_hold', '')).upper() == 'Y' or bool((r.get('hold_code') or '').strip())
    ss = str(r.get('ship_status') or '').strip()

    if nack:
        checks.append({'name': 'nack', 'level': 'error', 'detail': 'PO 被拒（ACK REJECT）'})
    if shipped and not r.get('sn_cdt'):
        checks.append({'name': 'sn', 'level': 'error', 'detail': '已标记出货但无 SN_CDT（数据异常）'})
    if not shipped and sq > 0:
        checks.append({'name': 'flag', 'level': 'warn', 'detail': f'有出货量 {sq} 但未标记出货'})
    if sq > q and q > 0:
        checks.append({'name': 'over', 'level': 'warn', 'detail': f'超发 {sq - q} pcs（shipped {sq} > po_qty {q}）'})
    if hold:
        checks.append({'name': 'hold', 'level': 'warn', 'detail': f'PO on Hold（{r.get("hold_code") or "Y"}）'})
    if 0 < sq < q:
        checks.append({'name': 'partial', 'level': 'info', 'detail': f'部分出货 {sq}/{q}（差 {q - sq}）'})
    if ss and not shipped:
        checks.append({'name': 'ship_status', 'level': 'info', 'detail': f'出货报告 SHIP_STATUS={ss} 但未标记出货'})

    if nack:
        verdict = 'NACK'
    elif any(c['level'] == 'error' for c in checks):
        verdict = 'ERROR'
    elif any(c['level'] == 'warn' for c in checks):
        verdict = 'WARN'
    elif 0 < sq < q:
        verdict = 'PARTIAL'
    elif shipped:
        verdict = 'PASS'
    else:
        verdict = 'OPEN'
    return verdict, checks


def compute(records):
    by_po = {}
    by_asn = {}

    for r in records:
        po = r.get('po')
        aid = str(r.get('asn') or '').strip()
        if not aid or aid.lower() == 'none':
            aid = ''  # OMS 空值存成 'None'，视为无 ASN
        verdict, checks = _check_record(r)
        item = {
            'po': po, 'po_line': r.get('po_line', '1'),
            'cust': r.get('cust') or '', 'so': r.get('dell_so') or '',
            'mcid': r.get('mcid') or '', 'region': r.get('region') or '',
            'cto_p1': r.get('cto_p1') or '',
            'po_qty': r.get('po_qty', 0) or 0,
            'shipped_qty': r.get('shipped_qty', 0) or 0,
            'ship_status': str(r.get('ship_status') or ''),
            'status': r.get('status') or '', 'ack_status': r.get('ack_status') or '',
            'is_hold': r.get('is_hold') or '', 'hold_code': r.get('hold_code') or '',
            'sn_cdt': str(r.get('sn_cdt', ''))[:16],
            'createasn_cdt': str(r.get('createasn_cdt', ''))[:16],
            'actual_shipped': 1 if r.get('actual_shipped') else 0,
            'asn': aid,
            'verdict': verdict,
            'checks': checks,
        }
        by_po[po] = item
        if aid:
            by_asn.setdefault(aid, []).append(item)

    # ASN 级汇总（取 PO 中最严重判定）
    _order = {'NACK': 0, 'ERROR': 1, 'WARN': 2, 'PARTIAL': 3, 'OPEN': 4, 'PASS': 5}
    asn_summary = {}
    for aid, items in by_asn.items():
        worst = min(items, key=lambda i: _order.get(i['verdict'], 9))
        asn_summary[aid] = {
            'asn': aid, 'po_count': len(items),
            'po_qty_total': sum(i['po_qty'] for i in items),
            'shipped_total': sum(i['shipped_qty'] for i in items),
            'ship_status': '/'.join(sorted({i['ship_status'] for i in items if i['ship_status']})),
            'verdict': worst['verdict'],
            'checks': [c for i in items for c in i['checks']][:10],
            'pos': items,
        }

    meta = {'po_count': len(by_po), 'asn_count': len(by_asn)}
    for v in ('PASS', 'PARTIAL', 'OPEN', 'WARN', 'ERROR', 'NACK'):
        meta[v.lower()] = sum(1 for i in by_po.values() if i['verdict'] == v)
    return {'by_po': by_po, 'by_asn': asn_summary, '__meta': meta}
