# Express 分层架构：Router / Controller / Service / Repository

## 1. 核心调用链

```text
HTTP Request
↓
Router
↓
Controller
↓
Service
↓
Repository
↓
Database
```

返回：

```text
Database
↓
Repository
↓
Service
↓
Controller
↓
HTTP Response
```

---

## 2. Router

职责：

> 什么 Method + 什么 URL，由谁处理。

```ts
router.get('/', getUsers)

router.get('/:id', getUserById)

router.post('/', createUser)

router.delete('/:id', deleteUser)
```

Router 不应该写复杂业务。

---

## 3. Controller

职责：

```text
读取 HTTP 参数
↓
调用 Service
↓
决定 HTTP Status
↓
返回 Response
```

例如：

```ts
export function getUserById(
  req: Request,
  res: Response,
) {
  const id = Number(req.params.id)

  const user =
    userService.getUserById(id)

  res.json({
    data: user,
  })
}
```

Controller 应该知道：

```text
req
res
params
query
body
header
statusCode
```

但尽量不要知道：

```text
SQL
复杂业务规则
数据库实现
```

---

## 4. Service

职责：

> 真正的业务逻辑。

```ts
export function getUserById(
  id: number,
): User {
  const user =
    userRepository.findById(id)

  if (!user) {
    throw ...
  }

  return user
}
```

Service 不应该出现：

```ts
req
res
```

因为 Service 不属于 HTTP。

理论上：

```text
HTTP
IPC
CLI
WebSocket
Scheduler
```

都可以调用同一个 Service。

---

## 5. Repository

职责：

> 怎么访问数据。

```ts
export function findById(
  id: number,
): User | undefined {
  return users.find(
    user => user.id === id,
  )
}
```

现在可以是数组。

以后可以替换成：

```text
MySQL
PostgreSQL
Prisma
TypeORM
远程 API
```

Service 不需要知道底层实现。

---

## 6. DTO / Types

```ts
export interface User {
  id: number
  name: string
  age: number
}

export interface CreateUserDTO {
  name: string
  age: number
}
```

DTO：

```text
Data Transfer Object
```

用于描述：

> 这个接口允许传什么数据。

例如创建用户时：

```text
客户端允许传：
name
age

客户端不应该决定：
id
createdAt
role
```

---

## 7. 推荐的 Feature-first 目录

```text
src/
├─ common/
│
├─ user/
│  ├─ user.router.ts
│  ├─ user.controller.ts
│  ├─ user.service.ts
│  ├─ user.repository.ts
│  └─ user.types.ts
│
├─ task/
│  ├─ task.router.ts
│  ├─ task.controller.ts
│  ├─ task.service.ts
│  └─ task.repository.ts
│
└─ server.ts
```

优势：

```text
一个业务模块相关代码放在一起
```

比：

```text
controllers/
services/
repositories/
```

在模块越来越多时更容易维护。

---

## 8. 不要机械分层

下面这种层级如果没有实际职责差异：

```text
Controller
↓
Manager
↓
Provider
↓
Facade
↓
UseCase
↓
Service
↓
Repository
```

就是过度设计。

判断标准不是“层越多越专业”。

而是：

> 每一层是否真的有独立职责和变化原因。

---

## 9. 与 Electron 架构的对应关系

Express：

```text
Router
↓
Controller
↓
Service
↓
Repository
```

Electron：

```text
IPC Handler
↓
Service
↓
Repository / System Adapter
```

IPC Handler 本身就可以承担一部分 Controller 的作用。

因此 Electron 不一定非要再拆一个 `xxx.controller.ts`。

关键是：

```text
IPC 不写业务
Service 不依赖 IPC
Repository 不处理通信
```

---

## 10. 一句话判断边界

```text
Router：
谁来处理？

Controller：
HTTP 要怎么收、怎么回？

Service：
业务应该怎么做？

Repository：
数据从哪里来、怎么存？
```


## Service 的组织方式

Express中：

无状态简单Service：

``` ts
function getUserById()
```

复杂依赖：

``` ts
class UserService
```

适合：

-   Repository
-   Redis
-   Logger
-   外部服务

NestJS：

更偏向：

Class + Dependency Injection


## 关联学习

[[20-后端/实践/Node后端学习项目/01-Node后端学习项目]]
