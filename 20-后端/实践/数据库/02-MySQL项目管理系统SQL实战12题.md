# MySQL SQL 实战练习：项目管理系统 12 题

> **适用环境**：MySQL 8.4 / MySQL Workbench / Obsidian  
> **练习数据库**：`project_management`  
> **题目安排**：基础查询 → 聚合统计 → 多表查询 → 索引与性能优化  
> **使用方法**：先独立写 SQL，再展开每题下方的「参考答案与解析」。折叠使用 HTML `<details>`，适合 GitHub Markdown 及多数 Obsidian 阅读视图。

---

## 0. 练习前准备

先在 MySQL Workbench 中执行：

```sql
USE project_management;
```

### 当前四张表（按你提供的实际 DDL）

| 表名 | 主要字段 | 已有索引 |
| --- | --- | --- |
| `users` | `id`, `username`, `email`, `password_hash`, `status`, `created_at` | `PRIMARY(id)`、`UNIQUE(email)` |
| `projects` | `id`, `name`, `owner_id`, `status`, `created_at` | `PRIMARY(id)` |
| `tasks` | `id`, `project_id`, `creator_id`, `title`, `status`, `priority`, `created_at` | `PRIMARY(id)`、`idx_project_id(project_id)`、`idx_project_status(project_id, status)` |
| `project_members` | `id`, `project_id`, `user_id`, `role` | `PRIMARY(id)` |

**注意**：这四张表的 DDL 中尚未声明外键（`FOREIGN KEY`）。因此关联查询遇到找不到用户或项目的孤立记录时，`INNER JOIN` 可能不返回该条数据，而 `LEFT JOIN` 可以保留左表的数据。

**安全原则**：第 1～11 题都只使用查询/分析语句；第 12 题的建约束操作仅作为方案展示，**不要在检查数据前直接执行 `ALTER TABLE`**。

### 完成进度（自己勾选）

- [x] 第 1 题：查询未完成任务 ✅ 2026-10-21
- [x] 第 2 题：查询高优先级任务 ✅ 2026-10-21
- [x] 第 3 题：任务状态分布 ✅ 2026-10-21
- [x] 第 4 题：任务数最多的项目 ✅ 2026-10-21
- [x] 第 5 题：高工作量项目 ✅ 2026-10-21
- [x] 第 6 题：用户创建任务排行榜 ✅ 2026-10-21
- [x] 第 7 题：任务详情与关联信息 ✅ 2026-10-21
- [x] 第 8 题：所有项目任务统计 ✅ 2026-10-21
- [x] 第 9 题：没有任务的项目 ✅ 2026-10-21
- [x] 第 10 题：联合索引执行计划 ✅ 2026-10-21
- [x] 第 11 题：索引与全表扫描实测 ✅ 2026-10-21
- [x] 第 12 题：重复项目成员与唯一约束 ✅ 2026-10-21

---

# 第一关：基础查询

## 第 1 题｜查询未完成的任务 ★☆☆

**业务场景**：任务管理页面需要展示最新创建的未完成任务。

**要求**：

1. 从 `tasks` 表查询 `status = 0` 的任务。
2. 只返回 `id`、`title`、`status`、`created_at` 四列。
3. 按 `created_at` **从新到旧**排序。
4. 只取前 20 条。

**考察**：`SELECT`、`WHERE`、`ORDER BY`、`LIMIT`。

<details>
<summary>🔒 点击展开：参考答案与解析</summary>

```sql
SELECT id, title, status, created_at
FROM tasks
WHERE status = 0
ORDER BY created_at DESC
LIMIT 20;
```

- `ASC` 是升序，日期从早到晚；`DESC` 是降序，日期从晚到早。
- `LIMIT 20` 限制返回 20 条。若相同时间有多条任务，而业务要求顺序稳定，可增加 `id DESC` 作为次级排序。

</details>

---

## 第 2 题｜查询高优先级任务 ★☆☆

**业务场景**：查看某个项目中需要重点处理的任务。

**要求**：

1. `project_id = 100`。
2. `priority >= 3`。
3. `status != 2`。
4. 按 `priority` 降序；**同一优先级按任务 `id` 降序**。
5. 返回前 30 条，允许返回全部字段。

**考察**：复合筛选、比较运算符、多字段排序。

<details>
<summary>🔒 点击展开：参考答案与解析</summary>

```sql
SELECT *
FROM tasks
WHERE project_id = 100
  AND priority >= 3
  AND status != 2
ORDER BY priority DESC, id DESC
LIMIT 30;
```

