# Node HTTP 与请求响应基础

## 1. `node:http` 是什么

```ts
import http from 'node:http'

const server = http.createServer((req, res) => {
  res.end('hello')
})

server.listen(3000)
```

`http.createServer()` 创建 HTTP Server。

每次请求都会进入：

```ts
(req, res) => {}
```

其中：

```text
req = IncomingMessage
res = ServerResponse
```

---

## 2. 一次 HTTP 请求的基本结构

```text
HTTP Request
├─ Method
├─ URL
├─ Headers
└─ Body
```

后端通常会拆成：

```text
Method
Path
Path Params
Query Params
Headers
Body
```

例如：

```http
GET /users/123?page=2
Authorization: Bearer xxx
```

其中：

```text
Method       = GET
Path         = /users/123
Path Param   = 123
Query Param  = page=2
Header       = Authorization
```

---

## 3. Response

原生 Node：

```ts
res.writeHead(200, {
  'Content-Type': 'application/json; charset=utf-8',
})

res.end(
  JSON.stringify({
    message: 'ok',
  }),
)
```

常见状态码：

```text
200 OK
201 Created
204 No Content

400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
413 Payload Too Large

500 Internal Server Error
```

---

## 4. `res.write()` 与 `res.end()`

```ts
res.write('A')
res.write('B')
res.end('C')
```

含义：

```text
write()
= 写一个响应数据块

end()
= 写最后一个数据块，并结束响应
```

`end()` 不是“把之前所有 write 一次性发送出去”。

真正的流式响应可以边写边传。

---

## 5. 为什么 `fetch().text()` 看起来不是流式

```js
const res = await fetch('/stream')
const text = await res.text()
```

`res.text()` 会等 Body 全部读取完成。

如果想逐块读取：

```js
const res = await fetch('/stream')
const reader = res.body.getReader()
const decoder = new TextDecoder()

while (true) {
  const { done, value } = await reader.read()

  if (done) break

  console.log(
    decoder.decode(value, {
      stream: true,
    }),
  )
}
```

---

## 6. Path Params 与 Query Params

一般约定：

```text
/users/123
```

`123` 用于标识资源：

```text
Path Params
```

而：

```text
/users?page=2&status=active
```

用于：

```text
分页
筛选
搜索
排序
```

属于：

```text
Query Params
```

---

## 7. Body 本质是什么

客户端：

```js
fetch('/users', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    name: 'Tom',
  }),
})
```

网络真正传输的不是 JS Object，而是：

```text
JS Object
↓
JSON.stringify
↓
String
↓
UTF-8 Bytes
↓
Network
↓
Buffer
↓
String
↓
JSON.parse
↓
JS Object
```

原生 Node：

```ts
const chunks: Buffer[] = []

req.on('data', (chunk: Buffer) => {
  chunks.push(chunk)
})

req.on('end', () => {
  const body = Buffer
    .concat(chunks)
    .toString('utf-8')

  const data = JSON.parse(body)
})
```

---

## 8. Body Size Limit

不能无限接收请求体。

```ts
let size = 0
const maxSize = 10 * 1024

req.on('data', chunk => {
  size += chunk.length

  if (size > maxSize) {
    res.statusCode = 413
    res.end('Payload Too Large')
  }
})
```

原因：

```text
超大请求
↓
内存持续增长
↓
服务不可用
```

这是最基础的 DoS 防御之一。

---

## 9. CORS 与 CSP

### CORS

浏览器问目标服务器：

> 我的 Origin 能不能读取你的 Response？

后端一般返回：

```http
Access-Control-Allow-Origin: ...
```

JSON 跨域 POST 常触发：

```text
OPTIONS Preflight
```

### CSP

当前网页自己规定：

> 页面里的 JS 允许连接哪些地址？

所以：

```text
CSP = 当前页面限制自己
CORS = 目标服务器允许哪些 Origin 读取响应
```

CORS 不是身份认证，也不能阻止：

```text
curl
Postman
其他服务器
```

真正安全依赖：

```text
JWT
Session
权限校验
API Key
```


## 关联学习

[[20-后端/实践/Node后端学习项目/01-Node后端学习项目]]
