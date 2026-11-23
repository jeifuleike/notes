---
type: inbox
status: new
captured: 2026-11-23T17:20
source: "https://github.com/obra/superpowers"
kind: skill
capture_reason: source
value: unknown
tags: ["AI", "agent", "skill", "coding", "TDD"]
---

# Superpowers：给 coding agent 装一套完整开发方法论

## 内容

Superpowers 是一套给 coding agent 用的完整软件开发方法论：先把需求问清，再拆实现计划，然后用子 Agent 逐项执行并自审，强调 TDD、YAGNI、DRY。支持 Claude Code、Codex、Cursor、Hermes 等多种 harness。

## 怎么用

Claude Code 里 `/plugin install superpowers@claude-plugins-official`；其他 harness 按 README 的插件方式安装。装好后正常提需求即可，它会自动先问清目标、拆计划、用子 Agent 执行并自审。

## 优化什么工作

优化“需求没问清就开写、跳步、漏测”的开发流程；适合从 0 到 1 的功能、重构和需要 TDD 的任务。

## 来源

- https://github.com/obra/superpowers
