# 850 SCOS — 版本记录

## v1.0.0（2026-08-18）— 线上基线

> 代码内版本号：`scos-1.0`（portal/api/server.py health 端点）

- Data Engine（采集/清洗/存储/增量推送）+ Portal（PWA 看板）+ Service Layer（API/认证）
- 看板：k1 / e2e-kpi / cto-kpi / cto-analysis / report-builder / status
- Business Engine 功能在 data-engine/processor 内（未拆层）
- 部署：公司电脑 `D:\Kaka\2.系统\CC\850-scos`（Engine）+ Yumin `d:\workspace\850-scos`（Portal，端口 5050）
- 公网：https://yumin.taila2a2ad.ts.net

### 版本规则

- 线上版本号记录于此文件，每次升级线上时递增
- **开发在 `d:\workspace\850-scos-dev` 进行，端口 5051/8701/8901，不干扰线上**
- dev 验证通过后，按增量合并回本目录并升级版本号
