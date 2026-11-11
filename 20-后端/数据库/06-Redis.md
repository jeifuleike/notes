# Redis：从基础命令到并发、持久化与高可用

> 本篇目标：理解 Redis
> 是什么、它如何被后端项目使用，以及常见数据结构、原子操作、事务、Lua、分布式锁、持久化、内存淘汰、复制和集群分别解决什么问题。
>
> 学习重点不是背命令，而是建立一个判断能力：**当前业务问题属于数据结构、并发控制、性能、持久化，还是高可用问题？应该使用
> Redis 的哪项能力？它又不能保证什么？**

------------------------------------------------------------------------

## 0. 先建立整体认识

Redis 是一个独立运行的数据服务。后端程序通过 Redis 客户端连接 Redis
服务，发送命令，Redis 执行命令并返回结果。

一个典型后端项目可能同时运行多个服务：

``` text
Vue / React 前端
      |
      | HTTP
      v
Node.js / Java 后端服务
      |
      +---- MySQL 客户端 ----> MySQL 服务
      |
      +---- Redis 客户端 ----> Redis 服务
      |
      +---- 其他客户端 ------> 消息队列、对象存储等
```

这里要区分：

-   **服务（Service）**：独立运行的程序，例如 Node.js、MySQL、Redis。
-   **服务器（Server）**：运行这些程序的计算机或虚拟机。
-   **客户端（Client）**：连接服务并发送请求的程序或库，例如 `redis` npm
    包、`mysql2` npm 包。
-   **业务代码**：开发者编写的订单、用户、支付、登录等逻辑。

多个服务不代表需要多台机器。开发环境中，Node.js、MySQL、Redis
完全可以运行在同一台 Ubuntu 机器上，也可以分别放在 Docker
容器中；规模较大时再拆到不同服务器或使用托管服务。

Redis
提供数据存储、数据结构操作、原子命令和消息传递等基础能力。它不会自动理解订单、发送短信或执行你的业务流程。具体业务仍然由后端代码实现。

## 1. Redis 是什么

Redis
是一个主要在内存中保存和操作数据的独立数据服务。应用通过网络访问它。

最基本的抽象可以理解为：

``` text
key（键） -> value（值）
```

例如：

``` text
study:user:1 -> {"id":1,"name":"小明"}
study:article:17:views -> 100
study:session:1001 -> "token-abc"
```

但 Redis 不只是"只能存字符串的 Key-Value 数据库"。它的 value
可以使用不同的数据结构，例如 String、Hash、List、Set、Sorted Set、Stream
等。不同结构提供不同的命令和操作能力。

### 1.1 Redis 与 JavaScript 的 Map

``` js
const cache = new Map()
cache.set('study:user:1', '{"id":1,"name":"小明"}')
```

这个例子只用于类比"根据名字存取数据"。

| 维度 | 进程内 Map | Redis |
| --- | --- | --- |
| 数据在哪里 | 当前 Node.js 进程的内存 | 独立 Redis 服务的内存 |
| 多进程共享 | 默认不共享 | 多个进程可以连接同一个 Redis |
| 访问方式 | 本地函数调用 | 通过网络发送命令 |
| 生命周期 | 进程退出，Map 消失 | Node 进程退出不影响 Redis；Redis 自身重启后的恢复取决于持久化 |
| 过期管理 | 自己编写 | Redis 提供 TTL、EXPIRE 等命令 |
| 数据结构 | Map 本身的结构 | Redis 提供多种服务端数据结构 |

Redis 与 Map 最大的区别之一，是 Redis
是独立服务，因此不同后端实例可以共享同一份数据。

### 1.2 Redis 与 MySQL 的关系

可以先这样理解：

| 对比 | MySQL | Redis |
| --- | --- | --- |
| 主要用途 | 关系型业务数据存储 | 内存数据结构服务，常用于缓存、计数、会话、消息等 |
| 数据组织 | 数据库、表、行、列 | Key 和不同类型的 Value |
| 常见访问方式 | SQL | Redis 命令 |
| 主要工作方式 | 磁盘持久化与内存缓冲结合 | 主要在内存中操作，可配置持久化 |
| 典型能力 | SQL 查询、索引、事务、约束、JOIN | 原子数据结构操作、TTL、集合、排序、消息流等 |

不要简单地理解成"MySQL 读磁盘、Redis 读内存"。MySQL
也会使用内存缓冲池；两者在数据模型、查询能力、持久化和访问方式上有更深的差异。

Redis 常被用来做缓存，但 **Redis 不等于缓存**。缓存只是 Redis
的一种使用场景。

## 2. Redis 为什么通常很快，以及为什么仍然可能慢

Redis 的常见操作主要围绕内存数据结构进行，简单的 GET、SET、INCR
等操作通常很轻量。

但不能把"Redis 很快"理解成所有命令的成本都一样：

-   简单的字符串 GET、SET 通常很快。
-   返回一个很大的 List、Set 或
    Hash，可能需要遍历大量元素并通过网络传输。
-   网络距离、连接排队、客户端等待、慢命令都会增加响应时间。
-   一个超大的 Value 会增加内存占用、序列化和网络传输成本。
-   大量请求集中访问同一个 Key，也可能形成热点。

### 2.1 Redis 是单线程吗？

常见 Redis 命令的主要执行路径通常由 Redis
的事件循环串行处理。因此，某个耗时很长的命令可能阻塞其他客户端命令。

但"Redis 是单线程"不是说 Redis 整个程序的所有工作都只有一个线程。网络
I/O、后台任务、持久化、释放内存等工作可能涉及其他线程或进程。

也不能因为 Redis 的命令执行通常串行，就认为：

``` text
GET -> 应用计算 -> SET
```

这整个业务流程自动是原子的。多个命令之间仍然可能被其他客户端的命令插入。

### 2.2 大 Key 与热 Key

这两个概念不要混淆：

-   **大 Key**：单个 Key 对应的数据量很大，例如一个包含几十万成员的
    Set，或一个很大的字符串。
-   **热 Key**：大量请求集中访问少量 Key，例如热门商品详情、全站计数器。

一个 Key 可以很小但很热，也可以很大但不热。

处理方式也不同：大 Key 关注拆分、扫描、传输和删除成本；热 Key
关注请求分散、缓存策略和访问压力。

## 3. Redis 服务端、客户端和后端项目的关系

典型结构：

``` text
浏览器
  |
  | HTTP
  v
Node.js / Express / NestJS
  |
  +---- mysql2 客户端 ----> MySQL 服务
  |
  +---- redis 客户端 -----> Redis 服务
```

几个概念：

-   `redis-server`：Redis 服务端程序，真正保存和操作数据。
-   `redis-cli`：命令行客户端，用来手工连接 Redis 并执行命令。
-   Node.js 的 `redis` npm 包：客户端库，让业务代码连接 Redis。
-   Docker 镜像：只是运行服务所需的镜像；拉取镜像不等于容器已经启动。

常见默认端口：

| 服务 | 常见端口 |
| --- | --- |
| Node.js 后端 | 3000（由项目决定） |
| MySQL | 3306 |
| Redis | 6379 |

### 3.1 多个服务不等于多台服务器

同一台 Ubuntu 机器可以运行：

``` text
Ubuntu
├── Node.js 后端：3000
├── MySQL：3306
└── Redis：6379
```

也可以使用 Docker 分开运行：

``` text
Ubuntu
└── Docker
    ├── backend 容器
    ├── mysql 容器
    └── redis 容器
```

生产环境还可以把它们部署到不同机器，或使用云厂商托管的 MySQL、Redis。

### 3.2 连接地址中的 127.0.0.1

``` js
const client = createClient({
  url: 'redis://127.0.0.1:6379'
})
```

`127.0.0.1` 表示"当前网络命名空间中的本机"。

如果 Node.js 和 Redis 都直接运行在同一台主机上，这通常可用。

但如果 Node.js 在 Docker 容器 A，Redis 在 Docker 容器 B，那么 Node.js
容器里的 `127.0.0.1` 指向容器 A 自己，不是 Redis 容器。使用 Docker
Compose 时，通常通过 Redis 的服务名连接，例如：

``` js
url: 'redis://redis:6379'
```

具体地址取决于部署网络。

## 4. Key、Value 和基本命令

下面代码块是 `redis-cli` 中执行的 Redis 命令，不是 SQL，也不是
PowerShell 命令：

``` redis
PING
SET study:hello "Redis" EX 60
GET study:hello
TYPE study:hello
EXISTS study:hello
TTL study:hello
DEL study:hello
GET study:hello
```

