# 第01节：NestJS 启动、Controller、参数与 Service

## 1. 本节要掌握什么

用一个**内存用户接口**串起项目启动、路由、请求参数和Service。已有HTTP、TypeScript和Express知识直接复用，重点看Nest如何组织同一套能力。

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

Nest是运行在Node.js上的后端框架，提供路由、依赖管理等组织方式。装饰器是框架读取的描述信息；写一个普通类方法，并不会自动变成HTTP接口。

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
  constructor(private readonly usersService: UsersService) {}

  @Get(':id')
  findOne(@Param('id', ParseIntPipe) id: number) {
    return this.usersService.findOne(id);
  }
}
~~~

`@Controller('users')` 指定路由前缀，`@Get(':id')` 指定HTTP方法和后半段路径。框架据此注册 `GET /users/:id`。方法叫 `findOne` 只是命名习惯，接口路径由装饰器决定。

参考：[官方Controllers](https://docs.nestjs.com/controllers)。

## 3. 启动与目录怎么读

新建工程时可用Nest CLI，例如 `pnpm dlx @nestjs/cli new nest-basics --package-manager pnpm`，进入工程后执行 `pnpm start:dev`。这是学习时的命令示意，本篇没有替你创建独立代码工程。

环境要求以所用CLI版本为准：[官方入门与前置条件](https://docs.nestjs.com/first-steps)。CLI创建过程可能询问模块制式等选项，本节沿用生成的配置，不另外切换模块系统或增加可观测服务。

在生成的工程中，本节涉及这些位置：

~~~text
src/
├─ main.ts
├─ app.module.ts
├─ app.controller.ts       # CLI默认接口，可以保留
├─ app.service.ts          # CLI默认Service，可以保留
└─ users/
   ├─ user.types.ts
   ├─ users.controller.ts
   └─ users.service.ts
~~~

下面的局部文件导入使用 `.js` 后缀，适合TypeScript编译后的本地模块引用；沿用工程已有的解析与编译配置，不因为看到后缀就把源文件改成JavaScript。

### main.ts：先创建，再监听

~~~ts
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';

async function bootstrap() {
  // 从根模块出发，创建应用并组织它声明的依赖。
  const app = await NestFactory.create(AppModule);

  // 到这一步才开始监听HTTP请求。
  await app.listen(3000);
}

void bootstrap();
~~~

`NestFactory.create(AppModule)` 创建应用；`app.listen(3000)` 才负责监听端口。业务接口写在Controller中，main.ts保持简短。

开发模式修改代码通常会触发重新编译和重启。**本节用户数据在内存里，应用重启后会恢复初始数据。** 修改文件导致开发重启，也会出现这种现象。

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

它们是三份不同来源的数据。参数装饰器让框架把对应输入传给方法参数；名称可以按业务约定取，不是Nest固定要求所有接口都叫id或name。

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

这些TypeScript类型帮助编译器检查代码和提示字段。**它们不会在运行时自动拦截非法JSON或多余字段。** 正式校验会在第03节通过DTO与ValidationPipe接入。

下面的Service还会显式选择赋值字段，避免把请求体里的任意字段整体覆盖到用户对象上；这同样不能代替输入格式校验。

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

`@Injectable()` 是把这个类交给框架依赖管理体系使用的标记，还要配合Module中的注册。今天先把注册接通，第二节解释容器如何创建和传递对象。[官方Providers](https://docs.nestjs.com/providers)

本节没有做邮箱唯一性和字段格式校验；创建、更新练习使用合法数据，不能把本示例视为完整用户系统。

## 7. Controller：绑定路由并转交 Service

示例位置：`src/users/users.controller.ts`。

~~~ts
import {
  Body,
  Controller,
  Get,
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
  constructor(private readonly usersService: UsersService) {}

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

`constructor(private readonly usersService: UsersService) {}` 使用了TypeScript的参数属性语法：既声明构造函数参数，也把传进来的值保存为实例属性。

因此后续方法可用 `this.usersService`。谁负责创建和传入这个实例，是下一节的依赖注入重点；本节先记住“声明需要什么，框架按注册信息提供什么”。

`readonly` 约束的是属性重新赋值，不会让Service内部数组自动变成不可变数据。

### 为什么这里先用了 ParseIntPipe

路径参数原本是字符串；写 `id: number` 本身不会完成转换。`ParseIntPipe` 帮我们做整数解析，不能解析的输入会返回400。

今天会使用这个现成工具即可。它不等于正整数、安全整数或权限校验，完整边界留到第03节；例如“整数解析成功”和“此用户存在”仍是两回事。

## 8. Module：把类注册进应用

示例位置：`src/app.module.ts`。下面保留CLI默认的AppController和AppService，再加入用户类：

~~~ts
import { Module } from '@nestjs/common';
import { AppController } from './app.controller.js';
import { AppService } from './app.service.js';
import { UsersController } from './users/users.controller.js';
import { UsersService } from './users/users.service.js';

@Module({
  imports: [],
  controllers: [AppController, UsersController],
  providers: [AppService, UsersService],
})
export class AppModule {}
~~~

`controllers` 声明要挂载哪些Controller，`providers` 声明本模块提供哪些依赖。只创建一个文件或写一个 `import`，不代表Nest已经把类注册进应用。

如果你的工程还包含其他生成配置，保留它们并添加用户注册项。本节暂时直接放根模块；第二节再拆UsersModule和跨模块依赖。[官方Modules](https://docs.nestjs.com/modules)

## 9. 用一次请求把代码连起来

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

标准处理方式下，Nest会处理Controller方法返回的对象或数组；默认成功状态通常为200，POST默认201。也可以返回Promise，框架会等待其结果。

因此这里直接 `return user` 即可，无需再手写 `res.json(user)`。返回格式是用户对象本身；本例没有自动包裹成 `{ data: user }`。

如果显式使用普通 `@Res()`，则通常需要自行发送响应，不能默认认为 `return` 还会替你完成发送。本节先用标准返回方式。[官方响应处理说明](https://docs.nestjs.com/controllers#standard-response-handling)

## 10. 怎么练、怎么自测

实际工程的完整HTTP请求文件和执行记录放在代码仓库维护。本篇用下面的观察目标理解本节是否掌握：

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

## 11. 与 Spring Boot 的初步对照

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

## 12. 本节验收

- [ ] 能找到启动入口，说明create应用与listen端口各做什么。
- [ ] 能写出列表、详情、创建、修改接口，并分清三种输入来源。
- [ ] Controller只组织HTTP入口，数组与业务方法在Service中。
- [ ] 能解释构造函数参数属性和Module注册的基本用途。
- [ ] 知道为何可直接return对象、POST为什么默认201。
- [ ] 知道内存数据重启会丢失，类型标注不会自动完成输入校验。
- [ ] 能不照整段答案，自己增加一个简单接口并调用Service。

完成后进入路线中的第02节：Provider、依赖注入与Module。这里只记录计划中的验收项，不自动标记学习完成。

返回：[[20-后端/NestJS/00-NestJS学习路线-面向SpringBoot过渡]]、[[20-后端/00-后端学习导航]]。

