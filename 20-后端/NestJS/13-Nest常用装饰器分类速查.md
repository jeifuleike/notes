# 附录：NestJS 常用装饰器分类速查

> 用途：看到 `@xxx` 时，先判断它挂在哪里、由谁执行、什么时候执行。本篇供按需查阅，当前学习顺序见 [[20-后端/NestJS/00-NestJS学习路线-面向SpringBoot过渡]]。

## 1. 先分清装饰器的来源

外观都是 `@xxx`，但来源和执行者完全不同。混在一起记，最容易出现“写了 `@IsString()` 以为 Nest 会自动校验”的问题。

| 来源 | 常见装饰器 | 作用 | 谁来执行 |
| --- | --- | --- | --- |
| `@nestjs/common` | `@Controller`、`@Get`、`@Body`、`@UseGuards` | 描述路由、参数和请求链 | Nest 运行时 |
| `class-validator` | `@IsString`、`@IsEmail`、`@MaxLength` | 给 DTO 字段附加校验规则 | `ValidationPipe` |
| `class-transformer` | `@Type`、`@Transform`、`@Exclude` | 转换对象、控制序列化字段 | `ValidationPipe` / `ClassSerializerInterceptor` |
| `@nestjs/swagger` | `@ApiTags`、`@ApiProperty` | 生成接口文档 | Swagger 模块 |
| 其他官方包 | `@Cron`、`@WebSocketGateway`、`@MessagePattern` | 定时任务、WebSocket、微服务 | 对应模块 |

判断方法：**Nest 核心装饰器管“请求怎么进来、怎么出去”；class-validator 管“字段值合不合法”。**

## 2. 一张地图：装饰器挂在哪里

| 挂载位置 | 典型装饰器 | 说明 |
| --- | --- | --- |
| 类 | `@Module`、`@Controller`、`@Injectable`、`@Global`、`@Catch` | 声明模块、控制器、可注入类、过滤器 |
| 方法 | `@Get`、`@Post`、`@UseGuards`、`@HttpCode`、`@Header` | 路由、请求链扩展、响应控制 |
| 方法参数 | `@Body`、`@Query`、`@Param`、`@Headers`、`@Req` | 从请求中取数据 |
| 类属性 | `@IsString`、`@IsEmail`、`@Exclude`、`@ApiProperty` | 字段规则、序列化、文档 |
| 构造函数参数 | `@Inject`、`@Optional` | 指定依赖 token、允许缺省 |
| 自定义 | `createParamDecorator`、`applyDecorators` | 组合或封装已有装饰器 |

速记：类三件套 `@Module` / `@Controller` / `@Injectable`，路由四件套 `@Get` / `@Post` / `@Patch` / `@Delete`，参数三件套 `@Param` / `@Query` / `@Body`。

## 3. 模块、控制器与依赖注入

| 装饰器 | 挂在哪 | 作用 |
| --- | --- | --- |
| `@Module({...})` | 类 | 声明 `imports`、`controllers`、`providers`、`exports` |
| `@Controller('users')` | 类 | 注册控制器，并给所有路由加前缀 |
| `@Injectable()` | 类 | 表示可由容器创建、参与依赖注入 |
| `@Global()` | 模块类 | 模块导出对所有模块可见，非必要不用 |
| `@Inject(TOKEN)` | 构造函数参数 / 属性 | 显式指定注入 token |
| `@Optional()` | 构造函数参数 / 属性 | 依赖不存在时注入 `undefined`，不抛错 |
| `@Catch(HttpException)` | 过滤器类 | 声明该过滤器捕获哪些异常 |

~~~ts
@Module({
  controllers: [UsersController],
  providers: [{ provide: 'USER_REPOSITORY', useClass: UsersRepository }],
  exports: ['USER_REPOSITORY'],
})
export class UsersModule {}
~~~

三个常见坑：

- 只写 `@Injectable()` 不等于注册；还要出现在某个模块的 `providers` 中，跨模块使用还需要 `exports`。
- `interface` 编译后不存在，不能直接当注入 token；必须配字符串或 `Symbol`。
- 循环依赖用 `@Inject(forwardRef(() => OtherService))`，但优先检查是不是职责划分有问题。

## 4. 路由与响应控制