| 命令 | 作用 | 常见返回 |
| --- | --- | --- |
| `PING` | 检查 Redis 是否有响应 | `PONG` |
| `SET key value EX 60` | 写入字符串并设置 60 秒过期 | `OK` |
| `GET key` | 读取字符串 | 内容；不存在返回 nil |
| `TYPE key` | 查看 Value 的类型 | `string`、`hash` 等 |
| `EXISTS key` | 检查 Key 是否存在 | 1 或 0 |
| `TTL key` | 查看剩余秒数 | 剩余秒数、-1、-2 |
| `DEL key` | 删除 Key | 实际删除的 Key 数量 |
| `INCR key` | 将整数值原子递增 1 | 递增后的值 |

重复删除不存在的 Key，返回 0，通常不是异常。字符串 Key 被写成 List
后再用 GET 读取，会出现类型不匹配错误；命令必须与 Value 的类型对应。

### 4.1 Key 命名

推荐使用有规律的前缀，表达应用、环境、实体、用途和标识。

例如：

``` text
study:dev:user:1:profile
study:dev:user:2:profile
study:prod:login-fail:account:42
shop:prod:product:1001:detail
shop:prod:order:1001:lock
```

冒号只是命名习惯，不会创建文件夹，也不会自动形成权限隔离。

命名时注意：

1.  **应用或项目**：例如 `study`、`shop`。
2.  **环境**：例如
    `dev`、`test`、`prod`，避免测试数据和生产数据混在一起。
3.  **业务实体**：例如 `user`、`order`、`product`。
4.  **实体标识**：例如用户 ID、订单 ID。
5.  **用途**：例如 `profile`、`detail`、`lock`、`views`。

如果数据内容依赖租户、语言、地区、查询条件或权限范围，这些维度也要进入
Key 设计，否则可能把不同上下文的数据读混。

Key 前缀不是安全边界。真正的访问控制需要 Redis ACL、网络隔离和凭证配置。

## 5. TTL：数据为什么会过期

TTL 是 Time To Live，表示 Key 的剩余生存时间。普通 Key
的过期时间是设置在整个 Key 上的。

``` redis
SET study:ttl "hello" EX 30
TTL study:ttl
GET study:ttl
```

TTL 返回值：

| 返回值 | 含义 |
| --- | --- |
| 大于等于 0 | 剩余有效秒数 |
| `-1` | Key 存在，但没有过期时间 |
| `-2` | Key 不存在 |

常用命令：

``` redis
EXPIRE study:ttl 60
PEXPIRE study:ttl 60000
TTL study:ttl
PTTL study:ttl
PERSIST study:ttl
```

-   `EXPIRE`：设置秒级过期时间。
-   `PEXPIRE`：设置毫秒级过期时间。
-   `TTL` / `PTTL`：查看剩余时间。
-   `PERSIST`：移除过期时间。

### 5.1 GET 不会自动续期

例如：

``` redis
SET study:session:1001 "token-abc" EX 3600
GET study:session:1001
```

GET 只是读取，不会自动把有效期延长一小时。

如果需要滑动过期，需要在业务逻辑中明确续期。

### 5.2 覆盖 SET 时要注意 TTL

普通 SET 覆盖同名 Key 时，默认会移除原来的 TTL：

``` redis
SET study:temporary "value" EX 60
SET study:temporary "new-value"
TTL study:temporary
```

第二条 SET 后，Key 默认没有过期时间。

如果想保留原 TTL，可以根据需求使用 `KEEPTTL`：

``` redis
SET study:temporary "new-value" KEEPTTL
```

### 5.3 为什么推荐 SET 时同时设置过期时间？

下面是两条独立命令：

``` redis
SET study:temporary "value"
EXPIRE study:temporary 60
```

如果应用在 SET 成功后、EXPIRE 执行前崩溃，Key 可能没有过期时间。

更稳妥的写法是：

``` redis
SET study:temporary "value" EX 60
```

这样写入和设置 TTL 由一条命令完成。

Redis 的过期处理结合访问时检查和后台主动清理；不要把它想象成每个 Key
都有一个精确到期、立即释放内存的独立定时器。

**TTL 与内存淘汰不是一回事**，后文单独解释。

## 6. 常用数据类型：按业务需求选择

Redis 的数据类型决定了 Value
可以使用哪些命令。下面介绍常见类型和实际业务场景。

### 6.1 String：字符串、JSON 文本、整数计数

``` redis
SET study:user:1 '{"id":1,"name":"小明"}' EX 60
GET study:user:1

INCR study:article:17:views
INCRBY study:article:17:views 5
```

String 保存字节序列。JSON
在这里仍然是一段字符串，并不会因为内容长得像对象，就自动变成可按字段查询的原生对象。

常见用途：

-   保存简单字符串。
-   保存 JSON 序列化后的对象。
-   保存验证码、Token 等短文本。
-   使用 `INCR`、`DECR`、`INCRBY` 做计数。

`INCR` 对可以解析为整数的字符串递增；Key 不存在时以 0
为起点。普通文本不能直接递增。

### 6.2 Hash：一个 Key 下的多个字段

``` redis
HSET study:profile:1 name "Tom" age 20
HGET study:profile:1 name
HGETALL study:profile:1
HINCRBY study:profile:1 age 1
```

Hash 可以理解成一个轻量的字段和值集合：

``` text
study:profile:1
  ├── name = Tom
  └── age  = 20
```

适合保存一个对象的多个字段，并且需要单独读取或修改其中某些字段的场景。

与 JSON String 对比：

| 方式 | 特点 |
| --- | --- |
| String + JSON | 一次读取整个 JSON；修改字段时通常需要取出、解析、修改、重新序列化并写回 |
| Hash | 可以单独 HGET、HSET 某个字段；字段操作更直接 |

Hash 不是关系型数据库中的表：它没有自动外键、JOIN、关系约束等能力。

### 6.3 List：有顺序，允许重复

``` redis
RPUSH study:tasks "task-A" "task-B" "task-A"
LRANGE study:tasks 0 -1
LPOP study:tasks
```

List 是有序列表，允许相同元素重复出现。

本例从右侧加入、左侧取出：

``` text
RPUSH：右侧加入
LPOP：左侧取出
```

所以可以形成先进先出（FIFO）的简单队列：

``` text
加入：A -> B -> C
取出：A -> B -> C
```

适合简单队列、最近操作列表等。

但要注意：`LPOP` 取出消息后，消息就从 List
中删除。如果消费者取出后突然崩溃，任务可能丢失。仅靠 List 的 LPUSH/RPOP
并不等于可靠消息队列；还需要确认、重试、失败恢复和幂等设计。

### 6.4 Hash 与 List 的区别

| 对比 | Hash | List |
| --- | --- | --- |
| 主要结构 | 字段 -> 值 | 有序元素序列 |
| 是否有顺序 | 不用于表达元素排列顺序 | 有顺序 |
| 是否允许重复 | 字段名唯一 | 元素允许重复 |
| 常见用途 | 用户资料、对象字段 | 简单队列、操作记录列表 |
| 典型操作 | HSET、HGET、HGETALL | LPUSH、RPUSH、LPOP、LRANGE |

例如：

``` redis
HSET study:profile:1 name "Tom" age 20
```

表达的是一个对象的字段。

而：

``` redis
RPUSH study:tasks "task-A" "task-B" "task-A"
```

表达的是一串有顺序、允许重复的任务标识。

### 6.5 Set：无重复成员的集合

``` redis
SADD study:project:1:members "user:1" "user:2" "user:1"
SISMEMBER study:project:1:members "user:1"
SMEMBERS study:project:1:members
```

Set 的成员唯一，没有可依赖的排列顺序。

重复添加相同成员不会产生重复项。

适合：

-   项目成员去重。
-   用户是否点赞。
-   标签集合。
-   共同好友、交集、并集等集合运算。

成员集合很大时，直接 SMEMBERS 取回全部成员可能产生较大开销。

### 6.6 Sorted Set：成员唯一，按分数排序

``` redis
ZADD study:ranking 100 "Tom" 80 "Jack" 120 "Alice"
ZRANGE study:ranking 0 2 REV WITHSCORES
```

Sorted Set（有序集合）由"成员 Member + 分数 Score"组成：

``` text
Tom   -> 100
Jack  -> 80
Alice -> 120
```

它有两个重要特点：

1.  同一个成员只能存在一次。
2.  Redis 根据 Score 维护成员的有序关系。

如果再次给同一个成员赋分：

``` redis
ZADD study:ranking 150 "Tom"
```

不是新增一个 Tom，而是把 Tom 的分数从 100 更新成 150，Redis
会相应维护排序。

因此它适合排行榜：

