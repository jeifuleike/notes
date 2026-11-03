# Redis

先学 Redis 服务、命令、数据类型、TTL、客户端、持久化及运维。应用结果缓存策略已独立到下一篇。

## 1. Redis 是什么

Redis 是独立运行的数据服务，主要在内存中保存和操作数据，通过网络向应用提供读写能力。

最基础的访问方式是：

```text
key（键） → value（值）

study:user:1 → {"id":1,"name":"小明"}
```

key 是程序给数据起的名字。value 是这个名字对应的内容，可以是字符串，也可以是列表、集合等结构。

Redis 常被用来做缓存，也能用于计数、排行榜、会话等。Redis 是一种数据服务，缓存是它的一种用途，二者不是同一个概念。

### 与 JavaScript 对象、Map 的关系

```js
const cache = new Map()
cache.set('study:user:1', '{"id":1,"name":"小明"}')
```

这个例子只用来类比“按名字存取”。真正的区别是：

| 维度 | 进程内 Map | Redis |
| --- | --- | --- |
| 数据在哪 | 当前 Node 进程内 | 独立 Redis 服务内 |
| 多进程共享 | 需要额外实现 | 多个进程可以连接同一实例 |
| 访问成本 | 本地内存访问 | 通常包含网络通信 |
| 过期管理 | 自行实现 | 提供过期命令 |
| Node 重启 | Map 数据丢失 | Redis 未重启时仍可保留数据 |

Redis 自己重启后能恢复多少数据，要看它的持久化配置，不能因为它独立于 Node 就认为数据永远存在。

## 2. 为什么通常很快，以及为什么仍可能慢

Redis 常见操作主要在内存中执行，提供直接操作数据结构的命令，并通过事件循环处理请求。按 key 定位通常不需要扫描所有 key。

但不能把“Redis 很快”理解为所有操作成本相同：

- 简单字符串 GET、SET 通常很轻量。
- 返回整个超大集合，需要遍历和传输大量元素。
- 网络距离、连接排队、慢命令、大 value 都会增加延迟。
- MySQL 本身也使用缓冲池，不能用“Redis 读内存，MySQL 永远读磁盘”解释全部差异。

“Redis 是单线程”也需要限定：常见命令的主要执行路径通常串行处理，但网络 I/O、后台任务、持久化等可以涉及其他线程或进程。不能据此认为一次业务中的多个命令自动成为不可分割的整体。

## 3. 服务端、客户端和应用之间的关系

```text
浏览器
  ↓ HTTP
Node / Express
  ├─ mysql2 客户端 → MySQL 服务
  └─ redis 客户端  → Redis 服务
```

redis-server 是提供存储能力的服务端；redis-cli 是手工执行命令的客户端；Node 的 redis 包是代码使用的客户端库。

安装 npm 包不等于启动 Redis 服务，装好 Docker 也不等于 Redis 容器已经运行。常见默认端口是 6379，具体使用连接配置为准。

本文讲通用知识。Windows 环境启动、学习端口和项目配置见 [第 17 章运行说明](../../../node/node-backend-study/labs/17-redis-cache/README.md)，避免在两处维护同一份运行步骤。

## 4. 先学 key、value 和基本命令

下面代码块是 redis-cli 中的命令，不是 PowerShell 命令，也不是 SQL。

