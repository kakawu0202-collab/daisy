---
name: 850-supply-chain-os
description: 850 Supply Chain OS 完整架构蓝图 — 五层系统：Data Engine + Business Engine + Service Layer + AI Engine + Portal（2026-08-01）
metadata: 
  node_type: memory
  type: project
  updated: 2026-08-01
  originSessionId: 59f737cb-72a3-47b9-a322-d27083bd9118
---

# 850 Supply Chain OS — 架构蓝图

## 定位

**Supply Chain Operating System**，不是 Dashboard，不是 AI 工具。

850AI 只是它的 AI 引擎层。

## 五层架构

```
┌─────────────────────────────────────────────────────────┐
│                   Portal（PWA + Mobile）                  │
│             人机交互 · 看板 · 工具 · 移动端                │
│                                                         │
│  页面：Home | Operations | Risk Center | Reports |       │
│        Tools | AI Assistant | System                    │
│                                                         │
│  设备：Desktop PWA | Mobile PWA | Tablet                │
├─────────────────────────────────────────────────────────┤
│                     AI Engine                            │
│          自然语言 · 分析 · 报告 · 邮件 · 预测              │
│                                                         │
│  能力：NL Query | Business Analysis | Report Gen         │
│        Email Gen | Anomaly Detection | Forecast         │
│                                                         │
│  约束：只能调用 Service Layer API                         │
│        不直接访问 Data Engine 或 Business Engine          │
├─────────────────────────────────────────────────────────┤
│                   Service Layer                          │
│         API 网关 · 工作流编排 · 通知 · 定时任务            │
│                                                         │
│  功能：REST API | Webhook | 飞书/企微通知                │
│        Cron调度 | 工作流引擎 | 权限控制                   │
│                                                         │
│  对接：Portal ← Service Layer → AI Engine                │
├────────────────────────┬────────────────────────────────┤
│    Business Engine      │       Data Engine              │
│  规则 · 计算 · 校验      │   采集 · 清洗 · 存储 · 发布     │
│                         │                               │
│  模块：                 │  模块：                        │
│  - KPI 计算引擎         │  - Collector（OMS/SAP/TRAX）   │
│  - 风险判定规则          │  - Processor（清洗/标准化）     │
│  - NACK 自动判定        │  - Storage（SQLite）           │
│  - ASN 校验            │  - Publisher（增量发布）         │
│  - ST 验证             │                               │
│  - 客户规则（Dell/HP/..）│                               │
│  - 项目规则（Daisy/NPI） │                               │
│                         │                               │
│  公司电脑（内网）         │  公司电脑（内网）               │
└────────────────────────┴────────────────────────────────┘
```

## 各层职责

### Layer 1: Data Engine
- **位置**：公司电脑（内网，可访问 OMS/SAP/TRAX）
- **职责**：数据采集、清洗、存储、发布
- **不做**：不包含任何业务规则、不对外提供 API
- **输出**：结构化 SQLite 数据 + 增量变更推送

### Layer 2: Business Engine
- **位置**：公司电脑（与 Data Engine 同机）
- **职责**：所有业务规则和计算
- **原则**：规则可配置，不硬编码
- **输入**：Data Engine 的 SQLite
- **输出**：KPI、风险标记、告警、校验结果

### Layer 3: Service Layer
- **位置**：Yumin 电脑（Windows Server，公网可达）
- **职责**：API 网关、工作流编排、通知、定时任务
- **原则**：Portal 和 AI 只通过 Service Layer 获取数据
- **对接**：接收 Data Engine 推送 → 存储 → 提供 REST API

### Layer 4: AI Engine
- **位置**：Yumin 电脑（或云端）
- **职责**：自然语言理解、智能分析、报告生成
- **约束**：只能调用 Service Layer API，不能直接读数据库
- **能力**：问答、分析、预测、邮件、报告

### Layer 5: Portal
- **位置**：Yumin 电脑（PWA 静态文件）
- **职责**：人机交互界面
- **原则**：零业务逻辑、纯展示和交互
- **页面**：Home / Operations / Risk / Reports / Tools / AI / System

## 数据流

```
OMS → Collector → SQLite → Processor → Business Engine
                              │              │
                              ▼              ▼
                         Structured    KPI / Risk
                          Records      / Alerts
                              │              │
                              ▼              ▼
                         Publisher ─── HTTPS POST ──→ Service Layer
                                                      │
                                          ┌───────────┼───────────┐
                                          ▼           ▼           ▼
                                      SQLite      REST API    Notifications
                                          │           │
                                          ▼           ▼
                                      Portal      AI Engine
```

## 开发阶段

### Phase 1 ✅ 已完成
- Data Engine 基础（collector / processor / storage / publisher）
- Portal 基础（PWA + K1 看板 + 首页）
- 数据推送链路（公司 → Yumin）

### Phase 2 — 当前
- Business Engine（KPI 引擎、风险规则、NACK 判定）
- Portal 功能型工具（ASN Checker / ST Validator / Excel Generator）
- 系统状态监控页

### Phase 3
- Service Layer 完善（工作流、通知、权限）
- AI Engine（自然语言查询、自动报告）
- 客户模块（Dell 定制规则）

### Phase 4
- 移动端 PWA 优化
- 知识库 + 企业微信/Teams 集成
- 多客户/多项目扩展

## 与旧架构的对应

| 旧 850AI 架构 | 新 SCOS 架构 |
|--------------|-------------|
| 850 Data Engine | Data Engine + Business Engine |
| 850 AI Portal | Service Layer + AI Engine + Portal |
| collector/ | Data Engine / Collector |
| processor/ | Business Engine（规则计算）+ Data Engine / Processor（清洗）|
| publisher/ | Data Engine / Publisher |
| receiver/ | Service Layer / Receiver |
| api/ | Service Layer / API |
| dashboard/ | Portal |

## 当前项目文件

```
d:\workspace\
├── 850-data-engine\          ← Data Engine（已构建）
│   ├── collector/
│   ├── processor/            ← 需要拆分：清洗归Data，规则归Business
│   ├── storage/
│   ├── publisher/
│   └── scheduler.py
│
├── 850-ai-portal\            ← Portal + Service Layer（已构建）
│   ├── receiver/
│   ├── api/
│   └── dashboard/
│
├── 850-toolbox\              ← 旧系统（过渡期保留）
│
└── 850-business-engine\      ← 【待构建】
    ├── kpi/
    ├── risk/
    ├── rules/
    └── validation/
```

## 关联记忆

- [[850ai-project-architecture]] — 旧架构方案（已被本文档替代）
- [[850-toolbox-pwa]] — 旧系统参考
- [[cto-p1-kpi-formula]] — CTO P1 28H KPI 公式
- [[fga870-allocation]] — 870 FGA 优先级分配
- [[ai-os]] — AI 个人操作系统（参考 AI Engine 设计）
