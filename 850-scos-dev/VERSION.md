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

## v1.5-dev（2026-09-04）— Phase 5 Config Rule Engine（P5-1~4，在 v1.4-dev 之上）

- 新增 `business-engine/config/rules.json`：risk 阈值（28H/2天/1H/各段 target+over_warn）、
  KPI（28H SLA + 75/90 目标线）、E2E UNCLEAN_HOLDS 代码表——全部可改配置不动代码
- risk.py / kpi.py / e2e_kpi.py 改读 rules.json（默认值 = v1.0 硬编码值）
- 同日回归：8711 条最新数据下 5 基线键 100% 一致 → 默认配置行为零变化
- ⏭️ P5-5 待确认：merge.py 的 status_label/cto_p1 判定配置化（跨层，Data Engine 侧）

## v1.4-dev（2026-09-03）— Phase 4 ST Validator + Excel Generator（在 v1.3-dev 之上）

- **ST Validator**（SHIP_STATUS 出货状态校验）：rules/st.py 按 PO/ASN 校验
  （NACK/已出货无SN/有量未标记/超发/Hold/部分出货 → NACK>ERROR>WARN>PARTIAL>OPEN>PASS）
  /api/st?po=X&asn=X；tools.html ST Tab；ship_status 字段贯通管线（公司侧同步后有原始值）
- **Excel Generator**：/api/export/orders（openpyxl XLSX，表头样式+冻结首行+列宽）
  过滤与 /api/orders 完全同源（抽取 _build_orders_sql 共用），新增 msbd_from/msbd_to 范围过滤
  tools.html Excel Tab：类型/区域/出货/ACK/CUST/MSBD范围/CTO P1/Hold + 下载 + 查条数
- 修复：st.py 过滤 asn='None' 假 ASN（OMS 空值字符串坑）
- dev 数据已同步线上最新（8711 条）
- 同日回归通过（5 基线键一致）

## v1.3-dev（2026-08-23 起，持续增强中）— Phase 3 ASN Checker + K1 提醒卡片

**2026-08-30 增强**：
- Business Engine 新增 `rules/cto_asn.py`：CTO P1 已入库（STOCKIN_CDT）未开立 ASN（无 CREATEASN_CDT）未出货清单，每笔附 28H 目标出货时间 + 已入库时长
- `/api/cto-asn-missing` 端点；K1 日报 Tab 新增 🚨 提醒卡片（笔数/数量/已过28H，点击展开明细表：PO/SO/MCID/QTY/入库时间/28H目标/时长/状态/Hold）
- MSBD 卡片标注"非 CTO P1 口径"；ASN 卡片补显 NACK
- 同日回归通过（5 基线键一致，新增键 asn_check/cto_asn_missing）

**2026-08-23**：
- Business Engine 新增 `rules/asn.py`：按 ASN 聚合 + 业务校验（NACK/HOLD/PASS/PARTIAL/PENDING/OPEN）

- Business Engine 新增 `rules/asn.py`：按 ASN 聚合 + 业务校验（NACK/HOLD/PASS/PARTIAL/PENDING/OPEN）
- 数据链：engine.run 新增 asn_check 结果 → cache → push → sync（全加法式，旧 5 项不变）
- Service Layer：`/api/asn?asn=X`（found/check/meta/computed_at，404=NOT_FOUND，400=缺参）
- Portal：`tools.html`（ASN Checker Tab 可用，ST/Excel 为 Phase 4 占位）+ 首页 Quick Links 入口
- 同日回归 check-live 通过：M1-start 旧代码 vs 新代码 5 基线键 100% 一致（从 git 取旧代码同日对比，跨天无时间漂移）
- 端点验证：真实 ASN → PASS（qty=11/9 PO）；bogus→404；缺参→400；tools.html 200
- ⏳ 未上线——随 v1.1/v1.2 一起等待确认

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