```text
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
| PING | 检查命令通路是否有响应 | PONG |
| SET key value EX 60 | 写入字符串，设置 60 秒有效期 | OK |
| GET key | 读取字符串 | 内容；不存在返回 nil |
| TYPE key | 查看值的数据类型 | string、hash 等 |
| EXISTS key | 查看 key 是否存在 | 单 key 时 1 或 0 |
| TTL key | 查看剩余秒数 | 剩余秒数、-1、-2 |
| DEL key | 删除 key | 实际删除的 key 数量 |

重复删除不存在的 key 返回 0，通常不是异常。字符串键被写成 List 后再用 GET 读取，会出现类型不匹配错误；Redis 的命令要与值的类型对应。

### key 命名

```text
study:17:user:1
study:17:user:2
study:login-fail:account:42
```

前缀表达应用、用途和实体标识。冒号是命名习惯，不会创建文件夹，也不会带来访问隔离。

多个环境共享服务时，需要明确区分命名空间。若缓存内容依赖租户、语言或查询条件，这些维度也要体现在 key 的设计中，否则可能返回另一种上下文的数据。

## 5. TTL：数据为什么会消失

TTL 是剩余生存时间。对普通 key 的过期设置，是给整个 key 设置有效期限。

```text
SET study:ttl "hello" EX 30
TTL study:ttl
GET study:ttl
```

| TTL 返回 | 含义 |
| --- | --- |
| 大于等于 0 | 剩余有效秒数，接近到期时可以为 0 |
| -1 | key 存在，但没有过期时间 |
| -2 | key 不存在 |

GET 不会自动续期。再次执行普通 SET 覆盖同名 key 时，原 TTL 默认会被移除；需要在写入时重新指定 EX，或按需求使用 KEEPTTL。

下面两条命令之间存在中断窗口：

```text
SET study:temporary "value"
EXPIRE study:temporary 60
```

如果应用在第二条之前失败，数据可能没有过期时间。因此，写缓存优先用一条 `SET key value EX seconds` 同时完成。

过期处理结合访问时检查和后台清理；到期后不能继续把该 key 当有效数据读取，但不需要想象每个 key 都有一个精确到瞬间释放内存的独立定时器。命令语义见 [SET](https://redis.io/docs/latest/commands/set/) 与 [EXPIRE](https://redis.io/docs/latest/commands/expire/)。

## 6. 常用数据类型：按需求选择

以下先学常见的基础类型，不是 Redis 所有能力的完整清单。数据类型决定可以使用哪些命令；概览见 [Redis 数据类型](https://redis.io/docs/latest/develop/data-types/)。

### 1. String：字符串、JSON 文本、整数计数

```text
SET study:user:1 '{"id":1,"name":"小明"}' EX 60
GET study:user:1
INCR study:page:views
INCRBY study:page:views 5
```

String 保存字节序列。JSON 在这里是一段字符串，并不会因为内容长得像对象，就自动变成可以通过字段查询的原生结构。

INCR 对可以解析为整数的字符串递增；key 不存在时以 0 为起点。普通文本不能直接递增。

### 2. Hash：同一个对象的多个字段

```text
HSET study:profile:1 name "Tom" age 20
HGET study:profile:1 name
HGETALL study:profile:1
```

Hash 是一个 key 下的字段和值集合。与“把整个对象转成 JSON String”相比，它便于单独操作字段。它不是关系表，没有自动外键，也不自动执行 JOIN。

### 3. List：有顺序、允许重复

```text
RPUSH study:tasks "task-A" "task-B" "task-A"
LRANGE study:tasks 0 -1
LPOP study:tasks
```

本例从右侧加入、左侧取出，体现先进先出。只会 LPUSH / RPOP 不代表已经实现可靠任务队列：任务取出后消费者崩溃，还需要确认、重试和幂等设计。

### 4. Set：无重复成员

```text
SADD study:project:1:members "user:1" "user:2" "user:1"
SISMEMBER study:project:1:members "user:1"
SMEMBERS study:project:1:members
```

适合去重和成员判断，没有可依赖的排列顺序。成员集合很大时，直接取全部成员会产生较大开销。

### 5. Sorted Set：成员唯一，按分数排序

```text
ZADD study:ranking 100 "Tom" 80 "Jack" 120 "Alice"
ZRANGE study:ranking 0 2 REV WITHSCORES
```

适合积分榜。再次给同一成员赋分会更新该成员分数，不会插入一个重复成员。

### 6. Streams、Pub/Sub：先知道区别

Streams 保存可读取的条目，并支持消费组；可靠处理还需要管理确认、待处理消息和重试。

Pub/Sub 面向实时发布订阅，断开的订阅者不会在重新连接后自动补收错过的消息。不能把它当作默认可靠的离线任务队列。

## 7. Node 如何访问 Redis

下面只演示独立的客户端基础，不提供项目 TODO 的完整答案。假设已安装 redis 包，Redis 正在本机提供服务。

```js
import { createClient } from 'redis'

