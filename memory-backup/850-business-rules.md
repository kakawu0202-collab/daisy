---
name: 850-business-rules
description: 850 SCOS Business Engine 业务规则 — 风险判定、NACK处理、KPI考核标准（2026-08-02）
metadata: 
  node_type: memory
  type: reference
  updated: 2026-08-02
  originSessionId: 59f737cb-72a3-47b9-a322-d27083bd9118
---

# 850 SCOS — 业务规则

## 一、风险判定规则

### R1 · CTO P1 28H 风险
- CTO P1：PO_RECEIVE_DATE + 28H 截止
- 超时未出货 → 风险

### R2 · MSBD 到期未出货（非CTO P1）
- MSBD 到达且无 SN send → 风险

### R3 · STBL 异常
- STBL > 0 即异常
- **FGA**：按 STBL 数量（pcs）计算
- **非FGA（CTO/RTL）**：按整条 PO 的 pcs 计算

### R4 · ATB 预警
- 距离 MSBD ≤ 2天 → 预警

### R5 · CTO P1 Shuttle 段
- 入库（FG）后 5H 内必须出货
- 入库后 1H 内未开立 ASN → 警告

### R6 · 各环节超时预警
- Planning（11H）/ Build（12H）/ Shuttle（5H）
- 每段超过目标 1H 即预警

### R7 · 风险等级
- 待定义（TBD）

---

## 二、NACK 处理规则

| 类型 | 处理方式 |
|------|---------|
| PO NACK | 仅记录，不特殊分析 |
| ASN NACK | 直接提醒 |
| SN NACK | 直接提醒 |

---

## 三、KPI 考核标准

### 主要 KPI：CTO P1 28H 达标率

| 维度 | 值 |
|------|----|
| 统计周期 | 按天 + 按周 |
| 周的区间 | **周六 ~ 周五** |
| 分析范围 | 周期内已出货的订单 |
| 及格线 | ≥ 75% |
| 内部目标 | ≥ 90% |

### 28H 三段目标

| 段 | 计时 | 目标 | 超1H预警 |
|----|------|------|---------|
| Planning | PO_RECEIVE_DATE → INPUT_CDT | ≤ 11H | > 12H |
| Build | INPUT_CDT → STOCKIN_CDT | ≤ 12H | > 13H |
| Shuttle | STOCKIN_CDT → SN_CDT | ≤ 5H | > 6H |
| SS-ASN | STOCKIN_CDT → CREATEASN_CDT | ≤ 1H | > 2H |

---

## 关联

- [[850-data-dictionary]] — 数据字典（字段含义、编码规则）
- [[850-supply-chain-os]] — 五层架构蓝图
- [[cto-p1-kpi-formula]] — CTO P1 28H 计算公式
