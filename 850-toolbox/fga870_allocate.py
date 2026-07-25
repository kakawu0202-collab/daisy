# -*- coding: utf-8 -*-
"""
870 FGA 优先级分配引擎
===============================================================
业务规则（对齐需求）：
  分组键     : IPN + MCID（仅同组内互相分配）
  组内优先级 : MSBD 升序，最早 = P1 = 最优先
  锁定量     : ACK / ASN / SN 只对本 PO 生效，不参与分配
  好产出     : SS / BS / SCH 池化后【上浮】到高优先级 PO
               单 PO 内扣减顺序 = SS → BS → SCH（越接近出货越先给）
  坏缺口     : 缺料(A11族) + 质量hold(A05/A01) 【下沉】到低优先级 PO
  A32        : 整单锁，退出需求；其好产出【退回组内池】给他人用
  缺料 MAX   : 单 PO 缺多材料时，平衡只计 MAX(材料缺量)，展示前 3 个材料
  hold 数量  : A05/A01 的 KEY_QTY 无意义，用【残差】兜平
  平衡等式   : ACK + SCH + BS + SS + ASN + SN + MAX(缺料) + A05hold = PO_QTY
===============================================================
本文件不依赖任何三方库，纯逻辑，可直接单测。
"""
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from collections import defaultdict


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class PO:
    """一条 FGA 订单行的原始输入（分配前）。"""
    po: str
    po_line: str
    ipn: str
    mcid: str
    msbd: str                 # ISO 日期字符串，可直接字典序排序
    po_qty: int
    ack: int = 0              # 锁定：验证后 open 数量
    asn: int = 0              # 锁定：已开 ASN 数量
    sn: int = 0               # 锁定：SN send 数量
    # 本 PO 自身的好产出（会被池化重分配）
    sch: int = 0
    bs: int = 0
    ss: int = 0
    # 本 PO 自身的缺料（A11 族），[(材料, 缺量), ...]；同族 A12/A14 也归这里
    shortages: List[Tuple[str, int]] = field(default_factory=list)
    has_hold: bool = False    # 是否有 A05/A01 质量 hold（与 A11 并存时优先归 A05/A01）
    hold_qty: int = 0         # A05/A01 质量 hold 数量（保留在本 PO，好产出不得覆盖）
    a32: bool = False         # A32 整单锁


@dataclass
class Alloc:
    """一条 FGA 订单行的分配结果。"""
    po: str
    po_line: str
    ipn: str
    mcid: str
    msbd: str
    rank: int                 # 组内优先级序号，1 = 最优先
    po_qty: int
    ack: int
    asn: int
    sn: int
    sch: int
    bs: int
    ss: int
    shortage_lines: List[Tuple[str, int]]   # 分配后落到本 PO 的缺料行（展示用，前3）
    shortage_balance: int                    # 计入平衡的缺料量 = MAX(材料)
    a05: int                                 # 质量 hold 数量（生产中hold，落最低有产出的PO）
    a32: int                                 # A32 整单锁数量
    remark: str
    balanced: bool
    alert: str = ""                          # 异常提醒（如 A05 溢出到 SCH/ACK）


