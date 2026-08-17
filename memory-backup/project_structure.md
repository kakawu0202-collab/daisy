---
name: project-structure
description: 工作区完整目录结构映射，帮助定位文件
metadata: 
  node_type: memory
  type: reference
  originSessionId: cf53b75f-c5b0-4e73-8335-ef7a0db1cd97
---

# 工作区目录结构

## D:\workspace 顶层

| 目录/文件 | 用途 |
|-----------|------|
| `planning-kb/` | Obsidian 知识库（主 vault） |
| `odm-ops-manual/` | HTML PPT 操作手册集 |
| `odm-planning-team-deck/` | 团队能力介绍 PPT |
| `notebooklm-api/` | NotebookLM API 分析工具 |
| `seedance-api/` | Seedance API 客户端 |
| `feishu/` | 飞书 MCP 集成 |
| `rpa/` | RPA 自动化脚本 |
| `inbox/` | 待处理文件 |
| `examples/` | 示例项目 |
| `简历-施敏芳.html` | 个人简历 |
| `settings.json` | Claude Code 项目设置 |

## planning-kb（Obsidian 知识库）

```
planning-kb/
├── 00-Dashboard/          ← 工作台主页
├── 01-仓储/               ← 仓库管理
├── 02-物控与采购/          ← 物控 + 采购（合并）
├── 03-生管/               ← 生产管理
├── 04-订单管理/            ← 订单管理
├── 05-团队运营/            ← 团队运营
├── 06-资源库/              ← 参考资料（原09-资源库）
│   ├── Dell-ODM规范/
│   │   ├── 01-物流与运输/        ← 6.2.6 + 6.2.10
│   │   ├── 02-质量管理/          ← 6.2.5 + AIT/PhaseGate
│   │   ├── 03-IT与EDI/          ← 6.2.4 + 6.2.7
│   │   ├── 04-合规与安规/        ← 6.1.1 + 6.2.11 + 6.2.13
│   │   ├── 05-采购与订单管理/     ← 6.2.1 + 6.2.3
│   │   ├── 06-生产与BOM/         ← 6.2.2
│   │   ├── 07-CFI与客户履约/     ← 6.2.8 + 6.2.16 + 6.2.17
│   │   ├── 08-OTM运营流程/       ← 6.5.2
│   │   ├── 09-周会与报告/        ← 周会/归档
│   │   ├── _archive_old_versions/ ← 历史版本归档
│   │   ├── Dell-ODM规范总览.md
│   │   ├── SPEC全量汇总.md
│   │   ├── 知识点与流程.md
│   │   ├── PDF精读笔记.md
│   │   └── 0520更新日志.md
│   ├── Lenovo/
│   ├── TikTok电商/
│   ├── Templates/
│   ├── 内部培训/
│   ├── 数据分析/
│   └── 其他文档/
├── 99-Inbox/
└── CLAUDE.md
```

## odm-ops-manual（HTML PPT 操作手册）

```
odm-ops-manual/
├── index.html              ← 主操作手册（10页）
├── om-workflow/            ← 订单管理工作思路
├── order-timeline/         ← 28H订单交付时间轴
├── priority-sop/           ← 优先级SOP
└── shuttle-cutoff/         ← 穿梭班车时间轴
```

## 关键词 → 路径映射

| 用户说 | 我去 |
|--------|------|
| Dell SPEC / 6.x.x 编号 | `planning-kb/06-资源库/Dell-ODM规范/` |
| 物流/标签/打板/Carrier/Shuttle | `Dell-ODM规范/01-物流与运输/` |
| 质量/检验/QPA/PPID | `Dell-ODM规范/02-质量管理/` |
| EDI/NACK/IT | `Dell-ODM规范/03-IT与EDI/` |
| 合规/SIRIM/安规 | `Dell-ODM规范/04-合规与安规/` |
| 优先级/Priority/OA3 | `Dell-ODM规范/05-采购与订单管理/` |
| BOM | `Dell-ODM规范/06-生产与BOM/` |
| CFI/SCV | `Dell-ODM规范/07-CFI与客户履约/` |
| OTM | `Dell-ODM规范/08-OTM运营流程/` |
| 知识库/Obsidian | `planning-kb/` |
| 操作手册/SOP/PPT | `odm-ops-manual/` |
| 飞书/文档上传下载 | 用 `lark-cli` 命令 |
| 设置/权限 | `~/.claude/settings.json` |
| 简历 | `D:\workspace\简历-施敏芳.html` |
| NotebookLM | `notebooklm-api/` |
| RPA | `rpa/` |

## SPEC 编号 → 职能目录

| 编号段 | 职能目录 |
|--------|----------|
| 6.1.1 | 04-合规与安规 |
| 6.2.1 | 05-采购与订单管理 |
| 6.2.2 | 06-生产与BOM |
| 6.2.3 | 05-采购与订单管理 |
| 6.2.4 | 03-IT与EDI |
| 6.2.5 | 02-质量管理 |
| 6.2.6 | 01-物流与运输 |
| 6.2.7 | 03-IT与EDI |
| 6.2.8 | 07-CFI与客户履约 |
| 6.2.10 | 01-物流与运输 |
| 6.2.11 | 04-合规与安规 |
| 6.2.13 | 04-合规与安规 |
| 6.2.16 | 07-CFI与客户履约 |
| 6.2.17 | 07-CFI与客户履约 |
| 6.5.2 | 08-OTM运营流程 |
