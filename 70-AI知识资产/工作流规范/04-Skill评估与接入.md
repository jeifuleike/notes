---
type: ai-workflow
status: active
scope: global
audience: ai
version: 1
reviewed: 2026-11-16
sources: []
---

# 工作流：Skill 评估与接入

## 适用场景

收藏了一个第三方 Skill，或准备把自己写的流程封装成 Skill。

## 输入

- Skill 包、README、许可证、版本、依赖。
- 现有 Skill 清单和重叠能力。

## 步骤

1. 把 Skill 包放到 `80-Skill库/候选/<name>/`，原样保留。
2. 在同一个目录写 `评估.md`。
3. 检查来源、许可证、维护状态、依赖、权限和联网要求。
4. 与现有 Skill 比较，列出重叠和差异。
5. 在隔离目录或临时 Vault 试运行，记录 doctor、dry-run 和真实任务结果。
6. 结论只有三种：采用、观察、淘汰。
7. 采用后移到 `80-Skill库/已采用/`，登记 `00-索引.md`，再复制到 `~/.codex/skills/`；不使用 junction。

## 禁止

- 不把收藏的 Skill 放进 `80-Skill库/Codex备份/skills/`。
- 不跳过许可证和权限检查。
- 不在未试运行的情况下标记“已采用”。
- 不让收藏的 Skill 默认获得知识库写权限。

## 验收标准

- `评估.md` 完整。
- 试运行结果可复现。
- `80-Skill库/00-索引.md` 有条目。
- 部署路径和回滚方式明确。

## 失败处理

试运行失败就留在 `候选/` 或移到 `已淘汰/`，不要为了凑数强行采用。

## 关联 Skill

- `kb-curator`：生成评估报告。

