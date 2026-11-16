# NestJS 学习路线：每日一节，面向 Spring Boot 过渡

## 1. 学习目标与节奏

2026-11-11 更新：NestJS零基础，但已有TypeScript、Express、HTTP、数据库基础。**熟悉的接口与分层一起过，Nest特有的依赖注入、模块和请求扩展点重点练；然后完成一个NestJS小项目，再转Java / Spring Boot。**

按 **12节：7节基础 + 5节项目** 安排，通常一天一节。基础节约1～1.5小时，项目节约1～2小时，仅作为参考；完成验收就前进，卡住可延续到次日，不按每个装饰器拆一天。

> [!important] 学习重点
> IoC / DI、Module与Provider、运行时校验、请求处理链、数据库与事务如何接入框架。HTTP和SQL原理直接复用，不重复整章学习。

当前所有验收项都是计划，不表示已完成。基础阶段使用一个逐步演进的小工程，项目阶段再建独立应用，不为每一节创建一个工程。

## 2. 整体安排

| 节次 | 主题 | 本节产出 |
| --- | --- | --- |
| 01 | 启动、Controller、参数、Service一起练 | 内存用户接口 |
| 02 | Provider、DI与Module（重点） | 能解释并组织依赖关系 |
| 03 | DTO、Pipe、校验与异常 | 完整输入和错误边界 |
| 04 | 配置、连接池与Repository | MySQL用户接口 |
| 05 | 事务与多表业务 | 创建项目与owner成员的原子操作 |
| 06 | Guard与JWT认证 | 受保护的当前用户接口 |
| 07 | 请求链路与基础复盘 | 分清扩展点，独立补一个功能 |
| 08 | 小项目：范围、结构、数据准备 | 可启动的独立项目骨架 |
| 09 | 小项目：用户与登录 | 注册、登录、当前用户闭环 |
| 10 | 小项目：项目与权限 | 创建、查询项目与成员权限 |
| 11 | 小项目：任务业务 | 创建、查询任务和更新状态 |
| 12 | 小项目：验收与复盘 | 测试、运行说明、Spring Boot迁移清单 |

项目阶段的具体安排见 [[20-后端/实践/NestJS/01-项目任务管理API巩固计划]]。

装饰器速查：[[20-后端/NestJS/13-Nest常用装饰器分类速查]]。按作用位置分类，配合第01～07节随时查阅，不单独占用学习日。

## 3. 第01节：把接口与 Service 一起跑通

学习笔记：[[20-后端/NestJS/01-NestJS启动-Controller参数与Service-]]。

**本节一起学**：项目启动、Controller路由、常用HTTP装饰器、三种输入、Service职责。这里主要是把已有Express经验换成Nest写法，不逐个装饰器分节。

- 认识 `main.ts`、`AppModule`、Controller、Service各在什么位置；装饰器只理解其描述作用，不研究底层。
- 在一个UsersController中练 `@Get()`、`@Post()`、`@Patch()`，读取 `@Param()`、`@Query()`、`@Body()`。
- 数组读写放在UsersService，Controller只接HTTP输入并调用Service。先照最小例子注册依赖，下一节解释原因。
- **练习**：用户列表、按ID查询、按姓名筛选、创建及修改用户。先用约定的合法输入；转换和校验在第03节补齐。
- [ ] **验收**：能独立加接口并用HTTP请求文件调用，区分params/query/body，能说清请求如何进入Service；知道类型标注不等于运行时校验。