# ---------------------------------------------------------------------------
# 核心：单组分配
# ---------------------------------------------------------------------------
def allocate_group(pos: List[PO]) -> List[Alloc]:
    """对同一 (IPN, MCID) 分组做优先级分配，返回逐 PO 的 Alloc（保持优先级顺序）。"""
    if not pos:
        return []

    active = [p for p in pos if not p.a32]          # 参与分配的 PO
    a32s = [p for p in pos if p.a32]                # A32 整单锁的 PO

    # ---- 好产出池：含 A32 PO 退回的好产出（规则：A32 好产出退回组内池）----
    pool = {
        'ss':  sum(p.ss for p in pos),
        'bs':  sum(p.bs for p in pos),
        'sch': sum(p.sch for p in pos),
    }

    # ---- 缺料池：按材料汇总（全部 PO 的 A11）----
    mat_total: Dict[str, int] = defaultdict(int)
    for p in active:
        for m, q in p.shortages:
            mat_total[m] += q

    # ---- 组内优先级排序：MSBD 升序，同日按 PO 号稳定 ----
    active.sort(key=lambda p: (p.msbd, p.po, p.po_line))

    # ---- 好产出【上浮】：SS/BS/SCH 从 P1→Pn 依次喂满（含将被 A05 抽走的部分）----
    prod: Dict[str, Dict[str, int]] = {}
    residual: Dict[str, int] = {}
    for p in active:
        need = max(0, p.po_qty - (p.ack + p.asn + p.sn))
        take = {'ss': 0, 'bs': 0, 'sch': 0}
        for k in ('ss', 'bs', 'sch'):
            t = min(need, pool[k]); pool[k] -= t; need -= t; take[k] = t
        prod[_key(p)] = take
        residual[_key(p)] = need                        # 未被产出覆盖的缺口 = 待缺料/ACK

    # ---- A05/A01 质量 hold【从最低优先级、有产出的 PO 往上灌】----
    #      生产中发生的 hold 只能落在已产出(SS/BS)的货上；吃完往次低 PO 找；
    #      溢出到 SCH / ACK（hold 了还没造出来的货）→ 记 alert。
    a05_total = sum(p.hold_qty for p in active)
    a05_on_po: Dict[str, int] = defaultdict(int)
    alert_on_po: Dict[str, str] = {}
    a05_rem = a05_total
    # Pass1: 落在最低优先、有产出(BS/SS)的 PO；吃完该 PO 再上移到次低
    for p in reversed(active):                          # Pn → P1，最低优先先
        if a05_rem <= 0:
            break
        t = prod[_key(p)]
        for k in ('bs', 'ss'):                          # 该 PO 先吃 BS 再吃 SS
            take = min(a05_rem, t[k]); t[k] -= take
            a05_on_po[_key(p)] += take; a05_rem -= take
            if a05_rem <= 0:
                break
    # Pass2: 全组 BS/SS 吃完仍有剩 → 占 SCH（排产未产先 hold，异常）
    if a05_rem > 0:
        for p in reversed(active):
            if a05_rem <= 0:
                break
            t = prod[_key(p)]
            take = min(a05_rem, t['sch']); t['sch'] -= take
            if take > 0:
                a05_on_po[_key(p)] += take; a05_rem -= take
                alert_on_po[_key(p)] = "A05占用SCH(排产未产先hold)"
    if a05_rem > 0:                                      # 连排产都没有 → 占 ACK 缺口，严重异常
        for p in reversed(active):
            if a05_rem <= 0:
                break
            take = min(a05_rem, residual[_key(p)]); residual[_key(p)] -= take
            if take > 0:
                a05_on_po[_key(p)] += take; a05_rem -= take
                alert_on_po[_key(p)] = "A05溢出到ACK(无产出可hold)"
    if a05_rem > 0:                                      # 全组都放不下（over-hold）
        p = active[-1]
        a05_on_po[_key(p)] += a05_rem
        alert_on_po[_key(p)] = f"A05无法安放{a05_rem}(超过全组可hold量)"

    # ---- 缺料【集中下沉】：每种材料从最低优先级 PO 往上灌，每 PO 每种料可占到其缺口(MAX 可叠加)----
    mat_on_po: Dict[str, Dict[str, int]] = {_key(p): {} for p in active}
    for m in sorted(mat_total, key=lambda k: -mat_total[k]):     # 量大的料先灌
        remaining = mat_total[m]
        for p in reversed(active):                               # Pn → P1，最低优先先承接
            if remaining <= 0:
                break
            cap = residual[_key(p)]                              # 缺口（A05已从中扣过溢出部分）
            take = min(remaining, cap)
            if take > 0:
                mat_on_po[_key(p)][m] = mat_on_po[_key(p)].get(m, 0) + take
                remaining -= take

    # ---- 组装结果 ----
    out: List[Alloc] = []
    for rank, p in enumerate(active, start=1):
        key = _key(p)
        g = prod[key]                                   # 已扣除 A05 的好产出
        mats = mat_on_po[key]
        short_bal = max(mats.values()) if mats else 0   # 缺任一料即整段不可产 → MAX
        lines3 = sorted(([m, q] for m, q in mats.items()), key=lambda mq: -mq[1])[:3]
        a05 = a05_on_po[key]
        ack = p.ack + residual[key] - short_bal         # 预置ACK + 缺口减掉 MAX 缺料
        bal_ok = (ack + g['sch'] + g['bs'] + g['ss'] + p.asn + p.sn
                  + short_bal + a05) == p.po_qty
        out.append(Alloc(
            po=p.po, po_line=p.po_line, ipn=p.ipn, mcid=p.mcid, msbd=p.msbd,
            rank=rank, po_qty=p.po_qty,
            ack=ack, asn=p.asn, sn=p.sn,
            sch=g['sch'], bs=g['bs'], ss=g['ss'],
            shortage_lines=[(m, q) for m, q in lines3], shortage_balance=short_bal,
            a05=a05, a32=0,
            remark=_remark(ack, g['sch'], g['bs'], g['ss'], p.asn, p.sn,
                           lines3, a05, a32=0),
            balanced=bal_ok, alert=alert_on_po.get(key, ""),
        ))

    # ---- A32 整单锁 PO：整单已未出部分全锁，好产出已退回池 ----
    for p in a32s:
        a32_qty = max(0, p.po_qty - p.asn - p.sn)
        bal_ok = (p.asn + p.sn + a32_qty) == p.po_qty
        out.append(Alloc(
            po=p.po, po_line=p.po_line, ipn=p.ipn, mcid=p.mcid, msbd=p.msbd,
            rank=0, po_qty=p.po_qty,
            ack=0, asn=p.asn, sn=p.sn, sch=0, bs=0, ss=0,
            shortage_lines=[], shortage_balance=0, a05=0, a32=a32_qty,
            remark=_remark(0, 0, 0, 0, p.asn, p.sn, [], 0, a32=a32_qty),
            balanced=bal_ok,
        ))
    return out


