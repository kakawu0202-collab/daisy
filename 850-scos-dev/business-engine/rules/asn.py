"""ASN Checker — 按 ASN 聚合订单记录并做业务校验（Business Engine 规则）。

口径（数据字典 §八 / 业务规则 §二）：
- SN_STATUS S / SN ACK → 已出货；NONE → 待出货（Backlog）
- ASN_STATUS NACK 或关联 PO ACK_STATUS=REJECT → NACK 直接提醒
- shipped_qty：ASN.QTY 按 SHIP_QTY 比例分配到 PO（cap at PO_QTY）
- CTO 不可 Partial（数据字典 §二），FGA 可 Partial

result 优先级：NACK > HOLD > PASS/PARTIAL/PENDING/OPEN
纯计算、零存储副作用。raw_asn/raw_ship 仅作富化（公司侧有原始报告）。
"""


def compute(records, raw_asn=None, raw_ship=None):
    """records: merged orders。raw_asn/raw_ship: OMS 原始报告（可选）。
    Returns {ASN: check_result}（含 __meta 汇总计数）。"""
    raw_asn = raw_asn or []
    raw_ship = raw_ship or []
    if isinstance(raw_asn, dict):
        raw_asn = raw_asn.get('data', raw_asn.get('ResultData', [])) or []
    if isinstance(raw_ship, dict):
        raw_ship = raw_ship.get('data', raw_ship.get('ResultData', [])) or []

    # Raw 富化映射（可选）
    asn_info = {}   # ASN -> {qty, sn_status, asn_status, ship_date}
    for a in raw_asn:
        aid = str(a.get('ASN', '')).strip()
        if not aid:
            continue
        asn_info[aid] = {
            'qty': a.get('QTY', 0) or 0,
            'sn_status': str(a.get('SN_STATUS', '')).upper(),
            'asn_status': str(a.get('ASN_STATUS', '')).upper(),
            'ship_date': str(a.get('SHIP_DATE', ''))[:10],
        }
    ship_info = {}  # ASN -> {truck_no, scac, ship_qty}
    for s in raw_ship:
        aid = str(s.get('ASN', '')).strip()
        if not aid:
            continue
        d = ship_info.setdefault(aid, {'truck_no': '', 'scac': '', 'ship_qty': 0})
        d['truck_no'] = d['truck_no'] or str(s.get('TRUCK_NO', '')).strip()
        d['scac'] = d['scac'] or str(s.get('SCAC', '')).strip()
        d['ship_qty'] += s.get('SHIP_QTY', 0) or 0

    # 按 ASN 聚合 records
    groups = {}
    for r in records:
        aid = str(r.get('asn', '')).strip()
        if not aid:
            continue
        groups.setdefault(aid, []).append(r)

    result = {}
    for aid, rows in groups.items():
        po_list = []
        qty_total = 0
        shipped_total = 0
        pending_qty = 0
        nack_pos = []
        hold_pos = []
        for r in rows:
            q = r.get('po_qty', 0) or 0
            sq = r.get('shipped_qty', 0) or 0
            qty_total += q
            shipped_total += sq
            if r.get('asn_pending'):
                pending_qty += max(0, q - sq)
            if str(r.get('ack_status', '')).upper() == 'REJECT':
                nack_pos.append(r['po'])
            if str(r.get('is_hold', '')).upper() == 'Y' or (r.get('hold_code') or '').strip():
                hold_pos.append(r['po'])
            po_list.append({
                'po': r.get('po'), 'po_line': r.get('po_line', '1'),
                'po_qty': q, 'shipped_qty': sq, 'ship_qty': r.get('ship_qty', 0) or 0,
                'status': r.get('status'), 'ack_status': r.get('ack_status'),
                'is_hold': r.get('is_hold'), 'hold_code': r.get('hold_code'),
                'cto_p1': r.get('cto_p1'), 'region': r.get('region'),
                'sn_cdt': str(r.get('sn_cdt', ''))[:10] if r.get('sn_cdt') else '',
            })

        info = asn_info.get(aid, {})
        shp = ship_info.get(aid, {})

        # 校验判定
        checks = []
        if nack_pos:
            checks.append({'name': 'nack', 'level': 'error',
                           'detail': f'{len(nack_pos)} PO NACK: {", ".join(nack_pos[:5])}'})
        if hold_pos:
            checks.append({'name': 'hold', 'level': 'warn',
                           'detail': f'{len(hold_pos)} PO on hold: {", ".join(hold_pos[:5])}'})
        shipped_ok = shipped_total >= qty_total
        if shipped_total == 0:
            checks.append({'name': 'ship', 'level': 'info', 'detail': '尚未出货'})
        elif not shipped_ok:
            checks.append({'name': 'ship', 'level': 'warn',
                           'detail': f'部分出货 {shipped_total}/{qty_total}（差 {qty_total - shipped_total}）'})

        if nack_pos:
            verdict = 'NACK'
        elif hold_pos:
            verdict = 'HOLD'
        elif shipped_ok:
            verdict = 'PASS'
        elif shipped_total > 0:
            verdict = 'PARTIAL'
        elif pending_qty > 0:
            verdict = 'PENDING'
        else:
            verdict = 'OPEN'

        # SN_STATUS 优先 raw；否则由记录推导（actual_shipped → S；asn_pending → NONE）
        sn_status = info.get('sn_status', '')
        if not sn_status:
            any_shipped = any(r.get('actual_shipped') for r in rows)
            any_pending = any(r.get('asn_pending') for r in rows)
            sn_status = 'S' if any_shipped else ('NONE' if any_pending else '')

        result[aid] = {
            'asn': aid,
            'qty': info.get('qty') or qty_total,
            'sn_status': sn_status,
            'asn_status': info.get('asn_status', ''),
            'ship_date': info.get('ship_date', ''),
            'truck_no': shp.get('truck_no', ''),
            'scac': shp.get('scac', ''),
            'ship_qty_raw': shp.get('ship_qty', 0),
            'po_count': len(po_list),
            'po_qty_total': qty_total,
            'shipped_total': shipped_total,
            'pending_qty': pending_qty,
            'cto_p1_any': any(p['cto_p1'] == 'Y' for p in po_list),
            'result': verdict,
            'checks': checks,
            'pos': po_list,
        }

    result['__meta'] = {
        'asn_count': len(groups),
        'pass': sum(1 for k, v in result.items() if k != '__meta' and v['result'] == 'PASS'),
        'partial': sum(1 for k, v in result.items() if k != '__meta' and v['result'] == 'PARTIAL'),
        'pending': sum(1 for k, v in result.items() if k != '__meta' and v['result'] == 'PENDING'),
        'nack': sum(1 for k, v in result.items() if k != '__meta' and v['result'] == 'NACK'),
        'hold': sum(1 for k, v in result.items() if k != '__meta' and v['result'] == 'HOLD'),
        'open': sum(1 for k, v in result.items() if k != '__meta' and v['result'] == 'OPEN'),
    }
    return result
