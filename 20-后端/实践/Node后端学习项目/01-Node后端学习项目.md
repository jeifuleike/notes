# Node 后端学习项目

本页连接通用知识笔记与独立代码仓库。

- [代码仓库](../../../../node/node-backend-study)
- [项目文档入口](../../../../node/node-backend-study/doc/README.md)

## 章节与知识对应

| 项目章节 | 相关通用知识 |
| --- | --- |
| [12：Express 分层](../../../../node/node-backend-study/labs/12-express-architecture/README.md) | [[20-后端/Express与工程化/01-Express基础与Middleware]]、[[20-后端/Express与工程化/02-Express分层架构]]、[[20-后端/Express与工程化/03-统一异常处理与工程化]] |
| [13：校验与配置](../../../../node/node-backend-study/labs/13-validation-config/README.md) | [[20-后端/Express与工程化/04-运行时校验与配置管理]] |
| [14：MySQL 用户持久化](../../../../node/node-backend-study/labs/14-mysql-repository/README.md) | [[20-后端/数据库/01-数据库基础知识整理]]、[[20-后端/数据库/03-MySQL索引核心知识整理]] |
| [15：事务与多表操作](../../../../node/node-backend-study/labs/15-transactions/README.md) | [[20-后端/数据库/04-InnoDB事务提交与刷盘]] |
| [16：登录认证与项目权限](../../../../node/node-backend-study/labs/16-auth/README.md) | [[20-后端/认证与安全/01-登录认证与Cookie-JWT-Session重点总结]] |

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
