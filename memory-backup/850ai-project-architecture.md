---
name: 850ai-project-architecture
description: 850AI Project V1.0 完整架构设计 — Data Engine + AI Portal 双组件独立部署（2026-07-31）
metadata: 
  node_type: memory
  type: project
  updated: 2026-07-31
  originSessionId: 59f737cb-72a3-47b9-a322-d27083bd9118
---

# 850AI Project V1.0 — 架构设计

## 核心设计原则

1. **Data Engine 负责所有业务逻辑**，Portal 只做展示
2. **Dashboard 不包含任何业务计算**
3. **SQLite 是唯一可信数据源**
4. **推送预计算摘要**，Portal 不做二次计算
5. **AI 是数据的另一个消费者**，不直接访问 SAP/Excel

## 架构

```
公司电脑 (内网)                       Yumin 电脑 (外网 Windows Server)
─────────────────────                ─────────────────────────────
850 Data Engine                      850 AI Portal
├─ Collector (拉取 OMS/SAP/TRAX)     ├─ Receiver (接收推送)
├─ Processor (业务逻辑/计算)          ├─ SQLite (存储预计算结果)
├─ SQLite (唯一数据源)                ├─ REST API (数据服务层)
├─ Publisher (推预计算摘要)           ├─ Dashboard PWA (纯展示)
├─ Scheduler (编排调度)               ├─ AI Assistant (自然语言)
└─ main.py                            ├─ Customer Modules (插件化)
                                      └─ System (状态/日志)

Data Engine ──HTTPS POST──→ AI Portal
  (无 Tailscale)     公网      (Tailscale Funnel)
```

## 目录结构

```
d:\workspace\
├── 850-data-engine\          ← 公司电脑
│   ├── collector/            ← 数据拉取
│   ├── processor/            ← 业务计算
│   ├── storage/              ← SQLite + schema
│   ├── publisher/            ← 推送预计算摘要
│   ├── scheduler.py          ← 编排调度
│   └── main.py
│
└── 850-ai-portal\            ← Yumin 电脑
    ├── receiver/             ← 接收推送
    ├── api/                  ← REST API
    ├── dashboard/            ← PWA 静态文件
    ├── ai/                   ← AI Assistant (未来)
    └── main.py
```

## 数据库

新增表：
- `dashboard_cache` — 预计算摘要（Portal 直接读）
- `publish_log` — 发布日志（排查同步问题）

## 推送协议（升级）

POST /sync 推预计算结构化数据而非原始记录：
```json
{
  "seq": 42,
  "tables": {
    "k1_summary": {...},
    "daily_summary": {...},
    "orders_delta": [...],
    "alerts": [...]
  }
}
```

## Phase 1 实施顺序

1. 目录重构（创建两个独立项目）
2. Collector（从 server.py 抽离 OMS 拉取）
3. Processor（K1 摘要集中计算）
4. Storage（统一 schema + 新表）
5. Publisher（推预计算摘要 + 重试 + 日志）
6. Portal Receiver（接收预计算数据）
7. Portal API（REST API 层）
8. Portal Dashboard（PWA 迁移适配）
9. 端到端验证

## 关键约束

- **实施期间不修改 850-toolbox/**，旧系统保持可用
- Data Engine 和 AI Portal 是完全独立的两个项目
- DB 路径: `Daisy850-data/prd_data.db`（Engine）+ `Daisy850-data/yumin_data.db`（Portal）
- [[850-toolbox-pwa]] — 旧系统参考
- [[ai-os]] — AI 阶段参考