| 装饰器 | 作用 |
| --- | --- |
| `@Get()`、`@Post()`、`@Put()`、`@Patch()`、`@Delete()` | 绑定对应 HTTP 方法 |
| `@Options()`、`@Head()` | 处理预检、响应头探测 |
| `@All()` | 匹配该路径的所有方法，少用 |
| `@Sse('events')` | Server-Sent Events，方法返回 `Observable<MessageEvent>` |
| `@HttpCode(204)` | 覆盖默认状态码；POST 默认 201 |
| `@Header('Cache-Control', 'no-store')` | 设置响应头 |
| `@Redirect(url, 302)` | 重定向；返回 `{ url, statusCode }` 可覆盖 |
| `@Render('view')` | MVC 模板渲染，API 项目不用 |
| `@Version('1')` | 接口版本控制，需要先 `enableVersioning()` |

~~~ts
@Controller('users')
export class UsersController {
  @Get('me')
  me() {}

  @Get(':id')
  findOne(@Param('id', ParseIntPipe) id: number) {}
}
~~~

`@Get('me')` 要写在 `@Get(':id')` 前面。Nest 按方法声明顺序注册路由，否则 `me` 会被 `:id` 抢先匹配。

## 5. 参数装饰器：最常用的一张表

| 装饰器 | 取到什么 | 示例 | 注意 |
| --- | --- | --- | --- |
| `@Body()` | 整个请求体 | `@Body() dto: CreateUserDto` | 需要校验时类型必须是 `class`，且普通导入 |
| `@Body('name')` | 请求体中的单个字段 | `@Body('name') name: string` | 只取字段，不做校验 |
| `@Query()` | 查询对象 | `@Query() query: ListUsersDto` | 原始值都是字符串 |
| `@Query('page')` | 单个查询参数 | `@Query('page') page: string` | 不会自动转数字 |
| `@Param('id')` | 路径参数 | `@Param('id') id: string` | 同样不会自动转数字 |
| `@Headers('authorization')` | 请求头 | `@Headers('authorization') auth: string` | 名称大小写不敏感 |
| `@Ip()` | 客户端 IP | `@Ip() ip: string` | 代理场景需配置 `trust proxy` |
| `@Session()` | session 对象 | `@Session() session: Session` | 需要 `express-session` |
| `@HostParam()` | 主机名中的变量 | `@HostParam('account') account: string` | 需要 `@Controller({ host: ':account.example.com' })` |
| `@Req()` | 原始请求对象 | `@Req() req: Request` | 直接依赖框架对象，抽象度最低 |
| `@Res({ passthrough: true })` | 原始响应对象 | `@Res({ passthrough: true }) res: Response` | 不写 `passthrough` 会跳过 Nest 后续处理 |
| `@Next()` | Express 的 `next` | `@Next() next: NextFunction` | 仅在需要交给后续中间件时使用 |
| `@UploadedFile()` | 单个上传文件 | `@UploadedFile() file: Express.Multer.File` | 需要 `FileInterceptor('file')` |
| `@UploadedFiles()` | 多个上传文件 | `@UploadedFiles() files: Express.Multer.File[]` | 需要 `FilesInterceptor` |
| `@RawBody()` | 原始请求体 Buffer | `@RawBody() raw: Buffer` | 需要启动时 `rawBody: true` |

参数装饰器只负责“取”，转换和校验交给 Pipe。常用内置 Pipe：

| Pipe | 用途 | 示例 |
| --- | --- | --- |
| `ParseIntPipe` | 转整数，失败返回 400 | `@Param('id', ParseIntPipe) id: number` |
| `ParseFloatPipe` | 转浮点数 | `@Query('rate', ParseFloatPipe) rate: number` |
| `ParseBoolPipe` | 转布尔值 | `@Query('active', ParseBoolPipe) active: boolean` |
| `ParseUUIDPipe` | 校验 UUID | `@Param('id', ParseUUIDPipe) id: string` |
| `ParseEnumPipe` | 校验枚举成员 | `@Query('role', new ParseEnumPipe(Role)) role: Role` |
| `ParseArrayPipe` | 解析数组并校验元素 | `@Query('ids', new ParseArrayPipe({ items: Number })) ids: number[]` |
| `ParseFilePipe` | 校验上传文件大小、类型 | 配合 `@UploadedFile()` 使用 |
| `DefaultValuePipe` | 提供默认值 | `@Query('page', new DefaultValuePipe(1), ParseIntPipe) page: number` |
| `ValidationPipe` | 执行 DTO 上的 class-validator 规则 | 通常全局注册，不在每个参数上写 |

