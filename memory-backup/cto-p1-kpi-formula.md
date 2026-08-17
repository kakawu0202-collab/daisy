---
name: cto-p1-kpi-formula
description: CTO P1 28H KPI 计算公式 — Planning/Build/Shuttle三段（仅已出货）
metadata: 
  node_type: memory
  type: project
  updated: 2026-07-28
  originSessionId: 51f8955d-e6f2-41b3-bd7e-c8ca576e12ba
---

# CTO P1 28H KPI 计算公式

## 数据源
- 850 PO: `PO_RECEIVE_DATE`
- E2E: `INPUT_CDT`, `STOCKIN_CDT`, `SN_CDT`
- 筛选: `SUB_TYPE=CTO AND PRIORITY=1 AND MASTER_TYPE=PRD AND SN_CDT非空`

## 三段公式

| 阶段 | 公式 | 目标 | 含义 |
|------|------|------|------|
| Planning 11H | `INPUT_CDT - PO_RECEIVE_DATE` | ≤11H | PO接收→上线 |
| Build 12H | `STOCKIN_CDT - INPUT_CDT` | ≤12H | 上线→入库 |
| Shuttle 5H | `SN_CDT - STOCKIN_CDT` | ≤5H | 入库→SN发送 |
| Clean 28H | `SN_CDT - PO_RECEIVE_DATE` | ≤28H | PO接收→SN发送 |

## 达成率

```
达成率 = 达标PO数 / 已出货PO总数 × 100%
```

已出货 = SN_CDT 存在（S/N已分配）

## 关联
- [[850-toolbox]]
