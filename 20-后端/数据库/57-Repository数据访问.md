# Repository数据访问

补充专题：Repository数据访问。本文为通用学习知识，示例和实验不表示已经执行到项目数据库。项目运行与验收仍在独立代码仓库维护。

## 1. Repository：把表结构转成应用可使用的数据能力

### 1. Repository 负责什么

它集中封装查询、写入、结果映射和数据库访问细节。Service 通过清楚的方法表达业务所需的数据操作，而不用到处拼 SQL。

本学习项目使用 Repository 作为数据访问模块；严格领域建模中的 Repository 还可能提供更贴近领域对象集合的接口，不必为了名称机械引入类。[Repository 模式原始说明](https://martinfowler.com/eaaCatalog/repository.html)

Router / Controller / Service 的完整分工复用 [[20-后端/Express与工程化/02-Express分层架构]]；这里专门讲数据库接口设计。

### 2. 先写输入输出契约

```ts
type ProjectId = number
type UserId = number

type Project = {
  id: ProjectId
  name: string
  ownerId: UserId
  createdAt: Date
}

type ProjectRepository = {
  findById(id: ProjectId): Promise<Project | undefined>
  isMember(projectId: ProjectId, userId: UserId): Promise<boolean>
}
```

这是接口设计示意，不是本仓库待填函数的实现答案。需要提前明确“不存在”返回 undefined、空列表还是抛特定异常，避免调用方依靠猜测。

数据库行的 created_at、API 的 createdAt、JSON 中的时间字符串属于不同边界；不能因为 TypeScript 写了 Date，就假定驱动和 JSON 自动符合全部约定。

### 3. SQL 值参数化，动态标识符用白名单

```sql
SELECT id, name, owner_id, created_at
FROM projects
WHERE id = ?;
```

值通过驱动参数绑定，不拼接用户输入。列名和排序方向通常不能用值占位符直接替代，动态排序需要固定映射或白名单。

查询明确列清单，避免 SELECT * 无意返回新增的敏感字段。数据库返回类型的泛型帮助编译检查，不会在运行时验证外部数据。

### 4. 结果映射与错误分类

| 数据库细节 | Repository 或调用边界需要处理的内容 |
| --- | --- |
| snake_case 列名 | 映射为约定的业务字段 |
| BIGINT / DECIMAL | 明确精度及字符串、数字转换策略 |
| 无匹配记录 | 使用约定的不存在结果 |
| 唯一约束冲突 | 识别具体约束，交由合适层映射业务错误 |
| 连接故障、超时 | 保留真实故障，不伪装成“用户不存在” |

不要把所有数据库异常统一转成 404，也不要将原始 SQL、连接密码直接暴露给客户端。

### 5. 事务连接由谁传递

```text
Service 决定事务边界
  ↓ 借出的同一个 connection
Repository.insertProject(connection, ...)
Repository.insertOwner(connection, ...)
  ↓
Service commit / rollback
```

也可以通过事务上下文或 Unit of Work 实现，但必须确保所有参与操作实际使用同一事务连接。Repository 私自 commit，会破坏上层想要的原子性。

### 6. 分页、排序与查询一致性

分页至少要明确默认排序和稳定的第二排序键。相同 created_at 时按 id 再排序，避免结果顺序含糊。

OFFSET 很大时可能扫描和丢弃大量记录，可以按实际需求研究基于游标的分页。查询列表与总数是两条语句，若不使用一致的读取边界，并发写入时可能不对应同一时刻；应按产品需要决定是否接受。

避免循环内对每行再发一条查询造成 N+1，也不要为了避免 N+1 就一次性读取所有数据；可以选择合适 JOIN 或批量查询。

### 7. Repository 不代替什么

谁能看成员、是否可以转让项目、什么时候发通知等业务流程应有清楚的 Service 边界。Migration 定义数据库怎么演进，Repository 定义应用怎么访问，两者职责不同。

更换 MySQL 为另一种存储时，接口稳定可以减少影响，但事务语义、查询能力和一致性差异仍需重新评估，不能保证“换个连接字符串就完全无感”。

**本阶段产出**：方法契约、字段映射、错误语义、连接与事务约定、分页方案。能解释一次业务请求最终会执行哪些 SQL。

## 2. Node.js 后端调用 SQL 的基本原则

你后续学习 `Express + TypeScript + mysql2` 时，SQL 不应依赖在 Workbench 中手动执行，而应由后端 Repository 负责访问数据库。

### 使用参数化查询

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

### 在 Repository 中管理 SQL

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

## 阅读导航

上一篇：[[20-后端/数据库/56-Migration数据库迁移]]。

下一篇：[[20-后端/数据库/58-数据库设计综合案例]]。

返回 [[20-后端/数据库/00-数据库学习导航]]。
