---
name: write-notes-like-deepseek
description: 当行为、架构、跨模块契约、工程流程或测试策略发生值得追溯的取舍时，建立、更新或流转项目决策笔记。包含 README 范本、三种状态的模板和本地校验脚本。
---

# 工程决策记录与流转

当另一位维护者将来会追问“为什么这样定、其他方案为什么没用”时，记录这次决定。纯样式、格式化、无歧义重命名和从 diff 即可看懂的局部修改，通常无需建笔记。

## 在目标项目使用

在当前项目的 `.agents/notes/` 中按主题搜索已有记录。README 写本项目特有的记录约定。首次引入时可取用 [notes README 范本](templates/notes-README.md)。只建立本次需要的状态和分类目录。

笔记路径为 `.agents/notes/{状态}/{分类}/YYYY-MM-DD-topic.md`。日期取首次提出日，分类选 `feature`、`bug-fix`、`simplification`、`architecture`、`process`、`testing` 之一。

| 触发条件 | 操作 |
| --- | --- |
| 重要的备选仍在比较 | 在 `proposed/` 写[提案](templates/proposed.md)，记下问题、候选方案、可验证条件及风险。用户已授权时直接推进，真正待裁决的取舍集中提问 |
| 决定已随改动落地 | 将同一文件移到 `implemented/`，保留分类、文件名和日期。按[已实施模板](templates/implemented.md)同步状态，将提案和计划改写为当前决定、代价和验证依据 |
| 放弃提案且理由值得保留 | 将文件移到 `rejected/`，保留原标题与日期，按[被否模板](templates/rejected.md)在状态行写一句否决原因 |
| 已实施决定的路径或事实更新 | 原地修正现有笔记和受影响的引用；核心决定翻转时新写一篇，互链并说明哪部分被取代 |

例如曾提议按天缓存查询结果，最终选择仅在单次页面会话内缓存。若方案仍在比较，用一篇提案记下两种策略。落地时把最终选择和失效条件写入同一篇已实施记录；已比较的备选留在该篇即可。

笔记保留取舍与代价，规格、接口和测试证据链接到项目原有记录。移动笔记时更新指向旧路径的链接。归档属于项目另行采用的生命周期；已有归档可以使用随包脚本校验封印。

## 校验

在**持有笔记的目标项目根目录**执行。以下命令假定 Skill 位于该项目的 `.agents/skills/write-notes-like-deepseek/`。如果使用个人安装位置，只替换脚本路径，工作目录仍保留在项目根。已用支持直接执行 TypeScript 的 Node.js 24 验证这三个命令。

```sh
node .agents/skills/write-notes-like-deepseek/scripts/verify-agent-note-tree.ts
node .agents/skills/write-notes-like-deepseek/scripts/verify-agent-note-format.ts
node .agents/skills/write-notes-like-deepseek/scripts/verify-archived-agent-notes.ts
```

第一条检查生命周期、分类、文件名和活动笔记间相对链接；第二条检查状态行和对应章节；第三条只读核对已有归档的哈希及可用的 Git 基线。检查输出的笔记数量应与预期一致，零篇通过不能证明目标笔记已被检查。门禁通过后仍需核对问题是否真实、备选是否实际考虑过、结果能否复现。

方法沿用既有 `write-notes-like-deepseek` Skill 的实践。其方法来源见 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)。
