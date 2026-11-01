# Express 基础与 Middleware

## 1. Express 帮 `node:http` 封装了什么

原生：

```ts
if (
  req.method === 'GET' &&
  req.url === '/hello'
) {
  ...
}
```

Express：

```ts
app.get('/hello', handler)
```

原生：

```ts
res.writeHead(200, {
  'Content-Type': 'application/json',
})

res.end(JSON.stringify(data))
```

Express：

```ts
res.json(data)
```

所以 Express 主要帮你封装：

```text
Routing
Request
Response
Middleware
Body Parser
```

---

## 2. 最小 Express

```ts
import express from 'express'

const app = express()

app.get('/hello', (req, res) => {
  res.json({
    message: 'hello',
  })
})

app.listen(3000)
```

---

## 3. JSON Body

```ts
app.use(express.json())
```

然后：

```ts
app.post('/users', (req, res) => {
  console.log(req.body)

  res.status(201).json({
    data: req.body,
  })
})
```

本质：

```text
HTTP Request Stream
↓
express.json()
↓
Buffer
↓
JSON.parse
↓
req.body
```

---

## 4. Params / Query

Path Params：

```ts
app.get('/users/:id', (req, res) => {
  const id = req.params.id
})
```

Query：

```ts
app.get('/users', (req, res) => {
  const page = req.query.page
})
```

---

# Middleware

## 5. Middleware 是什么

```ts
app.use((req, res, next) => {
  console.log(req.method, req.url)

  next()
})
```

核心：

```text
Request
↓
Middleware
↓
Middleware
↓
Router
↓
Response
```

---

## 6. `next()`

```ts
next()
```

表示：

> 当前中间件处理完，继续往后执行。

如果既不：

```ts
next()
```

也不：

```ts
res.end()
res.json()
```

请求会一直挂着。

---

## 7. Middleware 有三条主要出口

```text
next()
→ 正常继续

res.xxx()
→ 直接结束 Response

next(error)
→ 进入 Error Middleware
```

---

## 8. Middleware 顺序非常重要

```ts
app.use(express.json())

app.use(loggerMiddleware)

app.use('/users', userRouter)

app.use(errorHandler)
```

Express 基本按照注册顺序向后查找。

---

## 9. Logger Middleware

```ts
function logger(
  req: express.Request,
  res: express.Response,
  next: express.NextFunction,
) {
  const start = Date.now()

  console.log(
    `→ ${req.method} ${req.url}`,
  )

  res.on('finish', () => {
    console.log(
      `← ${req.method} ${req.url} ${res.statusCode} ${
        Date.now() - start
      }ms`,
    )
  })

  next()
}
```

为什么不用：

```ts
next()

console.log(Date.now() - start)
```

因为 `next()` 不一定意味着后面的异步响应已经真正结束。

更可靠的是：

```ts
res.on('finish')
```

---

## 10. Auth Middleware

```ts
function authMiddleware(
  req: express.Request,
  res: express.Response,
  next: express.NextFunction,
) {
  const token =
    req.headers.authorization

  if (!token) {
    res.status(401).json({
      message: 'Unauthorized',
    })

    return
  }

  next()
}
```

挂在单个路由：

```ts
app.get(
  '/private',
  authMiddleware,
  handler,
)
```

或者一组路由：

```ts
app.use(
  '/admin',
  authMiddleware,
)
```

---

## 11. 横切关注点

Middleware 非常适合处理：

```text
日志
CORS
认证
权限
限流
Request ID
请求耗时
Body Parser
```

这些功能横跨多个业务模块，因此叫：

```text
Cross-Cutting Concern
横切关注点
```

---

## 12. Error Middleware

普通：

```ts
(req, res, next)
```

错误 Middleware：

```ts
(error, req, res, next)
```

例如：

```ts
app.use(
  (error, req, res, next) => {
    console.error(error)

    res.status(500).json({
      message: 'Internal Server Error',
    })
  },
)
```


## 关联学习

[[20-后端/实践/Node后端学习项目/01-Node后端学习项目]]
