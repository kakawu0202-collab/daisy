---
name: project-tracker
description: 项目追踪看板——单文件HTML看板，支持看板拖拽、事项管理、进度追踪、筛选搜索、dark mode、localStorage持久化（2026-07-05创建）
metadata: 
  node_type: memory
  type: project
  originSessionId: 7ae6532b-01e5-4db8-b0b1-6fac7c305034
---

# 项目追踪看板 (Project Tracker)

## 打开方式

```
D:\workspace\project-tracker\index.html
```

双击在浏览器打开即可，无需服务器。

## 功能清单

| 功能 | 操作 |
|------|------|
| 📋 看板视图 | 待办 / 进行中 / 已完成 三列，可拖拽切换状态 |
| ➕ 新增事项 | 右上角 "+ 新增事项" 按钮，或按键盘 `N` |
| ✎ 编辑事项 | 鼠标悬停卡片→点 ✎，或点击卡片→右侧面板→✎ |
| 🔍 搜索 | Ctrl+K 聚焦搜索框，按标题/描述搜索 |
| 🎯 筛选 | 按负责人(小P/小O/小C/小Z) + 优先级(高/中/低) 筛选 |
| 📊 子任务 | 事项内添加子任务 checkbox，自动算进度 |
| 📅 截止日期 | 逾期事项红色标注 |
| 🌓 暗色模式 | 右上角 🌓 切换，偏好自动保存 |
| 💾 数据持久化 | localStorage 自动保存，刷新不丢失 |
| 📤 导出 | 导出 JSON 文件备份 |
| 📥 导入 | 导入 JSON 文件恢复 |
| ⌨️ 快捷键 | N=新增, Escape=关闭弹窗, Ctrl+K=搜索 |

## 数据字段

每个事项包含：标题、描述、负责人(小P/小O/小C/小Z)、优先级(高/中/低)、状态、截止日期、分类、进度、子任务、备注、创建时间、更新时间

## 关联

- [[role-assignment]] — 四角色分工
- [[priority-sort-tool]] — 优先级排序工具
- [[k1-prd-dashboard]] — K1 PRD看板
- [[fullstack-office-skills]] — 全链路办公技能体系