~~~ts
@Get()
findAll(
  @Query('page', new DefaultValuePipe(1), ParseIntPipe) page: number,
  @Query('pageSize', new DefaultValuePipe(20), ParseIntPipe) pageSize: number,
) {}
~~~

Pipe 按书写顺序执行，`DefaultValuePipe` 必须在 `ParseIntPipe` 前面，否则 `undefined` 会先让整数解析失败。

## 6. 请求链扩展点：Guard、Interceptor、Pipe、Filter

| 装饰器 | 挂在哪 | 作用 |
| --- | --- | --- |
| `@UseGuards(AuthGuard, RolesGuard)` | 控制器 / 方法 | 判断请求能否进入；先认证，再授权 |
| `@UseInterceptors(LoggingInterceptor)` | 控制器 / 方法 | 包裹 handler，可记录耗时、改写返回值 |
| `@UsePipes(new ValidationPipe(...))` | 控制器 / 方法 / 参数 | 局部启用管道 |
| `@UseFilters(HttpExceptionFilter)` | 控制器 / 方法 | 局部异常处理 |
| `@SetMetadata('roles', ['admin'])` | 类 / 方法 | 附加自定义元数据，配合 `Reflector` 读取 |

~~~text
请求
  → Middleware
  → Guard              能否进入
  → Interceptor 前置    进入前
  → Pipe               转换 + 校验
  → Controller Handler 业务入口
  → Interceptor 后置    离开前
  → 响应

任一环节抛错 → Exception Filter → 错误响应
~~~

要点：

- Guard 在 Pipe 之前，所以认证失败时不会先跑 DTO 校验。
- 多个 Guard 按绑定顺序执行，先认证再角色检查。
- Interceptor 中，`tap({ next })` 观察成功值，`catchError` 可处理下游异常，`finalize` 在成功、失败或取消订阅时都会执行。
- Filter 不是链条末端的一步，而是包住整条链的错误出口。
- 全局注册用 `app.useGlobalGuards(...)` 等；需要注入依赖时改用 `APP_GUARD`、`APP_INTERCEPTOR`、`APP_PIPE`、`APP_FILTER`。

## 7. 字段校验装饰器（class-validator，不是 Nest）

| 类别 | 装饰器 | 说明 |
| --- | --- | --- |
| 类型 | `@IsString()`、`@IsNumber()`、`@IsInt()`、`@IsBoolean()`、`@IsArray()`、`@IsObject()` | 运行时类型检查 |
| 格式 | `@IsEmail()`、`@IsUUID()`、`@IsUrl()`、`@IsDateString()`、`@Matches(/\S/)` | 字符串格式 |
| 长度 | `@MinLength(n)`、`@MaxLength(n)`、`@Length(min, max)` | 字符串长度 |
| 数值 | `@Min(n)`、`@Max(n)`、`@IsPositive()`、`@IsNegative()` | 数值范围 |
| 必填 | `@IsNotEmpty()`、`@IsDefined()` | `IsNotEmpty` 拒绝空字符串、`null`、`undefined`；`IsDefined` 只拒绝 `null`、`undefined` |
| 可选 | `@IsOptional()`、`@ValidateIf(fn)` | 条件跳过 |
| 数组 | `@ArrayNotEmpty()`、`@ArrayMinSize(n)`、`@ArrayMaxSize(n)`、`@ArrayUnique()` | 数组约束 |
| 枚举 | `@IsEnum(Role)` | 值必须在枚举内 |
| 嵌套 | `@ValidateNested()` + `@Type(() => AddressDto)` | 校验子对象，缺 `@Type` 时拿不到类 |
| 自定义 | `@Validate(MyConstraint)`、`registerDecorator()` | 复杂业务规则 |

~~~ts
export class CreateUserDto {
  @IsString()
  @Matches(/\S/, { message: 'name must contain non-whitespace characters' })
  @MaxLength(50)
  name!: string;

  @IsEmail()
  @MaxLength(254)
  email!: string;
}
~~~

