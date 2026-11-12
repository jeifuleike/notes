# 第01节：NestJS 启动、Controller、参数与 Service

## 1. 本节要掌握什么

用一个**内存用户接口**串起项目启动、路由、请求参数和Service。重点讲清 NestJS 特有的启动机制、装饰器、路由参数、Pipe、Provider 和依赖注入，不重复讲 TypeScript 或 HTTP 的通用基础。

学完能回答：应用在哪里启动？请求进入哪个方法？参数从哪里来？业务代码放在哪里？对象返回后怎样变成HTTP响应？

本节暂不接MySQL和JWT；DTO运行时校验、完整异常处理在第03节补齐。下面的类型和示例输入用于理解调用关系，不代表接口已经具备完整输入防护。

学习路线：[[20-后端/NestJS/00-NestJS学习路线-面向SpringBoot过渡]]。

## 2. 先认识这四个角色

| 角色 | 做什么 | 本节例子 |
| --- | --- | --- |
| main.ts | 创建应用并监听端口 | 启动HTTP服务 |
| Module | 告诉Nest需要组织哪些Controller与Provider | AppModule注册用户相关类 |
| Controller | 匹配HTTP路由、取参数、调用业务方法 | UsersController |
| Service | 组织业务逻辑；本节暂时也保管内存数据 | UsersService |

读下面的代码时，先区分两个时刻。**启动时**，Nest 要知道有哪些类、怎样创建它们、哪个方法对应哪个地址。**请求到达时**，Nest 才拿得到这次请求的 ID、查询串或请求体，同一个方法每次收到的值可以不同。

Nest 用**装饰器**记录这些约定。以 `@Get(':id')` 为例，加载类定义时，装饰器把“GET、路径为 `:id`”的信息关联到它下面的方法。这类用来描述代码的数据叫**元数据**。Nest 初始化路由时读取它，收到匹配的请求时才调用方法。你可以用一个问题读每个 `@`：它标记了哪个类、方法或参数，框架随后会用这条信息做什么？

### 从 Express 迁移过来看

~~~ts
// Express：自己把路由接到Service。
app.get('/users/:id', (req, res) => {
  const user = usersService.findOne(Number(req.params.id));
  res.json(user);
});
~~~

在Nest中，相同的职责可以写成：

~~~ts
@Controller('users')
export class UsersController {
  constructor(@Inject(UsersService) private readonly usersService: UsersService) {}

  @Get(':id')
  findOne(@Param('id', ParseIntPipe) id: number) {
    return this.usersService.findOne(id);
  }
}
~~~

`@Controller('users')` 指定路由前缀，`@Get(':id')` 指定HTTP方法和后半段路径。框架据此注册 `GET /users/:id`。方法叫 `findOne` 只是命名习惯，接口路径由装饰器决定。

