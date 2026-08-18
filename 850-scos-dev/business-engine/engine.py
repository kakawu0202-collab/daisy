"""Business Engine — entry point (Layer 2).

Reads merged records + raw reports (from Data Engine), executes ALL business
rules (KPI / E2E / Risk / Summary), returns results. Zero storage side effects —
Data Engine 负责存储与发布，本引擎只计算。

Contract:
    run(records, raw_ship, raw_asn, raw_e2e)
    → {'k1_summary', 'daily_summary', 'risks', 'kpi', 'e2e_kpi'}
    （key 与 cache 表 key 一一对应，scheduler 直接 put_cache + push）
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from summary.k1 import compute as k1_compute
from summary.daily import compute as daily_compute
from rules.risk import compute as risk_compute
from kpi.kpi import compute as kpi_compute
from kpi.e2e_kpi import compute_all as e2e_kpi_compute


def run(records, raw_ship=None, raw_asn=None, raw_e2e=None):
    """Execute all business rules. 算法与 v1.0.0 完全一致（M1 只搬不拆）。"""
    k1 = k1_compute(records)
    daily = daily_compute(records, raw_ship or [], raw_asn or [])
    risks = risk_compute(records)
    kpi = kpi_compute(records)
    e2e_kpi = e2e_kpi_compute(raw_e2e or [], records)
    return {
        'k1_summary': k1,
        'daily_summary': daily,
        'risks': risks,
        'kpi': kpi,
        'e2e_kpi': e2e_kpi,
    }