``` text
Alice 120
Tom   100
Jack   80
```

注意：Sorted Set 不是 JavaScript 数组，也不是"某个外部数组变化后 Redis
自动监听并排序"。是你每次通过 ZADD 等命令更新成员分数时，Redis
自动维护这个 Sorted Set 内部的排序。

常见用途：

-   积分排行榜。
-   热度排行。
-   延迟任务的到期时间排序。
-   按权重取成员。

### 6.7 Streams：保存消息的消息流

Streams 是 Redis 提供的消息流数据结构。

它不只是把消息广播给在线客户端，而是可以保存消息条目，并提供消费组等能力。

例如生产者写入一条任务：

``` redis
XADD shop:tasks * type send_sms orderId 1001
```

Redis 返回一个消息 ID。

消费者可以使用消费组读取：

``` redis
XGROUP CREATE shop:tasks sms-workers 0 MKSTREAM
```

``` redis
XREADGROUP GROUP sms-workers worker-1
  COUNT 1 BLOCK 5000
  STREAMS shop:tasks >
```

处理成功后确认：

``` redis
XACK shop:tasks sms-workers 消息ID
```

可以把相关角色理解为：

``` text
API 服务
  |
  | XADD：写入任务
  v
Redis Streams
  |
  | XREADGROUP：消费者读取
  v
Worker 后台进程
  |
  | 执行业务代码
  v
短信服务 / 邮件服务 / 其他业务
  |
  | XACK：确认处理完成
  v
Redis
```

这里 Redis 只保存和提供消息，真正发送短信的是 Worker 中的业务代码。

Streams 的消费组还涉及：

-   消费者组（Consumer Group）。
-   待处理消息（Pending Entries）。
-   消息确认（XACK）。
-   失败消息重新处理或转交（例如 XCLAIM / XAUTOCLAIM）。
-   消息保留和裁剪（例如 MAXLEN）。

Streams
提供了可靠消费所需的基础能力，但不意味着任务自动完成了"恰好执行一次"。消费者可能在业务执行成功、XACK
之前崩溃，导致消息被重新处理。因此业务需要幂等；还要配置持久化、消息保留和失败重试策略。

### 6.8 Pub/Sub：实时发布订阅

Pub/Sub 的主要用途是实时发布和广播。

订阅者：

``` redis
SUBSCRIBE shop:notice
```

发布者：

``` redis
PUBLISH shop:notice "有新订单"
```

Redis 会把消息发送给当时订阅该频道的客户端。

例如：

``` text
订单服务
   |
   | PUBLISH shop:notice
   v
Redis Pub/Sub
   |
   +---- 通知服务
   |
   +---- WebSocket 服务
   |
   +---- 其他在线订阅者
```

通知服务收到消息后，可以再通过 WebSocket 推送给 Vue 前端。

但 Pub/Sub 有一个关键限制：

**它不是默认可靠的离线消息队列。**

如果订阅者断开连接期间发布了消息，重新连接后不会自动补收错过的消息。Pub/Sub
不会为离线订阅者保存待消费消息。

### 6.9 Streams 与 Pub/Sub 的区别

| 对比 | Streams | Pub/Sub |
| --- | --- | --- |
| 是否保存消息条目 | 是 | 否，不提供可回放的消息历史 |
| 是否支持消费组 | 是 | 否 |
| 是否支持确认 | 支持 XACK | 不提供消息确认机制 |
| 断线后能否补收 | 在消息仍保留且消费状态可恢复时可以继续消费 | 不能补收断线期间错过的消息 |
| 典型用途 | 异步任务、消息处理 | 实时通知、在线广播 |
| 是否自动执行业务 | 否 | 否 |

选择时可以这样判断：

-   任务不能因为消费者暂时离线就丢掉：考虑 Streams 或专业消息队列。
-   只需要通知当前在线订阅者：可以考虑 Pub/Sub。
-   需要复杂路由、确认、死信队列和更完整的消息治理：还可以考虑
    RabbitMQ、Kafka、RocketMQ 等。

## 7. Node.js 如何连接 Redis

安装客户端库：

``` bash
npm install redis
```

注意：安装 npm 包只是安装客户端，不会启动 Redis 服务端。Redis
服务需要单独运行。

### 7.1 一次性演示脚本

``` js
import { createClient } from 'redis'

const client = createClient({
  url: 'redis://127.0.0.1:6379'
})

client.on('error', (err) => {
  console.error('Redis connection error:', err)
})

try {
  await client.connect()

  await client.set('study:hello', 'Redis', { EX: 60 })

  const value = await client.get('study:hello')
  console.log(value) // "Redis"；key 不存在时为 null
} finally {
  if (client.isOpen) {
    await client.quit()
  }
}
```

### 7.2 真实后端项目如何管理连接？

上面的代码适合独立演示脚本。

常驻 HTTP 服务通常在应用启动时建立 Redis
连接，之后复用这个客户端，而不是每个接口请求都重新创建客户端、重新连接。

可以抽成一个模块：

``` js
// redis.js
import { createClient } from 'redis'

export const redis = createClient({
  url: process.env.REDIS_URL ?? 'redis://127.0.0.1:6379'
})

redis.on('error', (err) => {
  console.error('Redis error:', err)
})

export async function connectRedis() {
  if (!redis.isOpen) {
    await redis.connect()
  }
}

export async function closeRedis() {
  if (redis.isOpen) {
    await redis.quit()
  }
}
```

业务代码复用连接：

``` js
import { redis } from './redis.js'

async function getUserCache(userId) {
  return redis.get(`study:user:${userId}:profile`)
}
```

生产项目还需要在应用启动、关闭时处理连接失败、重连和优雅退出。不要把连接密码写入日志或提交到代码仓库。

## 8. 原子操作、事务、Pipeline、Lua 与分布式锁

这一章是 Redis 并发控制的重点。

先看它们各自解决什么问题：

| 机制 | 主要解决的问题 | 核心作用 |
| --- | --- | --- |
| 单条原子命令 | 多个请求同时修改一个值 | 将一次操作作为不可分割的命令执行 |
| MULTI / EXEC | 多条命令需要连续执行 | 命令组执行期间不与其他客户端命令交错 |
| WATCH | 读取后可能被其他请求修改 | 检测冲突，放弃事务 |
| Pipeline | 多条命令网络往返过多 | 批量发送命令，降低通信成本 |
| Lua | 多条命令之间有判断和计算 | 在 Redis 服务端执行一段原子脚本 |
| 分布式锁 | 多个进程争抢同一业务操作 | 通过共享状态协调谁可以执行 |

### 8.1 单条命令原子，不代表多条命令自动原子

假设文章浏览量当前为 10。

错误的读改写方式：

``` js
const value = Number(await redis.get('study:article:17:views'))
const newValue = value + 1
await redis.set('study:article:17:views', newValue)
```

两个请求可能同时发生：

``` text
请求 A                         请求 B

GET -> 10                      GET -> 10
计算 10 + 1                    计算 10 + 1
SET -> 11                      SET -> 11
```

正确结果应该是 12，实际却是 11。这就是丢失更新。

原因：

-   GET 是一条命令。
-   SET 是一条命令。
-   但 GET + JavaScript 计算 + SET 不是一个原子整体。

优先使用 Redis 已提供的原子命令：

``` redis
INCR study:article:17:views
```

Node.js：

``` js
await redis.incr('study:article:17:views')
```

Redis 会把每次 INCR
作为一个原子命令执行。多个请求同时递增，不会出现两个请求都读取旧值再覆盖写入的问题。

类似命令还有：

``` redis
INCRBY study:counter 5
HINCRBY study:profile:1 age 1
SADD study:project:1:members user:1
```

如果内置命令已经能表达业务操作，通常优先使用内置命令，不要为了简单操作自己实现锁。

### 8.2 多条命令之间仍然可能失败

例如登录失败次数：

``` js
await redis.incr('study:login-fail:1001')
await redis.expire('study:login-fail:1001', 900)
```

这两条命令之间可能发生进程崩溃，导致 INCR 成功但 EXPIRE 没执行，Key
没有过期时间。

如果需求是"第一次失败时设置 15
分钟过期，后续失败不重置过期时间"，就需要把判断和操作设计成一个整体，后面可以使用
Lua 实现。

### 8.3 Redis 事务：MULTI / EXEC

Redis 事务使用 MULTI 和 EXEC：

``` redis
MULTI
INCRBY study:user:1001:points 10
INCR study:user:1001:tasks
EXEC
```

执行过程：

