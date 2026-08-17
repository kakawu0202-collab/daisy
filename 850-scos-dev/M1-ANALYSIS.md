# SCOS M1 拆层分析报告（2026-08-18）

> 原则：先搬后拆、行为不变、结构改变。本报告确认前不动代码。

---

## A. Current Architecture（当前实际架构）

```
公司电脑（data-engine/）                          Yumin（portal/）
─────────────────────                            ─────────────────
OMS（5 报告：po/e2e/gpp/asn/ship）
  ↓ collector/oms.py            登录+拉取（双URL容错，oms_creds.json）
  ↓ processor/merge.py          PRD过滤 + 字段标准化 + 派生字段
  │                             （含业务规则：status_label 推导、cto_p1 标记、
  │                              shipped_qty ASN比例分配、asn_pending、GPP/E2E fallback）
  ↓ processor/k1.py             K1 摘要（类型/区域矩阵、MSBD plan、CTO 28H timeline）
  ↓ processor/daily.py          日报（5am窗口、30日趋势、ASN/SN、fwd_dist）
  ↓ processor/risk.py           R1-R6 风险规则（28H/12H/13H/6H 硬编码）
  ↓ processor/kpi.py            CTO P1 28H KPI（28H 硬编码）
  ↓ processor/e2e_kpi.py        E2E 7 KPI（读 kpi_config.json + UNCLEAN_HOLDS 硬编码 + Dell日历）
  ↓ storage/db.py               engine.db：orders(40列) + cache + sync_log + push_state
  ↓ publisher/push.py           增量推送（分块2000 + 确认机制）→ HTTPS POST
  ↑ scheduler.py run()          编排以上全部（collect→process→store→publish）
  ↑ main.py(--daemon, :8700) / control.py(监控台, :8900)

                                    ↓ POST /sync（records + 6 种摘要）
                              receiver/sync.py       幂等 upsert + cache 存储（零业务逻辑）
                              api/server.py          :5050 静态 + 认证 + /api/cache/* + /api/orders
                              dashboard/*.html       PWA 看板（纯 fetch + display）
```

### 业务逻辑分布现状