规则细节：

- 同一字段的多个规则都会执行，错误会聚合返回，不是“第一条失败就停”。
- `@IsOptional()` 只在值为 `null` 或 `undefined` 时跳过；空字符串仍会继续校验。
- 更新 DTO 用 `PartialType(CreateUserDto)`，不要手写一堆 `@IsOptional()`。
- `whitelist: true` 删除 DTO 未声明的字段；`forbidNonWhitelisted: true` 遇到多余字段直接返回 400。
- `transform: true` 才会按类型转换查询参数、路径参数；不开启时 `@Query('page')` 始终是字符串。
- `@ValidateNested()` 必须配 `@Type(() => ChildDto)`，否则元数据是 `Object`，子字段规则不会生效。

## 8. 序列化与响应整形（class-transformer）

| 装饰器 | 作用 |
| --- | --- |
| `@Exclude()` | 序列化时排除该字段 |
| `@Expose()` | 只暴露显式标记的字段，配合 `excludeExtraneousValues` |
| `@Transform(({ value }) => ...)` | 自定义转换 |
| `@Type(() => Number)` | 指定运行时类型，常用于查询参数和嵌套对象 |
| `@SerializeOptions({...})` | 控制器 / 方法级设置序列化选项 |

~~~ts
@UseInterceptors(ClassSerializerInterceptor)
@Controller('users')
export class UsersController {}

export class UserResponse {
  @Expose() id!: number;
  @Expose() name!: string;
  @Exclude() passwordHash!: string;
}
~~~

`@Exclude()` 是兜底，不是设计替代品。响应字段仍应通过显式 Response DTO 选择，避免以后新增敏感字段时默认泄露。

## 9. 其他官方包的装饰器（按需查阅）

| 场景 | 装饰器 | 包 |
| --- | --- | --- |
| 接口文档 | `@ApiTags()`、`@ApiOperation()`、`@ApiProperty()`、`@ApiResponse()`、`@ApiBearerAuth()` | `@nestjs/swagger` |
| 定时任务 | `@Cron()`、`@Interval()`、`@Timeout()` | `@nestjs/schedule` |
| WebSocket | `@WebSocketGateway()`、`@SubscribeMessage()`、`@MessageBody()`、`@ConnectedSocket()` | `@nestjs/websockets` |
| 微服务 | `@MessagePattern()`、`@EventPattern()`、`@Payload()`、`@Ctx()` | `@nestjs/microservices` |
| GraphQL | `@Resolver()`、`@Query()`、`@Mutation()`、`@Args()` | `@nestjs/graphql` |

这些不在当前学习路线内。知道它们存在即可，不要和 `@nestjs/common` 的同名或近似装饰器混用；例如 GraphQL 的 `@Query()` 与 HTTP 的 `@Query()` 完全不是一回事。

## 10. 自定义装饰器：先会读，再会写

参数装饰器适合把重复的“取值 + 类型”封装起来：

~~~ts
export const CurrentUser = createParamDecorator(
  (field: keyof User | undefined, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest<{ user: User }>();
    return field ? request.user?.[field] : request.user;
  },
);

@Get('me')
me(@CurrentUser() user: User) {}
~~~

组合装饰器适合把“元数据 + Guard”打包：

~~~ts
export const AdminOnly = () =>
  applyDecorators(SetMetadata('roles', ['admin']), UseGuards(RolesGuard));

@AdminOnly()
@Get('admin')
adminOnly() {}
~~~

自定义装饰器只是语法糖，底层仍是 `SetMetadata`、`Reflector` 和已有的 Guard / Pipe。当前路线不展开自定义装饰器体系，遇到看不懂的封装时按这个思路拆开即可。

