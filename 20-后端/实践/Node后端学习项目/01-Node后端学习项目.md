# Node 后端学习项目

本页连接通用知识笔记与独立代码仓库。

- [代码仓库](../../../../node/node-backend-study)
- [项目文档入口](../../../../node/node-backend-study/doc/README.md)

数据库按 01–08 顺序学习，入口见 [[20-后端/数据库/00-数据库学习导航]]。需求、实体、关系、ER 图、表设计、主外键、范式与 SQL 集中在 [[20-后端/数据库/02-SQL基础与数据库设计]]；其余深入与工程化专题在 5x。

## 当前学习方向（2026-11-19）

当前进入 [[20-后端/Java/00-Java后端学习路线|Java 主力后端路线]]。本项目的 Express、数据库和 Nest 代码继续作为类比与实验参照。Nest 收尾练习见 [[20-后端/NestJS/00-NestJS学习路线-面向SpringBoot过渡]]。

独立仓库已有 Nest 第 01～05 节案例。收尾练习从[第 03 节用户接口](../../../../node/node-backend-study/labs/nest-03-dto-validation/README.md)开始。旧版项目场景见 [[20-后端/实践/NestJS/01-项目任务管理API巩固计划]]。

## 章节与知识对应

| 项目章节 | 相关通用知识 |
| --- | --- |
| [12：Express 分层](../../../../node/node-backend-study/labs/12-express-architecture/README.md) | [[20-后端/Express与工程化/01-Express基础与Middleware]]、[[20-后端/Express与工程化/02-Express分层架构]]、[[20-后端/Express与工程化/03-统一异常处理与工程化]] |
| [13：校验与配置](../../../../node/node-backend-study/labs/13-validation-config/README.md) | [[20-后端/Express与工程化/04-运行时校验与配置管理]] |
| [14：MySQL 用户持久化](../../../../node/node-backend-study/labs/14-mysql-repository/README.md) | [[20-后端/数据库/01-数据库基础]]、[[20-后端/数据库/03-索引]] |
| [15：事务与多表操作](../../../../node/node-backend-study/labs/15-transactions/README.md) | [[20-后端/数据库/04-事务]]、[[20-后端/数据库/05-锁与并发控制]]、[[20-后端/数据库/55-InnoDB提交与刷盘]] |
| [16：登录认证与项目权限](../../../../node/node-backend-study/labs/16-auth/README.md) | [[20-后端/认证与安全/01-登录认证与Cookie-JWT-Session重点总结]] |
| [17：Redis 基础与用户缓存](../../../../node/node-backend-study/labs/17-redis-cache/README.md) | [[20-后端/数据库/06-Redis]]、[[20-后端/数据库/07-缓存]] |
| [17a：Redis 登录失败限制](../../../../node/node-backend-study/labs/17a-login-limit/README.md) | [[20-后端/数据库/06-Redis]] 第8.2 / 8.6节：原子计数、首次设置过期、固定窗口；登录成功清零与故障策略见案例 |

## 历史学习记录（由原大总结迁移）

以下保留原有自述，不作为本次验证后的实时进度。

### 项目管理系统设计

核心实体：

    User

    Project

    Task

    ProjectMember

关系：

    User 1:N Project

    Project 1:N Task

    User N:N Project

### 数据库实战记录

已完成：

-   MySQL安装
-   Workbench连接
-   创建数据库
-   创建项目管理系统表
-   创建测试数据
-   生成约77万tasks数据
-   EXPLAIN分析
-   索引测试

### 当时列出的后续学习内容

继续学习：

    聚簇索引
    ↓
    普通索引
    ↓
    B+Tree深入
    ↓
    回表
    ↓
    覆盖索引
    ↓
    联合索引
    ↓
    最左前缀
    ↓
    事务
    ↓
    隔离级别
    ↓
    锁
    ↓
    连接池
    ↓
    Repository
    ↓
    Migration

### 最终项目目标

Project Management System

技术：

Backend:

-   Node.js
-   TypeScript
-   Express
-   NestJS

Database:

-   MySQL
-   Redis

Frontend:

-   React

功能：

-   用户系统
-   登录认证
-   JWT
-   RBAC权限
-   项目管理
-   任务管理
-   消息通知
-   日志系统
