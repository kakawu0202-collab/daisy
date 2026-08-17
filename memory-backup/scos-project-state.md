---
name: scos-project-state
description: SCOS 项目当前状态全记录 — 架构/页面/API/数据流/部署/已知问题（2026-08-18）
metadata: 
  node_type: memory
  type: project
  updated: 2026-08-18
  originSessionId: 59f737cb-72a3-47b9-a322-d27083bd9118
  modified: 2026-08-17T16:44:08.939Z
---

# 850 SCOS 项目状态（2026-08-18）

## 备份

`d:\workspace\850-scos-backup-20260818.zip` (2.3 MB) — 完整项目快照

## 项目结构

```
850-scos/                          ← 自包含，路径全相对
├── data/                          ← 所有数据库
│   ├── engine.db                  ← Data Engine SQLite
│   ├── portal.db                  ← Portal SQLite
│   └── users.db                   ← 用户账号
├── data-engine/                   ← 公司电脑
│   ├── collector/oms.py           ← OMS 拉取（5报告，双URL容错）
│   ├── processor/
│   │   ├── merge.py               ← 合并（PRD过滤+shipped_qty+asn_pending）
│   │   ├── k1.py                  ← K1摘要（per-record口径+ZC/CLOSE排除+类型拆分GPP）
│   │   ├── daily.py               ← 日报（by_type_region矩阵+趋势类型/货代/运输方式拆分）
│   │   ├── risk.py                ← 风险引擎（R1-R6规则）
│   │   ├── kpi.py                 ← CTO P1 28H周KPI
│   │   ├── e2e_kpi.py             ← E2E KPI引擎（7 KPI+PASS/FAIL/OPEN+Dell日历+clean/48H）
│   │   └── kpi_config.json        ← KPI中心化配置
│   ├── storage/db.py              ← SQLite（push_state表+增量查询）
│   ├── publisher/push.py          ← 增量推送+分块2000+确认机制
│   ├── scheduler.py               ← 编排器
│   ├── main.py                    ← 入口（daemon+8700触发端点+断网恢复）
│   ├── control.py                 ← 监控台（8900端口，监控优先）
│   ├── control-panel.vbs          ← 双击启动监控台（无黑框）
│   ├── run-push.vbs               ← 双击手动推送
│   └── start-silent.vbs           ← 静默启动Engine
├── portal/                        ← Yumin电脑
│   ├── receiver/sync.py           ← 接收（幂等upsert+cache存储）
│   ├── api/server.py              ← HTTP服务（认证+缓存读取+订单查询+admin）
│   ├── dashboard/                 ← PWA前端
│   │   ├── index.html             ← 首页（Quick Links）
│   │   ├── k1.html                ← K1看板（PRD+Daily双Tab+下钻+趋势）
│   │   ├── e2e-kpi.html           ← E2E KPI页
│   │   ├── cto-kpi.html           ← CTO P1 KPI页
│   │   ├── cto-analysis.html      ← CTO站别分析
│   │   ├── report-builder.html    ← 查询构建器（最新）
│   │   ├── status.html            ← 系统状态
│   │   ├── login.html / admin.html
│   │   ├── sw.js                  ← 直通模式SW（无缓存）
│   │   └── 风格demo: scos-demo/uiux-demo/style-cinema/style-glass-brutal/style-spatial-liquid/style-studio/k1-demo
│   └── main.py                    ← Portal入口
├── start-all-silent.vbs           ← 双击启动双服务
├── test-pipeline.bat              ← 端到端测试
├── _recalc_cache.py               ← 缓存重算（双DB）
├── setup-startup.ps1              ← 开机自启安装
├── deploy-company.md              ← 公司部署指南
└── README.md                      ← 项目文档
```

## 架构与数据流

```
公司电脑 (Engine)                     Yumin电脑 (Portal)
OMS → Collector → Processor → SQLite → 增量推送(分块+确认) → 公网 → Receiver → SQLite → API → PWA
```

**增量推送完整性**：
- 只推 updated_at > last_confirmed_push 的记录
- Yumin 确认后推进标记；失败下轮重试
- 分块 2000 条/块，3 次重试，幂等 upsert
- 首次/长期断连自动全量

## 核心数据口径（重要！）

- **PRD 过滤**：MASTER_TYPE='PRD'（语义层定义）
- **shipped_qty**：ASN QTY 按 SHIP_QTY 比例分配到 PO，per-record 口径
- **unshipped** = po_qty - shipped_qty，per-record（类型卡片与总计必然一致）
- **GPP 生产状态**：排除 ZC + CLOSE已全部出货（残留数据）
- **CTO P1**：SUB_TYPE='CTO' AND PRIORITY='1'
- **Clean**：无 Hold 历史（UNCLEAN_HOLDS 代码表）
- **Dell 日历**：WK01=2026-01-31，周六-周五
- **28H**：PO_RECEIVE + 28H；Clean 28H / Non-Clean 48H
- **MSBD 达成**：SN_CDT ≤ MSBD

## API 端点

| 端点 | 说明 |
|------|------|
| POST /sync | 接收推送（records+7种摘要） |
| GET /api/health | 健康+同步状态 |
| GET /api/cache/{key} | 缓存读取（k1_summary/daily_summary/risks/kpi/e2e_kpi） |
| GET /api/k1-summary, /api/daily-summary | 兼容别名 |
| GET /api/orders | 订单查询（region/sub_type/ack/ship_mode/scac/mcid/cto_p1/priority/is_hold/shipped/msbd/sn/po_received/gpp/cto_28h/limit） |
| POST /api/login, /api/register | 认证 |
| POST /api/admin-login, /api/admin-action | 管理（密码admin850，可SCOS_ADMIN_PW覆盖） |

## 部署

- 公司电脑：`D:\Kaka\2.系统\CC\850-scos`（双击 control-panel.vbs + start-all-silent.vbs）
- Yumin电脑：`d:\workspace\850-scos`（双击 start-all-silent.vbs + Tailscale Funnel 5050）
- 公网：https://yumin.taila2a2ad.ts.net
- OMS密码：OMS_PASSWORD 环境变量（User级）

## 已知问题/坑

1. **setdefault 陷阱**（Python）：`d.setdefault(k,{})[x] = d[k].get(...)` 右侧先求值会 KeyError——必须两行写
2. **JS 函数名**：k1.html 用 fmt()，其他页用 F()——新代码别混
3. **Service Worker**：已改直通模式（scos-pass-through），无缓存
4. **Portal 重启**：taskkill python.exe 后必须重新启动（无自愈）
5. **多进程端口冲突**：曾出现 3 个进程挤 5050，重启前先 netstat 检查
6. **OMS 超时**：公司网络推送大包会超时，已改分块 2000
7. **RTL 无 GPP 数据**：RTL 不走产线（直发零售），生产状态全 0 是正常

## 关联记忆

- [[850-supply-chain-os]] — 五层架构蓝图
- [[850-business-rules]] — 业务规则
- [[850-data-dictionary]] — 数据字典
- [[850-toolbox-pwa]] — 旧系统参考
