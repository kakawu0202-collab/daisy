---
name: 850-data-dictionary
description: 850 PO 数据字典 — 结合语义层Excel + 代码实践，按业务域整理的完整字段参考（2026-08-02）
metadata: 
  node_type: memory
  type: reference
  updated: 2026-08-02
  originSessionId: 59f737cb-72a3-47b9-a322-d27083bd9118
---

# 850 PO 数据字典

> 来源：语义层.xlsx（手工整理） + server.py/merge_orders.py 代码实践

---

## 〇、客户标识

| 字段 | 类型 | 说明 | 来源 |
|------|------|------|------|
| CUST | 文本 | 客户代码，区分 Oldco / Newco | API参数 |
| CORP | 文本 | 公司代码，Shipment API 必传 `3100` | API参数 |

### CUST 取值

| 值 | 含义 |
|----|------|
| DAISY | Dell Newco（新城），当前系统对接的客户 |
| （其他） | Oldco（旧城）历史客户代码 |

### 业务背景

Dell 拆分为 Oldco（旧公司）和 Newco（新公司，代号 Daisy）。当前系统（850 Toolbox / SCOS）只处理 **DAISY（Newco）** 的数据。

- `server.py` OMS 请求中 `CUST=DAISY`
- `oms_pull.ps1` Shipment API 中 `CUST=DAISY, CORP=3100`
- 分析指标（K1/CTO P1）仅针对 PRD 且 CUST=DAISY 的订单

---

## 一、订单标识

| 字段 | 类型 | 说明 | 来源 |
|------|------|------|------|
| PO | 文本 | 订单号，主键之一 | E2E Report |
| PO_LINE | 文本 | 订单行号，与PO组成联合主键 | E2E Report |
| DELL_SO | 文本 | Dell Sales Order 编号 | E2E Report |
| DPN | 文本 | Dell Part Number，Dell料号 | E2E Report |
| IPN | 文本 | Internal Part Number，内部料号 | E2E Report |
| MCID | 文本 | 制造节点/工厂代码 | E2E Report |

---

## 二、订单分类

### MASTER_TYPE（主类型）

| 值 | 含义 | 是否做指标统计 |
|----|------|-------------|
| PRD | 正式订单（Production） | ✅ 是 |
| PLB | Build, no ship（只做不运） | ❌ 否 |
| PLP | No build, no ship（都不做） | ❌ 否 |
| PLS | Build, ship | ❌ 否 |

### SUB_TYPE（子类型/订单类型）

| 值 | 含义 | Partial出货 |
|----|------|------------|
| CTO | 客制化订单（Config to Order） | ❌ 不可 |
| FGA | 成品订单，通常出到HUB囤货 | ✅ 可 |
| RTL | Retail，大型公司/超市合作方下单 | ❌ 不可 |
| CFS | 2nd touch，可归到CTO | ❌ |

### PRIORITY（优先级）

- 850 PO 自带，1/2/3/4 等级
- **CTO + Priority=1 → CTO P1**（28H 时效管控）

### REGION（区域）

| 值 | 说明 |
|----|------|
| DAO | 亚太（含中国） |
| APJ | 亚太其他 |
| EMEA | 欧洲/中东/非洲 |

---

## 三、物流字段

### SHIP_MODE（运输方式）

| 方式 | Oldco代码 | ODW代码 |
|------|----------|--------|
| 陆运 | G | GD |
| 空运 | A / SA / PA | AR / SA / PA |
| 海运 | S / CS / OR / CR / P | ON / CO / OR / CR / FB |

### SCAC（货代代码）

- 承运人代码，如 KNTT（Kuehne+Nagel）/ DNZA（DHL）
- 用于区分不同的物流供应商

### SHIP_TO_COUNTRY（目的国）

- 订单发往的国家

---

## 四、日期字段

| 字段 | 含义 | 用途 |
|------|------|------|
| PO_RECEIVE_DATE | 订单接收时间 | CTO P1 28H 计时起点 |
| MSBD | Must Ship By Date，最晚离厂时间 | 出货计划基准 |
| PSD | Planned Ship Date，计划出货日 | 出货排程 |
| FINAL_MSBD | 最终MSBD | 变更后的最终截止日 |

### 脏日期（代码中过滤）

```
0001-01-01, 1900-01-01 及其变体 → 视为无日期
```

---

## 五、数量字段

| 字段 | 含义 |
|------|------|
| PO_QTY | 订单总数量 |
| REMAIN_QTY | 剩余未出数量 |
| SHIP_QTY | 出货数量（PO级别） |

---

## 六、状态字段

### STATUS（订单状态）

| 值 | 代码中的标签 |
|----|------------|
| Open | OPEN（无SN日期显示为 "Backlog"） |
| Close | CLOSE（正常关闭） |
| ZC | ZC（已取消） |
| E | V（校验中未通过） |

### ACK_STATUS（确认状态）

