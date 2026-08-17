"""Orchestrator: collect → process → store → publish. Automatic pipeline."""
import sys, os, json, time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collector.oms import OMSClient
from processor.merge import merge
from processor.k1 import compute as k1_compute
from processor.daily import compute as daily_compute
from processor.risk import compute as risk_compute
from processor.kpi import compute as kpi_compute
from processor.e2e_kpi import compute_all as e2e_kpi_compute
from storage.db import get_db, upsert, put_cache
from publisher.push import push

PULL_INTERVAL = 10 * 60  # 10 minutes


def run(account='31000161', password=None):
    print(f'[{datetime.now().strftime("%H:%M:%S")}] Pipeline start...')

    # 1. Collect
    c = OMSClient()
    if not c.login(account, password):
        print('  Login FAILED'); return None, None
    reports = c.pull_all()
    if not reports.get('po'):
        print('  No data'); return None, None

    # 2. Process
    records = merge(reports['po'], reports['e2e'], reports['gpp'], reports['asn'], reports['ship'])
    print(f'  Records: {len(records)}')

    k1 = k1_compute(records)
    daily = daily_compute(records, reports.get('ship', []), reports.get('asn', []))
    risks = risk_compute(records)
    kpi = kpi_compute(records)
    e2e_kpi = e2e_kpi_compute(reports.get('e2e', []), records)
    tw = kpi.get('weekly', {}).get(kpi.get('this_week_start', ''), {})
    print(f'  K1: {k1["total_qty"]:,}pcs | Risks: {len(risks)} | KPI this week: {tw.get("pct",0)}%')
    if 'error' not in e2e_kpi:
        print(f'  E2E KPI: {len(e2e_kpi.get("kpis",{}))} KPIs computed, {len(e2e_kpi.get("exceptions",[]))} exceptions')

    # 3. Store
    conn = get_db()
    added, updated = upsert(conn, records)
    for key, data in [('k1_summary', k1), ('daily_summary', daily), ('risks', risks), ('kpi', kpi), ('e2e_kpi', e2e_kpi)]:
        put_cache(conn, key, data)
    print(f'  DB: +{added} ~{updated}')

    # 4. Publish (incremental, ack-tracked)
    target, sent = push(conn, records, k1, daily, risks, kpi, e2e_kpi)
    conn.close()
    if target and sent:
        push_summary = f'OK: {sent} records → {target}'
    elif target:
        push_summary = f'OK: summaries → {target}'
    else:
        push_summary = ''
    return records, push_summary


class DailyProcessor:
    """Placeholder for daily_summary module — implemented inline for now."""
    pass
