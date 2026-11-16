# 第02节：Provider、依赖注入与 Module

## 1. 本节要掌握什么

第01节已经让 `UsersController → UsersService` 跑通，但 `UsersService` 还把用户数组直接放在自己内部。本节把存储职责抽到 `UsersRepository`，形成：

~~~text
UsersController → UsersService → UsersRepository
~~~

真正要掌握的不是多写一个 `new`，也不是机械增加层级，而是回答：

- 这些对象由谁创建，什么时候创建？
- Controller 需要 Service、Service 需要 Repository 时，依赖由谁交给它们？
- 一个类写了 `@Injectable()`，为什么还必须注册到 Module？
- 类、字符串和 `Symbol` 怎样成为注入 token？
- 两个 Module 之间怎样公开和获取 Provider？
- 为什么替换 Repository 实现时，Controller 不必跟着修改？
- 默认 Provider 为什么能跨请求保存内存数据，又为什么不能拿来保存“当前用户”？

学习路线：[[20-后端/NestJS/00-NestJS学习路线-面向SpringBoot过渡]]。上一节：[[20-后端/NestJS/01-NestJS启动-Controller参数与Service-]]。

> [!important] 本节主线
> Nest 应用启动时，根据 Module 中的注册信息构建对象图，按 token 找到依赖并创建对象；请求到达时，路由继续复用这些默认作用域的实例。DI 改变的是“谁创建和组装对象”，不会取消 HTTP、业务和数据访问各自的职责。

本节不研究容器源码，也不展开请求作用域、动态 Module、循环依赖和完整测试体系。这里只把默认作用域下最常见的依赖组织方式学清楚。

## 2. 从手写 `new` 到依赖注入

如果完全手写装配，三项依赖可能会写成：

~~~ts
const repository = new InMemoryUsersRepository();
const service = new UsersService(repository);
const controller = new UsersController(service);
~~~

假设明天把内存 Repository 换成 MySQL 实现，装配代码就要改成：

~~~ts
const repository = new MySqlUsersRepository(pool);
const service = new UsersService(repository);
const controller = new UsersController(service);
~~~

Controller 和 Service 的调用关系没变，但负责装配的应用入口越来越难维护。还要手动保证创建顺序，并在测试中自己替换依赖。

在 Nest 中，类只需要声明“我需要什么”：

~~~ts
constructor(
  @Inject(USERS_REPOSITORY)
  private readonly usersRepository: UsersRepository,
) {}
~~~

具体给哪个实现、什么时候创建、先创建谁，由 Module 注册信息和容器完成。下面的三个词经常一起出现：

| 概念 | 回答的问题 | 在 Nest 中对应什么 |
| --- | --- | --- |
| 依赖（Dependency） | 当前对象要工作还需要谁？ | 构造函数参数声明的 Service、Repository 等 |
| IoC（控制反转） | 谁控制对象创建与组装？ | 从业务类交给 Nest 容器 |
| DI（依赖注入） | 依赖怎样进入对象？ | 容器通过构造函数等方法传入已解析的依赖 |

“控制反转”不表示依赖方向反过来。`UsersController` 仍然依赖 `UsersService`；被反转的是创建和装配的控制权。

### 启动时到底发生了什么

可以把启动过程简化成：

~~~text
读取 Module
  → 收集 controllers 与 providers
  → 建立 token → Provider 注册表
  → 从入口对象读取构造依赖
  → 递归解析依赖图
  → 创建实例并注入
  → 注册路由
  → 开始监听端口
~~~

依赖无法解析时，应用通常在启动阶段就失败，而不是等第一个请求到达才发现。能成功启动，也不代表所有业务逻辑正确；它只说明容器能完成必要对象的创建和装配。

## 3. 本节的目标目录

继续使用第01节的内存用户接口，把用户目录逐渐整理成：

~~~text
src/
├─ main.ts
├─ app.module.ts
└─ users/
   ├─ user.types.ts
   ├─ users.repository.ts
   ├─ in-memory-users.repository.ts
   ├─ users.service.ts
   ├─ users.controller.ts
   └─ users.module.ts
~~~

职责如下：

