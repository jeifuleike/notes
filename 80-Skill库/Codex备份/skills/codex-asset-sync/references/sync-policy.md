# Codex 资产同步规则

## 目录

本机运行目录：

```text
~/.codex/
├─ skills/
│  ├─ kb-curator/
│  ├─ kb-query/
│  └─ codex-asset-sync/
├─ AGENTS.md
└─ codex-assets.json
```

`notes` 备份目录：

```text
90-知识系统/
└─ prompts/AGENTS.global.md

80-Skill库/Codex备份/
├─ skills/
└─ manifest.json
```

`codex-assets.json` 只保存本机路径和同步清单，不写入笔记内容：

```json
{
  "vault": "D:\\notes",
  "skills_dir": "80-Skill库/Codex备份/skills",
  "prompt_backup": "90-知识系统/prompts/AGENTS.global.md",
  "sync_skills": ["kb-curator", "kb-query", "codex-asset-sync"]
}
```

## 提示词规则

只同步 `AGENTS.md` 中以下标记之间的内容：

```text
<!-- BEGIN codex-kb -->
...
<!-- END codex-kb -->
```

这样不会覆盖各机器自己的其他 `AGENTS.md` 内容。`notes` 中的 `prompts/AGENTS.global.md` 保存的也应是这个规则块，而不是整份本机配置。

## 冲突与安全

- 状态比较使用文件 SHA256；两边都改动时拒绝自动覆盖。
- `restore` 前把本机旧文件保存到 `~/.codex/skill-backups/<时间>/`。
- 只替换清单内的 Skill，不删除清单外的本机 Skill。
- 备份完成才更新 `Codex备份/manifest.json`。
- 默认不使用删除选项；需要删除旧文件时必须由用户明确确认。

## 多机流程

1. 家里：让我执行 `backup`，再提交/推送 `notes`。
2. 公司：同步 `notes` 后让我执行 `restore`。
3. 公司改完：执行 `backup`，再同步回家里。

Codex 运行时始终读取 `~/.codex` 的真实副本，不读取 `notes`。
