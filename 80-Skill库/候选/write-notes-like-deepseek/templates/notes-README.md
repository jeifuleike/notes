# 工程决策笔记

本目录说明项目为什么采用某个方案，以及当时考虑过的备选和代价。功能规格、接口定义和验收结果分别保存在项目已有位置，决策笔记链接到相关记录。

## 存放

```text
.agents/notes/
  README.md
  proposed/<分类>/YYYY-MM-DD-topic.md
  implemented/<分类>/YYYY-MM-DD-topic.md
  rejected/<分类>/YYYY-MM-DD-topic.md
```

目录随实际记录建立。分类可选功能（`feature`）、缺陷（`bug-fix`）、简化（`simplification`）、架构（`architecture`）、流程（`process`）、测试（`testing`）。

## 流转

新提案先记录问题和可观察的验收条件。决定落实时，保留首次提出的日期和文件名，移入已实施目录并改写状态、结论和代价。值得留存的被否提案移入被否目录，并在状态行写明原因。移动后同步更新引用。

使用本项目采用的决策笔记校验入口检查目录、链接和格式。只把项目特有的记录位置、使用命令和例外补充在本页。
