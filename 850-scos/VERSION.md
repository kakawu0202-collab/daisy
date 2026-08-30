# 850 SCOS — 版本记录

## v1.0.1（2026-08-30）— 🔒 线上锁定（卡片版）

> 代码内版本号：`scos-1.0.1`（portal/api/server.py health 端点）

**本次上线内容（仅卡片，架构保持 v1.0 不变）：**

- K1 日报新增 🚨 **CTO P1 已入库未开 ASN** 提醒卡片：笔数/数量/已过28H，点击展开明细（PO/CUST/SO/MCID/QTY/入库时间/28H目标出货/已入库时长/状态/Hold）
- MSBD 卡片标注「非 CTO P1 口径」；ASN 卡片补显 NACK
- 卡片明细新增 CUST 栏位（DAISY / DAISY 35）
- 卡片数据在 Yumin 侧从 portal.db 实时计算（`portal/rules/cto_asn.py`），无公司侧依赖
- 老功能全部验证未破坏（K1/orders/同步正常）

**待办：公司电脑同步（让 CUST 有值）**
- 把 `data-engine/processor/merge.py` + `data-engine/storage/db.py`（已加 cust 字段）复制到公司电脑 `D:\Kaka\2.系统\CC\850-scos` 对应位置，重启 Engine 后下一轮全量拉数即带 CUST

## v1.0.0（2026-08-18）— 线上基线

- Data Engine（采集/清洗/存储/增量推送）+ Portal（PWA 看板）+ Service Layer（API/认证）
- 看板：k1 / e2e-kpi / cto-kpi / cto-analysis / report-builder / status
- Business Engine 功能在 data-engine/processor 内（未拆层）
- 部署：公司电脑 `D:\Kaka\2.系统\CC\850-scos`（Engine）+ Yumin `d:\workspace\850-scos`（Portal，端口 5050）
- 公网：https://yumin.taila2a2ad.ts.net

### 版本规则

- 线上版本号记录于此文件，每次升级线上时递增
- **开发在 `d:\workspace\850-scos-dev` 进行，端口 5051/8701/8901，不干扰线上**
- dev 验证通过后，按增量合并回本目录并升级版本号
- **🔒 锁定规则（2026-08-30 起）：任何线上改动（含后续 v1.1/v1.2/v1.3 等）必须经用户逐次明确批准（"点头"）后方可执行，不得擅自上线**