1.  `MULTI`：进入事务模式。
2.  后续命令先排队，通常返回 `QUEUED`，此时还没有执行这些命令。
3.  `EXEC`：连续执行排队的命令。
4.  执行这批命令期间，其他客户端的命令不会插入到这批命令之间。

Node.js 示例：

``` js
await redis.multi()
  .incrBy('study:user:1001:points', 10)
  .incr('study:user:1001:tasks')
  .exec()
```

Redis 事务与 MySQL InnoDB 事务有重要区别：

**Redis 不提供与 InnoDB 相同的失败回滚语义。**

例如先准备：

``` redis
SET study:a 10
SET study:b hello
```

然后执行：

``` redis
MULTI
INCR study:a
INCR study:b
EXEC
```

执行结果：

-   `INCR study:a` 成功，a 变成 11。
-   `INCR study:b` 因为值是 hello 而发生类型错误。
-   先前已经执行成功的 a 不会自动恢复为 10。

要区分两类错误：

-   **排队阶段错误**：例如命令语法或参数错误，可能导致整个事务无法执行。
-   **执行阶段错误**：例如类型不匹配，某条命令失败，但其他排队命令仍会继续执行，已经发生的修改不会自动回滚。

因此，Redis
事务主要提供命令组执行期间不被其他客户端命令交错的保证，不等于 MySQL
的完整事务回滚能力。

也不能用 Redis 事务把 MySQL 写入包进去。Redis 事务无法自动保证 MySQL 和
Redis 两边同时成功或同时回滚。

### 8.4 WATCH：乐观并发控制

WATCH 用于检测某个 Key 在事务执行前是否被其他客户端修改。

例如商品库存：

``` redis
WATCH study:product:1001:stock
GET study:product:1001:stock
MULTI
DECR study:product:1001:stock
EXEC
```

假设 A、B 都 WATCH 并读取到库存 1：

1.  A 先执行事务，库存变成 0。
2.  B 的事务执行前，Redis 发现被 WATCH 的 Key 已经改变。
3.  B 的 EXEC 放弃执行，事务冲突。

WATCH 不会把 Key 锁住。其他请求仍然可以读写它；WATCH
只是让提交方发现数据已变化，并放弃基于旧数据的操作。

这和 MySQL 乐观锁的思想类似：先读取，提交时检测版本或数据是否变化。

实际使用 WATCH 时要注意：

-   冲突后需要重试，或者返回业务失败。
-   在 Node.js 等并发环境中，WATCH
    与后续事务应使用隔离的客户端连接，避免不同请求共用连接时互相影响监视状态。
-   如果只是"检查库存大于 0，再扣减 Redis 库存"，Lua 通常更直接。
-   如果真实库存保存在 MySQL，Redis WATCH 不能代替 MySQL
    的条件更新、事务和约束。

### 8.5 Pipeline：优化网络通信，不是事务

假设需要读取 100 个用户缓存。

串行执行：

``` js
for (const userId of userIds) {
  await redis.get(`study:user:${userId}`)
}
```

每次都等待上一次响应，网络往返成本可能很高。

Pipeline 的思路是把多条命令批量发送，再集中读取结果，减少网络往返。

概念上：

``` text
普通调用：
发送 GET 1 -> 等结果
发送 GET 2 -> 等结果
发送 GET 3 -> 等结果

Pipeline：
批量发送 GET 1、GET 2、GET 3
             |
             v
        批量读取结果
```

Pipeline 不自动提供事务隔离、原子性或回滚。其他客户端命令可能在 Pipeline
中不同命令之间执行。

在 node-redis 中，事务和 Pipeline 的 API 要区分。常见版本可以使用：

``` js
const results = await redis.multi()
  .get('study:user:1')
  .get('study:user:2')
  .get('study:user:3')
  .execAsPipeline()
```

这里 `execAsPipeline()` 表示按 Pipeline 方式执行，而不是 MULTI/EXEC
事务语义。具体 API 以项目安装的 node-redis 版本为准。

### 8.6 Lua：把判断和操作放到 Redis 服务端执行

Lua 脚本的价值是：多条 Redis 命令之间有判断和计算时，可以把逻辑交给
Redis 服务端执行。

例如登录失败计数：

需求：

-   失败次数加一。
-   只有第一次失败时设置 15 分钟过期。
-   后续失败不重置过期时间。

Lua：

``` lua
local count = redis.call('INCR', KEYS[1])

if count == 1 then
    redis.call('EXPIRE', KEYS[1], 900)
end

return count
```

Node.js：

``` js
const count = await redis.eval(`
  local count = redis.call('INCR', KEYS[1])

  if count == 1 then
      redis.call('EXPIRE', KEYS[1], 900)
  end

  return count
`, {
  keys: ['study:login-fail:1001'],
  arguments: []
})
```

Lua 脚本执行期间，其他客户端命令不会插入脚本的执行过程。

配套代码实验见 [第17a章：Redis 登录失败限制](../../../node/node-backend-study/labs/17a-login-limit/README.md)。案例复用第16章认证，附中文学习标注，串起“登录前检查 → 失败计数与阈值 → 429 / Retry-After → 成功清零 → 到期恢复”，并说明 Redis 故障返回503及并发在途请求的边界。它与第18章查询缓存的进程内熔断计数是不同能力。

再看库存扣减：

``` lua
local stock = tonumber(redis.call('GET', KEYS[1]) or '0')

if stock <= 0 then
    return 0
end

redis.call('DECR', KEYS[1])
return 1
```

它在 Redis 服务端完成：

``` text
读取库存
  |
  v
判断库存是否大于 0
  |
  +---- 否：返回失败
  |
  +---- 是：扣减库存并返回成功
```

Lua 与 MULTI/EXEC 的区别：

-   MULTI/EXEC：先排队，再连续执行命令；不能在排队阶段根据尚未执行的 GET
    结果决定后续命令。
-   Lua：脚本可以先读取、判断，再决定执行哪些命令。

注意：

-   Lua 脚本执行期间会阻塞其他 Redis 命令，因此脚本必须短小。
-   不要在脚本里做 HTTP 请求、长时间计算或复杂业务流程。
-   Lua 脚本报错也不会自动撤销此前已经执行的写入。
-   Redis 内的 Lua 原子执行，不等于 MySQL 与 Redis 之间的跨系统事务。

### 8.7 分布式锁：协调多个后端进程

先看进程内锁：

``` js
let running = false

async function doTask() {
  if (running) return

  running = true
  try {
    await doSomething()
  } finally {
    running = false
  }
}
```

`running` 是当前 Node.js 进程中的变量。

如果部署了三个 Node.js 实例：

``` text
服务器 A：running = false
服务器 B：running = false
服务器 C：running = false
```

它们各自有独立内存，互相不知道对方的变量值。

Redis 分布式锁可以把类似的状态放到所有实例都能访问的 Redis 中。

``` redis
SET lock:order:1001 token-A NX EX 30
```

含义：

-   `lock:order:1001`：锁的 Key。
-   `token-A`：本次持有者的唯一标识。
-   `NX`：只有 Key 不存在时才设置成功。
-   `EX 30`：设置 30 秒过期时间。

`SET ... NX EX` 是一条原子命令。多个实例同时抢同一个不存在的锁
Key，只有一个能成功创建。

可以把它理解成：

``` text
进程内 running：
只有当前进程能看到

Redis lock Key：
连接同一 Redis 的多个进程都能看到
```

#### 分布式锁不是数据库强制锁

这是非常重要的边界：

**Redis 分布式锁只是 Redis 中保存了一个代表锁状态的数据。它不会自动锁住
MySQL 记录，也不会禁止其他程序执行 SQL 或 Redis 命令。**

例如服务 A 获得：

``` redis
SET lock:order:1001 token-A NX EX 30
```

Redis 中只是保存了：

``` text
lock:order:1001 = token-A
```

如果服务 B 绕过加锁代码，直接执行：

``` sql
UPDATE orders
SET status = 'paid'
WHERE id = 1001;
```

MySQL 并不知道 Redis 里存在这个 Key，因此 SQL 仍然可以执行。

分布式锁依赖所有参与者遵守同一套协议：

``` text
尝试获取锁
    |
    +---- 失败：不执行受保护的业务
    |
    +---- 成功：执行受保护的业务
                  |
                  v
                释放锁
```

因此它是应用层协调机制，而不是 MySQL 的行锁。

#### 为什么需要唯一 token？

不能只写：

``` redis
SET lock:order:1001 1 NX EX 30
```

然后在结束时直接：

``` redis
DEL lock:order:1001
```

因为锁可能已经过期，并被另一个实例重新获得。旧实例恢复后直接
DEL，可能误删新实例的锁。

