# -*- coding: utf-8 -*-
"""
870 FGA loader —— 从 850 行(OMS) + 上传的 Hold/Status CSV 构建 PO 列表并分配。
供 850-toolbox server.py 调用。
"""
import csv, io
from collections import defaultdict
from fga870_allocate import PO, allocate_all, alloc_to_dict


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return 0


def parse_status(csv_text):
    """T_STATUS_PO CSV 文本 → {po: {'SS':n,'BS':n,'SCH':n}}"""
    status = defaultdict(lambda: defaultdict(int))
    for row in csv.DictReader(io.StringIO(csv_text or "")):
        code = (row.get("STATUS_CODE") or "").strip()
        if code in ("SS", "BS", "SCH"):
            status[(row.get("AC_PO") or "").strip()][code] += _int(row.get("KEY_QTY"))
    return status


def parse_hold(csv_text):
    """T_HOLD_PO CSV 文本 → {po: {'short':[(mat,qty)],'hold':n,'a32':bool}}（FLAG=H 且 OH）"""
    holds = defaultdict(lambda: {"short": [], "hold": 0, "a32": False})
    for row in csv.DictReader(io.StringIO(csv_text or "")):
        if (row.get("FLAG") or "").strip() != "H":
            continue
        if (row.get("HOLD_TYPE") or "").strip() != "OH":    # IH 忽略
            continue
        po = (row.get("AC_PO") or "").strip()
        code = (row.get("HOLD_CODE") or "").strip()
        q = _int(row.get("KEY_QTY"))
        if code in ("A11", "A12", "A14"):
            holds[po]["short"].append(((row.get("KEY_REF") or code).strip(), q))
        elif code in ("A01", "A05"):
            holds[po]["hold"] += q
        elif code == "A32":
            holds[po]["a32"] = True
    return holds


def build_pos(po_rows, status, holds):
    """po_rows: 850 原始 dict 行（OMS rpt_850_po）。返回 (pos, skipped)。"""
    pos, skipped = [], defaultdict(int)
    for r in po_rows:
        if str(r.get("SUB_TYPE") or "").strip().upper() != "FGA":
            continue
        if str(r.get("IS_CANCEL") or "").strip().upper() == "Y":
            skipped["cancelled"] += 1; continue
        qty = _int(r.get("PO_QTY"))
        if qty <= 0:
            skipped["qty<=0"] += 1; continue
        st_lbl = str(r.get("STATUS") or "").strip().upper()
        if st_lbl in ("NACK", "ZC", "CLOSE"):
            skipped["status=" + st_lbl] += 1; continue

        po = str(r.get("PO") or "").strip()
        line = str(r.get("PO_LINE") or "").strip()
        sn = _int(r.get("SHIP_QTY"))
        open_qty = qty - sn

        st = status.get(po, {})
        ss_cum, bs_cum, sch_cum = st.get("SS", 0), st.get("BS", 0), st.get("SCH", 0)
        hd = holds.get(po, {"short": [], "hold": 0, "a32": False})
        has_hold = hd["hold"] > 0
        eff_hold = min(hd["hold"], open_qty) if has_hold else 0

        good_room = max(0, open_qty)                    # 产出按 open 封顶
        prod_ss = max(0, ss_cum - sn)
        prod_bs = max(0, bs_cum - ss_cum)
        prod_sch = max(0, sch_cum - bs_cum)
        ss = min(prod_ss, good_room); good_room -= ss
        bs = min(prod_bs, good_room); good_room -= bs
        sch = min(prod_sch, good_room); good_room -= sch

        pos.append(PO(
            po=po, po_line=line,
            ipn=str(r.get("IPN") or "").strip(), mcid=str(r.get("MCID") or "").strip(),
            msbd=str(r.get("MSBD") or "").strip(), po_qty=qty,
            ack=0, asn=0, sn=sn, sch=sch, bs=bs, ss=ss,
            shortages=[(m, q) for m, q in hd["short"]],
            has_hold=has_hold, hold_qty=eff_hold, a32=hd["a32"],
        ))
    return pos, dict(skipped)


def run_allocation(po_rows, status_text, hold_text):
    """整合入口：850 行 + 两份 CSV 文本 → 分配结果 JSON。"""
    status = parse_status(status_text)
    holds = parse_hold(hold_text)
    pos, skipped = build_pos(po_rows or [], status, holds)
    allocs = allocate_all(pos)
    groups = {}
    for a in allocs:
        groups.setdefault((a.ipn, a.mcid), 0)
        groups[(a.ipn, a.mcid)] += 1
    return {
        "records": [alloc_to_dict(a) for a in allocs],
        "total": len(allocs),
        "groups": len(groups),
        "multi_groups": sum(1 for v in groups.values() if v > 1),
        "balanced": sum(1 for a in allocs if a.balanced),
        "skipped": skipped,
        "alerts": [{"po": a.po, "ipn": a.ipn, "mcid": a.mcid, "alert": a.alert}
                   for a in allocs if a.alert],
    }
