---
name: scos-project-state
description: SCOS 项目当前状态全记录 — 架构/页面/API/数据流/部署/已知问题（2026-08-18）
metadata: 
  node_type: memory
  type: project
  updated: 2026-08-18
  originSessionId: 59f737cb-72a3-47b9-a322-d27083bd9118
  modified: 2026-09-06T15:42:20.925Z
---

# 850 SCOS 项目状态（2026-08-18）

## 版本与环境（2026-08-18 起）

- **线上 = `d:\workspace\850-scos`（v1.0.2 🔒 锁定，代码内版本号 scos-1.0.2，2026-09-02）**
- **开发 = `d:\workspace\850-scos-dev` — 所有新功能在这里做（当前 v1.3-dev 攒着拆层/ServiceLayer/ASN Checker 未上线）**
- **🔒 上线铁律（用户 2026-08-30 定）：任何线上改动必须经用户逐次明确批准，不得擅自上线**
- 端口隔离：线上 5050/8700/8900 vs dev 5051/8701/8901（env: SCOS_PORTAL_PORT/SCOS_ENGINE_PORT/SCOS_CONTROL_PORT/YUMIN_URL）
- dev Engine 推送目标 = http://localhost:5051/sync（本机闭环，绝不推线上）
- dev 数据 = 线上 2026-08-18 快照副本（data/*.db），改坏可重拷
- dev 启动：start-dev.bat（Portal 控制台）/ start-dev-silent.vbs（双服务静默）/ start-engine-dev.bat（Engine）
- **禁忌：dev 机上严禁 taskkill python.exe 全局杀进程（会杀线上 Portal）**
- 版本规则：dev 验证通过后增量合并回线上并升级版本号（VERSION.md）
- v1.0.1 上线内容：K1 日报 🚨 已入库未开ASN 卡片（Yumin 侧实时算 portal/rules/cto_asn.py）+ MSBD 口径标注 + ASN NACK + CUST 列
- v1.0.2 上线内容（2026-09-02）：卡片排除 ZC 已取消 + ⬇ CSV 下载按钮
- **公司电脑待同步（用户手动）**：merge.py + storage/db.py（加 cust）→ `D:\Kaka\2.系统\CC\850-scos`，重启 Engine 后 CUST 才有值

## 开发路线（严格串行：拆层 → Service Layer → Tools → Config → AI）

- ✅ **M1 拆层（2026-08-19，v1.1-dev，⏳ 未上线）**：
  - business-engine/ 独立（engine.py + config/kpi_config.json + kpi/{kpi,e2e_kpi}.py + rules/risk.py + summary/{k1,daily}.py）
  - data-engine/processor 只剩 merge.py；scheduler 纯编排；git tag M1-start 可回滚
  - 已知 v1.0 既有现象（非 M1 引入）：K1 shipped+unshipped 与 total 差 3（超发截断）；本周无 CTO P1 出货时 KPI weekly 缺本周桶
- ✅ **Phase 2 Service Layer（2026-08-23，v1.2-dev，⏳ 未上线）**：
  - 标准端点 /api/k1 /api/daily /api/kpi /api/e2e /api/risk /api/risk-summary /api/nack；?meta=1 数据溯源
  - 审计发现：cto-analysis.html JS 重算 CTO P1 段耗时（与 risk R6 重复）→ 后续改为服务端 /api/cto-analysis
- ✅ **Phase 3 ASN Checker（2026-08-23，v1.3-dev，⏳ 未上线）**：
  - business-engine/rules/asn.py：NACK>HOLD>PASS/PARTIAL/PENDING/OPEN 校验；engine.run 新增 asn_check（加法式）
  - /api/asn?asn=X；tools.html（ASN Tab 可用）；index 加 Tools 入口
  - **回归方法升级**：regression_test.py 新增 check-live 模式——从 git M1-start 提取旧代码同日对比（baseline.json 跨天会时间漂移，勿用跨天 check）
- ✅ **Phase 4（2026-09-03，v1.4-dev，⏳ 未上线）**：
  - ST Validator = SHIP_STATUS 出货状态校验（用户拍板口径）：rules/st.py 按 PO/ASN → NACK>ERROR>WARN>PARTIAL>OPEN>PASS；/api/st；tools.html ST Tab
  - Excel Generator：/api/export/orders（openpyxl XLSX）；过滤抽取 _build_orders_sql 与 /api/orders 同源；新增 msbd_from/msbd_to
  - ship_status 字段贯通（同 cust 模式，公司侧同步后才有原始值）；修 asn='None' 假 ASN 坑
  - **dev 数据已刷成线上最新快照（8711 条）**；注意：_recalc_cache.py 读 dev engine.db 会覆盖 portal 缓存，刷新后别跑 recalc，用 portal.db 源重算 dev 专属缓存
- ⏭️ Phase 5：Config Rule Engine（risk 阈值/kpi 28H/UNCLEAN_HOLDS 配置化；merge 的 status_label/cto_p1 也在此阶段）
- ✅ **Phase 6 AI Engine v0（2026-09-06，v1.6-dev，⏳ 未上线）**：
  - ai-engine/{config,llm,tools,agent,ask}.py——NL → function calling → Service Layer（10 工具）→ 中文答案 + computed_at 溯源
  - 防编造加固：未调工具的回答拦截 + 首轮强制重查 + --debug 追踪；明细工具默认 limit=50
  - **LLM 凭据：用户已配置智谱 GLM-4-Flash（免费）**，在 ai-engine/.env（AI_API_KEY/AI_BASE_URL=https://open.bigmodel.cn/api/paas/v4/AI_MODEL=glm-4-flash）；.env 已 gitignore，勿提交勿打印
  - **安全拦截**：Claude 代跑 ask.py 会被 exfiltration 策略拦截（订单数据→外部 LLM）——用户自己在终端跑（路线 A）或加可信域名权限（路线 B）
  - 实测跑通：get_daily_summary 工具调用正常；注意 daily 缓存 nack_count 与实时 /api/nack 可能差少量（快照时差）
- ✅ **Phase 7 AI Assistant Portal（2026-09-06，v1.7-dev，⏳ 未上线）**：
  - ai-engine/web.py（localhost:5099 聊天页 + /api/ask）+ start-ai.bat + 首页 Quick Links 入口
  - **安全边界（重要）**：AI 自改权限被 HARD 拦截（不允许自开数据外发通道）；路线 B 需用户亲手在 settings.local.json 的 allow 数组加 `PowerShell(cd d:\workspace\850-scos-dev\ai-engine; python ask.py *)` 等规则
  - 用户浏览器直问（5099）不受任何拦截——推荐主用方式
  - 蓝图 Phase 0-7 全部完成（测试版）；线上仍 v1.0.2 锁定，全量上线待用户点头
- 上线方式（待确认）：把 dev 的 business-engine/ + 改动文件复制回 850-scos，重启线上 Portal，VERSION.md 升版本，打标签；**每次上线需用户逐次点头**

## 备份

- `d:\workspace\850-scos-backup-20260818.zip` (2.3 MB) — 完整项目快照（含 data/ 数据库）
- GitHub `kakawu0202-collab/daisy` main 分支 — 源码快照（commit `9c93d1d`，2026-08-18）+ `memory-backup/` 记忆全量备份
- 同步方式：改动后运行 `git add 850-scos-dev memory-backup; git commit; git push`（node_modules/data 已被 .gitignore 排除）

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