参考：[Nest入门](https://docs.nestjs.com/first-steps)、[Controllers](https://docs.nestjs.com/controllers)。

## 4. 第02节：Provider、依赖注入与 Module（重点）

这是从Express手动组装业务转向框架管理对象的核心，需要比路由语法多花时间。

学习笔记：[[20-后端/NestJS/02-Provider依赖注入与Module]]。

- IoC：对象创建与组装交给容器；DI：通过构造函数接收依赖。
- 理解 `@Injectable()`、`providers`、`controllers`、`imports`、`exports`；仅加装饰器不等于完成注册。
- 将数组读写抽成UsersRepository，完成Controller → Service → Repository的构造函数注入。
- 用一个小例子认识token、`@Inject()`与 `useValue / useFactory`；TS interface运行时被擦除，不能直接作为注入token。
- **练习**：拆出UsersModule；替换一个Repository依赖；故意漏一次注册或exports，读懂报错后恢复。
- [ ] **验收**：解释谁创建对象、跨模块依赖怎么接、替换依赖为何不必改业务；知道默认共享Provider不应保存当前用户等请求状态。

参考：[Providers](https://docs.nestjs.com/providers)、[Modules](https://docs.nestjs.com/modules)、[自定义Provider](https://docs.nestjs.com/fundamentals/custom-providers)。

## 5. 第03节：DTO、校验、Pipe 与统一异常

学习笔记：[[20-后端/NestJS/03-DTO校验Pipe与统一异常]]。

围绕“非法输入进不去、错误响应说清楚”一起练，不把DTO、每个校验装饰器和每种异常再拆成多天。

- 区分请求DTO、数据库记录与响应；DTO class本身也不提供自动校验。
- 使用基本字段约束与 `ValidationPipe`，理解 `whitelist`、`forbidNonWhitelisted`。
- 路径ID用 `ParseIntPipe` 等显式转换，再检查正整数及安全整数边界；不假定transform覆盖所有业务要求。
- 会使用内置HTTP异常；读写一个最小Exception Filter，保留已知状态，未知错误返回通用500。
- **练习**：补齐第01节接口的400、404；非法邮箱、空姓名、多余字段和非法ID不进入数据访问。
- [ ] **验收**：合法请求成功，失败状态正确；无SQL/堆栈泄露，不在每个Controller重复try/catch。正常响应不走Exception Filter。

参考：[Validation](https://docs.nestjs.com/techniques/validation)、[Exception Filters](https://docs.nestjs.com/exception-filters)。原理复用 [[20-后端/Express与工程化/04-运行时校验与配置管理]]、[[20-后端/Express与工程化/03-统一异常处理与工程化]]。

## 6. 第04节：配置、MySQL 与 Repository

本节直接把内存用户接口改成数据库接口，继续用熟悉的mysql2和参数化SQL，不同时学习ORM。

- 配置集中读取，必要配置启动时校验，代码中不写真实密钥。
- 用工厂Provider提供共享连接池，Repository注入使用；理解应用关闭时释放资源。
- Service组织业务，Repository负责SQL；不为每个请求创建连接池。
- **练习**：实现用户查询、创建与更新；重复邮箱转换为409，返回值仅包含公开字段。
- [ ] **验收**：重启后数据仍在；所有输入参数绑定；数据库实现替换后Controller保持原有调用方式，缺少必要配置时启动失败。

参考：[Configuration](https://docs.nestjs.com/techniques/configuration)。已有知识见 [[20-后端/数据库/57-Repository数据访问]]、[[20-后端/数据库/56-Migration数据库迁移]]。复用迁移，不删除重建已有学习库。

## 7. 第05节：事务与多表业务

本节重点是Nest的注入和分层如何配合已有事务能力，不重学ACID、锁和隔离级别。

- Service决定事务边界，多次Repository调用显式共享同一个事务连接。
- 失败回滚，最终释放连接；不把MySQL与Redis想象成一个自动事务。
- **练习**：创建项目并插入owner成员；人为让第二步失败，检查第一步是否回滚。
- [ ] **验收**：两步一起成功或一起失败，连接不泄漏；能指出哪个方法负责开启、提交和回滚。

已有原理见 [[20-后端/数据库/04-事务]]。Spring后续的 `@Transactional` 有自己的基础设施与调用条件，Nest普通装饰器不会自动提供同样能力。

## 8. 第06节：Guard 与 JWT 认证

把已有密码和JWT知识接到Nest，重点看Guard的位置、依赖与请求身份传递。

- 认识 `CanActivate`、`ExecutionContext`，读取Bearer token。
- 复用已学的密码校验、JWT签发与验签原理；验证签名和必要声明后才信任身份。
- Guard保护处理器；项目成员等业务权限仍由业务层检查，不能“有token就能访问所有项目”。
- **练习**：登录取得token，再访问当前用户接口；密码算法可复用已有实现，JWT工具沿用熟悉的一种，不同时研究多套库或Passport。
- [ ] **验收**：缺失、伪造、过期凭证返回401，合法凭证正常；身份来自验证结果，不来自body中的userId。

参考：[Authentication](https://docs.nestjs.com/security/authentication)、[Guards](https://docs.nestjs.com/guards)。原理复用 [[20-后端/认证与安全/01-登录认证与Cookie-JWT-Session重点总结]]。

## 9. 第07节：请求处理链与一次独立练习

- 认识Middleware、Guard、Pipe、Interceptor、Exception Filter各自的职责。
- 读懂一个简单耗时Interceptor；RxJS只理解该例所需的用法，不单开深入学习。
- 用顺序日志观察正常请求主干：Middleware → Guard → Interceptor进入 → Pipe → Controller/Service → Interceptor返回；异常进入相应处理路径。
- **练习**：不看整套答案，自己增加一个受保护、带校验的查询接口，串起模块、注入、数据访问及错误处理。
- [ ] **验收**：能解释代码为什么放在这一层，以及正常、校验失败、认证失败、Service抛错的区别。完成后进入小项目，不再继续扩展框架功能。

参考：[Interceptors](https://docs.nestjs.com/interceptors)、[请求生命周期](https://docs.nestjs.com/faq/request-lifecycle)。

## 10. 第08～12节：小项目巩固

做一个**精简项目任务管理API**：注册登录、创建/查询项目、项目成员访问权限、创建/查询任务与修改任务状态。

基础阶段跟例子建立概念，项目阶段从独立应用重新组织模块，自己先列依赖与业务规则，再查文档。沿用熟悉的业务与表关系，主要练Nest写法，不靠增加功能制造难度。

完整安排见 [[20-后端/实践/NestJS/01-项目任务管理API巩固计划]]。本轮先完成后端，用HTTP请求文件验收；前端页面是自愿加餐，不引入新的前端框架。

## 11. 学完后怎样转 Spring Boot

| 本轮掌握的内容 | 后续Spring学习方向 |
| --- | --- |
| Controller、路由、参数绑定 | @RestController、@GetMapping、@PostMapping |
| Provider、构造函数注入 | Spring Bean、IoC / DI |
| Module组织依赖 | 组件扫描、配置类；并非同样的模块机制 |
| DTO、校验、异常出口 | Bean Validation、@Valid、@RestControllerAdvice |
| Repository、事务边界 | JDBC或MyBatis、@Transactional及生效条件 |
| Guard与请求扩展点 | Spring Security、Servlet Filter、MVC拦截器、AOP，分别学习 |

完成小项目并能解释上述内容后，按 **Java必要基础 → Spring Boot Web与DI → 重写同一组接口 → 数据访问与事务 → 安全、测试与部署** 继续。

TypeScript装饰器不等于Java注解；Nest Module不是Java package或Maven模块。Java线程模型也不能照搬Node事件循环，迁移时另外学习这些差异。

参考：[Spring REST入门](https://spring.io/guides/gs/rest-service/)、[Spring构造函数注入](https://docs.spring.io/spring-framework/reference/core/beans/annotation-config/autowired.html)、[Spring声明式事务](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html)。

## 12. 边界与资料位置

本轮不展开Fastify、ORM深入、复杂动态模块、自定义装饰器体系、源码、GraphQL、微服务、消息队列、复杂RBAC和生产部署。Swagger、前端页面、缓存接入以后按需求补充。

Redis登录失败限制已有 [第17a章独立实验](../../../node/node-backend-study/labs/17a-login-limit/README.md)，第18章缓存实验也保留；它们都不阻塞当前路线。

- 通用知识：本库 `20-后端/NestJS/`，新增前先检索。
- 项目学习安排：[[20-后端/实践/NestJS/01-项目任务管理API巩固计划]]。
- 代码、章节TODO、运行及实际验收记录：[node-backend-study](../../../node/node-backend-study)。基础工程和独立项目在开始实践时创建，本路线不代表已具备可运行NestJS案例。
- 总入口：[[20-后端/00-后端学习导航]]、[[20-后端/实践/Node后端学习项目/01-Node后端学习项目]]。