| 角色 | 本节职责 | 不负责 |
| --- | --- | --- |
| `UsersController` | HTTP 路由、请求参数、调用用例 | 数组、SQL、依赖实例装配 |
| `UsersService` | 用户用例与业务异常 | `req` / `res`、具体存储实现 |
| `UsersRepository` | 用户数据读写契约 | HTTP 状态码和业务错误响应 |
| `InMemoryUsersRepository` | 当前的内存实现 | 向 Controller 暴露存储细节 |
| `UsersModule` | 组织本模块 Controller 与 Provider | 代替 HTTP 层或业务层 |

“Repository”并不强制每个小接口都加上一层。它在这里有明确价值：下一阶段要从内存切换到 MySQL，测试也需要替换存储。若两层没有不同职责或变化原因，直接增加空转发层只会制造复杂度。已有通用讨论见 [[20-后端/Express与工程化/02-Express分层架构]]。

## 4. 先定义 Repository 契约和 token

`users.repository.ts`：

~~~ts
import type {
  CreateUserInput,
  UpdateUserInput,
  User,
} from './user.types.js';

export const USERS_REPOSITORY = Symbol('USERS_REPOSITORY');

export interface UsersRepository {
  findAll(name?: string): User[];
  findOne(id: number): User | undefined;
  create(input: CreateUserInput): User;
  update(id: number, input: UpdateUserInput): User | undefined;
}
~~~

这里有三个不同对象，不能混为一体：

- `UsersRepository` 是 TypeScript 接口，描述 Service 可以调用哪些方法。
- `USERS_REPOSITORY` 是运行时存在的 `Symbol`，作为 Provider 的查找标识。
- `InMemoryUsersRepository` 是当前真正被创建的实现类。

为什么不能直接写 `@Inject(UsersRepository)`？因为 `interface` 只存在于类型系统，TypeScript 编译后不会留下名为 `UsersRepository` 的运行时值。`Symbol` 会保留下来，适合作为稳定、不易与其他名称冲突的 token。

字符串也可以作为 token，例如 `'USERS_REPOSITORY'`；Symbol 更容易避免名称碰撞。无论使用哪种自定义 token，声明与使用时必须引用同一个常量。

## 5. 写一个内存 Repository

`in-memory-users.repository.ts`：

~~~ts
import { Injectable } from '@nestjs/common';
import type {
  CreateUserInput,
  UpdateUserInput,
  User,
} from './user.types.js';
import type { UsersRepository } from './users.repository.js';

@Injectable()
export class InMemoryUsersRepository implements UsersRepository {
  private readonly users: User[] = [
    { id: 1, name: 'Tom', email: 'tom@example.com' },
    { id: 2, name: 'Alice', email: 'alice@example.com' },
  ];

  private nextId = 3;

  findAll(name?: string): User[] {
    const keyword = name?.trim().toLowerCase();

    if (!keyword) return [...this.users];

    return this.users.filter(user =>
      user.name.toLowerCase().includes(keyword),
    );
  }

  findOne(id: number): User | undefined {
    return this.users.find(user => user.id === id);
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

  update(id: number, input: UpdateUserInput): User | undefined {
    const user = this.findOne(id);
    if (!user) return undefined;

    if (input.name !== undefined) user.name = input.name;
    if (input.email !== undefined) user.email = input.email;

    return user;
  }
}
~~~

这里让 Repository 在“找不到”时返回 `undefined`，而不是抛 HTTP 异常。HTTP 状态码是接口层关心的事；Repository 换到 MySQL 后仍然只需表达“没有记录”。将 `NotFoundException` 的职责放到 Service，分层更清楚。

`@Injectable()` 表示这个类可以参与 Nest 的依赖注入，并提供所需元数据。它本身仍不会自动把这个类注册到任何 Module。

## 6. Service 通过 token 接收 Repository

`users.service.ts` 改成：

~~~ts
import { Inject, Injectable, NotFoundException } from '@nestjs/common';
import type {
  CreateUserInput,
  UpdateUserInput,
  User,
} from './user.types.js';
import {
  USERS_REPOSITORY,
  type UsersRepository,
} from './users.repository.js';

@Injectable()
export class UsersService {
  constructor(
    @Inject(USERS_REPOSITORY)
    private readonly usersRepository: UsersRepository,
  ) {}

  findAll(name?: string): User[] {
    return this.usersRepository.findAll(name);
  }