const client = createClient({ url: 'redis://127.0.0.1:6379' })
client.on('error', () => console.error('Redis connection error'))

try {
  await client.connect()
  await client.set('study:hello', 'Redis', { EX: 60 })
  const value = await client.get('study:hello')
  console.log(value) // string；key 不存在时为 null
} finally {
  if (client.isOpen) client.destroy()
}
```

这是一次性演示脚本，所以结束时释放客户端。常驻 HTTP 服务通常在启动时建立并复用连接，在退出时统一关闭，不要每个请求都重新 connect。destroy 是立即关闭，不能把它当成等待未完成命令处理完毕的优雅退出。

### JSON 与 TypeScript 的边界

```text
JavaScript 对象
  ↓ JSON.stringify
JSON 字符串
  ↓ SET / GET
JSON 字符串
  ↓ JSON.parse
运行时仍需要检查的数据
```

JSON.parse 可能抛错。即使解析成功，也可能得到数字、数组或不符合 User 结构的对象；TypeScript 的 `as User` 不会在运行时校验。

因此缓存读取通常需要检查字段类型、必填字段及用户 ID 是否与当前 key 对应。损坏内容可以按未命中处理，但 Redis 网络错误与 JSON 格式错误应该分别处理。

客户端的连接、错误事件和版本相关 API 以 [node-redis 官方文档](https://redis.io/docs/latest/develop/clients/nodejs/) 为准，不混用其他客户端或旧版示例。

## 8. 原子操作、事务、锁分别解决什么

### 1. 单条命令与多条命令

```text
GET study:counter → 得到 10
应用计算 10 + 1
SET study:counter 11
```

两个请求同时读到 10，最终都写 11，就少计了一次。INCR 将这次递增放进一个原子命令执行，可以避免这种读改写竞争。

但 `INCR` 后再发 `EXPIRE` 仍是两条命令，可能在中间失败。不要把“每条命令原子”推导成“任意一串命令都原子”。

### 2. Redis 事务与 MySQL 事务

MULTI 将命令排队，EXEC 时连续执行，其他客户端命令不会插入该批命令之间；WATCH 可以在受监视的 key 改变时让事务放弃执行。

Redis 不提供与 InnoDB 相同的失败回滚语义。执行阶段某条命令因类型不匹配而出错，不代表已经执行的其他命令都会撤销。也不能用 Redis 事务把 MySQL 写入包进去。见 [Redis 事务](https://redis.io/docs/latest/develop/using-commands/transactions/)。

### 3. Pipeline

Pipeline 将多条命令批量发送，减少网络往返。它优化通信成本，不自动提供事务隔离或回滚；见 [Pipeline](https://redis.io/docs/latest/develop/using-commands/pipelining/)。

### 4. Lua 与分布式锁

Lua 脚本可以把判断和操作放到服务端连续执行，脚本执行期间会阻塞其他命令，所以脚本应短小；脚本报错也不自动撤销先前写入。

分布式锁用于多个进程之间协调操作。只看到 `SET key value NX EX seconds` 还不足以设计可靠锁，还涉及唯一持有者标识、租约过期、比较后删除与暂停后恢复等问题。MySQL 行锁与 Redis 分布式锁有不同作用范围，不要混成一个概念。

## 9. 重启后数据去哪了：RDB 与 AOF

“主要在内存中工作”不代表完全不能持久化。

| 方式 | 基本思路 | 主要边界 |
| --- | --- | --- |
| RDB | 保存某时刻的数据快照 | 故障可能丢失最近快照之后的修改 |
| AOF | 记录写操作，重启时重放恢复 | 数据安全和性能受刷盘策略影响 |
| 不启用持久化 | 只保留运行中的数据 | 重启后需要重建数据 |

AOF 每秒刷盘等策略并非每条成功命令都同步落盘；RDB 也不是“每次 SET 都完整保存一遍”。选择要结合可接受丢失范围和性能预算。

缓存通常可以回源重建，而会话等状态丢失会影响用户体验。因此不能照抄另一用途的持久化配置。持久化也不能替代独立备份及恢复演练。见 [Redis 持久化](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)。

## 10. 过期与内存淘汰不是一回事

TTL 处理“时间到了”。内存淘汰处理“达到配置的内存限制后怎么办”。

| 策略举例 | 含义 |
| --- | --- |
| noeviction | 不主动淘汰，达到限制后部分需要新增内存的写操作报错 |
| allkeys-lru | 在所有 key 中近似选择最近较少使用的 key 淘汰 |
| allkeys-lfu | 在所有 key 中近似选择访问频率较低的 key 淘汰 |
| volatile-lru | 只在设置了过期时间的 key 中选择淘汰对象 |

这不是完整策略表。没有合适的候选 key 时，也可能无法释放足够空间。设置 TTL 不保证该 key 到期前一直存在，因为它还可能被删除、淘汰或因故障丢失。

纯缓存与必须保留的状态不宜随意混用同一淘汰配置。还要为进程本身、复制及持久化缓冲等预留内存，不能把全部机器内存都分给业务 value。见 [内存淘汰](https://redis.io/docs/latest/reference/eviction/)。

## 11. 复制、Sentinel 与 Cluster

| 能力 | 主要目的 | 不能保证什么 |
| --- | --- | --- |
| 主从复制 | 将主节点数据复制到副本 | 默认异步复制下，副本未必已收到最新写入 |
| Sentinel | 监控及协调故障转移 | 不负责把数据自动分片扩容 |
| Cluster | 按哈希槽分片并配合复制、故障转移 | 不自动实现任意跨节点事务 |

复制、分片和备份分别解决不同问题。删除命令也可能复制到副本，因此副本不是天然的历史备份。复制与故障转移仍可能有数据丢失窗口，见 [Redis 复制](https://redis.io/docs/latest/operate/oss_and_stack/management/replication/)。

这部分先知道用途即可，当前学习无需搭建集群。

## 12. 排查问题时观察什么

```text
TYPE study:user:1
TTL study:user:1
INFO memory
INFO stats
SLOWLOG GET 10
SCAN 0 MATCH study:* COUNT 100
```

SCAN 返回下一次游标和本批结果，要继续传回游标，直到游标为 0。COUNT 是扫描工作量提示，不是保证每批返回的数量；扫描期间数据变化时也不能把它当作一致性快照，返回项可能重复。

关注命中与未命中、内存、淘汰、延迟和回源量。INFO stats 中的命中统计属于实例统计，未必等于某个业务接口的命中率。SLOWLOG 主要记录服务端命令执行耗时，不能覆盖全部网络与应用等待。

大 key 指单个 key 内容过多或过大；热 key 指请求集中到少量 key。一个 key 可以很小但很热，两者处理方式不同。

在有大量 key 的共享环境避免随意使用 KEYS 全量扫描，不用 FLUSHDB / FLUSHALL 清理练习。网络访问、ACL 与凭证需要明确配置；key 前缀不能代替权限控制，也不应把带密码的连接 URL 写进日志。

## 13. 关联阅读

- [[20-后端/数据库/01-数据库基础]]
- [[20-后端/数据库/02-SQL基础与数据库设计]]
- [[20-后端/数据库/55-InnoDB提交与刷盘]]
- [[20-后端/认证与安全/01-登录认证与Cookie-JWT-Session重点总结]]：会话与认证相关用途。
- [[20-后端/实践/Node后端学习项目/01-Node后端学习项目]]：学习项目入口。

本文示例优先采用稳定的基础命令；官方 latest 文档可能包含更新版本或额外功能，使用前核对服务端和客户端版本。参考链接已放在对应主题处，便于进一步阅读。

## 14. 动手自检

保存一个 10 秒有效的字符串，观察 SET、GET、TTL、DEL；分别操作 String、Hash、List、Set、Sorted Set；再用 Node 完成连接和 JSON 读写。先证明工具能用，再进入缓存设计。

## 阅读导航

上一篇：[[20-后端/数据库/05-锁与并发控制]]。

下一篇：[[20-后端/数据库/07-缓存]]。

返回 [[20-后端/数据库/00-数据库学习导航]]。