| 文件 | 内容 | M1 归属 |
|------|------|---------|
| collector/oms.py | 采集 | Data Engine（不动） |
| processor/merge.py | 清洗+标准化（混有 status_label/cto_p1 业务判定） | Data Engine（M1 保留，见 F6） |
| processor/k1.py | K1 摘要 | → Business Engine |
| processor/daily.py | 日报摘要 | → Business Engine |
| processor/risk.py | R1-R6 风险 | → Business Engine |
| processor/kpi.py | CTO P1 28H KPI | → Business Engine |
| processor/e2e_kpi.py | E2E KPI（半配置化） | → Business Engine |
| processor/kpi_config.json | KPI 配置 | → Business Engine config/ |
| storage/db.py | SQLite | Data Engine（不动） |
| publisher/push.py | 增量发布 | Data Engine（不动） |
| scheduler.py | 编排（直接 import 业务模块） | 修改：只 orchestrate |
| portal/receiver + api | 接收 + API | Service Layer（已零业务逻辑，不动） |
| dashboard/*.html | 展示 | Portal（不动） |

### 关键事实

1. **引用点只有 2 处**：`scheduler.py` 和 `_recalc_cache.py` import 业务模块（已 grep 全项目确认）——迁移面很小。
2. `kpi_config.json` 已存在且被 e2e_kpi.py 使用（`__file__` 相对路径定位，移动后自动正确）；但 risk.py/kpi.py 的阈值仍硬编码——**M1 不配置化**（属 Phase 5）。
3. 业务结果经 cache 表（k1_summary/daily_summary/risks/kpi/e2e_kpi）推送 → Portal 端对拆层**完全无感知**。
4. NACK 目前只有统计（k1/daily 计数），无自动判定规则——按指令 M1 不加功能，NACK 判定属后续阶段。

---

## B. Proposed Architecture（M1 后）

```
data-engine/                        ← Layer 1（职责不变）
  collector/oms.py                  ← 不动
  processor/merge.py                ← 保留（清洗+标准化）
  storage/db.py                     ← 不动
  publisher/push.py                 ← 不动
  scheduler.py                      ← 修改：纯编排（见下）
  main.py / control.py              ← 不动

business-engine/                    ← Layer 2（新建）
  config/kpi_config.json            ← 移入
  kpi/kpi.py                        ← CTO P1 28H
  kpi/e2e_kpi.py                    ← E2E
  rules/risk.py                     ← R1-R6
  summary/k1.py                     ← K1 摘要
  summary/daily.py                  ← 日报
  engine.py                         ← 新建：run(records, raw_ship, raw_asn, raw_e2e)
                                       → {k1, daily, risks, kpi, e2e_kpi}

portal/                             ← Layer 3+5（零改动）
  receiver/sync.py · api/server.py · dashboard/  全部不动
```

### 调度流（M1 后）

```python
# scheduler.py run():
collect → merge → business_engine.engine.run(records, raws) → upsert + put_cache → push
```

Result Layer 物理实现 = 现有 cache 表（**不新建表**，避免改动存储结构和 Portal 端读取）。

---

## C. Files to Move（6 个，git mv 保历史）

| 源 | 目标 |
|----|------|
| data-engine/processor/k1.py | business-engine/summary/k1.py |
| data-engine/processor/daily.py | business-engine/summary/daily.py |
| data-engine/processor/risk.py | business-engine/rules/risk.py |
| data-engine/processor/kpi.py | business-engine/kpi/kpi.py |
| data-engine/processor/e2e_kpi.py | business-engine/kpi/e2e_kpi.py |
| data-engine/processor/kpi_config.json | business-engine/config/kpi_config.json |

**不移动**：merge.py（清洗，留 Data Engine）。移动的 5 个模块除 e2e_kpi 外无文件路径依赖；e2e_kpi 的 CONFIG_PATH 用 `__file__` 相对定位，移动后自动指向 business-engine/config/。

---

## D. Files to Modify（3 个）

1. **data-engine/scheduler.py** — import 路径改为 business-engine；run() 改为先 merge 后调 engine.run()
2. **_recalc_cache.py** — import 路径同步改（缓存重算工具）
3. **_test_pipeline.py** — ⚠️ 安全修复：端口 5050 → 5051；步骤 0 的 taskkill 改为只杀 dev 测试进程 PID（原逻辑会杀线上 Portal！）

---

## E. Files to Create（3 个）

1. **business-engine/engine.py** — 薄编排：接收 records + raw 报告 → 调 5 个 compute → 返回结果 dict。无算法逻辑。
2. **regression_test.py** — 回归验证（见 G）
3. 本报告 M1-ANALYSIS.md（已建）

---

## F. Risk Points（风险点）

1. **🔴 _test_pipeline.py 会 taskkill 5050 端口进程 = 杀线上 Portal**。dev 必须改 5051 且按 PID 精确杀（D3 已列）。push.py 的 5050 硬编码已在建环境时修复。
2. **import 路径**：business-engine/ 与 data-engine/ 平级，需在 scheduler.py/_recalc_cache.py 里把 business-engine 加入 sys.path（或从项目根 import）。回归测试会立刻暴露问题。
3. **e2e_kpi CONFIG_PATH**：靠 `__file__` 定位，移动后自动正确，但回归必须验证。
4. **daily.py 依赖 raw ship/asn**（今日出货、ASN 统计、fwd_dist、progress）：engine.py 接口必须传 raw 数据，否则日报字段空。
5. **时间敏感字段**：k1/daily/kpi 含"今天/本周"逻辑（5am 窗口、week_start）。baseline 与 new 必须在同一次会话内先后跑（间隔 <1 分钟），diff 时对 `date`/`computed_at` 类字段 normalize。
6. **merge.py 内嵌业务规则**（status_label 推导、cto_p1 标记）：M1 留在 Data Engine 不动。理由：status_label 是 orders 表存储字段，拆出去意味着存储时序两段化，违背"行为不变"。列入 Phase 5 配置化清单。
7. **dev 机 OMS 可达性**：regression_test.py 用 DB 快照数据作输入（不依赖 OMS 登录）；test-pipeline.bat 需 OMS 网络，仅在网络可达时跑（公司机/aTrust）。
8. **进程残留**：多进程抢端口的历史坑（记忆已录）。dev 测试脚本结束必须按 PID 清理。

---

## G. Regression Test Plan（回归验证方案）

### 验收标准：业务结果 100% 一致，任何差异 → STOP → 分析 → 修复 → 重测。

**G1. 函数级回归（主门槛，离线可跑）**
1. 输入：dev engine.db 现有 7344 条 orders 记录（字段与 merge 输出同构）+ 空 raw 报告
2. Baseline：旧代码（data-engine/processor/*）跑 5 个 compute → `regression/baseline.json` 存档
3. New：新代码（business-engine/*）跑同样输入 → new.json
4. 深对比：类型一致 + 逐 key 逐值比较；normalize 规则：时间戳字段（date/computed_at/本周窗口）容忍同次会话内差异
5. e2e_kpi 输入用 orders 表重建的 e2e-like 记录（缺 PO_STATUS 字段，但新旧代码同输入，一致性判定不受影响）

**G2. 结构快照对照（辅助）**
- dev portal.db cache 里现有 6 份摘要（08-17 08:00 线上最新值）作为 golden 结构快照，验证新代码输出 key 集合与之一致

**G3. 端到端（网络可达时）**
- test-pipeline.bat（已改 dev 端口）：collect → merge → business → store → push → dev portal 5051 闭环

**G4. 人工抽查**
- dev 5051 的 K1 / 风险 / KPI 页面与线上 5050 同页面对照（同源数据快照，应一致）

### 回滚

- git 提交 M1-start 基线，任一环节失败 → `git reset` 回基线，线上全程不受影响。

---

## H. M1 Implementation Steps（实施步骤）

1. 提交 dev 当前状态为 M1-start 基线 commit
2. 安全修复：_test_pipeline.py 端口改 5051 + 按 PID 杀进程（先行，防误杀）
3. 写 regression_test.py，跑旧代码生成 baseline.json 并存档
4. 建 business-engine/ 目录结构（config/kpi/rules/summary）+ engine.py
5. git mv 6 个文件到 business-engine/
6. 改 scheduler.py + _recalc_cache.py 的 import 与编排
7. 跑回归：new vs baseline → diff 必须为空
8. 跑 G2 结构对照 + G4 人工抽查（5051 vs 5050）
9. （网络可达时）跑 G3 端到端
10. 提交 M1 结果，dev 版本 v1.1-dev 候选；**线上合并与重启由你决策**（需短暂重启线上 Portal）

### 明确不做（M1 范围外）

- 不改任何算法/阈值/字段
- 不新建 Result Layer 表（继续用 cache）
- 不做配置化（Phase 5）、不做 ASN/ST/Excel 工具（Phase 3-4）、不做 AI（Phase 6）
- 不动 portal/ 任何文件、不动 dashboard UI