  findOne(id: number): User {
    const user = this.usersRepository.findOne(id);

    if (!user) throw new NotFoundException('User not found');

    return user;
  }

  create(input: CreateUserInput): User {
    return this.usersRepository.create(input);
  }

  update(id: number, input: UpdateUserInput): User {
    const user = this.usersRepository.update(id, input);

    if (!user) throw new NotFoundException('User not found');

    return user;
  }
}
~~~

重点看构造函数的两部分：

- `@Inject(USERS_REPOSITORY)` 告诉 Nest 按哪个运行时 token 查找 Provider。
- `usersRepository: UsersRepository` 告诉 TypeScript，这个属性应当符合什么接口。

Service 现在依赖“能够读写用户的数据源”这一能力，不再关心数组、MySQL 或测试替身。这个依赖方向和替换能力就是依赖倒置在本节的实际价值。

Controller 仍然只依赖 `UsersService`：

~~~ts
@Controller('users')
export class UsersController {
  constructor(
    @Inject(UsersService)
    private readonly usersService: UsersService,
  ) {}

  // 五个接口的方法体和第01节保持一致。
}
~~~

Controller 不知道 Repository，也不应该知道。HTTP 请求经过 Controller 和 Service 后，具体存储由更内层的依赖完成。

## 7. Module 把“需要”和“实现”绑定起来

`users.module.ts`：

~~~ts
import { Module } from '@nestjs/common';
import { InMemoryUsersRepository } from './in-memory-users.repository.js';
import { UsersController } from './users.controller.js';
import {
  USERS_REPOSITORY,
} from './users.repository.js';
import { UsersService } from './users.service.js';

@Module({
  controllers: [UsersController],
  providers: [
    UsersService,
    {
      provide: USERS_REPOSITORY,
      useClass: InMemoryUsersRepository,
    },
  ],
  exports: [UsersService],
})
export class UsersModule {}
~~~

`AppModule` 只负责导入功能模块：

~~~ts
import { Module } from '@nestjs/common';
import { UsersModule } from './users/users.module.js';

@Module({
  imports: [UsersModule],
})
export class AppModule {}
~~~

对象图现在可以简化为：

~~~text
AppModule
└─ imports UsersModule
   ├─ controllers
   │  └─ UsersController
   └─ providers
      ├─ UsersService
      └─ USERS_REPOSITORY → InMemoryUsersRepository
~~~

依赖关系则是：

~~~text
UsersController
  → UsersService
    → @Inject(USERS_REPOSITORY)
      → InMemoryUsersRepository
~~~

`providers: [UsersService]` 是简写，它默认让 `UsersService` 类本身同时充当 provider token。自定义 Repository 使用了两套名字，所以需要展开：

~~~ts
{
  provide: USERS_REPOSITORY,          // Service 查找的 token
  useClass: InMemoryUsersRepository,  // token 对应的创建方式
}
~~~

遇到 Provider 对象时，先分别读 `provide` 和 `use...`：

- `provide` 回答“别人按哪个名字找它”。
- `useClass / useValue / useFactory` 回答“找到后得到什么，或者怎样创建它”。

## 8. `controllers`、`providers`、`imports`、`exports`

| 配置 | 处理什么 | 不表示什么 |
| --- | --- | --- |
| `controllers` | 注册由 Nest 实例化和挂载的 Controller | 自动注册 Controller 依赖的 Service |
| `providers` | 在当前 Module 注册可被容器解析的值或对象 | 自动向其他 Module 公开 |
| `imports` | 导入其他 Nest Module 的公开 Provider | 等同于 TypeScript 文件里的 `import` |
| `exports` | 把指定 Provider 或 Module 提供给导入本模块的其他模块 | 让 Provider 自动全局可用 |

Module 默认封装自己的 Provider。只有当前 Module 内部，或者从已导入 Module 的 `exports` 中得到的 Provider，才对使用方可见。

### 跨模块依赖怎样接

假设 `AdminModule` 中的 `AdminService` 也需要 `UsersService`：

~~~ts
@Module({
  imports: [UsersModule],
  providers: [AdminService],
})
export class AdminModule {}
~~~

仅满足这两个条件后，`AdminService` 才能正常注入它：

1. 提供方 `UsersModule` 在 `exports` 中公开 `UsersService`。
2. 使用方 `AdminModule` 在 `imports` 中导入 `UsersModule`。

~~~ts
// 提供方模块的公开面
exports: [UsersService]

// 使用方模块的依赖来源
imports: [UsersModule]
~~~

TypeScript 文件顶部的 `import { UsersService }` 只让代码能引用这个类；真正决定容器可见性的是 Module 的 `imports / exports`。

还需要区分“模块内依赖”和“对外公开”：

- `UsersService` 需要 `USERS_REPOSITORY`，但 Repository 属于 `UsersModule` 内部实现。其他模块通常不需要直接注入 Repository，因此不必导出它。
- 只有确认别的模块也要直接使用 `UsersService` 时，才把 `UsersService` 放入 `exports`。`exports` 是模块的公开 API，不应把所有内部 Provider 一次暴露出去。
- 导入 `UsersModule` 不会自动把 `UsersModule` 的 Controller 变成使用方 Controller；Controller 路由仍属于定义它的模块。

## 9. 注入 token、类型标注与装饰器元数据

Nest 按 token 查找 Provider。常见 token 有：

| token 形式 | 示例 | 用途 |
| --- | --- | --- |
| 类 | `UsersService` | 普通类 Provider，最常见 |
| 字符串 | `'CONNECTION'` | 自定义值或接口绑定；注意名称冲突 |
| Symbol | `USERS_REPOSITORY` | 自定义接口绑定；运行时存在且不易碰撞 |

类作为 token 时，常见写法是：

~~~ts
constructor(private readonly usersService: UsersService) {}
~~~

前提是当前 TypeScript / 构建配置会为构造函数参数生成设计类型元数据，Nest 才能据此推断 `UsersService` token。Nest CLI 的标准 TypeScript 构建通常支持这一点。

本节现有 `tsx` 案例不依赖这类元数据，因此显式写：

~~~ts
constructor(
  @Inject(UsersService)
  private readonly usersService: UsersService,
) {}
~~~

非类 token 则必须明确指定：

~~~ts
constructor(
  @Inject(USERS_REPOSITORY)
  private readonly usersRepository: UsersRepository,
) {}
~~~

接口不能直接当类 token，下面的声明没有可用的运行时标识：

~~~ts
// 错误思路：UsersRepository 编译后不再存在。
constructor(private readonly usersRepository: UsersRepository) {}
~~~

`experimentalDecorators`、`emitDecoratorMetadata`、运行环境和构建工具会影响推断行为。不要只根据“本机能启动”就假设任意 TypeScript 配置都能省略 `@Inject`；自定义 token 还会要求显式写出它。

## 10. 自定义 Provider 的两种写法

普通类可以直接放入 `providers`。需要把某个 token 绑定到其他实现或值时，就使用 Provider 对象。

| 写法            | 值从哪里来             | 常见用途               |
| ------------- | ----------------- | ------------------ |
| `useClass`    | Nest 实例化指定类       | 用不同实现满足同一个接口 token |
| `useValue`    | 直接使用一个已经存在的值或对象   | 常量、配置对象、测试替身       |
| `useFactory`  | 调用函数并用返回值创建依赖     | 需要条件判断、组合资源或异步初始化  |
| `useExisting` | 指向另一个已注册 Provider | 给同一个实例增加别名         |

本节核心写法：

~~~ts
{
  provide: USERS_REPOSITORY,
  useClass: InMemoryUsersRepository,
}
~~~

以后接入 MySQL 时，只需让新实现满足 `UsersRepository`，再替换 Module 中的绑定：

~~~ts
{
  provide: USERS_REPOSITORY,
  useClass: MySqlUsersRepository,
}
~~~

`useValue` 和 `useFactory` 的形状可以这样理解：

~~~ts
// 把一个现成对象绑定给 token。
{
  provide: USERS_REPOSITORY,
  useValue: existingRepository,
}

// 应用启动时调用工厂，使用它的返回值。
{
  provide: USERS_REPOSITORY,
  useFactory: () => createUsersRepository(),
}
~~~

工厂也可以依赖其他 Provider。第04节接配置和连接池时会用到带 `inject` 的工厂；异步工厂返回 Promise 时，Nest 会等待它解决后再完成相关应用初始化。本节先只分清“工厂函数决定怎样得到值”。

`useClass` 与 `new` 的关键区别不是字面上有没有创建对象，而是创建时机、依赖注入和生命周期由 Nest 容器管理。手写在业务类里执行 `new`，替换和测试时仍要修改业务类；写在 Module 绑定中，使用方的调用代码可以保持不变。

## 11. 默认 Provider 的生命周期与共享状态

大多数 Nest Provider 默认使用 singleton 作用域。这里的“单例”有几层重要边界：

- 在同一个应用中，某个 Module 为同一个 token 创建的 Provider 实例通常会被复用。
- 导入同一个 Module 的其他模块，拿到的是该 Module 导出的同一实例。
- 在不同 Module 中分别注册同一个实现类，可能得到不同实例，不能把“类名相同”误认为全应用只有一个对象。
- 开发模式重启应用会创建新进程级实例，内存状态随之重置。

因此，第01节的内存数组能跨请求保留：

~~~text
第一次 POST
  → 同一个 UsersService → 同一个 Repository → push 新用户

下一次 GET
  → 同一个 UsersService → 同一个 Repository → 读到新增用户

应用重启
  → 新实例的数组重新初始化 → 新增用户消失
~~~

这其实是共享可变状态。Repository 保存内存测试数据或缓存资源可以是合理的；把“当前请求的用户”“当前 Authorization 请求头”直接存进默认 singleton 的字段则很危险：

~~~ts
// 错误思路：不同请求会覆盖和读到彼此的当前用户。
@Injectable()
export class RequestContextService {
  currentUserId?: number;
}
~~~

请求 A 写入后，请求 B 可能在下一次写入前读到 A 的值，还可能发生并发请求交错。应用越大，这种隐式状态越难追踪。

本节先采用正确边界：当前请求的数据通过方法参数传递，例如 `usersService.findOne(id)` 中的 `id`。后续讲 Guard 和请求上下文时，会在需要时使用请求作用域或合适的请求存储机制，而不是把请求状态塞进普通 singleton。

请求作用域会让依赖链上的对象按请求创建，并可能向上传播，性能和设计复杂度都会增加。本项目不因为“Nest 支持”就提前使用它。

## 12. 故意改错：从启动报错定位依赖

| 改动 | 常见现象 | 先检查哪里 |
| --- | --- | --- |
| `AppModule` 没有 `imports: [UsersModule]` | 用户路由未挂载，通常得到 404 | 根模块是否导入功能模块 |
| `UsersModule` 有 Controller，但没有注册 `UsersService` | 启动时无法解析 `UsersController` 的依赖 | 当前模块的 `providers` |
| `UsersService` 未注册 `USERS_REPOSITORY` | 启动时无法解析 `UsersService` 的依赖 | custom provider 的 `provide` token |
| 外部模块只写了 TypeScript `import`，没有 Nest `imports` | 类型检查可能通过，但启动时找不到 Provider | Module 的 `imports` |
| 提供方没有 `exports: [UsersService]` | 使用方导入 Module 后仍无法注入 | 提供方模块的 `exports` |
| 用接口类型却没有 `@Inject(token)` | 运行时找不到可用于查找接口的 token | token 是否为类、字符串或 Symbol |
| `controllers` 中漏掉 Controller | 类存在，但对应路由未注册 | `controllers` 数组 |

遇到 `Nest can't resolve dependencies ...` 时，不要只看最后一行。沿着报错中提到的类向构造函数回溯：

~~~text
哪个类创建失败？
  → 它的第几个构造参数是 undefined / token？
  → 对应 token 是否在本模块 providers 中？
  → 若 Provider 来自别的模块，提供方是否 exports、使用方是否 imports？
  → @Inject 使用的常量是否与 provide 完全相同？
~~~

错误信息会随 Nest 版本变化，排查顺序比死记全文更重要。404 与启动失败也要分开：

- 模块没有进入应用图或 Controller 没有注册，往往表现为路由不存在。
- Module 已被加载但所需 Provider 不可解析，通常表现为启动失败。

## 13. 动手改造顺序

在独立学习项目中按下面顺序完成，不先看最终答案：

1. 保留第01节接口行为，先把用户相关类拆进 `UsersModule`，让 `AppModule` 只导入它。
2. 从 `UsersService` 移出用户数组、筛选和 ID 分配，定义 `UsersRepository` 接口与 `InMemoryUsersRepository`。
3. 用 `Symbol('USERS_REPOSITORY')` 作为 token，通过 `@Inject` 注入接口类型。
4. 在 `UsersModule` 中用 `{ provide, useClass }` 绑定实现，运行原有 HTTP 请求文件，确认行为不变。
5. 准备一个满足相同接口的替代实现或测试替身，只改 Module 绑定，确认 Controller 与 Service 的业务调用不需要修改。
6. 依次故意漏掉 `UsersService` 注册、`USERS_REPOSITORY` 注册、跨模块 `exports` 或 `imports`，记录报错后逐项恢复。

代码、运行命令与 HTTP 验收保存在独立学习项目，不在本库重复整套工程。当前起点见[第01节案例 README](../../../node/node-backend-study/labs/nest-01-users/README.md)；第02节代码整理到学习项目后再补对应 README，避免把计划写成已完成。

验收时所有响应应与第01节一致：

- `GET /users` 仍返回 Tom 和 Alice。
- `GET /users?name=TOM` 仍能筛选。
- `POST /users` 创建用户并分配当前内存实例中的下一个 ID。
- `PATCH /users/:id` 仍只修改提交字段。
- 不存在的用户仍由 Service 产生 404，非整数 ID 仍在 Pipe 处产生 400。

接口行为不变，说明这次重构改变的是对象组织和依赖来源，没有破坏 HTTP 契约。

## 14. 与 Spring Boot 的对应

| 本节 NestJS 写法 | Spring 中相近概念 | 仍需注意 |
| --- | --- | --- |
| Provider 注册 | Bean 定义、组件扫描 | Nest 的 Provider 可以是任意值或工厂结果 |
| 构造函数注入 | 构造函数注入 | 元数据来源和容器实现不同 |
| `useClass` 绑定接口实现 | 为接口选择一个 Bean 实现 | Spring 常用 Qualifier / Profile 等选择方式 |
| `exports / imports` | 组件扫描、配置类组织 | Nest Module 不是 Java package 或 Maven module |
| 默认 singleton Provider | 默认单例 Bean | 容器、生命周期和代理机制不能直接等同 |

可以带着“对象由容器创建、构造参数声明依赖、替换实现不改调用方”这一层联系进入 Spring；后续仍要分别学习 Spring 的组件扫描、作用域和依赖选择规则。

## 15. 本节知识地图

~~~text
AppModule
  |  imports
  v
UsersModule
  |  公开：exports UsersService
  |  内部：providers UsersService
  |         provide USERS_REPOSITORY → useClass InMemoryUsersRepository
  v
UsersController
  |  @Inject(UsersService)
  v
UsersService
  |  @Inject(USERS_REPOSITORY)
  v
UsersRepository 接口
  ^
  |  implements
InMemoryUsersRepository

启动时：Module 注册 → token 查找 → 递归解析依赖 → 创建并复用实例
请求时：路由方法 → 已注入的 Service → 已注入的 Repository
~~~

最重要的判断方法不是背装饰器，而是对任意一条调用关系问：

1. 谁依赖谁？
2. 依赖通过什么 token 查找？
3. Provider 在哪个 Module 注册？
4. 使用方能否看到提供方导出的 token？
5. 这个实例是按应用共享，还是应当每次请求重新获得？

## 16. 十个检查自己是否真正理解的问题

先自己回答，再点击问题标题展开参考答案：

> [!question]- 1. 手写 `new InMemoryUsersRepository()` 与 DI 的根本区别是什么？
> 手写时，业务类或入口负责决定创建什么实现、按什么顺序创建并如何组合；DI 时，依赖仍被声明在构造函数中，但创建和装配交给 Nest 容器。替换实现时，只需要改 Module 的绑定，使用方继续按同一 token 注入。

> [!question]- 2. 写了 `@Injectable()`，为什么还要放进 Module 的 `providers`？
> `@Injectable()` 只是标记类可参与依赖注入并提供框架需要的元数据，不会把类自动加入任何 Module。`providers` 才是在当前模块建立 Provider 注册；跨模块还要通过 `exports / imports` 说明可见关系。

> [!question]- 3. Provider 的 token 与实际对象是什么关系？
> token 是容器查找时使用的键，Provider 定义说明这个键绑定到什么类、值或工厂结果。使用方给出的 `@Inject(token)` 必须与 `provide` 使用同一个运行时 token；类可以直接充当 token，接口不能。

> [!question]- 4. `useClass`、`useValue`、`useFactory` 分别怎样得到依赖？
> `useClass` 让容器实例化指定类；`useValue` 直接绑定一个已有对象或值；`useFactory` 调用函数并使用函数的返回值。三者都可以配合 `provide` 定义 token，区别是绑定值从哪里来。

> [!question]- 5. 为什么 `Interface` 不能直接作为注入 token，`Symbol` 怎样解决？
> TypeScript 接口编译后会被擦除，运行时没有可供 Nest 查找的具体值。`Symbol('USERS_REPOSITORY')` 在运行时是一个唯一对象，可以让 Module 的 `provide` 与 Service 的 `@Inject` 指向同一个稳定 token。

> [!question]- 6. 跨模块使用 `UsersService` 需要同时满足哪些条件？
> 提供方 `UsersModule` 必须在 `exports` 中公开 `UsersService`，使用方 Module 必须在 `imports` 中导入 `UsersModule`。仅在 TypeScript 文件中 import 类名不会建立 Nest 的模块可见性。

> [!question]- 7. `UsersService` 依赖 Repository，为什么其他模块通常不需要导出 Repository？
> Repository 是 `UsersModule` 内部实现，Nest 在创建 `UsersService` 时可以在定义它的模块内解析该依赖。其他模块只注入公开的 `UsersService`，不必知道它的内部依赖；只有当别的模块确实要直接注入 Repository 时才考虑导出对应 token。

> [!question]- 8. `AppModule` 漏导入 `UsersModule` 与跨模块漏 `exports` 的现象为什么可能不同？
> `AppModule` 漏导入功能 Module 时，该模块的 Controller 和 Provider 没有进入应用图，用户路由可能表现为 404。提供方已进入应用图但使用方缺少导出或导入时，使用方依赖无法解析，通常表现为启动阶段的依赖注入错误。

> [!question]- 9. 为什么切换 Repository 实现时，Controller 和 Service 的调用代码通常不用改？
> Controller 只依赖 `UsersService`，Service 只依赖 `USERS_REPOSITORY` token 和 `UsersRepository` 接口。内存实现与后续存储实现都遵守同一接口，Module 只替换 token 对应的实现；只要契约和行为兼容，上层调用就保持不变。

> [!question]- 10. 默认 Provider 为什么能跨请求保存数据，又为什么不能保存当前用户？
> 默认 singleton 实例在应用进程内复用，所以同一个内存 Repository 的数组能让 POST 的修改被下一次 GET 读到；重启进程后状态重置。当前用户属于某一次请求，若放进共享字段，并发请求会互相覆盖和泄漏，应通过请求参数或后续专门的请求上下文机制传递。

## 17. 本节验收

- [ ] 能在对象图上指出 Controller、Service、Repository 和 Module 各负责什么。
- [ ] 能解释 IoC、DI、Provider、token 与容器之间的关系。
- [ ] 能写出 `@Injectable()`、`providers`、`@Inject()` 和 `useClass` 的最小示例。
- [ ] 能分别用类、字符串或 Symbol 说明 token 的注册与注入条件。
- [ ] 能接好跨模块依赖，并区分 TypeScript `import` 与 Module `imports`。
- [ ] 能故意制造一次注册或导出错误，并从报错链找到缺失 token。
- [ ] 能替换 Repository 实现而保持 Controller 的用户接口调用不变。
- [ ] 能解释默认 Provider 的共享状态，不把当前用户等请求数据放进普通 singleton。

完成后进入第03节：[[20-后端/NestJS/03-DTO校验Pipe与统一异常]]。所有验收项仅用于学习核对，不自动标记为已完成。

返回：[[20-后端/NestJS/00-NestJS学习路线-面向SpringBoot过渡]]、[[20-后端/00-后端学习导航]]。

参考：[官方 Providers](https://docs.nestjs.com/providers)、[官方 Modules](https://docs.nestjs.com/modules)、[官方 Custom Providers](https://docs.nestjs.com/fundamentals/custom-providers)、[官方 Injection Scopes](https://docs.nestjs.com/fundamentals/injection-scopes)。
