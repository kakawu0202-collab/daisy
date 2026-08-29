---
name: 850-business-rules
description: 850 SCOS Business Engine 业务规则 — 风险判定、NACK处理、KPI考核标准（2026-08-02）
metadata: 
  node_type: memory
  type: reference
  updated: 2026-08-02
  originSessionId: 59f737cb-72a3-47b9-a322-d27083bd9118
  modified: 2026-08-29T15:45:03.725Z
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

## 二点五、MSBD 统计口径

- **MSBD 出货卡片/plan 不统计 CTO P1**：CTO P1 单独走 28H 时效管控（PO_RECEIVE + 28H）
- 对应代码：k1.py msbd_plan 只遍历 `others`（非 CTO P1）
- 卡片 planned/actual 为"非 CTO P1"口径；全部明细含 CTO P1 时数字会更大

### 当日 ASN/SN 卡片口径（K1 日报 Tab）

- **范围**：OMS 原始 RPT_ASN_Status 报告，`SHIP_DATE = 当日`（VN 时区自然日，非 5am 窗口）的 ASN
- **计数单位**：ASN 个数（不是 pcs 件数），每个 ASN 计 1
- **总数** = N + S（当日出货 ASN 个数）
- **N / S**：按 SN_STATUS 分别计数——S、SN ACK → S；其余（含 NONE）→ N
- **ACK / NACK**：按 ASN_STATUS 分别计数（含 'ACK' / 含 'NACK'；两字段独立非互斥）
- 对应代码：daily.py `_compute_asn()`；卡片显示 N/S/ACK/NACK 四项
- 注意：raw ASN 数据只在公司侧 Engine 有，dev 重算缓存时 asn/sn 为空是正常的

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
