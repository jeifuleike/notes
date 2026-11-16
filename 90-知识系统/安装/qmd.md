# QMD 接入（按需）

当前默认是 `kb.py search` 的词法检索，不依赖任何外部服务。只有当你觉得关键词搜不准、需要语义召回时再接 QMD。

## 导出语料

```powershell
python "D:\notes\90-知识系统\脚本\kb.py" export
python "D:\notes\90-知识系统\脚本\kb.py" export --format json --out "D:\notes\90-知识系统\导出\qmd.json"
```

默认输出 `90-知识系统/导出/qmd.jsonl`，每行一篇笔记，字段：`id`、`path`、`title`、`type`、`tags`、`updated`、`text`。该目录已在 `.gitignore`，不会进版本库。

## 接入步骤

1. 按 QMD 官方 README 安装并初始化。
2. 让 QMD 索引 `D:\notes` 目录，或索引导出的 JSONL。两种方式二选一，优先直接索引目录，少一层同步。
3. 首次建索引和嵌入会消耗时间与磁盘，先只索引 `00-Inbox`、`70-AI知识资产`、`20-后端` 试效果。
4. 效果确认后，再让 `kb-query` 在词法检索之外增加一条 QMD 查询路径。

## 约束

- 导出文件包含全部笔记正文，不上传、不提交、不放进共享盘。
- QMD 只做检索，不参与写入；写入权限仍然只在 `kb-curator`。
- 接入后 `kb.py doctor` 和 `lint` 仍是发布前的必过检查。
