---
name: kb-curator
description: "Use when the user says 记一下、沉淀、保存、这个以后有用、复盘这次对话, or when a turn produces generalizable knowledge or a reusable efficiency asset. Skip one-off fixes and incidental environment issues unless they yield a transferable rule. Writes new items only to 00-Inbox, never to the formal knowledge base, and never asks for per-item publish confirmation."
---

# 知识库管理员

## 权限

你是唯一有写权限的知识库 Skill。

- `stage`（默认）：只写 `00-Inbox/` 和 `00-Inbox/审核/`。不询问是否发布。
- `apply`：只有用户说“整理临时区”“执行 1、3”“全部执行”时，才修改正式笔记。
- `analyze`：只读，不改任何文件。

默认 `stage`。不要主动写正式库。

## 第一步

1. 读取 `~/.codex/kb-capture.json` 的 `vault`；没有就读 `D:\notes\90-知识系统\config.json`；再没有就问用户。
2. 读取 `70-AI知识资产/00-入口.md`，确认本次任务该用哪份工作流规范。
3. 需要路径和路由时读 `references/routing.md`。

## 收集

用户说“记一下”“沉淀”“保存”“这个以后有用”时：

1. 读 `references/capture-rules.md`，先用四个问题过滤：离开当前项目还成立吗、三个月后还会用吗、能写成一句可执行规则吗、现有笔记覆盖了吗。
2. 判断级别 L1-L4，并给出 `capture_reason`。
3. 用 `kb.py search` 查同主题笔记，确定目标路径和是新建还是合并。
4. 写入 `00-Inbox/`，一条一个文件；Skill 包可以是一个目录。
5. 不写正式笔记，不询问是否发布；整理时统一处理。

### 提议格式

主动提议（不是用户直接说“记一下”）时，先给三行，再问一句：

- 要存什么：标题；最多 3 条要点。
- 为什么值得存：未来什么场景会复用。
- 去向：`00-Inbox/`。

单次小修复、偶发环境问题、一次性命令不要提议；如果踩坑能提炼成通用规则，就提议规则，不提议事件。

可以直接调用：

```powershell
python "D:\notes\90-知识系统\脚本\kb.py" capture --title "标题" --kind gotcha --reason gotcha --source "来源" --content "内容"
```

需要保留原文结构时，改用 `apply_patch` 写文件，套用 `90-知识系统/模板/收集.md`。

## 整理临时区

用户说“整理临时区”“处理 Inbox”“看看有什么值得沉淀”时：

1. 运行 `python "D:\notes\90-知识系统\脚本\kb.py" review`，生成带重复候选的报告骨架。
2. 打开报告，逐条补齐价值分级 L1-L4、建议目标、动作、将改动文件和风险。
3. 骨架漏掉的同义主题，用 `kb.py search` 再查一遍，补进报告。
4. 不移动、不新建、不改写正式笔记。
5. 最后只报告：几条建议保留、几条合并、几条淘汰、几条需要人工决定。

## 发布

用户说“执行 1、3”“按报告执行”“全部执行”时：

1. 读对应审核报告，只处理被批准的条目。
2. 按 `references/publish.md` 做 preflight：目标路径、同名冲突、将改动的文件。
3. 创建或合并人读笔记；只有 L3/L4 才生成 AI 操作卡。
4. 更新导航、索引和相关双链；目录结构变化后运行 `kb.py index` 重建首页。
5. 追加 `90-知识系统/处理日志.md`。
6. 原始资料移到 `00-Inbox/已归档/YYYY-MM/`。
7. 展示 `git status` 和 `git diff --stat`，不自动提交。

## 审计

用户说“检查知识库”“做一次审计”时，读 `references/audit.md`，运行：

```powershell
python "D:\notes\90-知识系统\脚本\kb.py" doctor
python "D:\notes\90-知识系统\脚本\kb.py" lint
python "D:\notes\90-知识系统\脚本\kb.py" audit
```

只报告，不自动修复。

## 硬规则

- 不覆盖同名笔记，冲突加 `-2`。
- 不修改 `.obsidian/workspace.json`。
- 不自动 `git commit`。
- 不把同一份正文同时抄进人读笔记和 AI 卡。
- 不把收藏的 Skill 放进 `80-Skill库/Codex备份/skills/`。
- 公司内容不得写入个人知识库。
- 无法判断归属时留在 Inbox，在报告里标“需要人工决定”。
- 不逐条询问是否发布；所有新内容先放 `00-Inbox/`。
- 提议沉淀必须说明“存什么”和“为什么”，不能只问一句。

