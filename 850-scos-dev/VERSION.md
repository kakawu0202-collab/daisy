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

## 开发路线（2026-08-18 起）

1. 拆层：Business Engine 从 data-engine/processor 独立
2. Portal 工具：ASN Checker / ST Validator / Excel Generator
3. AI Engine 起步：NL 查询 → Service Layer API