- `ORDER BY` 可以依次指定多个排序标准。
- 如果把第二排序字段写成 `project_id`，由于已经限定 `project_id = 100`，这个字段在结果中完全相同，不能用于区分先后顺序。
- `priority`、`status` 均允许 `NULL`；SQL 中 `NULL` 不会满足这里的比较条件。

</details>

---

## 第 3 题｜统计任务状态分布 ★☆☆

**业务场景**：统计各任务状态分别有多少条记录。

**要求**：

1. 按 `status` 分组。
2. 输出 `status` 和任务总数 `task_count`。
3. 按 `status` 升序排列。

**预期列**：`status | task_count`。

**考察**：`COUNT(*)`、`GROUP BY`、列别名。

<details>
<summary>🔒 点击展开：参考答案与解析</summary>

```sql
SELECT status, COUNT(*) AS task_count
FROM tasks
GROUP BY status
ORDER BY status ASC;
```

- `GROUP BY status` 把相同状态放在一组。
- `COUNT(*)` 统计每组的行数；即使 `status` 为 `NULL`，对应分组也会被统计。
- `ORDER BY status` 默认升序，因此 `ASC` 可以省略。

</details>

---

# 第二关：聚合统计

## 第 4 题｜找出任务数量最多的 10 个项目 ★★☆

**业务场景**：分析哪些项目的任务量最大。

**要求**：

1. 从 `tasks` 表按 `project_id` 分组。
2. 输出 `project_id` 和 `task_count`。
3. 按 `task_count` 降序。
4. 取前 10 个。

**考察**：聚合、分组、按聚合别名排序。

<details>
<summary>🔒 点击展开：参考答案与解析</summary>

```sql
SELECT project_id, COUNT(*) AS task_count
FROM tasks
GROUP BY project_id
ORDER BY task_count DESC
LIMIT 10;
```

- `GROUP BY` 的结果是**每个项目一行**，不再是每个任务一行。
- `task_count` 是通过 `AS` 定义的列别名，可以用于 `ORDER BY`。
- 由于当前 `tasks.project_id` 允许 `NULL`，可能出现 `project_id IS NULL` 的分组。如果只统计有项目 ID 的任务，可以先写 `WHERE project_id IS NOT NULL`。

</details>

---

## 第 5 题｜查询工作量较大的项目 ★★☆

**业务场景**：寻找任务很多、且平均优先级较高的项目。

**要求**：

1. 按 `project_id` 分组。
2. 任务数量 **大于 1000**。
3. 平均任务优先级 **大于 2**。
4. 输出 `project_id`、`task_count`、`avg_priority`。
5. 按任务数量降序。

**考察**：`COUNT(*)`、`AVG()`、`HAVING`，以及 `WHERE` 与 `HAVING` 的区别。

<details>
<summary>🔒 点击展开：参考答案与解析</summary>

```sql
SELECT
    project_id,
    COUNT(*) AS task_count,
    AVG(priority) AS avg_priority
FROM tasks
GROUP BY project_id
HAVING COUNT(*) > 1000
   AND AVG(priority) > 2
ORDER BY task_count DESC;
```

**为什么用 `HAVING`？**

- `WHERE` 在分组**之前**筛选单条任务。
- `GROUP BY` 将剩余记录分组。
- `HAVING` 在分组**之后**筛选聚合结果，因此适合判断 `COUNT(*) > 1000`。

`AVG(priority)` 忽略 `NULL`；但 `COUNT(*)` 仍包括这些记录。如果题目要求“平均值把缺失优先级当作 0”，需要另外明确业务规则，而不是默认这样处理。

</details>

---

## 第 6 题｜统计每个用户创建的任务数量 ★★☆

**业务场景**：给管理员展示用户创建任务排行榜。

**要求**：

1. 关联 `users`、`tasks`。
2. 使用 `tasks.creator_id` 匹配 `users.id`。
3. 输出 `user_id`、`username`、`task_count`。
4. 任务为 0 的用户也要能够出现在统计中。
5. 按任务数降序，返回前 20 个用户。

**考察**：`LEFT JOIN`、`GROUP BY`、`COUNT(*)` 和 `COUNT(列名)` 的区别。

<details>
<summary>🔒 点击展开：参考答案与解析</summary>

