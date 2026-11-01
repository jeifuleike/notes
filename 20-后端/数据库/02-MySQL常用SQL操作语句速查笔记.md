# MySQL 常用 SQL 操作语句速查笔记

> **适用环境**：MySQL 8.4 / MySQL Workbench  
> **学习场景**：`project_management` 项目管理系统  
> **用途**：日常查阅、SQL 练习、后端接口开发前的语法复习  
> **阅读建议**：先掌握 `SELECT / WHERE / JOIN / INSERT / UPDATE / DELETE`，再学习事务、索引和执行计划。

---

## 目录

1. [SQL 语句分类与基本规则](#1-sql-语句分类与基本规则)
2. [数据库和表的查看](#2-数据库和表的查看)
3. [SELECT：查询数据](#3-select查询数据)
4. [WHERE：条件筛选](#4-where条件筛选)
5. [ORDER BY / LIMIT：排序与分页](#5-order-by--limit排序与分页)
6. [聚合函数、GROUP BY 和 HAVING](#6-聚合函数group-by-和-having)
7. [JOIN：多表关联查询](#7-join多表关联查询)
8. [INSERT：新增数据](#8-insert新增数据)
9. [UPDATE：修改数据](#9-update修改数据)
10. [DELETE / TRUNCATE：删除数据](#10-delete--truncate删除数据)
11. [CREATE / ALTER / DROP：表结构管理](#11-create--alter--drop表结构管理)
12. [索引：创建、查看、删除](#12-索引创建查看删除)
13. [EXPLAIN：分析查询性能](#13-explain分析查询性能)
14. [IGNORE INDEX / FORCE INDEX：索引提示](#14-ignore-index--force-index索引提示)
15. [事务：COMMIT / ROLLBACK](#15-事务commit--rollback)
16. [子查询、CTE 与常用函数](#16-子查询cte-与常用函数)
17. [Node.js 后端调用 SQL 的基本原则](#17-nodejs-后端调用-sql-的基本原则)
18. [常见错误与安全提醒](#18-常见错误与安全提醒)
19. [动手练习：10 道 SQL 小题](#19-动手练习10-道-sql-小题)
20. [一页速查表](#20-一页速查表)

---

## 0. 示例数据与安全说明

你当前的数据库是 `project_management`，其中包括：

```text
project_management
├── users
├── projects
├── project_members
└── tasks
```

从实际操作记录可以确认，`tasks` 至少包含这些字段：

| 字段 | 示例含义 |
| --- | --- |
| `id` | 任务 ID |
| `project_id` | 所属项目 ID |
| `creator_id` | 创建者用户 ID |
| `title` | 任务标题 |
| `status` | 状态数值 |
| `priority` | 优先级数值 |
| `created_at` | 创建时间 |

**注意**：下面的 `tasks` 查询可以针对你的现有数据执行；涉及新增、修改、删除的示例优先使用独立练习表 `sql_practice_tasks`，避免把现有近百万条数据误改掉。`status` 的数字代表什么业务状态，必须以你自己的项目约定为准。

可先执行以下 SQL 创建练习表（不会修改 `tasks`）：

```sql
USE project_management;

CREATE TABLE IF NOT EXISTS sql_practice_tasks (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    project_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(200) NOT NULL,
    status TINYINT UNSIGNED NOT NULL DEFAULT 0,
    priority TINYINT UNSIGNED NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);
```

---

## 1. SQL 语句分类与基本规则

| 分类 | 常见命令 | 用途 |
| --- | --- | --- |
| DQL（查询） | `SELECT` | 读取数据 |
| DML（数据操作） | `INSERT`、`UPDATE`、`DELETE` | 新增、修改、删除数据 |
| DDL（结构定义） | `CREATE`、`ALTER`、`DROP`、`TRUNCATE` | 管理数据库对象或表结构 |
| TCL（事务控制） | `START TRANSACTION`、`COMMIT`、`ROLLBACK` | 控制事务 |
| DCL（权限控制） | `GRANT`、`REVOKE` | 用户权限管理 |

常见规则：

- SQL 通常以 `;` 结束。
- 关键字不区分大小写，推荐使用大写便于阅读。
- 字符串使用单引号，例如 `'task_1'`；标识符需要引用时使用反引号，例如 `` `status` ``。
- `-- `（后面有空格）和 `#` 可写单行注释；`/* ... */` 可写块注释。
- 不能用 `= NULL` 比较空值，应使用 `IS NULL`。
- MySQL 的 `LIMIT` 语法与部分其他数据库不同，本文以 **MySQL** 为准。

```sql
-- 一行注释
SELECT * FROM tasks LIMIT 10;

/* 多行注释
   用于说明查询目的 */
SELECT COUNT(*) FROM tasks;
```

---

## 2. 数据库和表的查看

### 2.1 查看与切换数据库

```sql
SHOW DATABASES;

USE project_management;

SELECT DATABASE();    -- 当前所选数据库
SELECT VERSION();     -- MySQL 版本
```

也可以直接写完整名称，不依赖 `USE`：

```sql
SELECT *
FROM project_management.tasks
LIMIT 10;
```

### 2.2 查看表、字段、建表语句

```sql
SHOW TABLES;

DESCRIBE tasks;
-- 或：
SHOW COLUMNS FROM tasks;

SHOW CREATE TABLE tasks;
```

### 2.3 查看已有索引

```sql
SHOW INDEX FROM tasks;
```

重点看：`Key_name`（索引名称）、`Column_name`（对应字段）、`Seq_in_index`（联合索引中的字段顺序）。

### 2.4 查看会话与自动提交状态

```sql
SELECT @@autocommit;
SHOW FULL PROCESSLIST;
```

`@@autocommit = 1` 通常表示非显式事务中的 DML 每条语句执行成功后自动提交。`SHOW FULL PROCESSLIST` 可以用来排查长时间运行的语句。

---

## 3. SELECT：查询数据

### 3.1 查询所有字段

```sql
SELECT *
FROM tasks
LIMIT 20;
```

`*` 表示全部字段。接口开发中更建议明确写需要的字段。

### 3.2 查询指定字段

```sql
SELECT id, project_id, title, status
FROM tasks
LIMIT 20;
```

### 3.3 使用字段别名和表别名

```sql
SELECT
    t.id AS task_id,
    t.title AS task_title,
    t.status
FROM tasks AS t
LIMIT 20;
```

`AS` 可省略，但建议初学时写清楚。

### 3.4 去重

```sql
SELECT DISTINCT status
FROM tasks;
```

获取出现过的不同状态值，而不是返回每一条任务。

---

## 4. WHERE：条件筛选

### 4.1 比较运算

```sql
-- 等于
SELECT * FROM tasks WHERE project_id = 100 LIMIT 20;

-- 不等于（<> 是标准写法，MySQL 也支持 !=）
SELECT * FROM tasks WHERE status <> 1 LIMIT 20;

-- 大于 / 小于 / 大于等于 / 小于等于
SELECT * FROM tasks WHERE priority >= 3 LIMIT 20;
```

| 运算符 | 含义 |
| --- | --- |
| `=` | 等于 |
| `<>`、`!=` | 不等于 |
| `>`、`<` | 大于、小于 |
| `>=`、`<=` | 大于等于、小于等于 |
| `AND` | 同时满足 |
| `OR` | 任一条件满足 |
| `NOT` | 条件取反 |

### 4.2 多条件组合

```sql
SELECT id, title, status, priority
FROM tasks
WHERE project_id = 100
  AND status = 1
  AND priority >= 3;
```

`AND` 与 `OR` 混合时使用括号，避免误解优先级：

```sql
SELECT *
FROM tasks
WHERE project_id = 100
  AND (status = 1 OR status = 2)
LIMIT 20;
```

### 4.3 IN / NOT IN

```sql
SELECT *
FROM tasks
WHERE status IN (0, 1, 2)
LIMIT 20;

SELECT *
FROM tasks
WHERE status NOT IN (0, 1)
LIMIT 20;
```

注意：集合中如果包含 `NULL`，`NOT IN` 可能产生与直觉不同的结果；复杂查询优先确认空值情况。

### 4.4 BETWEEN

```sql
SELECT *
FROM tasks
WHERE priority BETWEEN 2 AND 4
LIMIT 20;
```

`BETWEEN` **包含两个边界值**。

### 4.5 LIKE：模糊匹配

```sql
-- 以 task_ 开头（下划线在 LIKE 中是单字符通配符，
-- 此写法仅作宽泛匹配示例）
SELECT * FROM tasks WHERE title LIKE 'task%' LIMIT 20;

-- 包含关键字
SELECT * FROM tasks WHERE title LIKE '%123%' LIMIT 20;
```

- `%`：匹配任意长度的字符（包括零个）。
- `_`：匹配任意一个字符。
- `LIKE '%关键字%'` 这类前置通配符查询，普通 B+Tree 索引往往难以高效利用。

### 4.6 NULL 判断

```sql
SELECT * FROM tasks WHERE title IS NULL;
SELECT * FROM tasks WHERE title IS NOT NULL;
```

`NULL` 表示缺失/未知，不等于 `0`，也不等于空字符串 `''`。

### 4.7 时间区间查询

```sql
SELECT id, title, created_at
FROM tasks
WHERE created_at >= '2026-10-01 00:00:00'
  AND created_at <  '2026-11-01 00:00:00';
```

建议用左闭右开区间 `>= 起始 AND < 下月起始`，避免漏掉一天内带有时间部分的数据。

---

## 5. ORDER BY / LIMIT：排序与分页

### 5.1 升序、降序

```sql
-- 最新任务在前
SELECT id, title, created_at
FROM tasks
ORDER BY created_at DESC, id DESC
LIMIT 20;

-- 优先级从低到高
SELECT id, title, priority
FROM tasks
ORDER BY priority ASC, id ASC
LIMIT 20;
```

- `ASC`：升序（默认）。
- `DESC`：降序。
- 多个排序字段可使排序更稳定，例如时间相同时再按 `id` 排序。

### 5.2 分页

```sql
-- 第 1 页，每页 20 条
SELECT * FROM tasks ORDER BY id LIMIT 20 OFFSET 0;

-- 第 2 页，每页 20 条
SELECT * FROM tasks ORDER BY id LIMIT 20 OFFSET 20;

-- MySQL 另一种写法：LIMIT 偏移量, 行数
SELECT * FROM tasks ORDER BY id LIMIT 20, 20;
```

页码与偏移量的关系：`OFFSET = (页码 - 1) × 每页条数`。

**重要**：一定要配合 `ORDER BY`；否则“第一页”和“第二页”的记录顺序不可靠。大偏移量分页也可能越来越慢。

### 5.3 游标式分页（大数据量常用）

```sql
SELECT id, title
FROM tasks
WHERE id > 100000
ORDER BY id
LIMIT 20;
```

用于“下一页”时只需记住上一页最后一条 `id`，但这种方式不适合任意跳转到第 N 页。

---

## 6. 聚合函数、GROUP BY 和 HAVING

### 6.1 COUNT / SUM / AVG / MIN / MAX

```sql
-- 任务总数
SELECT COUNT(*) AS task_count FROM tasks;

-- 各种优先级的统计值（示例）
SELECT
    COUNT(*) AS total_tasks,
    SUM(priority) AS priority_sum,
    AVG(priority) AS priority_avg,
    MIN(priority) AS min_priority,
    MAX(priority) AS max_priority
FROM tasks;
```

区别：

- `COUNT(*)`：计数所有行。
- `COUNT(字段)`：只统计该字段非 `NULL` 的行。
- `COUNT(DISTINCT 字段)`：统计不同非空值的数量。

```sql
SELECT COUNT(DISTINCT project_id) AS project_count
FROM tasks;
```

### 6.2 GROUP BY：按状态统计

```sql
SELECT status, COUNT(*) AS task_count
FROM tasks
GROUP BY status
ORDER BY status;
```

**核心概念**：先按 `status` 分组，再对每一组计算数量。

### 6.3 分组后筛选 HAVING

```sql
SELECT project_id, COUNT(*) AS task_count
FROM tasks
WHERE status = 1
GROUP BY project_id
HAVING COUNT(*) >= 100
ORDER BY task_count DESC
LIMIT 20;
```

- `WHERE`：**分组前**筛选行。
- `HAVING`：**分组后**筛选组。

这个查询表示：统计每个项目中状态为 `1` 的任务，仅保留数量至少 100 的项目。

---

## 7. JOIN：多表关联查询

> 以下示例假定 `projects` 存在 `id`、`name` 字段；如果你的实际表结构不同，先运行 `DESCRIBE projects;` 查看后调整。

### 7.1 INNER JOIN：两表都匹配才返回

```sql
SELECT
    t.id AS task_id,
    t.title,
    p.name AS project_name
FROM tasks AS t
INNER JOIN projects AS p
    ON t.project_id = p.id
WHERE t.status = 1
LIMIT 20;
```

可以理解为：通过 `tasks.project_id = projects.id` 找到任务所属项目。

### 7.2 LEFT JOIN：保留左表记录

```sql
SELECT
    p.id AS project_id,
    p.name,
    t.id AS task_id,
    t.title
FROM projects AS p
LEFT JOIN tasks AS t
    ON t.project_id = p.id
WHERE p.id = 100;
```

即使项目没有任务，项目本身仍会出现在结果中，此时任务字段为 `NULL`。

### 7.3 用中间表查询多对多关系

```sql
-- 查询用户 ID = 10 参与的项目 ID
SELECT pm.project_id, pm.user_id
FROM project_members AS pm
WHERE pm.user_id = 10;
```

```sql
-- 如果要拿到项目名称，再关联 projects
SELECT p.id, p.name
FROM project_members AS pm
JOIN projects AS p
    ON p.id = pm.project_id
WHERE pm.user_id = 10;
```

**注意**：一对多 JOIN 可能让项目行重复出现，这是关联结果的正常现象，不等于数据库出现重复数据。

---

## 8. INSERT：新增数据

为避免修改实际 `tasks`，下面使用 `sql_practice_tasks`。

### 8.1 插入一条

```sql
INSERT INTO sql_practice_tasks (project_id, title, status, priority)
VALUES (100, '学习 INSERT', 0, 2);
```

### 8.2 一次插入多条（比循环逐条执行更高效）

```sql
INSERT INTO sql_practice_tasks (project_id, title, status, priority)
VALUES
    (100, '任务 A', 0, 1),
    (100, '任务 B', 1, 3),
    (101, '任务 C', 2, 4);
```

### 8.3 默认值与自动增长 ID

未写入 `id` 时由 `AUTO_INCREMENT` 分配；未写入 `created_at` 时使用 `CURRENT_TIMESTAMP` 默认值。

```sql
SELECT LAST_INSERT_ID();
```

`LAST_INSERT_ID()` 可获取**当前连接**最近一次相关自增插入产生的 ID；应用中使用连接池时要注意连接归属。

### 8.4 插入前检查约束

实际业务中，唯一索引、外键、`NOT NULL` 等约束可能让 INSERT 失败，这是数据库保护数据一致性的正常机制。

---

## 9. UPDATE：修改数据

### 9.1 按 ID 修改

```sql
UPDATE sql_practice_tasks
SET status = 1
WHERE id = 1;
```

### 9.2 同时修改多个字段

```sql
UPDATE sql_practice_tasks
SET title = '更新后的任务',
    status = 2,
    priority = 4
WHERE id = 1;
```

### 9.3 修改前先查询

```sql
SELECT * FROM sql_practice_tasks WHERE id = 1;
```

**危险写法**：

```sql
-- 不要对真实业务表随便执行！
-- UPDATE tasks SET status = 2;
```

没有 `WHERE` 时，会更新整张表；但也要注意 `WHERE` 写错仍可能误更新很多行。生产修改前应确认影响范围，并视场景使用事务和备份。

---

## 10. DELETE / TRUNCATE：删除数据

### 10.1 DELETE 指定记录

```sql
DELETE FROM sql_practice_tasks
WHERE id = 1;
```

### 10.2 删除符合条件的练习记录

```sql
DELETE FROM sql_practice_tasks
WHERE status = 2;
```

删除前先运行相同条件的 `SELECT`：

```sql
SELECT * FROM sql_practice_tasks WHERE status = 2;
```

### 10.3 DELETE 和 TRUNCATE 的区别

| 操作 | `DELETE FROM 表` | `TRUNCATE TABLE 表` |
| --- | --- | --- |
| 删除范围 | 可按 `WHERE` 删除 | 清空整表 |
| 命令分类 | DML | MySQL 中属于 DDL |
| InnoDB 显式事务 | 通常可以回滚 | 会隐式提交，不能像普通 DELETE 一样回滚 |
| 自增计数 | 通常不重置 | 通常重置 |
| 外键限制 | 按约束检查 | 被外键引用时可能不允许执行 |

```sql
-- 仅对你不再需要的独立练习表操作：
-- TRUNCATE TABLE sql_practice_tasks;
```

**警告**：不要对已有近百万条任务的 `tasks` 表运行 `TRUNCATE`，除非明确要清空且已做好数据备份。

---

## 11. CREATE / ALTER / DROP：表结构管理

### 11.1 创建数据库

```sql
CREATE DATABASE IF NOT EXISTS demo_database
CHARACTER SET utf8mb4;
```

### 11.2 创建表

本笔记开头已创建 `sql_practice_tasks`。下面是结构定义的常用元素：

```sql
CREATE TABLE IF NOT EXISTS demo_categories (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_category_name (name)
);
```

- `NOT NULL`：不允许 `NULL`。
- `DEFAULT`：默认值。
- `AUTO_INCREMENT`：自增。
- `PRIMARY KEY`：主键。
- `UNIQUE KEY`：唯一性约束/索引。

### 11.3 增加字段

```sql
ALTER TABLE sql_practice_tasks
ADD COLUMN remark VARCHAR(200) NULL;
```

### 11.4 修改字段类型或重命名

```sql
ALTER TABLE sql_practice_tasks
MODIFY COLUMN remark VARCHAR(500) NULL;

ALTER TABLE sql_practice_tasks
RENAME COLUMN remark TO description;
```

修改列名或类型前要检查后端代码、索引和依赖，实际项目应记录为 Migration，而不是仅在 Workbench 手工改线上表。

### 11.5 删除列、表

```sql
-- 危险操作；仅演示语法：
-- ALTER TABLE sql_practice_tasks DROP COLUMN description;
-- DROP TABLE IF EXISTS demo_categories;
```

`DROP TABLE` 会删除表结构和表中数据。DDL 在 MySQL 中通常触发隐式提交，不能假设包进事务就一定能回滚。

---

## 12. 索引：创建、查看、删除

### 12.1 查看表的索引

```sql
SHOW INDEX FROM tasks;
```

### 12.2 创建单列索引

```sql
CREATE INDEX idx_practice_project_id
ON sql_practice_tasks(project_id);
```

### 12.3 创建联合索引

```sql
CREATE INDEX idx_practice_project_status
ON sql_practice_tasks(project_id, status);
```

联合索引字段的**排列顺序**很重要，常见查询：

```sql
WHERE project_id = 100

WHERE project_id = 100 AND status = 1
```

通常更容易利用 `(project_id, status)` 这个索引。

只使用 `WHERE status = 1` 时，一般不能像从最左列开始那样高效定位，但 MySQL 某些情况下可能选择 **Index Skip Scan（跳跃扫描）** 等访问策略；不能把“最左前缀”理解为不符合就绝对不会用索引。

### 12.4 删除索引

```sql
DROP INDEX idx_practice_project_id
ON sql_practice_tasks;
```

注意：索引名称不等于字段名称；`idx_practice_project_id` 是索引名，`project_id` 才是表字段名。

---

## 13. EXPLAIN：分析查询性能

### 13.1 只查看预计执行计划

```sql
EXPLAIN
SELECT *
FROM tasks
WHERE project_id = 100;
```

关注：

| 字段 | 意思 |
| --- | --- |
| `type` | 访问方式，如 `ALL`、`ref` |
| `possible_keys` | 优化器认为可能使用的索引 |
| `key` | 最终选择的索引 |
| `rows` | 预计检查的行数（估算值） |
| `Extra` | 附加执行信息，例如 `Using where` |

`type = ALL` 常代表全表扫描；`key = NULL` 表示此节点未选择索引。但**全表扫描不等于一定慢**，要结合表大小和查询选择性。

### 13.2 实际执行并查看耗时

```sql
EXPLAIN ANALYZE
SELECT *
FROM tasks
WHERE project_id = 100;
```

可能看到：

```text
Index lookup on tasks using idx_project_id (project_id=100)
(actual time=0.236..2.02 rows=1027 loops=1)
```

解读：

- `Index lookup`：通过索引查找。
- `actual time=0.236..2.02`：此执行节点从产出第一条结果到产出最后结果的时间信息，单位毫秒。
- `rows=1027`：该节点实际输出约 1027 行。
- `loops=1`：该节点执行了一次。
- `cost`：优化器使用的**相对成本单位**，不是毫秒。

`EXPLAIN ANALYZE` **确实会执行查询**，不能把它当作只查看计划；分析修改性语句时尤其需要谨慎。

### 13.3 为什么有时全表扫描也快？

对 `WHERE status = 1` 而言，如果匹配全表约三分之一的记录，而查询还需要 `SELECT *`，走二级索引可能需要大量回表，优化器就可能认为全表扫描更划算。

对 `WHERE project_id = 100` 而言，如果只匹配约 1000 条，在百万行数据里通常更适合走索引。

---

## 14. IGNORE INDEX / FORCE INDEX：索引提示

你前面实验过这组语句：

```sql
-- 正常：让优化器自主选择索引
EXPLAIN ANALYZE
SELECT *
FROM project_management.tasks
WHERE project_id = 100;
```

```sql
-- 实验：不允许使用指定的两个索引
EXPLAIN ANALYZE
SELECT *
FROM project_management.tasks
IGNORE INDEX (idx_project_id, idx_project_status)
WHERE project_id = 100;
```

`IGNORE INDEX` 影响的是**当前 SQL 的索引选择**，**不会删除索引或改动表结构**。如果还有其他可用索引，优化器仍可选择其他索引。

其他两种提示：

```sql
-- 提示优化器使用所列索引作为候选
SELECT * FROM tasks USE INDEX (idx_project_id)
WHERE project_id = 100;

-- 强烈倾向使用该索引，但不是任何情况下都绝对强制
SELECT * FROM tasks FORCE INDEX (idx_project_id)
WHERE project_id = 100;
```

**建议**：正常业务优先让优化器选择；索引提示更适合调试、对照测试和经过验证的特殊场景。

---

## 15. 事务：COMMIT / ROLLBACK

### 15.1 一个可回滚的练习

```sql
START TRANSACTION;

UPDATE sql_practice_tasks
SET status = 2
WHERE project_id = 100;

-- 检查本事务中的修改
SELECT *
FROM sql_practice_tasks
WHERE project_id = 100;

-- 放弃修改
ROLLBACK;
```

如果确认业务修改正确，应使用：

```sql
START TRANSACTION;

UPDATE sql_practice_tasks
SET priority = 4
WHERE project_id = 100;

COMMIT;
```

### 15.2 什么情况下要事务？

例如同一个业务操作需要：

1. 创建项目记录；
2. 写入项目创建者的成员记录；
3. 两步必须同时成功或同时失败。

这类跨多条 SQL 的一致性要求，适合用事务控制。

### 15.3 必须记住的边界

- 事务主要保护一组数据库操作的原子性等性质，前提是存储引擎支持事务（例如 InnoDB）。
- 事务内执行 DDL（如大部分 `ALTER TABLE`、`TRUNCATE`）可能发生**隐式提交**。
- `ROLLBACK` 不能撤销已经成功 `COMMIT` 的修改。
- Node.js 使用连接池时，同一事务中的 SQL 必须在**同一数据库连接**上执行。

---

## 16. 子查询、CTE 与常用函数

### 16.1 子查询

```sql
-- 找到任务数量大于 500 的项目 ID
SELECT project_id, COUNT(*) AS task_count
FROM tasks
GROUP BY project_id
HAVING COUNT(*) > 500;
```

也可以把子查询放在 `IN` 中：

```sql
SELECT id, title, project_id
FROM tasks
WHERE project_id IN (
    SELECT project_id
    FROM tasks
    GROUP BY project_id
    HAVING COUNT(*) > 500
)
LIMIT 20;
```

这种写法仅用于演示子查询，实际大数据场景可能需要优化。

### 16.2 CTE：WITH 临时命名查询结果

```sql
WITH task_stats AS (
    SELECT project_id, COUNT(*) AS task_count
    FROM tasks
    GROUP BY project_id
)
SELECT project_id, task_count
FROM task_stats
WHERE task_count > 500
ORDER BY task_count DESC
LIMIT 20;
```

CTE 让复杂 SQL 更易读；不等于数据库一定会先生成一个永久表。

### 16.3 常见函数

```sql
-- 当前日期时间
SELECT NOW(), CURDATE(), CURTIME();

-- 日期格式化
SELECT DATE_FORMAT(NOW(), '%Y-%m-%d %H:%i:%s');

-- 当值为 NULL 时使用默认值
SELECT COALESCE(NULL, '默认文本');

-- 字符串拼接
SELECT CONCAT('task_', 100);

-- 四舍五入
SELECT ROUND(3.14159, 2);
```

注意：对索引列直接包裹某些函数可能影响索引的高效使用，例如 `WHERE DATE(created_at) = '2026-10-13'` 通常不如使用原字段的时间范围判断。

---

## 17. Node.js 后端调用 SQL 的基本原则

你后续学习 `Express + TypeScript + mysql2` 时，SQL 不应依赖在 Workbench 中手动执行，而应由后端 Repository 负责访问数据库。

### 17.1 使用参数化查询

```ts
// 示例：mysql2/promise 数据库连接池 pool 已经创建
const [rows] = await pool.execute(
  `SELECT id, title, status
   FROM tasks
   WHERE project_id = ? AND status = ?
   ORDER BY id DESC
   LIMIT 20`,
  [100, 1]
);
```

这里的 `?` 是 SQL 值参数占位符。**不能把用户输入直接拼成 SQL 字符串**：

```ts
// 不安全示例：容易造成 SQL 注入
const sql = `SELECT * FROM tasks WHERE title = '${userInput}'`;
```

另外，表名和字段名通常不能简单用 `?` 参数化，动态标识符需要服务端白名单校验。

### 17.2 在 Repository 中管理 SQL

```text
HTTP Request
    ↓
Router / Controller
    ↓
Service（业务规则）
    ↓
Repository（SQL 查询）
    ↓
MySQL Connection Pool
    ↓
MySQL
```

**记忆方式**：SQL 描述“怎么查/改数据”；Repository 组织数据访问；Service 决定“为什么允许这次操作”。

---

## 18. 常见错误与安全提醒

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `ERROR 1046 No database selected` | 没有选中数据库 | `USE project_management;` 或写完整库名 |
| 查询结果只显示 1000 行 | Workbench 常见的结果限制 | 查看 GUI 行数限制；需要时显式使用 `LIMIT` |
| `Unknown column` | 字段名错误或不在当前查询作用域 | `DESCRIBE 表名;` |
| `Duplicate entry` | 违反唯一索引或主键 | 检查主键和唯一键 |
| 外键插入失败 | 被引用记录不存在或字段定义不匹配 | 检查 FK 与关联数据 |
| `key = NULL` | 当前执行计划未使用索引 | 结合 `EXPLAIN` 检查原因，不要立即盲目建索引 |
| MySQL 执行很久 | 查询、锁等待或逐行插入效率低 | 查看执行计划、批量操作、检查事务或进程列表 |
| UPDATE/DELETE 影响行数异常 | `WHERE` 缺失或条件错误 | 先 `SELECT` 验证，必要时使用事务 |

### 长时间运行查询的排查

```sql
SHOW FULL PROCESSLIST;
```

如果确认需要取消某个会话正在运行的查询，可以从**另一个连接**中执行：

```sql
-- 替换为实际查到的连接 ID；不要盲目执行
-- KILL QUERY 12345;
```

`KILL QUERY` 通常只取消正在运行的语句，不会撤销之前已经自动提交成功的 INSERT；这也是此前批量生成测试数据时需要注意的地方。

---

## 19. 动手练习：10 道 SQL 小题

建议自己先写 SQL，再对照相应章节。前 8 题全部只读，不会修改数据。

1. 查询 `tasks` 中前 20 条任务的 `id`、`title`、`status`。
2. 查询 `project_id = 100` 且 `status = 1` 的任务。
3. 将某项目任务按 `created_at` 从新到旧排序。
4. 统计每个 `status` 对应的任务数量。
5. 找出任务数量超过 1000 的项目 ID。
6. 查询状态为 `1`、优先级至少 `3` 的任务前 20 条。
7. 使用 `JOIN` 查询任务标题及所属项目名称（先确认 `projects.name` 存在）。
8. 对 `WHERE project_id = 100` 执行 `EXPLAIN` 和 `EXPLAIN ANALYZE`，观察 `key`、预计行数、实际耗时。
9. 在 `sql_practice_tasks` 插入三条不同状态的练习任务，再查询检查结果。
10. 开启事务，修改练习任务状态，查询确认后执行 `ROLLBACK`，检查是否恢复。

---

## 20. 一页速查表

| 想做什么 | 常用语句 |
| --- | --- |
| 切换数据库 | `USE project_management;` |
| 查看所有表 | `SHOW TABLES;` |
| 看表结构 | `DESCRIBE tasks;` |
| 看建表 SQL | `SHOW CREATE TABLE tasks;` |
| 查询数据 | `SELECT ... FROM ...;` |
| 按条件筛选 | `WHERE ...` |
| 多条件 | `AND / OR / IN / BETWEEN / LIKE` |
| 空值判断 | `IS NULL / IS NOT NULL` |
| 排序 | `ORDER BY ... ASC/DESC` |
| 分页 | `LIMIT 20 OFFSET 40` |
| 去重 | `DISTINCT` |
| 统计总数 | `COUNT(*)` |
| 分组 | `GROUP BY` |
| 筛选分组结果 | `HAVING` |
| 关联其他表 | `JOIN ... ON ...` |
| 插入 | `INSERT INTO ... VALUES ...` |
| 修改 | `UPDATE ... SET ... WHERE ...` |
| 删除行 | `DELETE FROM ... WHERE ...` |
| 新建表 | `CREATE TABLE ...` |
| 增改字段 | `ALTER TABLE ...` |
| 看索引 | `SHOW INDEX FROM ...` |
| 建索引 | `CREATE INDEX ... ON ...` |
| 查看预计执行计划 | `EXPLAIN SELECT ...` |
| 测量真实查询执行 | `EXPLAIN ANALYZE SELECT ...` |
| 排除指定索引 | `IGNORE INDEX (...)` |
| 开始事务 | `START TRANSACTION;` |
| 提交事务 | `COMMIT;` |
| 回滚事务 | `ROLLBACK;` |
| 查看运行中的语句 | `SHOW FULL PROCESSLIST;` |

---

## 学习进度衔接

目前已经通过真实数据实践：

- 近百万条 `tasks` 数据的 SQL 查询；
- `WHERE project_id = 100` 的索引检索；
- `EXPLAIN` 和 `EXPLAIN ANALYZE`；
- `IGNORE INDEX` 对照全表扫描与索引查询；
- 理解为什么不同 SQL 即使条件相同，也可能选择不同的执行计划。

**下一阶段**：`Node.js + TypeScript + mysql2/promise` → 连接池 → Repository → 事务处理 → Express 项目接口开发。

> **最后的安全底线**：真实业务数据上，先 `SELECT` 确认范围，再考虑 `UPDATE` / `DELETE`；线上表结构变更使用 Migration、备份和审核流程，别把 Workbench 当成“随手点一下就能撤销”的文本编辑器。


## 相关原理与实践

本篇侧重 SQL 语句速查；索引结构、排序与维护见 [[20-后端/数据库/03-MySQL索引核心知识整理]]，提交、内存数据页和刷盘见 [[20-后端/数据库/04-InnoDB事务提交与刷盘]]，章节代码和验收见 [[20-后端/实践/Node后端学习项目/01-Node后端学习项目]]。