## 11. 最容易踩的十个坑

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 写了 `@IsEmail()` 但非法邮箱仍通过 | DTO 是 `interface`，或没有全局 `ValidationPipe` | 改成 `class`，注册 `APP_PIPE` |
| 校验规则全不生效，元数据是 `Object` | Controller 用了 `import type` | DTO 改普通导入 |
| `@Body()` 收到 `undefined` | 请求没有 body，或 Content-Type 不是 JSON | 检查请求头和 body 解析 |
| `@Query('page')` 得到 `"1"` 不是 `1` | 参数装饰器不转型 | 加 `ParseIntPipe` 或开 `transform` |
| `@Param('id')` 传 `abc` 进入 Service | 只声明 `number` 不会运行时转换 | 加 `ParseIntPipe` |
| `@Res()` 后接口挂起不返回 | 没有 `passthrough`，Nest 放弃后续处理 | 用 `@Res({ passthrough: true })` |
| `me` 请求被 `:id` 匹配 | 路由按声明顺序注册 | 静态路由写在参数路由前面 |
| 注入时报 `Nest can't resolve dependencies` | Provider 未注册、未导出，或 token 不匹配 | 检查模块 `providers` / `exports` / `@Inject` |
| Guard 里拿不到用户 | 认证 Guard 没执行或顺序在后 | 调整 `@UseGuards` 顺序 |
| 嵌套 DTO 不校验 | 缺 `@ValidateNested()` 或 `@Type()` | 两者都补齐 |

## 12. “我要做 X”决策表

| 目标 | 用什么 |
| --- | --- |
| 定义一个模块 | `@Module()` |
| 定义一个控制器 | `@Controller('users')` |
| 让类可被注入 | `@Injectable()` + 模块 `providers` |
| 接请求体 | `@Body() dto: XxxDto` |
| 接路径参数 | `@Param('id', ParseIntPipe)` |
| 接查询参数 | `@Query()` + DTO 或 `ParseIntPipe` |
| 校验字段 | class-validator 装饰器 + `ValidationPipe` |
| 认证 | `@UseGuards(JwtAuthGuard)` |
| 角色授权 | `@SetMetadata('roles', [...])` + `RolesGuard` |
| 记录日志 / 计时 | `@UseInterceptors(LoggingInterceptor)` |
| 统一异常 | `@Catch()` 过滤器 + `APP_FILTER` |
| 改状态码 | `@HttpCode(204)` |
| 设置响应头 | `@Header(...)` |
| 上传文件 | `@UseInterceptors(FileInterceptor('file'))` + `@UploadedFile()` |
| 隐藏敏感字段 | `@Exclude()` + `ClassSerializerInterceptor` |
| 定时任务 | `@Cron()` |
| 接口文档 | `@ApiTags()`、`@ApiOperation()`、`@ApiProperty()` |

## 13. 自测

> [!question]- 1. `@IsString()` 是 Nest 的装饰器吗？
> 不是。它来自 `class-validator`，Nest 只是通过 `ValidationPipe` 调用它。没有 Pipe，规则不会执行。

> [!question]- 2. 为什么 `@Body()` 的参数类型不能写成 interface？
> interface 编译后被擦除，`design:paramtypes` 元数据只能得到 `Object`，`ValidationPipe` 会跳过校验。

> [!question]- 3. 为什么 `@Param('id')` 声明成 `number` 仍然收到字符串？
> 类型标注只影响编译期。运行时必须靠 `ParseIntPipe` 等管道转换。

> [!question]- 4. Guard 和 Pipe 谁先执行？
> Guard 先执行。认证不通过时，DTO 校验还没开始，这能避免未认证请求消耗校验资源。

> [!question]- 5. `@UseGuards(AuthGuard, RolesGuard)` 的顺序能反过来吗？
> 一般不能。角色判断依赖已认证的用户信息，必须先认证再授权。

> [!question]- 6. `@Res()` 为什么会让接口不返回？
> 因为它接管了响应对象，Nest 认为你要自己处理。加 `passthrough: true` 才能继续走 Nest 的返回流程。

## 14. 参考资料

- [Controllers](https://docs.nestjs.com/controllers)
- [Providers](https://docs.nestjs.com/providers)
- [Modules](https://docs.nestjs.com/modules)
- [Pipes](https://docs.nestjs.com/pipes)
- [Validation](https://docs.nestjs.com/techniques/validation)
- [Guards](https://docs.nestjs.com/guards)
- [Interceptors](https://docs.nestjs.com/interceptors)
- [Exception Filters](https://docs.nestjs.com/exception-filters)
- [Serialization](https://docs.nestjs.com/techniques/serialization)
- [Request Lifecycle](https://docs.nestjs.com/faq/request-lifecycle)
- [class-validator README](https://github.com/typestack/class-validator)