所以每次加锁都使用唯一 token，释放时先比较当前值是否仍然是自己的 token。

可以使用 Lua：

``` lua
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end

return 0
```

Node.js 示例：

``` js
import { randomUUID } from 'node:crypto'

async function doProtectedTask() {
  const key = 'lock:order:1001'
  const token = randomUUID()

  const result = await redis.set(key, token, {
    NX: true,
    PX: 30000
  })

  if (result !== 'OK') {
    return false
  }

  try {
    await doBusinessWork()
    return true
  } finally {
    await redis.eval(`
      if redis.call('GET', KEYS[1]) == ARGV[1] then
          return redis.call('DEL', KEYS[1])
      end
      return 0
    `, {
      keys: [key],
      arguments: [token]
    })
  }
}
```

#### 锁过期后，旧进程恢复怎么办？

假设：

1.  A 获得 30 秒锁。
2.  A 执行任务时暂停了 40 秒。
3.  Redis 中的锁已经过期。
4.  B 获得新锁并开始执行。
5.  A 恢复，继续执行旧任务。

此时 A 和 B 可能同时操作业务数据。

唯一 token 可以防止 A 误删 B 的锁，但不能阻止 A 恢复后继续执行旧业务。

对重要业务，还要考虑：

-   合理设置锁租约和续期机制。
-   业务幂等。
-   数据库唯一约束和条件更新。
-   必要时使用 fencing token（栅栏令牌）等机制，拒绝旧持有者的过期操作。

不要把"设置了 EX"理解成"业务绝对不会并发"。

#### Redis 分布式锁与 MySQL 行锁

MySQL 示例：

``` sql
START TRANSACTION;

SELECT *
FROM orders
WHERE id = 1001
FOR UPDATE;

UPDATE orders
SET status = 'paid'
WHERE id = 1001;

COMMIT;
```

在事务持有相关行锁期间，与该锁冲突的数据库操作需要等待，或因超时、死锁等原因失败。

| 对比 | Redis 分布式锁 | MySQL 行锁 |
| --- | --- | --- |
| 锁在哪里 | Redis 中的 Key | InnoDB 内部锁机制 |
| 主要保护什么 | 遵守协议的跨进程业务操作 | 数据库记录的并发访问 |
| 是否要求业务主动检查 | 是 | SQL 由数据库执行锁协调 |
| 能否阻止绕过锁协议的请求 | 不能 | 冲突的数据库操作仍受数据库锁控制 |
| 是否自动回滚业务数据 | 否 | 配合 MySQL 事务可回滚事务修改 |
| 常见用途 | 多实例定时任务协调、任务去重 | 订单、余额、库存等数据库并发更新 |

对订单、账户余额、真实库存等核心数据，不能只依赖 Redis
分布式锁。通常还要使用 MySQL 事务、条件更新、唯一约束和幂等设计。

## 9. 重启后数据去哪了：RDB 与 AOF

Redis
主要在内存中工作，但可以通过持久化机制把数据保存到磁盘，以便重启后恢复。

如果没有启用持久化，Redis 进程退出后，原本只在内存中的数据不会自动恢复。

Redis 的两种主要持久化方式：

-   **RDB：保存某个时间点的数据快照。**
-   **AOF：记录数据修改操作，恢复时重放日志。**

### 9.1 RDB：数据快照

RDB 可以理解为给 Redis 当前数据集拍一张照片。

例如某个时间点：

``` text
study:user:1 = Tom
study:user:2 = Jack
study:views:17 = 100
```

Redis 生成 RDB 快照文件（常见名称为
`dump.rdb`），保存这个时间点的数据状态。

之后又发生修改：

``` redis
SET study:user:1 "Alice"
INCR study:views:17
```

内存变为：

``` text
study:user:1 = Alice
study:user:2 = Jack
study:views:17 = 101
```

但原来的 RDB 快照仍然保存：

``` text
study:user:1 = Tom
study:user:2 = Jack
study:views:17 = 100
```

如果在下一次快照之前发生故障，恢复时可能回到上一次快照的状态，丢失快照之后的修改。

常见触发方式：

-   配置 `save` 条件，达到条件后自动生成快照。
-   手工执行 `SAVE`（同步执行，可能阻塞）。
-   手工执行 `BGSAVE`（后台生成快照）。

示例配置：

``` conf
save 900 1
save 300 10
save 60 10000
dbfilename dump.rdb
```

这些条件表示不同时间窗口内达到指定修改次数时触发快照。它们只是示例，不是所有项目都应该照抄的固定配置。

RDB 的特点：

-   文件通常比较紧凑。
-   适合定期快照和备份。
-   恢复时加载快照，通常比较直接。
-   两次快照之间的修改可能丢失。
-   后台生成快照会有额外资源开销，尤其需要关注内存和 Copy-on-Write
    影响。

### 9.2 AOF：追加写操作日志

AOF（Append Only File）会记录用于修改数据集的写操作。Redis 重启时读取
AOF，并重放记录来恢复数据。

假设执行：

``` redis
SET study:user:1 "Tom"
SET study:user:2 "Jack"
INCR study:views:17
SET study:user:1 "Alice"
```

AOF 的逻辑记录可以理解为这些写操作。实际 AOF
文件格式和内部实现不必简单等同于一份人工编写的命令文本。

恢复时重新执行这些操作，最终得到：

``` text
study:user:1 = Alice
study:user:2 = Jack
study:views:17 = 1
```

### 9.3 为什么 AOF 也可能丢数据？

写入 AOF 缓冲区，不等于数据已经安全写入物理磁盘。

可以简化理解为：

``` text
Redis 收到写命令
    |
    v
修改内存数据
    |
    v
追加 AOF 数据
    |
    v
操作系统文件缓存
    |
    v
同步到持久化存储
```

如果机器突然断电，尚未安全落盘的数据仍可能丢失。

AOF 的 `appendfsync` 决定同步刷盘策略：

| 配置 | 含义 | 数据安全性与性能 |
| --- | --- | --- |
| `always` | 每次写入批次都请求同步刷盘 | 通常更安全，但磁盘同步开销更高 |
| `everysec` | 通常每秒同步一次 | 常见折中策略，故障时可能丢失最近约一秒的数据 |
| `no` | 由操作系统决定何时同步 | 刷盘时机不确定，数据丢失窗口可能更大 |

示例：

``` conf
appendonly yes
appendfsync everysec
```

`everysec`
是常见配置，但"最多只丢一秒"不应理解成任何硬件和故障条件下都严格保证的一秒上限。实际还受到操作系统和存储设备影响。

### 9.4 AOF 重写

如果 AOF 永远记录所有历史操作，文件会越来越大。

例如：

``` redis
SET study:counter 0
INCR study:counter
INCR study:counter
INCR study:counter
INCR study:counter
INCR study:counter
```

最终状态是：

``` text
study:counter = 5
```

AOF 重写可以根据当前数据集生成更精简的恢复记录，逻辑上可以简化成：

``` redis
SET study:counter 5
```

常见命令：

``` redis
BGREWRITEAOF
```

它会在后台启动 AOF 重写。

AOF
重写不是简单删除旧日志，而是重新生成能够恢复当前数据状态的文件。Redis 7
及之后版本使用多部分 AOF 结构，实际文件布局可能与旧版本不同。

### 9.5 RDB 和 AOF 可以同时开启吗？

可以。

| 对比 | RDB | AOF |
| --- | --- | --- |
| 保存什么 | 某个时间点的数据状态 | 数据修改操作 |
| 主要方式 | 定期生成快照 | 追加日志 |
| 恢复方式 | 加载快照 | 重放日志 |
| 文件特点 | 通常较紧凑 | 可能较大，需要重写 |
| 主要风险 | 上次快照之后的修改可能丢失 | 取决于刷盘策略 |
| 常见用途 | 快照备份、快速恢复 | 更细粒度的故障恢复 |

同时开启时，Redis 重启恢复通常优先使用 AOF，因为它一般比 RDB
快照更新。具体行为要结合 Redis 版本和配置。

### 9.6 不启用持久化

如果 Redis 只保存可以从 MySQL 重建的临时缓存，可以考虑不启用持久化。

但如果 Redis
保存会话、任务消息或重要状态，数据丢失可能影响用户体验或业务流程，需要谨慎评估。

### 9.7 持久化不等于备份

假设有人误操作：

``` redis
FLUSHALL
```

如果清空操作也进入 AOF，Redis 重启时可能恢复出"清空之后"的状态。

所以持久化主要解决：

> Redis 重启后，如何恢复最近保存的数据状态？

备份主要解决：

> 如果数据被误删、损坏或错误修改，能否恢复到过去某个正确时间点？

