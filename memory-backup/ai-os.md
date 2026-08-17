---
name: ai-os
description: 个人AI操作系统——语义层+Agent系统+知识库+数据库，跨模型可移植（2026-07-26）
metadata: 
  node_type: memory
  type: project
  originSessionId: 7ae6532b-01e5-4db8-b0b1-6fac7c305034
---

# AI-OS — 个人AI操作系统

## 位置

`D:\workspace\ai-os\`

## 四层架构

| 层 | 作用 | 格式 |
|------|------|------|
| **语义层** | 定义PO/Hold/生产等业务概念，让AI理解你的语言 | YAML |
| **Agent系统** | 4个工作伙伴(小P/小O/小C/小Z)，各有角色+工具+知识边界 | YAML |
| **知识库** | 你的"第二大脑"，主动往里存知识，AI随时查阅 | Markdown |
| **数据库** | 结构化数据存储，有Schema约束 | JSON |

## 核心文件

- `semantic-layer/entities/po.yaml` — PO实体定义
- `semantic-layer/entities/hold.yaml` — Hold实体
- `semantic-layer/rules/po-blocking.yaml` — 出货阻塞分析（5步排查）
- `semantic-layer/queries/po-analysis.yaml` — 5个常用查询模板
- `agents/definitions/agent-p/o/c/z.yaml` — 4角色Agent定义
- `deploy/generic-llm.md` — 跨模型部署方案

## 设计目标

1. 让AI根据自然语言分析PO为什么不能出货
2. 培养4个Agent处理日常工作任务
3. 随时添加知识，永不遗忘
4. 全文件化，不绑定Claude，任何LLM都能用

**Why:** 让AI从"通用助手"升级为"懂你业务的专属系统"。
**How to apply:** 对AI说"加载 ai-os 语义层，分析..."。