| 值 | 标签 |
|----|------|
| REJECT | NACK（被拒绝） |
| 其他 | 正常 |

### IS_HOLD / HOLD_CODE（Hold状态）

| CODE | 说明 | 责任部门 |
|------|------|---------|
| A01 | Engineering Hold Build | Quality |
| A02 | 流程不合规/质量审核失败 | Quality |
| A03 | Engineering Hold Ship | Quality |
| A05 | 质量问题验证中 | Quality |
| A06 | 物料质量问题 | SQE |
| A07 | 质量要求返工 | Quality |
| A09 | 维修中 | Repair |
| A11 | 缺料（套料/包材短缺） | MC |

---

## 七、E2E 站别（生产流水线）

> 来源：E2E Report。描述一条订单从收单到出货经过的站点。

### 五个阶段

```
STBL → ATB → WIP → FG → SN
待料    备料   产线   成品   出货
```

| 阶段 | 含义 | 判定条件 |
|------|------|---------|
| **STBL**（待料） | 物料未齐，未上线 | 无任何站别日期 |
| **ATB**（备料完成） | 物料齐套，待上线 | 有 AFT_CDT 但无 INPUT_CDT |
| **WIP**（产线中） | 已上线生产 | 有 INPUT_CDT 但无 STOCKIN_CDT |
| **FG**（成品入库） | 已完成，待出货 | 有 STOCKIN_CDT 但无 SN_CDT |
| **SN**（已出货） | SN 已完成 | 有 SN_CDT |

### E2E 关键日期字段

| 字段 | 含义 |
|------|------|
| INPUT_CDT | 上线时间 |
| AFT_CDT | 物料齐套确认时间 |
| STOCKIN_CDT | 成品入库时间 |
| SN_CDT | SN完成/出货时间 |
| CREATEASN_CDT | ASN创建时间 |

---

## 八、出货判定（ASN + Shipment）

### 出货逻辑（代码实现）

```
1. ASN Report: SN_STATUS = 'S' 或 'SN ACK' → ASN已出货
2. Shipment Report: PO → ASN 关联
3. PRD PO 中，关联到已出货ASN的 → actual_shipped = True
```

### ASN 状态

| SN_STATUS | 含义 |
|-----------|------|
| S | 已出货 |
| SN ACK | SN已确认 |
| NONE | ASN待S，留在Backlog |

### ASN_STATUS

| 值 | 含义 |
|----|------|
| ACK | 已确认 |
| NACK | 被拒绝 |

### shipped_qty（新增字段）

- ASN.QTY 按 SHIP_QTY 比例分配到各 PO
- 支持 Partial 出货场景
- capped at PO_QTY（不超过订单总量）

---

## 九、CTO P1 28H KPI

### 公式

```
总用时 = SN_CDT - PO_RECEIVE_DATE
达标 = 总用时 ≤ 28 小时
```

### 三段分解

| 段 | 计时 | 目标 |
|----|------|------|
| Planning | PO_RECEIVE_DATE → INPUT_CDT | ≤ 11H |
| Build | INPUT_CDT → STOCKIN_CDT | ≤ 12H |
| Shuttle | STOCKIN_CDT → SN_CDT | ≤ 5H |

---

## 十、数据源（5个核心Report）

| Report ID | 名称 | 提供内容 |
|-----------|------|---------|
| 0848012288 | RPT_850_PO | 订单主数据 |
| 1593920512 | RPT_E2E | 站别/生产状态 |
| 0320073728 | RPT_GPP | 生产状态汇总 |
| 0886717440 | RPT_ASN_Status | ASN/SN状态 |
| 1780017152 | RPT_Shipment_Rpt | 出货明细 |

---

## 十一、编码规则总结

### CTO_P1 判定
```
SUB_TYPE = 'CTO' AND PRIORITY = '1' → CTO_P1 = 'Y'
```

### STATUS_LABEL 判定
```
ACK_STATUS = 'REJECT' → 'NACK（被拒绝）'
STATUS = 'ZC'        → 'ZC（已取消）'
STATUS = 'Close'      → 'CLOSE（正常关闭）'
STATUS = 'Open', 无SN  → 'OPEN（Backlog）'
STATUS = 'E'          → 'V（校验中未pass）'
```

### actual_shipped 判定
```
PO 关联的 Shipment.ASN 的 SN_STATUS IN ('S', 'SN ACK') → 1
否则 → 0
```

### shipped_qty 判定
```
ASN.QTY × (PO.SHIP_QTY / SUM(同ASN下所有PO的SHIP_QTY))
取整 → 分配到该PO的出货量
cap at PO_QTY
```

---

## 关联记忆

- [[850-supply-chain-os]] — SCOS 五层架构蓝图
- [[850-toolbox-pwa]] — 旧系统参考
- [[cto-p1-kpi-formula]] — CTO P1 28H KPI 公式
- [[oms-workflow-v2]] — OMS 数据拉取工作流
