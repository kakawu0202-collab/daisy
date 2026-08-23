# 850 SCOS — DEV 环境（d:\workspace\850-scos-dev）

> 开发环境，与线上 `850-scos`（v1.0.0）完全隔离。

## 端口对照

| 服务 | 线上 | DEV |
|------|------|-----|
| Portal | 5050 | **5051** |
| Engine trigger | 8700 | **8701** |
| Control panel | 8900 | **8901** |
| Engine 推送目标 | yumin.taila2a2ad.ts.net/sync | localhost:5051/sync（本机闭环） |

端口通过环境变量覆盖：`SCOS_PORTAL_PORT` / `SCOS_ENGINE_PORT` / `SCOS_CONTROL_PORT` / `YUMIN_URL`。
线上代码保持硬编码默认值不变（不受影响）。

## 启动

- `start-dev.bat` — DEV Portal（5051，控制台模式）
- `start-dev-silent.vbs` — DEV Engine(8701) + Portal(5051) 静默双服务
- `start-engine-dev.bat` — DEV Engine（控制台，推送到本机 5051）

## 数据

- `data/` 为线上 2026-08-18 快照副本（engine.db / portal.db / users.db），改坏不影响线上
- 本目录代码改动不触碰线上 `850-scos` 与公司电脑部署

## v1.2-dev（2026-08-23）— Phase 2 Service Layer 标准化（在 v1.1-dev 之上）

- 新增标准端点：`/api/k1` `/api/daily` `/api/kpi` `/api/e2e` `/api/risk` `/api/risk-summary` `/api/nack`
- 所有摘要端点支持 `?meta=1` → `{key, computed_at, data}`（数据溯源，为 AI Engine 备）
- `/api/nack`：复用订单查询固定 ack_status=REJECT（零业务逻辑）
- 旧端点（/api/cache/*、/api/k1-summary、/api/sort-data 等）全部保留，逐字节一致（_test_endpoints.py 全绿）
- 审计发现（待后续阶段修）：cto-analysis.html 在 JS 里重算 CTO P1 段耗时规则（与 Business Engine risk R6 重复），应改为调 /api/cto-analysis
- ⏳ 未上线——随 v1.1-dev 一起等待确认

## v1.1-dev（2026-08-19）— M1 拆层完成，待验证后上线

- Business Engine（Layer 2）独立：`business-engine/`（engine.py + config/ + kpi/ + rules/ + summary/）
- Data Engine 只留采集/清洗（merge）/存储/发布；scheduler 变为纯编排
- 算法零改动（文件原样搬迁，仅 e2e_kpi CONFIG_PATH 随目录调整）
- 回归验证：old vs new 同输入逐值对比 **100% 一致**（regression/baseline.json 存档）
- 安全修复：_test_pipeline.py 改 dev 端口 5051 + 按 PID 杀进程（原脚本会误杀线上 5050）
- ⏳ 未上线——等待人工确认后合并 850-scos 并升级 v1.1

## 开发路线

1. ✅ 拆层：Business Engine 从 data-engine/processor 独立（M1，本版本）
2. ⏭️ Phase 2：Service Layer 标准化（/api/k1 /api/e2e /api/risk /api/nack）
3. ⏭️ Phase 3-4：ASN Checker / ST Validator / Excel Generator
4. ⏭️ Phase 5：Config Rule Engine（规则配置化）
5. ⏭️ Phase 6-7：AI Engine + AI Assistant