```sql
SELECT
    u.id AS user_id,
    u.username,
    COUNT(t.id) AS task_count
FROM users AS u
LEFT JOIN tasks AS t
    ON t.creator_id = u.id
GROUP BY u.id, u.username
ORDER BY task_count DESC, u.id ASC
LIMIT 20;
```

**为什么必须注意 `COUNT(t.id)`？**

`LEFT JOIN` 会保留没有任务的用户，并产生一行右侧字段都是 `NULL` 的结果。此时：

- `COUNT(*)` 会把这行也算进去，可能误报为 1。
- `COUNT(t.id)` 只统计非 `NULL` 的任务主键，没任务的用户计数就是 0。

补充：由于最后有 `LIMIT 20`，不是保证每一个“任务为 0”的用户都出现在**前 20 名**，而是保证这些用户属于完整统计结果，不会因为连接方式被排除。

</details>

---

# 第三关：真实业务多表查询

## 第 7 题｜查询任务详情及其所属项目、创建人 ★★★

**业务场景**：任务列表不仅显示 ID，还要显示项目名称和创建人用户名。

**要求**：

1. 关联 `tasks`、`projects`、`users` 三张表。
2. `tasks.project_id` 对应 `projects.id`。
3. `tasks.creator_id` 对应 `users.id`。
4. 只查 `tasks.status = 1`。
5. 输出：`task_id`、`task_title`、`project_name`、`creator_name`、`status`。
6. 按任务 `id` 倒序，取前 20 条。
7. 本题练习 `INNER JOIN`。

**考察**：三表连接、表别名、字段歧义。

<details>
<summary>🔒 点击展开：参考答案与解析</summary>

```sql
SELECT
    t.id AS task_id,
    t.title AS task_title,
    p.name AS project_name,
    u.username AS creator_name,
    t.status
FROM tasks AS t
INNER JOIN projects AS p
    ON t.project_id = p.id
INNER JOIN users AS u
    ON t.creator_id = u.id
WHERE t.status = 1
ORDER BY t.id DESC
LIMIT 20;
```

- `INNER JOIN` 只返回能成功关联到**项目**和**创建人**的任务。
- 使用 `t.id` 而不是直接 `id`，可以消除多表都有同名字段时的歧义。
- 当前数据库没有真正定义外键，因此孤立任务可能不会出现在结果中。若业务要求保留所有任务，可考虑 `LEFT JOIN` 并处理空名称。

</details>

---

## 第 8 题｜显示所有项目及其任务数量 ★★★

**业务场景**：项目总览页面即使是空项目，也必须显示。

**要求**：

1. 从 `projects` 开始查询，关联 `tasks`。
2. 输出：`project_id`、`project_name`、`task_count`。
3. 没有任务的项目仍需展示，计数为 0。
4. 按项目 `id` 升序取前 30 个项目。

**考察**：`LEFT JOIN`、正确统计 0 条任务的情况。

<details>
<summary>🔒 点击展开：参考答案与解析</summary>

```sql
SELECT
    p.id AS project_id,
    p.name AS project_name,
    COUNT(t.id) AS task_count
FROM projects AS p
LEFT JOIN tasks AS t
    ON t.project_id = p.id
GROUP BY p.id, p.name
ORDER BY p.id ASC
LIMIT 30;
```

- 主表是 `projects`，才能保留**所有项目**，包括没有任务的项目。
- 对右表非空主键 `t.id` 计数，空项目得到 0。
- 与第 4 题不同：第 4 题只从 `tasks` 分组，没有任务的项目根本无法出现。

</details>

---

## 第 9 题｜找出没有任何任务的项目 ★★★

**业务场景**：清理或检查从未创建任务的空项目。

**要求**：

1. 输出 `project_id`、`project_name`。
2. 仅返回没有任何任务的项目。
3. 不限制项目状态。

**考察**：反连接模式 `LEFT JOIN ... IS NULL` 或 `NOT EXISTS`。

<details>
<summary>🔒 点击展开：参考答案与解析</summary>

**解法 A：`LEFT JOIN + IS NULL`**

```sql
SELECT
    p.id AS project_id,
    p.name AS project_name
FROM projects AS p
LEFT JOIN tasks AS t
    ON t.project_id = p.id
WHERE t.id IS NULL;
```

**解法 B：`NOT EXISTS`**

```sql
SELECT
    p.id AS project_id,
    p.name AS project_name
FROM projects AS p
WHERE NOT EXISTS (
    SELECT 1
    FROM tasks AS t
    WHERE t.project_id = p.id
);
```