参考：[官方Controllers](https://docs.nestjs.com/controllers)。

## 2.1 `@` 到底是什么：四类常见装饰器

装饰器不是普通的注释；它们让 Nest 在运行时能读取路由、依赖、参数来源等配置。Nest 常见的是下面几类：

| 类型 | 写在哪里 | 示例 | Nest 读取后做什么 |
| --- | --- | --- | --- |
| 类装饰器 | `class` 上面 | `@Controller('users')` | 标记 Controller 及其路径前缀 |
| 类装饰器 | `class` 上面 | `@Injectable()` | 标记可参与依赖注入的类并提供相关元数据 |
| 类装饰器 | `class` 上面 | `@Module({...})` | 声明模块依赖、Controllers、Providers |
| 方法装饰器 | 方法上面 | `@Get(':id')` | 把 HTTP 方法、路径映射到方法 |
| 参数装饰器 | 方法参数前 | `@Param('id')` | 从当前请求提取路径参数 |
| 参数装饰器 | 构造参数前 | `@Inject(Token)` | 明确注入所使用的 Provider 标识 |

注意 `@Get(':id')` 与 `@Param('id')` 尽管都带字符串 `id`，但职责不同：前者**声明路由中哪里是动态段**，后者**从请求中读取这个动态段**。写 `@Get(':userId')` 时，读取它应写 `@Param('userId')`，方法变量可以叫 `id`。

### 生命周期：启动时与每次请求时

~~~text
程序启动：读取装饰器元数据 → 组装 Module / Provider → 创建实例 → 注册路由 → 监听端口
实际请求：匹配路由 → 运行相关 Pipe → 调用 Controller 方法 → Service 处理 → 形成 HTTP 响应
~~~

装饰器表达的配置不是每来一次请求都重新定义；但 `@Query()`、`@Body()` 读取的**值**因每次请求而不同。不要把装饰器误解成“自己调用了一次 Service”。

---

## 3. 启动与目录怎么读

本节有可直接运行的学习案例。对照代码时，先打开入口和根模块，再看用户目录。启动命令和环境要求见[学习案例 README](../../../node/node-backend-study/labs/nest-01-users/README.md)。

~~~text
src/
├─ main.ts
├─ app.module.ts
└─ users/
   ├─ user.types.ts
   ├─ users.controller.ts
   └─ users.service.ts
~~~

如果想从空目录搭建，可以用 `pnpm dlx @nestjs/cli new nest-basics --package-manager pnpm` 创建工程，进入后用 `pnpm start:dev` 启动。CLI 工程通常还带有默认的 AppController 和 AppService，可以保留。下面用学习案例的文件来解释启动过程。[官方入门](https://docs.nestjs.com/first-steps)

下面的局部文件导入使用 `.js` 后缀，适合TypeScript编译后的本地模块引用；沿用工程已有的解析与编译配置，不因为看到后缀就把源文件改成JavaScript。

### main.ts：先创建，再监听

~~~ts
import 'reflect-metadata';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';

const app = await NestFactory.create(AppModule);
await app.listen(3000);
~~~

`NestFactory.create(AppModule)` 以根模块为入口扫描模块关系、组装依赖并创建 Nest 应用；`app.listen(3000)` 初始化应用并开始监听端口。`reflect-metadata` 与 Nest 通过装饰器使用的元数据机制有关。

Nest CLI 生成的项目常使用 `bootstrap()` 启动函数；这个案例使用顶层 `await`，不影响 Nest 的启动和模块机制。

### 为什么根模块写成 `export class AppModule {}`？

~~~ts
import { Module } from '@nestjs/common';
import { UsersController } from './users/users.controller.js';
import { UsersService } from './users/users.service.js';

@Module({
  controllers: [UsersController],
  providers: [UsersService],
})
export class AppModule {}
~~~

`@Module({...})` 是 Nest 的模块配置；`AppModule` 作为根模块传给 `NestFactory.create()`。本例类体为空，是因为 Nest 主要读取的是模块装饰器配置。

- `controllers` 注册由 Nest 管理的路由控制器；没有注册就不会通过这个模块挂载它的路由。
- `providers` 注册可由依赖注入容器解析的 Provider；仅在文件中导入类，不等于将它注册进容器。
- 模块是 Nest 的组织和依赖可见性边界；拆成多个功能模块后，通过 `imports` / `exports` 协作。[官方 Modules](https://docs.nestjs.com/modules)

可以预测一次改动的结果：如果只保留文件顶部的两个 `import`，清空 `controllers` 数组，类名仍然可以在文件里使用，但启动后的 `GET /users` 会因没有匹配路由而返回 404。

### Module 为什么既要 `import` 又要 `providers`

文件中的 `import { UsersService } from './users.service.js'` 只让代码可以引用该类；**不等于**已注册到 Nest 容器。同样，`@Injectable()` 也不等于在整个项目全局可用。

~~~ts
@Module({
  controllers: [UsersController], // 管理哪些 HTTP Controller
  providers: [UsersService],       // 在本模块注册可注入的服务
})
export class UsersModule {}
~~~

按功能拆分模块后，其他模块需要访问这个 Service，通常需要：

~~~ts
@Module({
  providers: [UsersService],
  exports: [UsersService],        // 公开给导入本模块的其他模块
})
export class UsersModule {}

@Module({
  imports: [UsersModule],         // 导入提供 UsersService 的模块
  providers: [OrdersService],
})
export class OrdersModule {}
~~~

`OrdersService` 才能正常通过构造函数注入 `UsersService`。但**导出的是 Provider 的访问能力**，不是把 Service 变成全局对象。也可以通过全局模块等特殊方式共享，本节建议优先显式 `exports` / `imports`。

---

## 4. 本节接口：查询、筛选、创建与修改

| 请求 | 用途 | 参数从哪来 | 示例 |
| --- | --- | --- | --- |
| GET /users | 查询用户，可按姓名筛选 | query | /users?name=Tom |
| GET /users/:id | 查询某个用户 | params | /users/1 |
| POST /users | 创建用户 | body | JSON姓名和邮箱 |
| PATCH /users/:id | 修改用户 | params + body | /users/1加JSON修改字段 |

这是四种方法与路径组合；列表查询有“全部”和“按姓名筛选”两种用法，合起来练五个场景。不要为筛选另建一个几乎相同的接口。

### 三种参数一次分清

对于下面的请求：

~~~http
PATCH /users/1?source=web
Content-Type: application/json

{
  "name": "Tom Updated"
}
~~~

- `@Param('id')` 取路径里的 `"1"`。
- `@Query('source')` 取查询串里的 `"web"`。
- `@Body()` 取解析后的JSON对象 `{ name: 'Tom Updated' }`。

把其中一个参数展开读：`@Param('id') userId: string` 中，`'id'` 对应路由模板 `:id` 的名字，`userId` 是方法里的局部变量名。对于上面的 URL，它收到字符串 `"1"`。后面给参数加上 `ParseIntPipe`，方法才能直接收到数字 `1`。

`Content-Type: application/json` 告诉服务端请求体采用 JSON 格式。HTTP 适配器解析正文后，`@Body()` 把解析出的对象交给方法。本例的 PATCH 方法只声明了路径 ID 和 body 两个参数，所以实际调用相当于 `update(1, { name: 'Tom Updated' })`。查询串里的 `source=web` 仍在请求上，只有声明读取它，才会作为方法参数传入。

## 4.1 `@Query`、`@Param`、`@Body` 到底怎么写

这三者都是**参数装饰器**，作用都是把当前请求的数据注入到被装饰的方法参数中。常见形式：

~~~ts
@Query('name') name?: string            // 查询字符串的一个字段
@Query() query: Record<string, unknown> // 查询参数整体
@Param('id') id: string                 // 路径参数的一个字段
@Param() params: Record<string, string> // 路径参数整体
@Body() body: CreateUserInput           // 解析后的整个请求体
@Body('name') name: string              // 请求体中指定字段
~~~

### Query：`?` 后面，适合筛选和分页

~~~ts
@Get()
findAll(@Query('name') name?: string) {
  return this.usersService.findAll(name);
}
~~~

- `GET /users`：`name` 为 `undefined`，本例 Service 返回所有用户。
- `GET /users?name=Tom`：`name` 为 `"Tom"`。
- `GET /users?name=Tom&page=2`：若只声明 `@Query('name')`，方法只接收到 `name`；`page` 不会自动成为第二个参数。

多参数可以写成 `findAll(@Query('name') name?: string, @Query('page') page?: string)`；或者用 `@Query()` 接收整个查询对象。Query 中的 `"2"` 不等于数字 `2`。可选值如果配合必填的 `ParseIntPipe`，缺失时也可能被拒绝；带默认值的可选数字查询参数可以写作：

~~~ts
@Get('paged')
findPaged(@Query('page', new DefaultValuePipe(1), ParseIntPipe) page: number) {
  return { page };
}
~~~

`DefaultValuePipe` 先补缺失值，再由 `ParseIntPipe` 转整数。需要从 `@nestjs/common` 导入这两个 Pipe。

### Param：URL 路径里的 `:变量`

~~~ts
@Get(':id')
findOne(@Param('id', ParseIntPipe) id: number) {
  return this.usersService.findOne(id);
}
~~~

- `GET /users/7`：`@Get(':id')` 匹配路径，`@Param('id')` 原始值是字符串 `"7"`，`ParseIntPipe` 转成数字 `7`。
- `GET /users/abc`：无法解析整数，**进入 Controller 方法之前**返回 400。
- `GET /users/9999`：ID 合法，但 Service 查不到时抛 `NotFoundException`，返回 404。

路由里有几个占位符，就可以分别取：

~~~ts
@Get(':userId/orders/:orderId')
findOrder(
  @Param('userId', ParseIntPipe) userId: number,
  @Param('orderId', ParseIntPipe) orderId: number,
) {
  return { userId, orderId };
}
// GET /users/3/orders/8  →  { userId: 3, orderId: 8 }
~~~

### Body：POST/PATCH 的 JSON 请求体

~~~ts
@Post()
create(@Body() input: CreateUserInput) {
  return this.usersService.create(input);
}
~~~

请求示例：

~~~http
POST /users
Content-Type: application/json

{"name":"Bob","email":"bob@example.com"}
~~~

这里的 `input` 是**已解析的 JSON 对象**。JSON 的 `name` 是字符串、`age` 可能是数字，和 Query/Param 原始值的处理方式不同；但依然不能信任用户输入。`@Body('name')` 可单独取得某个字段，而 `@Body()` 接收整体。

### 装饰器位置与变量名别弄混

~~~ts
@Get(':id')
findOne(@Param('id', ParseIntPipe) userId: number) { /* ... */ }
~~~

`':id'` 是路由动态占位符；`'id'` 是要读取的参数名；`userId` 只是方法内变量名；`number` 是 TS 类型；`ParseIntPipe` 是实际执行的运行时转换/校验。**这五件事分别负责不同工作。**

### 其他常见请求装饰器

`@Headers('authorization')` 可以读取请求头；`@Req()` 可获得底层请求对象；`@Res()` 可控制底层响应。不过普通 CRUD 更推荐标准 `@Query/@Param/@Body + return`，避免无故依赖底层 Express/Fastify API。

---

## 5. 用户类型：先说明数据形状

示例位置：`src/users/user.types.ts`。

~~~ts
export interface User {
  id: number;
  name: string;
  email: string;
}

// 创建用户不接受客户端指定id。
export type CreateUserInput = Pick<User, 'name' | 'email'>;

// 更新时只允许描述可修改的业务字段。
export type UpdateUserInput = Partial<CreateUserInput>;
~~~

`User` 描述一条已保存记录。`Pick<User, 'name' | 'email'>` 从记录类型取出两个必填字段，正好描述创建时调用者要给什么。`Partial<CreateUserInput>` 再把这两个字段各自变为可选，因此更新时可以只传姓名，保留已有邮箱。

**这些类型在编译后会被擦除。** 如果你在 TypeScript 中写 `service.create({ name: 'Bob' })`，编译器能指出缺少邮箱。HTTP 客户端直接发送相同内容时，请求没有经过你的 TypeScript 编译器，`@Body()` 也不会凭类型标注补上或检查邮箱。下面的 Service 会显式挑选能写入的字段，字段格式的运行时校验留到第 03 节。

### 为什么本节使用类型输入，而后面改用 DTO 类？

本节用 `CreateUserInput` / `UpdateUserInput` 仅描述 Service 接受的数据形状，暂不提供运行时字段验证。实际 NestJS 接口通常会采用**类 DTO + 验证装饰器 + `ValidationPipe`**，让输入在进入 Controller 方法前接受检查。对于更新 DTO，NestJS 常用 `PartialType(CreateUserDto)` 生成字段可选的 DTO；这与上面的纯类型输入不同。完整 DTO 校验放在第 03 节，本节只需记住：`@Body()` 本身并不会验证数据。

## 6. Service：把数据操作集中起来

示例位置：`src/users/users.service.ts`。

~~~ts
import { Injectable, NotFoundException } from '@nestjs/common';
import type {
  CreateUserInput,
  UpdateUserInput,
  User,
} from './user.types.js';

@Injectable()
export class UsersService {
  // 本节用数组模拟存储，数据库和Repository后面再接。
  private readonly users: User[] = [
    { id: 1, name: 'Tom', email: 'tom@example.com' },
    { id: 2, name: 'Alice', email: 'alice@example.com' },
  ];

  // 用递增值分配id，不使用数组长度，避免后续删除后重复。
  private nextId = 3;

  findAll(name?: string): User[] {
    const keyword = name?.trim().toLowerCase();

    if (!keyword) return this.users;

    return this.users.filter(user =>
      user.name.toLowerCase().includes(keyword),
    );
  }

  findOne(id: number): User {
    const user = this.users.find(item => item.id === id);

    // 先用现成HTTP异常表达“不存在”，异常体系第03节再展开。
    if (!user) throw new NotFoundException('User not found');

    return user;
  }

  create(input: CreateUserInput): User {
    const user: User = {
      id: this.nextId++,
      name: input.name,
      email: input.email,
    };

    this.users.push(user);
    return user;
  }

  update(id: number, input: UpdateUserInput): User {
    const user = this.findOne(id);

    // findOne返回数组中该对象的引用，修改它会更新内存中的记录。
    // 只处理允许修改的字段，不用Object.assign(user, input)整体覆盖。
    if (input.name !== undefined) user.name = input.name;
    if (input.email !== undefined) user.email = input.email;

    return user;
  }
}
~~~

Service方法接收普通业务参数、返回普通数据，不需要知道 `req.params` 或 `res.json()`。将来换成数据库存储时，Controller仍然可以调用 `findOne(id)`。

**为什么创建 Bob 之后，另一次 GET 还能查到他？** `users` 和 `nextId` 都是实例属性，每执行一次 `new UsersService()` 就会得到一组新的初始值。本例只在根模块注册一次 Service，并使用默认作用域。Nest 创建这个实例后会复用它，因此 POST 的 `push` 和下一次 GET 的 `find` 操作的是同一份数组。开发模式重启进程会创建新的实例，数组随之恢复为 Tom 和 Alice。[官方 Providers](https://docs.nestjs.com/providers)

本节没有做邮箱唯一性和字段格式校验；创建、更新练习使用合法数据，不能把本示例视为完整用户系统。

## 6.1 `@Injectable()`、Service 与依赖注入从零理解

~~~ts
@Injectable()
export class UsersService {
  findOne(id: number) { /* ... */ }
}
~~~

`@Injectable()` 是**类装饰器**：标记这个类可参与 Nest 的依赖注入机制，并为框架提供相应元数据。**它不会直接 `new` 对象，也不会让它自动全局可用**。通常还要在某个 Module 的 `providers` 中注册。

什么是“依赖”？`UsersController` 要调用 `UsersService.findOne()`，就必须拥有 `UsersService` 的一个实例，因此 Service 是 Controller 的依赖。

### 不用依赖注入（手动创建）

~~~ts
class OrdersController {
  private usersService = new UsersService();
}
~~~

这样 Controller 自己决定怎样创建 Service；如果 Service 又需要数据库连接、日志服务，就要继续手工创建，测试时也难替换。

### 用 Nest 依赖注入（由容器组装）

~~~ts
@Module({
  controllers: [UsersController],
  providers: [UsersService],
})
class UsersModule {}

@Controller('users')
class UsersController {
  constructor(private readonly usersService: UsersService) {}
}
~~~

应用启动时容器会根据注册信息和依赖信息创建、提供实例。在**支持构造参数类型元数据的配置**下，可按 `UsersService` 类型推断依赖；原示例为适配 `tsx` 显式使用 `@Inject(UsersService)`，更直观地指定注入 token。不能断言所有 TS 编译/运行配置都可以省略 `@Inject`。

### `@Injectable()` 后，项目任意位置都能用吗？

不能。若在别的模块注入，通常需要提供方 `exports: [UsersService]`，使用方 `imports: [UsersModule]`。没有正确注册时，即使 TS 能 import 类名，Nest 依旧可能在启动时抛出依赖无法解析错误。

### 只有类才能使用 Service 吗？

也不是。普通函数可以**接收实例作为参数**：

~~~ts
function getNames(service: UsersService) {
  return service.findAll().map(user => user.name);
}
// 由某个已取得实例的对象调用：getNames(this.usersService)
~~~

普通函数不会仅凭 `@Injectable()` 自动获取实例。直接 `new UsersService()` 在技术上也可以（无其他构造依赖时），但实例将不由 Nest 管理。默认 Provider 是**单例作用域**，在对应模块的依赖关系中通常复用同一个实例；Nest 也支持请求作用域或瞬态作用域等配置，这不是本节必学内容。

### `@Injectable`、`providers`、`imports`、`exports` 对照

| 写法 | 作用 | 常见误解 |
| --- | --- | --- |
| `@Injectable()` | 标记可被注入管理的类 | “写了它就全局可访问” ❌ |
| `providers: [X]` | 在该模块注册 Provider | “只要 TS import 就注册了” ❌ |
| `exports: [X]` | 向其他模块公开 Provider | “暴露给所有模块” ❌ |
| `imports: [AModule]` | 使用 A 模块导出的 Provider | “等于 TS import 文件” ❌ |
| `constructor(... x: X)` | 声明实例依赖，由容器提供 | “类型注解本身执行 new” ❌ |

---

## 7. Controller：绑定路由并转交 Service

示例位置：`src/users/users.controller.ts`。

~~~ts
import {
  Body,
  Controller,
  Get,
  Inject,
  Param,
  ParseIntPipe,
  Patch,
  Post,
  Query,
} from '@nestjs/common';
import { UsersService } from './users.service.js';
import type {
  CreateUserInput,
  UpdateUserInput,
} from './user.types.js';

@Controller('users')
export class UsersController {
  // Nest提供UsersService实例，这里接收并保存为只读属性。
  // 不需要在每个接口里new UsersService()。
  constructor(@Inject(UsersService) private readonly usersService: UsersService) {}

  @Get()
  findAll(@Query('name') name?: string) {
    return this.usersService.findAll(name);
  }

  @Get(':id')
  findOne(@Param('id', ParseIntPipe) id: number) {
    return this.usersService.findOne(id);
  }

  @Post()
  create(@Body() input: CreateUserInput) {
    return this.usersService.create(input);
  }

  @Patch(':id')
  update(
    @Param('id', ParseIntPipe) id: number,
    @Body() input: UpdateUserInput,
  ) {
    return this.usersService.update(id, input);
  }
}
~~~

### 这里的构造函数在做什么

假设自己手动组装这两个对象，最少需要写出下面两行。它们用来说明对象关系，实际工程由 Nest 完成组装。

~~~ts
const service = new UsersService();
const controller = new UsersController(service);
~~~

第一行得到能调用 `findOne` 的**实例**。第二行把这个实例作为参数交给 Controller。Controller 需要 Service 才能工作，所以称 Service 为它的**依赖**。由外部把依赖传进来，就是这里的**依赖注入**。

把实际构造函数的缩写展开，可以看到传入的实例最后存在哪里：

~~~ts
private readonly usersService: UsersService;

constructor(@Inject(UsersService) service: UsersService) {
  this.usersService = service;
}
~~~

- `@Inject(UsersService)` 告诉 Nest 按哪个标识查找依赖。这里直接使用运行时存在的类作为标识，与根模块里注册的 `UsersService` 对应。负责按标识查找、创建和提供依赖的部分叫**容器**。
- `service: UsersService` 中冒号后面是 TypeScript 类型，供编译器检查。学习案例用 `tsx` 运行，显式写出 `@Inject`。在会生成构造参数类型元数据的 Nest 工程中，框架可以据此推断类依赖，所以也常看到省略 `@Inject` 的写法。
- `this.usersService` 是当前 Controller 实例的属性，供随后的路由方法访问。`private` 表示在类内部使用，`readonly` 约束属性的重新赋值。通过这个属性调用 Service 修改数组仍然是允许的。

### 路径参数在什么时候转换？

Pipe 是 Nest 在调用路由方法之前，对传入参数执行的处理步骤。这里的 `ParseIntPipe` 尝试把路径字符串解析为整数。可以在 Controller 的 `findOne` 第一行设断点，然后预测三个请求会发生什么。[官方 Pipes](https://docs.nestjs.com/pipes)

| 请求 | 断点会停吗？ | 谁决定结果？ |
| --- | --- | --- |
| `GET /users/1` | 会，`id` 已是数字 `1` | Service 找到 Tom，Controller 返回对象 |
| `GET /users/abc` | 不会 | Pipe 在调用方法前拒绝输入，返回 400 |
| `GET /users/99999` | 会，`id` 已是数字 `99999` | Service 查找失败，抛出 `NotFoundException`，Nest 将异常转成 404 响应 |

因此 404 也要结合调用位置判断。前面清空 `controllers` 的例子中没有匹配到路由；这里的 `99999` 已经匹配路由并进入了 Service。

## 7.1 Pipe 究竟是什么？`ParseIntPipe` 什么时候执行？

Pipe 是框架在执行 Controller 的路由处理方法**之前**，用来转换或验证参数的步骤。本例：

~~~ts
@Get(':id')
findOne(@Param('id', ParseIntPipe) id: number) {
  return this.usersService.findOne(id);
}
~~~

按顺序发生：路径 `"42"` 被 `@Param('id')` 取出 → `ParseIntPipe` 将其解析为整数 `42` → Controller 接收到数字 `42`。若传 `abc` 或 `12.5` 等不符合要求的值，会在进入方法前得到 400。`ParseIntPipe` **不负责**确认 ID 大于零、不负责检查记录是否存在。

为什么只写 `id: number` 不够？因为 TypeScript 类型编译后不会帮你处理真实 HTTP 请求。`ParseIntPipe` 才是运行时行为。

常见内置 Pipe：

| Pipe | 主要用途 | 备注 |
| --- | --- | --- |
| `ParseIntPipe` | 整数转换/校验 | 无效输入通常返回 400 |
| `ParseFloatPipe` | 浮点数转换/校验 | 不同于整数 |
| `ParseBoolPipe` | 布尔值转换/校验 | 接受符合规则的值，如 `true`/`false` |
| `ParseUUIDPipe` | UUID 格式校验 | 不查询数据库 |
| `DefaultValuePipe` | 为缺失参数提供默认值 | 常与其他 Pipe 组合 |
| `ValidationPipe` | 根据类 DTO 的验证规则处理请求数据 | 第03节详学 |

**特别注意**：`ParseIntPipe` 不是数据库锁、不是 TypeScript 类型、不是业务查询函数；它只是请求进入业务逻辑前的一道校验和转换。

---

## 8. 用一次请求把代码连起来

以 `GET /users/1` 为例：

~~~text
请求进入Nest
  → 匹配UsersController的GET /users/:id
  → @Param取id，ParseIntPipe把"1"转为1
  → Controller调用usersService.findOne(1)
  → Service查找内存数组
  → 找到用户并return
  → Nest把返回对象写成JSON响应
~~~

应用启动时的 `main.ts → AppModule → 注册类与依赖`，和每次请求的 `Controller → Service → 返回`，是两个不同阶段。

### return 为什么能返回给前端

这里有两次 `return`。Service 的 `return user` 把内存中的对象交还给调用它的 Controller；Controller 的 `return this.usersService.findOne(id)` 再把对象交给 Nest。后者处在 HTTP 请求处理流程里，框架通过 HTTP 适配器将对象序列化成 JSON，设置响应头和状态码，并发送响应。如果 Controller 返回 Promise，Nest 会等待它完成。

例如 Tom 的详情请求，客户端看到状态码 `200`、表明 JSON 格式的 `Content-Type`，以及响应体 `{"id":1,"name":"Tom","email":"tom@example.com"}`。创建接口也可以返回相同形状的对象，但 `@Post()` 在 Nest 的标准响应处理下默认使用 `201 Created`。状态码和响应体是 HTTP 响应的两个独立部分。

因此这里直接 `return user` 即可，无需再手写 `res.json(user)`。返回格式是用户对象本身；本例没有自动包裹成 `{ data: user }`。

如果显式使用普通 `@Res()`，则通常需要自行发送响应，不能默认认为 `return` 还会替你完成发送。本节先用标准返回方式。[官方响应处理说明](https://docs.nestjs.com/controllers#standard-response-handling)

## 8.1 故意写错：完整排错案例

| 现象 | 一般发生在哪一层 | 先查什么 |
| --- | --- | --- |
| `GET /users/abc` 返回 400 | 参数 Pipe | `ParseIntPipe` 拒绝非整数 |
| `GET /users/9999` 返回 404 | Service 业务逻辑 | ID 已转换，但记录不存在 |
| `GET /wrong-path` 返回 404 | 路由匹配 | `@Controller` + `@Get` 是否对应 |
| Nest 启动时报 `can't resolve dependencies` | DI 容器 | `providers`、跨模块 `exports/imports`、注入 token |
| 传了 JSON，但缺失 `name` 依然进到 Service | 运行时输入校验缺失 | `interface`/`Partial` 本身不验证输入 |
| POST 后能查到，新启动又消失 | 存储层 | 本例用的是内存数组，不是数据库 |
| `@Query('page') page: number` 实际还是字符串 | TS 与 HTTP 边界 | 类型声明不会自动转换，需 Pipe |

### 自己写一个接口（带标准答案）

需求：`GET /users/search?name=tom`，查找名字里包含 `tom` 的用户。为了避免将静态路径误当成 `:id`，将 `@Get('search')` 放在 `@Get(':id')` 之前，并注意实际路由适配器的匹配规则。

~~~ts
@Get('search')
search(@Query('name') name?: string) {
  return this.usersService.findAll(name);
}
~~~

但是原本的 `GET /users?name=tom` 已经能实现筛选，本题只用于理解路由，而不是推荐重复设计接口。想进一步练习，可以实现 `GET /users/paged?page=2`，给 `page` 配置默认值与整数转换，并尝试 `page=abc` 和不传 `page` 的行为。

---

## 9. 怎么练、怎么自测

可以在[案例的 HTTP 请求文件](../../../node/node-backend-study/labs/nest-01-users/requests.http)中逐个发送请求。先预测每个请求会进入哪个方法，再用响应中的状态码和字段核对。

| 场景 | 输入示例 | 本例预期 |
| --- | --- | --- |
| 列表 | GET /users | 200，初始包含Tom和Alice |
| 姓名筛选 | GET /users?name=tom | 200，包含Tom；未匹配返回空数组 |
| 查询单个 | GET /users/1 | 200，Tom |
| 创建 | POST /users，合法姓名和邮箱JSON | 201，新用户，初次分配id为3 |
| 修改 | PATCH /users/3，只提交name | 200，姓名变化，邮箱保留 |
| 不存在 | GET /users/99999 | 404 |
| 非整数ID | GET /users/abc | 400，由ParseIntPipe拒绝 |
| 重启后查询 | 重启后查刚创建的用户 | 新记录消失，因为尚未持久化 |

创建时的JSON例子：

~~~json
{
  "name": "Bob",
  "email": "bob@example.com"
}
~~~

修改时的JSON例子：

~~~json
{
  "name": "Bob Updated"
}
~~~

以当前响应中的实际ID继续操作，只有刚启动的初始状态才假设下一条是3。不要把每次练习的执行顺序与数据库真实自增规则混淆。

当出现问题时，先按职责定位：

- 404且方法未进入：检查HTTP方法、路径、Controller是否注册。
- 启动时无法解析UsersService依赖：检查providers及类的导入，下一节深入解释。
- 请求体读不到预期字段：检查Content-Type与JSON格式，确认读的是body。
- 新用户“突然消失”：查看开发模式是否因改代码而重启。
- 写了类型仍能提交非法字段：类型检查只在开发/编译阶段发挥作用，第三节再补运行时校验。

## 10. 与 Spring Boot 的初步对照

现在只建立用途上的联系，不要求同时写Java。

| 本节Nest写法 | 后续Spring方向 |
| --- | --- |
| @Controller('users')配合JSON返回 | @RestController + @RequestMapping |
| @Get / @Post / @Patch | @GetMapping / @PostMapping / @PatchMapping |
| @Param / @Query / @Body | @PathVariable / @RequestParam / @RequestBody |
| Controller调用Service | 同样保留入口与业务分层 |
| 构造函数接收Service | 构造函数依赖注入 |

装饰器和Java注解的实现机制不同，Module也不能直接等同Java包。下一节重点掌握“容器如何组装对象”，这比记住每个装饰器拼写更有迁移价值。

参考：[Spring REST入门](https://spring.io/guides/gs/rest-service/)。

## 10.1 本节完整知识地图（区分“代码怎么写”与“谁负责执行”）

~~~text
HTTP 客户端
  |  GET /users/1?source=web
  v
Nest HTTP 路由层
  |  @Controller('users') + @Get(':id') 找到 findOne
  v
参数提取和转换
  |  @Param('id') 读取 "1"；ParseIntPipe 转成 1
  |  @Query('source') 仅在方法声明读取时才提供给方法
  v
Controller（组织 HTTP 入口）
  |  this.usersService.findOne(1)
  v
Service（处理业务规则、操作内存数组）
  |  找到对象 / 抛出 NotFoundException
  v
Nest 响应处理
  |  返回 JSON + 状态码；异常交给异常处理机制
  v
HTTP 客户端

启动时另有：main.ts → AppModule → 模块配置 → Provider 注册与依赖注入
~~~

### 十个检查自己是否真正理解的问题

1. `@Controller('users')` 和 `@Get(':id')` 最终形成什么路径？
2. `@Get(':id')` 与 `@Param('id')` 都写了 `id`，分别是什么意思？
3. 为什么 `@Param('id') id: number` 未必是数字？
4. `ParseIntPipe` 失败时，Controller 和 Service 会不会执行？
5. `@Query()` 与 `@Query('name')` 返回的数据范围有什么不同？
6. `@Body()` 收到 JSON 后，`interface` 能否保证字段合法？
7. `Partial<CreateUserInput>` 与 `PartialType(CreateUserDto)` 有什么区别？
8. 为什么 `@Injectable()` 后仍要写 `providers`？跨模块时怎么办？
9. Nest 怎么知道该给 `UsersController` 注入哪个 Provider？
10. 为什么本例 POST 后 GET 能查到新增用户，而重启后消失？

能够自己用代码举例回答这些问题，才建议进入下一节 Provider、依赖注入与 Module 的深入内容。

---

## 11. 本节验收

- [ ] 能找到启动入口，说明create应用与listen端口各做什么。
- [ ] 能写出列表、详情、创建、修改接口，并分清三种输入来源。
- [ ] Controller只组织HTTP入口，数组与业务方法在Service中。
- [ ] 能解释 Nest 为何能将 UsersService 注入 Controller，以及 Module 注册的作用。
- [ ] 知道为何可直接return对象、POST为什么默认201。
- [ ] 知道内存数据重启会丢失，类型标注不会自动完成输入校验。
- [ ] 能不照整段答案，自己增加一个简单接口并调用Service。

完成后进入路线中的第02节：Provider、依赖注入与Module。这里只记录计划中的验收项，不自动标记学习完成。

返回：[[20-后端/NestJS/00-NestJS学习路线-面向SpringBoot过渡]]、[[20-后端/00-后端学习导航]]。
