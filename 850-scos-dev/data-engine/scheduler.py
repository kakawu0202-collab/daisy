"""Orchestrator: collect → process → store → publish. Automatic pipeline."""
import sys, os, json, time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collector.oms import OMSClient
from processor.merge import merge
from storage.db import get_db, upsert, put_cache
from publisher.push import push
# Business Engine (Layer 2) — 所有业务规则计算都在这里
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'business-engine'))
from engine import run as business_run

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

    # 2. Process (Data Engine: clean + standardize)
    records = merge(reports['po'], reports['e2e'], reports['gpp'], reports['asn'], reports['ship'])
    print(f'  Records: {len(records)}')

    # 3. Business Engine — all business rules (KPI / E2E / Risk / Summary)
    results = business_run(records, reports.get('ship', []), reports.get('asn', []), reports.get('e2e', []))
    k1 = results['k1_summary']
    daily = results['daily_summary']
    risks = results['risks']
    kpi = results['kpi']
    e2e_kpi = results['e2e_kpi']
    tw = kpi.get('weekly', {}).get(kpi.get('this_week_start', ''), {})
    print(f'  K1: {k1["total_qty"]:,}pcs | Risks: {len(risks)} | KPI this week: {tw.get("pct",0)}%')
    if 'error' not in e2e_kpi:
        print(f'  E2E KPI: {len(e2e_kpi.get("kpis",{}))} KPIs computed, {len(e2e_kpi.get("exceptions",[]))} exceptions')

    # 4. Store
    conn = get_db()
    added, updated = upsert(conn, records)
    for key, data in [('k1_summary', k1), ('daily_summary', daily), ('risks', risks), ('kpi', kpi), ('e2e_kpi', e2e_kpi)]:
        put_cache(conn, key, data)
    print(f'  DB: +{added} ~{updated}')

    # 5. Publish (incremental, ack-tracked)
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
