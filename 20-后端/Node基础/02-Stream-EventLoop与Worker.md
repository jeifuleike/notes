# Stream、Event Loop 与 Worker Threads

## 1. 什么是 I/O

I/O = Input / Output。

后端常见 I/O：

```text
读文件
写文件
MySQL
Redis
HTTP API
Socket
上传下载
日志
```

I/O-bound：

```text
大部分时间在等待
```

CPU-bound：

```text
大部分时间在计算
```

---

## 2. 同步 I/O 的问题

```ts
fs.readFileSync(...)
```

会阻塞 JS 主线程。

在高频请求里使用会造成：

```text
当前请求
↓
阻塞 Event Loop
↓
其他请求一起排队
```

异步：

```ts
await fs.promises.readFile(...)
```

不会阻塞 JS 主线程。

但仍然会一次性把整个文件读进内存。

---

## 3. Stream

大文件更适合：

```ts
const stream = fs.createReadStream('./big.txt')

stream.pipe(res)
```

数据流：

```text
Disk
↓
Readable Stream
↓
Buffer Chunk
↓
Writable Stream
↓
Network
```

常见 Stream：

```text
Readable
Writable
Duplex
Transform
```

---

## 4. Backpressure

如果磁盘读取速度比网络发送速度快：

```text
生产者 > 消费者
```

Writable 内部缓冲区可能越来越满。

```ts
const ok = res.write(chunk)
```

如果：

```ts
ok === false
```

代表：

> 暂时别继续写，等消费者消化。

之后等待：

```ts
res.once('drain', ...)
```

`pipe()` 会自动协调这种暂停和恢复。

所以：

```ts
readStream.pipe(res)
```

不只是语法糖。

---

## 5. Event Loop

Node 更准确的说法：

> JS 业务代码主要运行在一个主线程上，但 Node 进程并不只有一个线程。

典型执行顺序：

```text
同步代码
↓
process.nextTick
↓
Promise Microtask
↓
Event Loop Phases
```

常见例子：

```ts
console.log(1)

setTimeout(() => {
  console.log(2)
}, 0)

Promise.resolve().then(() => {
  console.log(3)
})

console.log(4)
```

输出：

```text
1
4
3
2
```

---

## 6. `await` 不等于阻塞线程

```ts
const user = await db.query(...)
```

`await` 的意思是：

> 当前 async 函数暂停，等 Promise 结果。

不是：

> 整个 Node 进程停住。

因此等待数据库期间，Event Loop 仍可以处理其他请求。

---

## 7. 真正会阻塞 Node 的代码

```ts
const start = Date.now()

while (Date.now() - start < 5000) {}
```

这 5 秒里：

```text
JS Main Thread 被占满
↓
Event Loop 无法继续
↓
所有其他请求被卡住
```

这就是 CPU-bound 对 Node 主线程的危险。

---

## 8. Thread 不等于 CPU Core

```text
CPU Core
= 硬件执行资源

Thread
= 软件执行流
```

8 核 16 线程 CPU：

```text
16 个逻辑处理器
```

不是：

```text
最多只能有 16 个软件线程
```

操作系统可以同时管理成百上千个软件线程，并进行调度。

---

## 9. Worker Threads

CPU 密集型任务可以交给 Worker：

主线程：

```ts
const worker = new Worker(
  new URL('./worker.ts', import.meta.url),
  {
    execArgv: ['--import', 'tsx'],
  },
)

worker.postMessage(5000)
```

Worker：

```ts
import {
  parentPort,
} from 'node:worker_threads'

parentPort?.on('message', (ms: number) => {
  const end = Date.now() + ms

  while (Date.now() < end) {}

  parentPort?.postMessage('done')
})
```

通信：

```text
Main:
worker.postMessage(...)

        ↓

Worker:
parentPort.on('message')

        ↓

Worker:
parentPort.postMessage(...)

        ↓

Main:
worker.on('message')
```

---

## 10. `done` 不是 Node 固定关键字

```ts
parentPort?.postMessage('done')
```

只是在发送一条普通消息。

真正含义由你自己的协议决定：

```ts
worker.on('message', msg => {
  if (msg === 'done') {
    resolve()
    worker.terminate()
  }
})
```

这里：

```text
'done'
```

代表的是：

> 我们自己约定的“任务完成”信号。

---

## 11. 一次性 Worker 与 Worker Pool

一次性：

```text
创建 Worker
↓
执行任务
↓
done
↓
terminate
```

Worker Pool：

```text
预创建 N 个 Worker
↓
空闲 Worker 接任务
↓
完成
↓
重新变成 idle
↓
继续接任务
```

Worker Pool 的核心价值：

```text
避免频繁创建 / 销毁线程
```

CPU-bound Worker 数量通常不会无限增加，而是结合 CPU 逻辑核心数和实际 Benchmark 控制。

---

## 12. 什么时候用什么

```text
数据库 / Redis / HTTP
→ async / await

大文件
→ Stream

CPU 重计算
→ Worker Threads

大量 CPU 任务
→ Worker Pool

单进程吞吐不够
→ 多进程 / 多实例 / 容器 / 负载均衡
```


## 关联学习

[[20-后端/实践/Node后端学习项目/01-Node后端学习项目]]