- `NOT EXISTS` 判断“是否不存在任何符合条件的任务”，表达业务含义很清晰。
- `NOT EXISTS` 的子查询 `SELECT 1` 表示只关心有没有行，不需要获取任务字段。
- 两种写法的具体执行效率要通过 `EXPLAIN ANALYZE` 验证，不能简单说某一种永远更快。

</details>

---

# 第四关：索引与性能优化

## 第 10 题｜验证联合索引的使用情况 ★★★

你的 `tasks` 表有两个索引：

```sql
idx_project_id(project_id)
idx_project_status(project_id, status)
```

**要求**：分别运行下列 SQL，记录 `type`、`possible_keys`、`key`、`rows` 等字段。

**A：仅按项目查询**

```sql
EXPLAIN
SELECT * FROM tasks
WHERE project_id = 100;
```

**B：同时按项目和状态查询**

```sql
EXPLAIN
SELECT * FROM tasks
WHERE project_id = 100
  AND status = 1;
```

**C：仅按状态查询**

```sql
EXPLAIN
SELECT * FROM tasks
WHERE status = 1;
```

**思考**：

1. A、B、C 分别使用了什么索引？
2. 为什么 B 通常更容易充分利用 `(project_id, status)`？
3. C 是否**一定**不能使用该联合索引？

<details>
<summary>🔒 点击展开：参考答案与解析</summary>

**答案重点不是预先写死 `key` 名称，而是解释实际执行计划。**优化器会基于统计信息、数据分布和查询方式选择计划。

- **A**：通常可以使用 `idx_project_id`，也可能选择具有相同最左前缀的 `idx_project_status`。
- **B**：通常适合 `idx_project_status`，因为查询同时对它的两个前导列提出等值条件。
- **C**：缺少联合索引最左侧的 `project_id` 条件，通常不能像 B 那样直接定位一个连续的小范围。**但这不等于绝对无法用索引**：在适当条件下，优化器可能选择索引跳跃扫描（Skip Scan），也可能走全表扫描。

`EXPLAIN` 的关注点：

| 列 | 解释 |
| --- | --- |
| `type` | 表访问方式，例如 `ALL`（全表扫描）、`ref`（索引等值查找） |
| `possible_keys` | 优化器认为可能相关的索引 |
| `key` | 本次实际选择的索引，`NULL` 代表未选用相应索引 |
| `rows` | 优化器估算需要检查的行数，不是准确的实际行数 |

你以前的测试中，`SELECT COUNT(*) WHERE status = 1` 就观察过覆盖索引跳跃扫描；但 `COUNT(*)` 和 `SELECT *` 的执行计划可能不同，不能直接混为一谈。

</details>

---

## 第 11 题｜对比使用索引与忽略索引的耗时 ★★★

**业务场景**：性能优化需要证据，而不是“我觉得加了索引就很快”。

**要求**：

1. 两条 SQL 都查询 `project_id = 100` 的全部任务。
2. 第一条允许优化器使用索引。
3. 第二条忽略 `idx_project_id`、`idx_project_status`。
4. 使用 `EXPLAIN ANALYZE` 比较真实执行方式、耗时和输出行数。
5. 解释为什么返回相同结果，耗时却可能明显不同。

<details>
<summary>🔒 点击展开：参考答案与解析</summary>

**允许使用索引：**

```sql
EXPLAIN ANALYZE
SELECT *
FROM project_management.tasks
WHERE project_id = 100;
```

**忽略两个已知的相关索引：**

```sql
EXPLAIN ANALYZE
SELECT *
FROM project_management.tasks
IGNORE INDEX (idx_project_id, idx_project_status)
WHERE project_id = 100;
```

**结果解释：**

- `Index lookup ... using idx_project_id`：可通过 B+Tree 定位 `project_id = 100` 对应记录。
- `Table scan on tasks`：需要遍历表记录，再筛选符合条件的任务。
- `actual time = 起始时间..结束时间`：本节点产生第一条输出到完成输出的实测时间（毫秒）。
- `actual ... rows`：实际输出行数；`loops`：执行次数。存在多次循环时，解读总耗时要结合循环次数。
- `cost`：优化器估计的相对成本，**单位不是毫秒**。

**你之前的一组实测结果（不是固定答案）：**

| 方式 | 约耗时 | 结果数 |
| --- | ---: | ---: |
| 忽略相关索引，走表扫描 | 568 ms | 1,027 |
| 使用 `idx_project_id` 索引查找 | 2.02 ms | 1,027 |

