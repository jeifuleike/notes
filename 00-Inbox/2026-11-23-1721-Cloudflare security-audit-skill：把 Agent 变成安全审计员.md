---
type: inbox
status: new
captured: 2026-11-23T17:21
source: "https://github.com/cloudflare/security-audit-skill"
kind: skill
capture_reason: source
value: unknown
tags: ["AI", "agent", "skill", "security", "audit"]
---

# Cloudflare security-audit-skill：把 Agent 变成安全审计员

## 内容

六阶段安全审计技能：侦察、覆盖式 hunting、候选验证、结构化输出、独立记录复核、目标无关报告；产出 findings.json、REPORT.md 等结构化结果，强调每个结论都有源码追踪。

## 怎么用

按 README 把 `skills/` 装进支持 skill 的 Agent；在目标仓库里让它跑 security audit，它会按六阶段产出 `findings.json`、`REPORT.md` 和 `NEEDS-VALIDATION.md`。

## 优化什么工作

优化发版前/接手陌生代码库的安全审查：把“让 Agent 随便看看”变成有覆盖账本、候选验证和独立复核的审计流程。

## 来源

- https://github.com/cloudflare/security-audit-skill
