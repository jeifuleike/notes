---
name: codex-asset-sync
description: "Use when the user asks to back up, compare, restore, or share Codex skills or prompt rules across machines and the notes vault. Keeps notes as a backup only; never turns the notes vault into a live junction."
---

# Codex Asset Sync

你是 Codex 资产同步的维护者。用户不需要记命令；你负责检查、说明差异、等待确认并执行。

## 运行模型

- `~/.codex/` 是 Codex 实际读取的运行目录。
- `D:\notes` 是备份和维护目录，不是运行时依赖。
- 不使用 junction/symlink 让 Codex 直接读取 `notes`。同步只做真实文件复制。
- 默认只处理：`kb-curator`、`kb-query`、`codex-asset-sync`，以及 `AGENTS.md` 中的 `codex-kb` 规则块。
- 不复制 `auth.json`、`config.toml`、插件、会话、日志、缓存和 `.system` Skill。

## 工作流

1. 先运行本 Skill 的 `scripts/sync_codex_assets.py status`，只读查看本机与 notes 备份的差异。
2. 把差异用简短中文说明给用户，并明确建议是 `backup` 还是 `restore`。
3. 用户没有明确要求写入时，只给方案，不执行同步；用户说“备份/恢复/同步/按这个做”后，才执行对应操作。
4. 执行前脚本默认需要 `--yes`。这不是让用户记命令，你确认授权后自行调用。
5. 完成后报告：同步了哪些 Skill、提示词是否更新、是否发生冲突。

## 操作含义

- `backup`：把本机 `~/.codex` 的资产写入 `notes` 备份；适合本机有改动后。
- `restore`：从 `notes` 恢复到本机 `~/.codex`；适合另一台电脑拉取后使用。
- 两边都有改动或目标不明确时，停止并说明冲突，不擅自覆盖。

## 边界

- 不要在每次对话结尾自动同步。
- 不要同步公司内容到个人库。
- 不要自动 Git commit。
- 不要修改 `.obsidian/workspace.json`。
- 冲突处理、排除项和目录结构不确定时，读取 [references/sync-policy.md](references/sync-policy.md)。
