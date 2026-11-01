# Project Management System 数据库实战学习路线

目标：

从 0 开始搭建一个真实后端项目数据库环境。

项目：

> Project Management System（项目管理系统）

通过这个项目实践：

-   MySQL 安装
-   数据库创建
-   表设计
-   SQL 操作
-   数据填充
-   索引设计
-   EXPLAIN 分析
-   后端连接数据库

------------------------------------------------------------------------

# 第一阶段：安装 MySQL

## 1. 安装 MySQL

推荐：

MySQL 8.x

安装内容：

-   MySQL Server
-   MySQL Client
-   MySQL Workbench（可选）

安装过程中：

设置：

    root 密码

例如：

    root
    123456

实际项目不要使用简单密码。

------------------------------------------------------------------------

# 2. 检查 MySQL 是否启动

Windows：

打开：

    服务

查看：

    MySQL80

状态：

    正在运行

命令检查：

``` bash
mysql --version
```

进入数据库：

``` bash
mysql -u root -p
```

输入密码。

成功后：

``` sql
mysql>
```

------------------------------------------------------------------------

# 第二阶段：创建项目数据库

创建数据库：

``` sql
CREATE DATABASE project_management;
```

查看：

``` sql
SHOW DATABASES;
```

进入数据库：

``` sql
USE project_management;
```

------------------------------------------------------------------------

# 第三阶段：设计业务表

项目管理系统包含：

## 用户表 users

保存用户账号。

字段：

    id
    username
    email
    password_hash
    status
    created_at

SQL：

``` sql
CREATE TABLE users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    status TINYINT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

------------------------------------------------------------------------

# 项目表 projects

关系：

一个用户可以创建多个项目。

结构：

    users

    1

    ↓

    N

    projects

SQL：

``` sql
CREATE TABLE projects (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    owner_id BIGINT,
    status TINYINT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

------------------------------------------------------------------------

# 任务表 tasks

一个项目包含多个任务。

关系：

    project

    1

    ↓

    N

    tasks

SQL：

``` sql
CREATE TABLE tasks (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    project_id BIGINT,
    creator_id BIGINT,
    title VARCHAR(200),
    status TINYINT DEFAULT 0,
    priority TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

------------------------------------------------------------------------

# 项目成员表 project_members

解决多对多关系。

一个项目：

多个成员

一个用户：

多个项目

结构：

    users

    N

    ↓

    project_members

    ↓

    N

    projects

SQL：

``` sql
CREATE TABLE project_members (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    project_id BIGINT,
    user_id BIGINT,
    role VARCHAR(50)
);
```

------------------------------------------------------------------------

# 第四阶段：插入测试数据

## 插入用户

``` sql
INSERT INTO users(username,email)
VALUES
('Tom','tom@test.com'),
('Jack','jack@test.com');
```

查询：

``` sql
SELECT *
FROM users;
```

------------------------------------------------------------------------

# 第五阶段：体验索引

## 先不要创建索引

查询：

``` sql
SELECT *
FROM tasks
WHERE project_id=100;
```

查看执行计划：

``` sql
EXPLAIN
SELECT *
FROM tasks
WHERE project_id=100;
```

观察：

    type
    key
    rows

------------------------------------------------------------------------

# 第六阶段：创建索引

创建普通索引：

``` sql
CREATE INDEX idx_project_id
ON tasks(project_id);
```

再次：

``` sql
EXPLAIN
SELECT *
FROM tasks
WHERE project_id=100;
```

观察变化。

理解：

没有索引：

    全表扫描

有索引：

    B+ Tree定位

------------------------------------------------------------------------

# 第七阶段：联合索引实验

业务查询：

``` sql
SELECT *
FROM tasks
WHERE project_id=100
AND status=1;
```

建立：

``` sql
CREATE INDEX idx_project_status
ON tasks(project_id,status);
```

学习：

-   联合索引
-   最左前缀

测试：

可以：

``` sql
WHERE project_id=100
```

可以：

``` sql
WHERE project_id=100
AND status=1
```

不推荐：

``` sql
WHERE status=1
```

------------------------------------------------------------------------

# 第八阶段：覆盖索引实验

查询：

``` sql
SELECT id,project_id,status
FROM tasks
WHERE project_id=100
AND status=1;
```

观察：

是否：

    Using index

理解：

索引已经包含所有需要字段。

无需回表。

------------------------------------------------------------------------

# 第九阶段：模拟真实数据量

小数据无法体现数据库性能。

生成：

users:

    10000条

projects:

    1000条

tasks:

    100万条

然后测试：

-   查询速度
-   索引效果
-   EXPLAIN变化

------------------------------------------------------------------------

# 第十阶段：连接后端

后端：

Node.js / Express

安装：

``` bash
npm install mysql2
```

连接：

``` javascript
const mysql = require('mysql2/promise');

const pool = mysql.createPool({
    host:'localhost',
    user:'root',
    password:'password',
    database:'project_management'
});
```

查询：

``` javascript
const [rows] = await pool.query(
    'SELECT * FROM users WHERE id=?',
    [1]
);
```

------------------------------------------------------------------------

# 第十一阶段：项目升级路线

## Level 1

单体后端：

    Express

    ↓

    MySQL

实现：

-   用户注册
-   登录
-   项目CRUD
-   任务CRUD

------------------------------------------------------------------------

## Level 2

加入：

    JWT
    Redis
    权限控制

------------------------------------------------------------------------

## Level 3

加入：

    Docker

    Nginx

    多实例部署

模拟：

    App1
    App2
    App3

------------------------------------------------------------------------

## Level 4

加入：

    消息队列

例如：

创建任务：

    Task Service

    ↓

    MQ

    ↓

    Notification Service

------------------------------------------------------------------------

# 最终学习目标

完成后应该掌握：

    数据库安装
        ↓
    SQL基础
        ↓
    表设计
        ↓
    关系设计
        ↓
    索引
        ↓
    B+ Tree
        ↓
    EXPLAIN
        ↓
    后端连接数据库
        ↓
    真实业务开发

核心目标：

不是只会写 SQL。

而是理解：

> 一个真实后端系统的数据如何设计、存储、查询和优化。