生产环境还需要考虑：

1.  本地 RDB / AOF 持久化。
2.  定期备份。
3.  将备份复制到其他磁盘或远程存储。
4.  定期进行恢复演练。
5.  对核心业务数据保留 MySQL 等可靠的最终数据来源。

Docker 部署时，还要把 Redis 数据目录挂载到持久化
Volume。否则删除容器时，容器可写层中的文件可能一起丢失。

## 10. 过期与内存淘汰不是一回事

这是 Redis 内存管理中非常重要的区别：

-   **TTL：业务设置的生命周期，时间到了就过期。**
-   **内存淘汰：Redis 达到配置的内存限制后，根据策略选择 Key
    删除或拒绝写入。**

### 10.1 TTL：时间驱动

``` redis
SET study:product:1 "商品A" EX 3600
```

表示商品缓存 3600 秒后过期。

### 10.2 内存淘汰：内存压力驱动

假设配置：

``` conf
maxmemory 2gb
```

当 Redis 用于数据集的内存达到配置上限，需要新增内存时，就会根据
`maxmemory-policy` 处理。

注意：`maxmemory` 是 Redis 用于触发内存管理策略的限制，不等于整台 Ubuntu
机器的物理内存上限。Redis 自身还有其他内存开销。

### 10.3 常见淘汰策略

| 策略 | 含义 |
| --- | --- |
| `noeviction` | 不主动淘汰 Key；达到限制后，部分需要新增内存的写操作报错 |
| `allkeys-lru` | 在所有 Key 中近似选择最近较少使用的 Key 淘汰 |
| `allkeys-lfu` | 在所有 Key 中近似选择访问频率较低的 Key 淘汰 |
| `allkeys-random` | 从所有 Key 中随机淘汰 |
| `volatile-lru` | 只在设置了过期时间的 Key 中按 LRU 选择 |
| `volatile-lfu` | 只在设置了过期时间的 Key 中按 LFU 选择 |
| `volatile-random` | 从设置了过期时间的 Key 中随机淘汰 |
| `volatile-ttl` | 优先选择剩余 TTL 较短的 Key |

### 10.4 LRU 与 LFU 的区别

LRU：Least Recently Used，最近最少使用。

它关注最近一次被访问的时间。可以粗略理解为：

``` text
商品 A：刚刚访问
商品 B：1 分钟前访问
商品 C：1 小时前访问
商品 D：3 天前访问
```

内存不足时，Redis 近似选择最近较少使用的 Key。

LFU：Least Frequently Used，访问频率较低。

它关注一段时间内的访问热度。可以粗略理解为：

``` text
商品 A：长期热门
商品 B：经常访问
商品 C：很少访问
商品 D：几乎没人访问
```

内存不足时，Redis 倾向于淘汰访问频率较低的 Key。

Redis 的 LRU / LFU
都是近似算法，会使用采样等机制，不应理解为每次都完整扫描所有 Key
后找出绝对最符合条件的那个。LFU 还带有访问频率衰减机制。

### 10.5 allkeys 与 volatile 的区别

-   `allkeys-*`：所有 Key 都可能成为淘汰候选，不管有没有 TTL。
-   `volatile-*`：只有设置了过期时间的 Key 才能成为淘汰候选。

例如：

| Key | 是否设置 TTL |
| --- | --- |
| `study:cache:product:1` | 是 |
| `study:session:1001` | 是 |
| `study:user:points:1` | 否 |

如果使用 `volatile-lru`，只有前两个 Key 可以成为淘汰候选。

如果所有 Key 都没有 TTL，就没有合适的 volatile 候选，Redis
可能无法释放足够空间，进而拒绝需要新增内存的写操作。

### 10.6 TTL 与淘汰的关系

假设：

``` redis
SET study:product:1 "商品A" EX 3600
```

才过去 10 分钟，Redis 内存就达到上限。

如果策略是 `allkeys-lru`，这个商品 Key 仍然可能被提前淘汰。

因此：

-   设置 TTL，不保证 Key 一定存活到过期时间。
-   没有设置 TTL，也不代表 Key 一定不会被淘汰；`allkeys-*` 可以淘汰没有
    TTL 的 Key。
-   Key 还可能被 DEL、故障或人为操作删除。

### 10.7 实际项目如何选择？

纯缓存与重要状态不宜随意混用同一淘汰策略。

例如：

``` text
Redis Cache
├── 商品详情缓存
├── 用户资料缓存
├── 文章内容缓存
└── 热门列表缓存

Redis State
├── 登录会话
├── 任务消息
└── 需要保留的业务状态
```

纯缓存通常可以回源重建，可以考虑 `allkeys-lru` 或 `allkeys-lfu`。

需要保护的状态可以考虑单独实例、容量规划、`noeviction`、持久化和可靠的业务数据来源。

即使拆分实例，也不代表 Redis 可以替代 MySQL 保存核心业务数据。

此外要给 Redis
进程、复制缓冲、持久化缓冲、快照期间的内存开销预留空间，不要把整台机器的全部物理内存都配置给
`maxmemory`。

## 11. 复制、Sentinel 与 Cluster

这一章主要回答两个问题：

1.  Redis 主节点故障，如何让其他节点接管？
2.  一台 Redis 容量和吞吐量不够，如何把数据分散到多台机器？

先区分三个概念：

| 能力 | 主要目的 | 不能保证什么 |
| --- | --- | --- |
| 主从复制 | 将主节点数据复制到副本 | 默认异步复制下，副本未必已收到最新写入 |
| Sentinel | 监控节点并协调故障转移 | 不负责把数据自动分片扩容 |
| Cluster | 按哈希槽分片，并配合复制和故障转移 | 不自动实现任意跨节点事务 |

### 11.1 主从复制：让副本拥有主节点的数据

假设有两台 Redis：

``` text
Redis A：192.168.1.10:6379
Redis B：192.168.1.11:6379
```

配置：

-   A：Master（主节点）。
-   B：Replica（副本节点）。

示意：

``` text
后端
 |
 v
Redis A（Master）
 |
 | 数据复制
 v
Redis B（Replica）
```

主节点处理写入，并把数据变化复制给副本。副本通常保存主节点数据集的副本，可以在合适场景下承担只读请求。

在副本上配置：

``` conf
replicaof 192.168.1.10 6379
```

也可以通过命令：

``` redis
REPLICAOF 192.168.1.10 6379
```

查看状态：

``` redis
INFO replication
```

主节点通常显示 `role:master`，副本通常显示 `role:slave` 或版本中对应的
replica 信息。

### 11.2 主从复制是异步的

Redis 默认使用异步复制。

可以简化成：

``` text
后端向 Master 写入
       |
       v
Master 修改自己的数据
       |
       v
Master 返回客户端成功
       |
       v
之后将数据变化传播给 Replica
```

所以主节点返回成功时，副本不一定已经收到最新数据。

如果 Master 在复制完成前故障，副本被提升为新
Master，那么最近已经确认成功但尚未复制到副本的写入可能丢失。

Redis 的 `WAIT`
命令可以等待指定数量的副本确认处理到某个复制偏移量，降低某些故障下丢失写入的概率，但它不能把
Redis 变成强一致的同步提交数据库。

### 11.3 主从复制解决什么，不解决什么？

解决：

-   让多个节点保存相同数据集。
-   为故障转移准备副本。
-   在业务允许读取旧数据的情况下分担部分读压力。

不解决：

-   不会自动把一份数据拆成多份。
-   不保证副本永远拥有最新写入。
-   不等于历史备份。
-   单独配置主从复制，不代表已经有自动故障转移机制。

### 11.4 Sentinel：监控主从节点并协调故障转移

Sentinel（哨兵）是 Redis 的监控和故障转移系统。

它主要负责：

1.  监控 Master 和 Replica 是否正常。
2.  多个 Sentinel 协调判断 Master 是否客观下线。
3.  选出负责故障转移的 Sentinel Leader。
4.  从可用副本中选择一个节点。
5.  将选中的副本提升为新 Master。
6.  让其他副本改为复制新的 Master。
7.  支持 Sentinel 的客户端重新发现新的 Master 地址。

示意：

``` text
                 Sentinel 1
                /           \
               /             \
Redis A（Master） ---------- Redis B（Replica）
               \             /
                \           /
                 Sentinel 2
                 Sentinel 3
```

生产环境通常建议至少部署三个
Sentinel，并尽量分布在不同机器或故障域，避免一个故障同时影响多数
Sentinel。

Sentinel 自己不负责保存业务数据，它负责监控和协调。

### 11.5 Sentinel 与主从复制的区别