def allocate_all(pos: List[PO]) -> List[Alloc]:
    """对全体 FGA 订单按 (IPN, MCID) 自动分组后逐组分配。"""
    groups: Dict[Tuple[str, str], List[PO]] = {}
    for p in pos:
        groups.setdefault((p.ipn, p.mcid), []).append(p)
    result: List[Alloc] = []
    for key in sorted(groups):
        result.extend(allocate_group(groups[key]))
    return result


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------
def _key(p: PO) -> str:
    return f"{p.po}|{p.po_line}"


def _remark(ack, sch, bs, ss, asn, sn, shortage_lines, a05, a32) -> str:
    """严格照需求13格式：ACK-0,SCH-314,BS-0,SS-0,ASN-0,SN-0,A11-mat-qty,...,A05-20"""
    parts = [f"ACK-{ack}", f"SCH-{sch}", f"BS-{bs}", f"SS-{ss}", f"ASN-{asn}", f"SN-{sn}"]
    for mat, q in shortage_lines:
        parts.append(f"A11-{mat}-{q}")
    if a05 > 0:
        parts.append(f"A05-{a05}")
    if a32 > 0:
        parts.append(f"A32-{a32}")
    return ",".join(parts)


# ---------------------------------------------------------------------------
# 表格导出（需求14）
# ---------------------------------------------------------------------------
TABLE_COLUMNS = [
    "PO", "PO_LINE", "IPN", "MCID", "MSBD", "PRIORITY", "PO_QTY",
    "ACK", "SCH", "BS", "SS", "ASN", "SN",
    "A11_MATERIAL", "A11_QTY(MAX)", "A05_HOLD", "A32", "BALANCED", "ALERT", "REMARK",
]


def alloc_to_row(a: Alloc) -> list:
    mats = ";".join(f"{m}:{q}" for m, q in a.shortage_lines)
    return [
        a.po, a.po_line, a.ipn, a.mcid, a.msbd,
        (a.rank if a.rank else "A32"), a.po_qty,
        a.ack, a.sch, a.bs, a.ss, a.asn, a.sn,
        mats, a.shortage_balance, a.a05, a.a32,
        ("OK" if a.balanced else "ERR"), a.alert, a.remark,
    ]


def alloc_to_dict(a: Alloc) -> dict:
    """给前端用的 JSON 记录。"""
    return {
        'po': a.po, 'po_line': a.po_line, 'ipn': a.ipn, 'mcid': a.mcid,
        'msbd': a.msbd, 'rank': a.rank, 'po_qty': a.po_qty,
        'ack': a.ack, 'sch': a.sch, 'bs': a.bs, 'ss': a.ss,
        'asn': a.asn, 'sn': a.sn,
        'a11': ";".join(f"{m}:{q}" for m, q in a.shortage_lines),
        'a11_qty': a.shortage_balance, 'a05': a.a05, 'a32': a.a32,
        'remark': a.remark, 'balanced': a.balanced, 'alert': a.alert,
    }


def write_table_csv(allocs: List[Alloc], path: str) -> None:
    import csv
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(TABLE_COLUMNS)
        for a in allocs:
            w.writerow(alloc_to_row(a))
