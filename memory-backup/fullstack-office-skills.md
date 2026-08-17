---
name: fullstack-office-skills
description: 2026-07-05 从 GitHub 集成的三套开源技能库：SenseNova-Skills(商汤)、Anthropic Skills(官方)、staticdash
metadata: 
  node_type: memory
  type: project
  originSessionId: 7ae6532b-01e5-4db8-b0b1-6fac7c305034
---

# 全链路办公自动化技能体系

## 来源

从 GitHub 克隆并集成了以下开源项目：

### 1. SenseNova-Skills (商汤) — 2K+ Stars
- 仓库：https://github.com/OpenSenseNova/SenseNova-Skills
- 核心技能：PPT 生成（entry/standard/creative）、Excel 数据分析（70+ 子技能）、深度研究（多 Agent）、信息图生成、HTML 报告美化

### 2. Anthropic Skills (官方) — 44K+ Stars
- 仓库：https://github.com/anthropics/skills
- 核心技能：pptx（专业 PPTX 编辑）、xlsx（财务建模）、theme-factory（主题设计）、internal-comms（内部沟通）

### 3. staticdash — PyPI 包
- pip install staticdash（已安装 v2026.9）
- 功能：Plotly 交互图表 + Mermaid 流程图 + Markdown → 自包含 HTML 看板

### 4. MarkItDown — 微软开源（2026-07-06 集成）
- GitHub：https://github.com/microsoft/markitdown（14万+ Stars，MIT 协议）
- 已安装版本：v0.1.6（`pip install 'markitdown[all]'`）
- 功能：PDF/Word/PPT/Excel/图片/音频/HTML/CSV → 干净 Markdown
- 定位：文档摄入层，全链路第一关——非结构化文件先转 Markdown 再喂给后续分析

## 新增技能清单（位于 ~/.claude/skills/）

### 演示层
- `sn-ppt-entry` — PPT 入口，模式选择+参数收集+文档解析
- `sn-ppt-standard` — 标准/快速 PPT 管线（AI 配图+ECharts+web 搜索）
- `sn-ppt-creative` — 创意模式（全页 AI 生成图片）
- `sn-ppt-doctor` — 环境诊断
- `pptx` — 专业 PPTX 编辑（openpyxl+QA 工作流）
- 已有：`html-ppt-skill` (36主题+31布局+演讲者模式)

### 数据层
- `sn-da-excel-workflow` — Excel 全流程（读取→清洗→筛选→统计→导出），含 70+ capability 子技能
- `sn-da-large-file-analysis` — 大文件（≥100k 行）流式处理
- 已有：`xlsx` (openpyxl+公式重算)、`data-analysis`

### 研究层
- `sn-deep-research` — 多 Agent 深度研究编排（scout→plan→research→review→perspective→supplement→write→render）
- `sn-research-report` — 结构化研究报告模板
- `sn-search-academic/finance/market-cn/social-cn/...` — 多源搜索
- 已有：`research`

### 报告层
- `sn-md-to-html-report` — Markdown→精美 HTML 专题页（编辑判断+设计契约）
- `sn-infographic` — 信息图生成（87 布局×66 风格）
- `internal-comms` — 内部沟通模板
- 已有：`presentation`

### 设计层
- `theme-factory` — 10 预设主题 + 自定义主题生成
- `brand-guidelines` — 品牌视觉规范
- `canvas-design` — 视觉设计

### 编排层（新建）
- `fullstack-office` — 全链路编排器，路由到上述专业 skill
- 新增文档摄入层：markitdown（2026-07-06）

## 集成要点

1. **PPT 生成优先级**：快速 HTML PPT → html-ppt-skill；正式 PPTX → sn-ppt-entry→standard；创意视觉 → sn-ppt-entry→creative
2. **数据量阈值**：<10k 行 pandas；10k-100k Parquet 缓存；≥100k 流式读取
3. **主题一致性**：用 theme-factory 生成主题 → 传递给下游 skill
4. **所有 skill 位于** `C:\Users\18124\.claude\skills\`，源码位于 `D:\workspace\cloned-skills\`

**Why:** 将项目管理、PPT 制作、数据分析三大能力从分散的工具整合为统一技能体系，实现数据→分析→看板→PPT 全链路自动化。
**How to apply:** 遇到办公自动化需求时，先调用 fullstack-office 判断路由，再由对应专业 skill 执行。