-   主从复制：把数据从 Master 复制到 Replica。
-   Sentinel：监控主从节点，主节点故障时协调角色切换。

Sentinel 不负责数据分片，也不会让一份数据自动拆成多个部分。

例如：

``` text
Master A：完整数据集
Replica B：完整数据副本
```

所以 Sentinel
主要解决主节点故障后的高可用问题，不解决单机容量不足的问题。

客户端也需要支持 Sentinel，能够通过 Sentinel 发现当前
Master；如果客户端始终写死原 Master
的地址，故障转移后仍然可能连接错误的节点。

### 11.6 Cluster：把数据分散到多台主节点

如果一台 Redis 的内存和吞吐量无法满足业务，可以考虑 Redis Cluster。

Sentinel 的主从结构通常是多份完整数据副本：

``` text
Master A：完整数据
  └── Replica B：完整数据副本
```

Cluster 则把数据分散到不同主节点：

``` text
Master A：一部分数据
Master B：另一部分数据
Master C：另一部分数据
```

这叫数据分片（Sharding）。

### 11.7 Cluster 的 16384 个哈希槽

Redis Cluster 有 16384 个 Hash Slot（哈希槽）。

Redis 根据 Key 计算槽位，再根据槽位找到负责的节点。

计算方式：

``` text
HASH_SLOT = CRC16(key) mod 16384
```

例如：

``` redis
SET study:user:1001 "Tom"
```

示意过程：

``` text
study:user:1001
       |
       v
计算 CRC16 和槽位
       |
       v
假设得到槽位 5000
       |
       v
槽位 5000 属于 Master A
       |
       v
存储到 Master A
```

槽位范围：

``` text
0 ~ 16383
```

可以分配给不同 Master：

``` text
Master A：0 ~ 5460
Master B：5461 ~ 10922
Master C：10923 ~ 16383
```

以上只是均匀分配的示意。实际槽位分配由集群配置决定，不要求每个节点一定负责相同数量的槽位。

### 11.8 后端客户端如何访问 Cluster？

普通单机 Redis 客户端只需要连接一个地址。

Cluster 客户端需要知道槽位和节点的对应关系，根据 Key
的槽位把命令路由到正确节点。

node-redis 示例：

``` js
import { createCluster } from 'redis'

const cluster = createCluster({
  rootNodes: [
    { url: 'redis://192.168.1.10:6379' },
    { url: 'redis://192.168.1.11:6379' },
    { url: 'redis://192.168.1.12:6379' }
  ]
})

cluster.on('error', console.error)

await cluster.connect()

await cluster.set('study:user:1001', 'Tom')
const value = await cluster.get('study:user:1001')
```

这只是客户端连接示意，实际项目还需要根据部署环境配置认证、TLS、节点地址和连接管理。

### 11.9 Cluster 也可以有副本和故障转移

Cluster 中的每个 Master 可以配置 Replica：

``` text
Master A  -> Replica A
Master B  -> Replica B
Master C  -> Replica C
```

如果 Master A 故障，符合条件的 Replica A 可以参与故障转移，提升为新的
Master，并继续负责原来 Master A 的槽位。

Cluster
同样使用异步复制，因此也可能存在已经确认的写入尚未复制、故障切换后丢失的窗口。

### 11.10 Cluster 的跨槽位限制

假设执行：

``` redis
MSET study:user:1001 "Tom" study:product:2001 "iPhone"
```

如果两个 Key 被分配到不同槽位，就可能落在不同 Master 上。

Cluster 不提供任意跨槽位的多 Key 原子事务，可能返回：

``` text
CROSSSLOT Keys in request don't hash to the same slot
```

可以使用 Hash Tag，让相关 Key 落在同一个槽位：

``` redis
SET study:{user1001}:profile "Tom"
SET study:{user1001}:points 100

MGET study:{user1001}:profile study:{user1001}:points
```

Redis 计算槽位时，会优先使用大括号 `{}` 中的内容。因此这两个 Key
会被分配到同一个槽位。

但不要让大量无关 Key 都使用同一个 Hash
Tag，否则可能造成槽位热点，削弱分片的意义。

### 11.11 复制、分片与备份不是一回事

假设 Master 和 Replica 都有：

``` text
study:user:1001 = Tom
```

执行：

``` redis
DEL study:user:1001
```

删除操作也会被复制到副本，最终两边都没有这个 Key。

所以：

-   **复制**：让其他节点拥有当前数据的副本。
-   **分片**：把不同数据分配到不同节点。
-   **备份**：保留某个历史时间点的数据，以便误删或损坏后恢复。

副本不是天然的历史备份。生产环境需要独立备份和恢复演练。

### 11.12 三种架构怎么选？

| 架构 | 数据组织 | 主要目的 | 适用理解 |
| --- | --- | --- | --- |
| 单机 Redis | 一台服务保存数据 | 简单部署 | 学习、开发、小型项目 |
| 主从复制 | 多个节点保存相同数据 | 副本和读扩展基础 | 为故障转移做准备 |
| 主从 + Sentinel | 完整数据副本 + 自动故障转移 | 高可用 | 主节点故障时自动切换 |
| Redis Cluster | 多主节点分片 + 副本 | 水平扩容和高可用 | 单机容量或吞吐量不够 |

不是每个项目都需要 Cluster。单机 Redis
能满足容量、性能和可用性要求时，没有必要为了使用集群而使用集群。企业也经常使用云厂商托管
Redis，由服务商负责部分高可用和运维工作。

当前学习阶段先理解架构和边界即可，不需要立即搭建集群。

## 12. 排查问题时观察什么

常用命令：

``` redis
TYPE study:user:1
TTL study:user:1

INFO memory
INFO stats
INFO persistence
INFO replication

SLOWLOG GET 10

SCAN 0 MATCH study:* COUNT 100
```

### 12.1 SCAN 不等于一次性完整查询

`SCAN` 会返回下一次游标和本批结果，需要把返回的游标继续传回，直到游标为
0。

`COUNT` 是扫描工作量提示，不是保证每批返回的数量。

扫描期间数据可能发生变化，因此 SCAN
不是一致性快照；结果可能重复，需要调用方能容忍重复项。

在有大量 Key 的共享环境中，避免随意使用 `KEYS *` 做全量扫描。

### 12.2 常见观察方向

| 现象 | 可以检查 |
| --- | --- |
| Redis 内存持续增长 | `INFO memory`、Key 数量、大 Key、TTL |
| Key 意外消失 | TTL、淘汰策略、DEL、故障恢复、误操作 |
| Redis 响应慢 | `SLOWLOG`、大 Key、热 Key、网络和客户端等待 |
| 写入失败 | `maxmemory`、淘汰策略、权限、连接状态 |
| 副本数据落后 | `INFO replication`、复制连接和复制延迟 |
| 重启后数据不完整 | RDB/AOF 状态、刷盘策略、备份和恢复流程 |

`SLOWLOG` 主要记录 Redis
服务端命令执行耗时，不等于整个应用请求的总耗时。网络延迟、连接池等待和
Node.js 自身处理时间也可能导致请求慢。

### 12.3 安全与运维注意事项

-   Redis 不应在没有必要时直接暴露到公网。
-   使用 ACL、密码或其他认证机制，并配置网络访问控制。
-   不要把带密码的 Redis URL 写入日志或提交到代码仓库。
-   Key 前缀只是命名约定，不是权限隔离。
-   练习环境也不要随意在共享实例执行 `FLUSHDB` 或 `FLUSHALL`。

## 13. 关联阅读

-   [[20-后端/数据库/01-数据库基础]]
-   [[20-后端/数据库/02-SQL基础与数据库设计]]
-   [[20-后端/数据库/05-锁与并发控制]]
-   [[20-后端/数据库/55-InnoDB提交与刷盘]]
-   [[20-后端/认证与安全/01-登录认证与Cookie-JWT-Session重点总结]]：会话与认证相关用途。
-   [[20-后端/实践/Node后端学习项目/01-Node后端学习项目]]：学习项目入口。
-   [[20-后端/数据库/07-缓存]]：应用缓存设计、缓存一致性等内容。

官方文档：

