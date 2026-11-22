# NestJS 学习路线：从现有接口过渡到 Spring Boot

2026-11-19 已转入 [[20-后端/Java/00-Java后端学习路线|Java 主力后端路线]]，从 [[20-后端/Java/01-变量类型与输出|Java 第 01 节]] 开始。本页保留 Nest 请求链练习与 Spring 对照，供按需查阅。

## 你的学习起点

| 已有记录 | 这次怎样安排 |
| --- | --- |
| Express 项目已涉及 Router、Middleware、Controller / Service / Repository、统一错误出口、参数与配置校验。第 16 章已有 JWT 验签、获取当前用户以及项目成员权限检查。[项目知识地图](../../../node/node-backend-study/doc/00-学习路线与知识地图.md) · [认证中间件](../../../node/node-backend-study/labs/16-auth/src/auth/auth.middleware.ts) | 沿用熟悉的用户接口。把精力放在 Nest 怎样选择并调用挂到路由上的组件。 |
| 项目管理系统的 12 道 SQL 题都已勾完，包括多表查询、联合索引执行计划、全表扫描对比和唯一约束。第 15 章已有创建项目和 owner 成员的事务实现。[[20-后端/实践/数据库/02-MySQL项目管理系统SQL实战12题\|SQL 实战记录]] · [原事务实现](../../../node/node-backend-study/labs/15-transactions/src/project/project.service.ts) | SQL、事务、连接池和 Repository 留作查阅。收尾练习使用内存数据。 |
| 11 月 15 日记录了过完 Nest 第 02 节，16 日记录了学习 DTO、Pipe 与统一异常。第 02 节的测试已有跨模块注入和 `useValue` 替换存储。[[50-每日自律/日报/2026-11/2026-11-15\|第 02 节学习记录]] · [[50-每日自律/日报/2026-11/2026-11-16\|第 03 节学习记录]] · [已有测试](../../../node/node-backend-study/labs/nest-02-providers/src/app.test.ts) | 复用现成的 Controller、Pipe 和异常处理。遇到依赖解析问题时再回看 Module 的注册与导出。 |

## 第 06 节（可跳过）：预测三次请求的执行路径

[[20-后端/NestJS/06-Guard与Interceptor的请求链|速读第 06 节：Interceptor 能看到哪一段请求？]]

打开第 03 节的 `UsersController.findOne`。它已经在 `GET /users/:id` 上绑定了两个 Pipe，内存里已有 ID 为 1 的用户。设想给 **findOne 方法**加一个能在测试中切换放行或拒绝的 Guard，给 **UsersController** 加一个记录进入与结束时间的 Interceptor。先遮住下面的“预期”一栏，判断每次请求会在哪一步结束。[现有 Controller](../../../node/node-backend-study/labs/nest-03-dto-validation/src/users/users.controller.ts) · [已有用户数据](../../../node/node-backend-study/labs/nest-03-dto-validation/src/users/users.service.ts)

| 请求条件 | 预期 |
| --- | --- |
| Guard 放行，`GET /users/1` | **200**。Guard 放行后进入 Interceptor，Pipe 校验参数，Controller 调用 Service。Interceptor 能观察到成功返回。 |
| Guard 返回 `false`，`GET /users/0` | **403**。虽然 ID 也非法，但 Guard 先拒绝请求，Interceptor、参数 Pipe 和 Controller 都不会执行。 |
| Guard 放行，`GET /users/0` | **400**。Interceptor 已进入，整数转换成功，正整数 Pipe 抛错，Controller 不执行。若用 `finalize` 记录耗时，这次失败也有结束日志。 |

**收尾标准**：能解释为什么同一个非法 ID 有时得到 403、有时得到 400，以及为什么只有后者进入了 Interceptor。再看同一 Controller 的列表接口 `GET /users`，能指出它会经过类上的 Interceptor，而 `findOne` 上的 Guard 只作用于详情接口，就可以转 Java。还有疑问时，只给这一个接口加日志，核对预测有出入的那一步。[[20-后端/NestJS/13-Nest常用装饰器分类速查#6. 请求链扩展点：Guard、Interceptor、Pipe、Filter|现有请求链速查]]

## 转入 Java 与 Spring Boot

| 顺序 | 学什么 | 用什么判断可以往下走 |
| --- | --- | --- |
| 1. Java 必要基础 | 用熟悉的用户查询练类、构造函数、接口、集合、泛型和异常，学会用构建工具运行测试。 | 能用内存列表实现按 ID 查询，写出“找到”和“找不到”两个用例。 |
| 2. Spring Boot Web 与依赖注入 | 将同一个查询暴露为 `GET /users/{id}`，用构造函数注入 Service，观察 Spring 如何发现和创建 Bean。 | 能发请求拿到用户，并从 Controller 的构造函数追到实际注入的对象。 |
| 3. 用已有接口比较框架 | 先接参数校验和统一异常，再按需接回已有 MySQL 表。遇到多表写入时，重点看 Spring 如何建立声明式事务边界。 | 对照已有 HTTP 用例说明响应是否一致，并指出对象创建、异常映射和事务管理分别交给了谁。 |

## 已有章节按需回查

- 启动与路由 → [[20-后端/NestJS/01-NestJS启动-Controller参数与Service-]]。依赖注册、导出和替换 → [[20-后端/NestJS/02-Provider依赖注入与Module]]。
- 参数校验与错误响应 → [[20-后端/NestJS/03-DTO校验Pipe与统一异常]]。
- 数据库工厂 Provider → [[20-后端/NestJS/04-配置MySQL与Repository]]。两个 Repository 共享事务连接 → [[20-后端/NestJS/05-事务与多表业务]]。
- 以后需要完整项目的表关系、权限场景和验收用例，可查 [[20-后端/实践/NestJS/01-项目任务管理API巩固计划|旧版项目任务管理 API 方案]]。
