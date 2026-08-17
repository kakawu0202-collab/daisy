"""Merge 5 OMS reports → unified order records. Single source of truth for all downstream processing."""
from datetime import datetime, timedelta, timezone

DIRTY = {"0001-01-01T00:00:00Z","0001-01-01T06:00:00Z","1900-01-01T00:00:00Z","1900-01-01T06:00:00Z","0001-01-01","1900-01-01"}

def cd(v):
    if not v: return None
    s = str(v).strip()
    return s[:10] if s and s not in DIRTY else None

def normalize(data):
    if isinstance(data, dict):
        return data.get('data', data.get('ResultData', [])) or []
    return data or []


def merge(po_raw, e2e_raw, gpp_raw, asn_raw, ship_raw):
    """Merge all reports. Returns list of dicts with all computed fields."""
    po_d = normalize(po_raw); e2e_d = normalize(e2e_raw); gpp_d = normalize(gpp_raw)
    asn_d = normalize(asn_raw); ship_d = normalize(ship_raw)

    po_prd = [p for p in po_d if p.get('MASTER_TYPE') == 'PRD']
    prd_pos = {str(p.get('PO', '')).strip() for p in po_prd}

    e2e_map = {f"{e.get('PO','')}_{e.get('PO_LINE','')}": e for e in e2e_d}
    gpp_map = {f"{g.get('PO','')}_{g.get('PO_LINE','')}": g for g in gpp_d}

    # Shipped: ASN.QTY (S/SN ACK) → distribute to POs by SHIP_QTY proportion
    asn_qty = {}
    asn_none = set()  # ASNs with SN_STATUS = NONE (pending, not yet S)
    for a in asn_d:
        sns = str(a.get('SN_STATUS','')).upper()
        aid = str(a.get('ASN','')).strip()
        if sns in ('S', 'SN ACK'):
            asn_qty[aid] = a.get('QTY', 0) or 0
        elif sns == 'NONE':
            asn_none.add(aid)

    asn_po = {}
    po_none = set()  # POs linked to NONE ASNs
    for s in ship_d:
        aid, po = str(s.get('ASN','')).strip(), str(s.get('PO','')).strip()
        if aid in asn_none and po in prd_pos:
            po_none.add(po)
        if aid in asn_qty and po in prd_pos:
            if aid not in asn_po: asn_po[aid] = {}
            asn_po[aid][po] = asn_po[aid].get(po, 0) + (s.get('SHIP_QTY', 0) or 0)

    po_shipped = {}
    ship_set = set()
    for aid, po_ships in asn_po.items():
        total = sum(po_ships.values())
        if total == 0: continue
        for po, sq in po_ships.items():
            po_shipped[po] = po_shipped.get(po, 0) + round(asn_qty[aid] * sq / total)
            ship_set.add(po)

    records = []
    for p in po_prd:
        po = str(p.get('PO','')).strip()
        sub, pri = p.get('SUB_TYPE',''), str(p.get('PRIORITY',''))
        cto_p1 = 'Y' if (sub == 'CTO' and pri == '1') else ''
        e, g = e2e_map.get(f"{po}_{p.get('PO_LINE','')}", {}), gpp_map.get(f"{po}_{p.get('PO_LINE','')}", {})

        ack, st = p.get('ACK_STATUS',''), p.get('STATUS','')
        sn_cdt = cd(e.get('SN_CDT'))
        if ack == 'REJECT': sl = 'NACK'
        elif st == 'ZC': sl = 'ZC'
        elif st == 'Close': sl = 'CLOSE'
        elif st == 'Open': sl = 'OPEN (Backlog)' if not sn_cdt else 'OPEN'
        elif st == 'E': sl = 'V'
        else: sl = st

        po_qty = p.get('PO_QTY', 0) or 0
        e_sn = int(e.get('SN_QTY') or 0) if sn_cdt else 0
        sc, ic = e.get('STOCKIN_CDT'), e.get('INPUT_CDT')
        e_fg = (int(e.get('STOCKIN_QTY') or 0) or (po_qty - e_sn)) if (sc and not sn_cdt) else 0
        e_wip = (po_qty - e_sn - e_fg) if (ic and not sc) else 0
        e_atb = (po_qty - e_sn - e_fg - e_wip) if (not ic and (sc or e.get('AFT_CDT'))) else 0
        e_stbl = max(0, po_qty - e_sn - e_fg - e_wip - e_atb)
        hg = g and any(g.get(k) for k in ('WIP','FG','SN','STBL','ATB'))

        records.append(dict(
            po=po, po_line=str(p.get('PO_LINE','')), region=p.get('REGION'),
            sub_type=sub, priority=pri, cto_p1=cto_p1,
            mcid=p.get('MCID'), ship_mode=p.get('SHIP_MODE'), scac=p.get('SCAC'),
            master_type=p.get('MASTER_TYPE'),
            po_qty=po_qty, remain_qty=p.get('REMAIN_QTY',0) or 0, ship_qty=p.get('SHIP_QTY',0) or 0,
            msbd=cd(p.get('MSBD')), psd=cd(p.get('PSD')), final_msbd=cd(p.get('FINAL_MSBD')),
            po_received=p.get('PO_RECEIVE_DATE','') if p.get('PO_RECEIVE_DATE') and str(p.get('PO_RECEIVE_DATE','')).strip()[:10] not in ('0001-01-01','1900-01-01') else None,
            status=st, ack_status=ack, is_hold=p.get('IS_HOLD'), hold_code=p.get('HOLD_CODE'),
            status_label=sl, asn=str(p.get('ASN','')).strip() or '',
            hawb=str(p.get('HAWB','')).strip() or '',
            dpn=p.get('DPN'), ipn=p.get('IPN'), dell_so=p.get('DELL_SO'),
            ship_to_country=p.get('SHIP_TO_COUNTRY'),
            description=str(p.get('DESCRIPTION',''))[:80] if p.get('DESCRIPTION') else '',
            input_cdt=cd(e.get('INPUT_CDT')), stockin_cdt=cd(e.get('STOCKIN_CDT')),
            sn_cdt=sn_cdt, createasn_cdt=cd(e.get('CREATEASN_CDT')),
            stbl=int(g.get('STBL') or 0) if hg else e_stbl,
            atb=int(g.get('ATB') or 0) if hg else e_atb,
            wip=int(g.get('WIP') or 0) if hg else e_wip,
            fg=int(g.get('FG') or 0) if hg else e_fg,
            sn=int(g.get('SN') or 0) if hg else e_sn,
            actual_shipped=1 if po in ship_set else 0,
            shipped_qty=po_shipped.get(po, 0),
            asn_pending=1 if po in po_none else 0,
        ))
    return records