-   [Redis 数据类型](https://redis.io/docs/latest/develop/data-types/)
-   [Redis 命令](https://redis.io/docs/latest/commands/)
-   [Redis
    事务](https://redis.io/docs/latest/develop/using-commands/transactions/)
-   [Redis
    Pipeline](https://redis.io/docs/latest/develop/using-commands/pipelining/)
-   [Redis
    持久化](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)
-   [Redis
    内存淘汰](https://redis.io/docs/latest/develop/reference/eviction/)
-   [Redis
    复制](https://redis.io/docs/latest/operate/oss_and_stack/management/replication/)
-   [Redis
    Sentinel](https://redis.io/docs/latest/operate/oss_and_stack/management/sentinel/)
-   [Redis
    Cluster](https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/)
-   [node-redis
    官方文档](https://redis.io/docs/latest/develop/clients/nodejs/)

本文示例以稳定的基础命令为主。Redis 服务端和客户端版本可能影响配置项及
API，实际使用前应核对项目版本和官方文档。

## 14. 动手自检

建议按下面顺序做小实验，不需要一开始就搭建 Sentinel 或 Cluster。

### 实验 A：基础命令与 TTL

1.  写入一个 10 秒过期的 String。
2.  使用 GET、TYPE、EXISTS、TTL 查看。
3.  等待过期后再 GET。
4.  对比 TTL 返回 -1 和 -2 的情况。
5.  观察普通 SET 覆盖 Key 后 TTL 是否保留。

### 实验 B：数据类型

分别创建并操作：

``` redis
SET study:hello "Redis"

HSET study:profile:1 name "Tom" age 20

RPUSH study:tasks "task-A" "task-B" "task-A"

SADD study:members "user:1" "user:2" "user:1"

ZADD study:ranking 100 "Tom" 80 "Jack" 120 "Alice"
```

回答：

-   Hash 为什么适合对象字段？
-   List 为什么允许重复？
-   Set 为什么不能保存重复成员？
-   Sorted Set 中再次给 Tom 设置新分数会发生什么？
-   List 的 LPOP 为什么不能直接等同于可靠任务消费？

### 实验 C：原子操作与并发

1.  用 GET + 应用计算 + SET 模拟并发计数。
2.  同时发起多个请求，观察是否丢失更新。
3.  改成 INCR，再比较结果。
4.  理解为什么 INCR + EXPIRE 仍是两条独立命令。

### 实验 D：事务、Pipeline 与 Lua

1.  用 MULTI/EXEC 执行两条命令。
2.  在事务中安排一条执行阶段会发生类型错误的命令，观察其他命令是否回滚。
3.  使用 Pipeline 批量读取多个 Key，理解它优化的是网络往返。
4.  使用 Lua 实现"库存大于 0 才扣减"。
5.  观察脚本执行期间其他命令不能插入脚本执行过程。

### 实验 E：分布式锁

1.  使用 `SET key token NX EX 30` 加锁。
2.  在两个独立客户端中同时尝试加锁。
3.  观察只有一个能成功。
4.  用比较 token 后删除的 Lua 脚本释放锁。
5.  思考：如果某个后端绕过加锁代码直接更新 MySQL，Redis
    锁能否阻止它？答案是不能。

### 实验 F：持久化

1.  查看 `INFO persistence`。
2.  观察 RDB 文件生成。
3.  开启 AOF，查看刷盘策略。
4.  在测试环境重启 Redis，观察数据恢复。
5.  了解持久化文件所在目录及 Docker Volume。

### 实验 G：内存淘汰与高可用概念

1.  查看 `maxmemory` 和 `maxmemory-policy`。
2.  理解 TTL 与淘汰的区别。
3.  画出 Master / Replica / Sentinel 的关系。
4.  画出 Cluster 不同 Master 分别负责不同槽位的关系。
5.  解释为什么 Replica 不是历史备份。

## 15. 学到什么程度算掌握

### 自测：先自己推演，再展开答案

> [!question]- 1. Redis 是独立服务，Node.js 的 redis 包只是客户端。
> `redis` npm 包只负责建立连接、发送命令和解析响应，数据保存在独立的 Redis 服务进程中。Node 进程退出不会自动带走 Redis 数据，Redis 能否恢复取决于自身的持久化配置。

> [!question]- 2. 多个服务可以运行在一台机器上，不等于需要多台服务器。
> Node.js、MySQL、Redis 是不同服务，可以监听不同端口运行在同一台主机，也可以用 Docker 容器隔离。只有容量、隔离或可用性需要时，才拆到多台服务器。

> [!question]- 3. String、Hash、List、Set、Sorted Set 分别适合什么数据。
> String 适合字符串、JSON 文本和计数；Hash 适合对象的多个字段；List 适合有顺序、允许重复的队列或记录；Set 适合去重和集合运算；Sorted Set 适合按分数排序的排行榜和延迟任务。

> [!question]- 4. Hash 和 List 的结构差异；Sorted Set 为什么能维护排行榜。
> Hash 是字段到值的映射，字段唯一，不用于表达元素顺序；List 是有序、允许重复的元素序列。Sorted Set 为每个唯一成员保存 Score，并按 Score 维护顺序，因此重复 ZADD 同一成员是更新分数，排行榜能自动保持有序。

> [!question]- 5. Streams 与 Pub/Sub 的消息保存和离线消费差异。
> Streams 会把消息条目保存在 Redis 中，支持消费组、Pending 和 XACK，消费者离线后可以在消息仍保留时继续消费；Pub/Sub 只向当时在线的订阅者广播，不保存历史，断线期间的消息不会补发。

> [!question]- 6. 为什么 GET + SET 会发生丢失更新，而 INCR 不会。
> GET 和 SET 是两条独立命令，两个请求可能都读到旧值，再分别写回相同的新值，后写覆盖先写。INCR 在 Redis 服务端作为一条原子命令完成读取、加一和写回，其他命令不能插入其中。

> [!question]- 7. MULTI/EXEC、WATCH、Pipeline、Lua 分别解决什么问题。
> MULTI/EXEC 让一组命令连续执行，期间不被其他客户端命令插入；WATCH 检测事务前的 Key 是否被改动，冲突时放弃事务；Pipeline 批量发送命令以减少网络往返，但不提供事务原子性；Lua 在服务端原子执行带判断和计算的脚本。

> [!question]- 8. Redis 事务为什么不能按 MySQL 的回滚语义理解。
> Redis 事务只保证排队命令连续执行；执行阶段某条命令因类型错误失败时，其他命令仍会继续执行，已经成功的修改不会自动回滚。它不能替代 InnoDB 的完整事务回滚，也不能把 MySQL 和 Redis 包成跨系统事务。

> [!question]- 9. Redis 分布式锁为什么只是应用层协调，不能锁住 MySQL 记录。
> 锁只是 Redis 中的一个 Key，MySQL 不知道它的存在；绕过加锁代码的 SQL 仍然可以执行。它依赖所有参与者遵守同一套加锁协议，不能替代 MySQL 的行锁、事务、条件更新和唯一约束。

> [!question]- 10. 为什么分布式锁需要唯一 token、过期时间和比较后删除。
> 过期时间避免持有者崩溃后锁永久不释放；唯一 token 标识本次持有者；释放时先比较当前值是否仍是自己的 token，再删除，避免锁已过期并被别人重新获得后误删新持有者的锁。

> [!question]- 11. RDB 和 AOF 的区别，以及为什么持久化不等于备份。
> RDB 保存某个时间点的数据快照，文件紧凑、恢复直接；AOF 记录写操作并在重启时重放，通常能减少丢失窗口，但受刷盘策略影响。持久化只保证重启后尽量恢复最近状态；误删、损坏或错误修改也会被持久化，所以还需要独立备份和恢复演练。

> [!question]- 12. TTL 和内存淘汰为什么是两套独立机制。
> TTL 由业务设置，按时间让 Key 过期；内存淘汰在 Redis 达到 `maxmemory` 后按策略选择 Key 删除或拒绝写入。设置了 TTL 的 Key 仍可能被提前淘汰，没有 TTL 的 Key 也可能被 `allkeys-*` 策略淘汰。

> [!question]- 13. 主从复制、Sentinel、Cluster 分别解决什么问题。
> 主从复制把主节点数据复制到副本，为读扩展和故障转移提供基础；Sentinel 监控主从节点并在主节点故障时协调故障转移；Cluster 按哈希槽把数据分片到多个主节点，并配合副本和故障转移实现水平扩容与高可用。

> [!question]- 14. 为什么副本不是历史备份，为什么异步复制存在数据丢失窗口。
> 副本持续跟随主节点的当前状态，主节点上的删除和错误修改也会复制过去，所以副本不能恢复误删前的历史版本。Redis 默认异步复制，主节点返回成功时副本可能还没收到最新写入；主节点故障切换后，这部分已确认但未复制的写入可能丢失。

------------------------------------------------------------------------

## 阅读导航

上一篇：[[20-后端/数据库/05-锁与并发控制]]

下一篇：[[20-后端/数据库/07-缓存]]

返回：[[20-后端/数据库/00-数据库学习导航]]