单次测试约有 **281 倍**差距。但实际倍率受缓存、并发、硬件、数据分布、SQL 写法影响。建议多运行几轮再比较。

`IGNORE INDEX` 只是当前 SQL 的索引提示，**不会删除索引**；它也不保证排除表上其他所有索引。

</details>

---

## 第 12 题｜查找重复成员，并设计唯一约束 ★★★

当前表结构的关键部分：

```sql
CREATE TABLE project_members (
    id BIGINT NOT NULL AUTO_INCREMENT,
    project_id BIGINT DEFAULT NULL,
    user_id BIGINT DEFAULT NULL,
    role VARCHAR(50) DEFAULT NULL,
    PRIMARY KEY (id)
);
```

**业务规则**：同一个用户不能重复加入同一个项目。

**要求**：

1. 查出所有重复的 `(project_id, user_id)` 组合。
2. 返回 `project_id`、`user_id`、`duplicate_count`。
3. 思考应该使用什么索引/约束保证业务唯一性。

**考察**：`GROUP BY`、`HAVING`、联合唯一索引、`NULL` 的特殊性。

<details>
<summary>🔒 点击展开：参考答案与解析</summary>

**第一步：查找重复组合（只读）：**

```sql
SELECT
    project_id,
    user_id,
    COUNT(*) AS duplicate_count
FROM project_members
GROUP BY project_id, user_id
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;
```

**第二步：检查空值（只读）：**

```sql
SELECT *
FROM project_members
WHERE project_id IS NULL
   OR user_id IS NULL;
```

**第三步：讨论如何增加约束（示例，先不要执行）：**

```sql
-- 确认重复数据和 NULL 数据已被妥善处理后，才考虑：
ALTER TABLE project_members
    MODIFY project_id BIGINT NOT NULL,
    MODIFY user_id BIGINT NOT NULL,
    ADD CONSTRAINT uk_project_user UNIQUE (project_id, user_id);
```

**关键原因：**

- 联合唯一约束 `UNIQUE(project_id, user_id)` 能限制**同一项目、同一用户**只出现一次。
- MySQL 的 `UNIQUE` 允许多个 `NULL`，仅添加联合唯一索引但仍允许 `NULL`，不能完整落实“成员必须有合法项目 ID 和用户 ID”的要求。
- 对已有非空重复组合建唯一索引会失败；把有空值的字段改成 `NOT NULL` 也会失败。务必先检查、清理或迁移数据，再变更结构。
- 当前 DDL 尚未定义真实外键；唯一约束不能替代外键来保证项目、用户是否存在。

</details>

---

# 五、12 道题背后的知识地图

| 题目 | 主要知识 | 企业中常见用途 |
| --- | --- | --- |
| 1 | WHERE / DESC / LIMIT | 最新任务列表 |
| 2 | 多条件过滤、多字段排序 | 条件筛选 |
| 3 | GROUP BY / COUNT | 状态分布 |
| 4 | 聚合结果排序 | 项目排行榜 |
| 5 | AVG / HAVING | 聚合后的业务筛选 |
| 6 | LEFT JOIN / COUNT(列) | 用户工作量统计 |
| 7 | 多表 INNER JOIN | 列表关联显示 |
| 8 | LEFT JOIN / 零条计数 | 项目总览 |
| 9 | NOT EXISTS / 反连接 | 检查空项目 |
| 10 | 联合索引、最左前缀、Skip Scan | 查询计划分析 |
| 11 | EXPLAIN ANALYZE / IGNORE INDEX | SQL 性能实验 |
| 12 | GROUP BY / HAVING / UNIQUE | 数据质量与完整性 |

## 做完后的自检标准

- [ ] 能根据业务描述独立写出 SQL，而不是只会看答案。
- [ ] 能解释 `WHERE` 和 `HAVING` 的使用时机。
- [ ] 能说清楚 `INNER JOIN` 和 `LEFT JOIN` 的区别。
- [ ] 能解释为什么 `COUNT(t.id)` 可以正确统计 0 条任务。
- [ ] 能看懂 `EXPLAIN` 的 `type`、`key`、`rows`。
- [ ] 知道查询快不快要看实际执行计划，而不是只看是否存在索引。
- [ ] 了解联合唯一索引与 `NULL` 的关系。

> **下一阶段衔接**：把这些 SQL 放入 Node.js + TypeScript 的 Repository 中，通过 `mysql2/promise` 连接池执行，再实现 Controller → Service → Repository → MySQL 的完整调用流程。
