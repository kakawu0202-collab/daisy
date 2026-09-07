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

    # 3. Business Engine — all business rules (KPI / E2E / Risk / Summary / ASN Check)
    results = business_run(records, reports.get('ship', []), reports.get('asn', []), reports.get('e2e', []))
    k1 = results['k1_summary']
    daily = results['daily_summary']
    risks = results['risks']
    kpi = results['kpi']
    e2e_kpi = results['e2e_kpi']
    asn_check = results['asn_check']
    cto_asn_missing = results['cto_asn_missing']
    st_check = results['st_check']
    tw = kpi.get('weekly', {}).get(kpi.get('this_week_start', ''), {})
    print(f'  K1: {k1["total_qty"]:,}pcs | Risks: {len(risks)} | KPI this week: {tw.get("pct",0)}%')
    if 'error' not in e2e_kpi:
        print(f'  E2E KPI: {len(e2e_kpi.get("kpis",{}))} KPIs computed, {len(e2e_kpi.get("exceptions",[]))} exceptions')
    print(f'  ASN Check: {asn_check.get("__meta",{}).get("asn_count",0)} ASNs indexed')
    print(f'  CTO ASN Missing: {cto_asn_missing["count"]} orders / {cto_asn_missing["qty"]}pcs')
    print(f'  ST Check: {st_check["__meta"]["po_count"]} POs indexed')

    # 4. Store
    conn = get_db()
    added, updated = upsert(conn, records)
    for key, data in [('k1_summary', k1), ('daily_summary', daily), ('risks', risks), ('kpi', kpi), ('e2e_kpi', e2e_kpi), ('asn_check', asn_check), ('cto_asn_missing', cto_asn_missing), ('st_check', st_check)]:
        put_cache(conn, key, data)
    print(f'  DB: +{added} ~{updated}')

    # 5. Publish (incremental, ack-tracked)
    target, sent = push(conn, records, k1, daily, risks, kpi, e2e_kpi, asn_check, cto_asn_missing, st_check)
    conn.close()
    if target and sent:
        push_summary = f'OK: {sent} records → {target}'
    elif target:
        push_summary = f'OK: summaries → {target}'
    else:
        push_summary = ''
    return records, push_summary


def run_swan(account=None, password=None):
    """SWAN 项目 pipeline — 独立 OMS 环境（规则与 DAISY 有差异，待定义后填充）。

    骨架：未配置 OMS_SWAN_URL 时优雅跳过；配置后走 独立拉数 → merge(project='SWAN')
    → Business Engine → 缓存 key 加 'SWAN:' 前缀 → 推送。
    """
    swan_url = os.environ.get('OMS_SWAN_URL', '')
    if not swan_url:
        print('[SWAN] 未配置 OMS_SWAN_URL（独立环境地址），本轮跳过')
        return None, None
    # TODO(SWAN): 待用户提供 SWAN OMS 环境地址/账号/报告ID 后实现拉数与规则差异
    print(f'[SWAN] 环境已配置（{swan_url}），拉数与规则待实现')
    return None, None


class DailyProcessor:
    """Placeholder for daily_summary module — implemented inline for now."""
    pass
