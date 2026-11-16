# 第03节：DTO、校验、Pipe 与统一异常

## 1. 本节要掌握什么

第02节已经把依赖组织成 `UsersController → UsersService → UsersRepository`。本节继续使用这组内存用户接口，补上输入和错误边界：**输入不符合约定时，在进入业务方法前拒绝；记录不存在时返回404；未知错误返回通用500。**

学完应能解释：为什么写了类型仍会收到非法输入？DTO类与Pipe怎样配合？`PATCH`没传字段和传`null`有什么不同？异常从哪里抛出，由谁写成HTTP响应？

学习路线：[[20-后端/NestJS/00-NestJS学习路线-面向SpringBoot过渡]]。上一节：[[20-后端/NestJS/02-Provider依赖注入与Module]]。

本节只新增DTO、自定义ID Pipe和一个HTTP异常Filter，修改Controller参数及启动配置；Module、Service、Repository沿用第02节。下面是改造说明与示例，不表示独立学习项目已经完成改造或验收。

## 2. 先确定接口规则

先写清楚接口接受什么，再选装饰器。否则容易出现“装饰器都加了，但业务规则仍不明确”。

| 输入 | 本节规则 | 失败结果 |
| --- | --- | --- |
| 创建用户的name | 必填字符串，包含非空白字符，最长50字符 | 400 |
| 创建用户的email | 必填，符合邮箱格式，最长254字符 | 400 |
| 更新用户 | 字段可不提交；提交后仍要符合对应规则，不接受null | 400 |
| 多余字段，如role、id | 不接受 | 400 |
| 路径id | 正的安全整数 | 400 |
| 合法id对应的用户不存在 | 由Service判断 | 404 |
| 意外程序或存储故障 | 客户端只看到通用信息 | 500 |

本节允许`PATCH /users/:id`提交`{}`，表示不改变字段；存在的用户原样返回，不存在仍为404。不额外引入“至少修改一个字段”的规则。

姓名允许保留前后空格，只拒绝全部为空白的内容；本节不自动trim或修改邮箱大小写。**校验与规范化是两个决定**，不要在没有规则时悄悄改变用户输入。

## 3. DTO、类型与数据库记录分开看

DTO是Data Transfer Object，描述边界上传递的数据。这里重点是**请求DTO**。

~~~ts
interface CreateUserInput {
  name: string;
  email: string;
}
~~~

这个接口仍可作为Service的输入契约，但编译后会被擦除。客户端发送`{"name":123}`时，它不会替你阻止请求。

改用`class CreateUserDto`可以保留一个运行时的类，但只声明属性同样不会校验。还需要把字段规则写成验证装饰器，再让`ValidationPipe`执行它们。请求DTO不要作为Module的Provider注册。

| 对象 | 关注什么 | 本例 |
| --- | --- | --- |
| 请求DTO | 客户端允许提交的字段和约束 | name、email |
| Service输入类型 | 业务方法需要的数据形状 | CreateUserInput、UpdateUserInput |
| 存储记录 | 数据实际怎样保存 | id、name、email；以后可能有passwordHash |
| 响应 | 客户端允许看到什么 | 公开用户字段 |

DTO校验不会自动过滤输出。以后记录含有`passwordHash`时，仍需显式选择响应字段；给返回值写一个TypeScript类型不会删除对象里多出来的属性。

## 4. 先检查编译方式，再启用校验

在独立学习工程中检查依赖；缺少时再安装：

~~~sh
pnpm add class-validator class-transformer
~~~

两者分别提供验证规则和对象转换能力，`ValidationPipe`负责把它们接入Nest请求处理。具体选项见[官方Validation说明](https://docs.nestjs.com/techniques/validation)。

### 前两节的tsx运行方式要特别注意

前两节使用显式`@Inject()`来解决构造函数依赖的token，但它不负责告诉Nest“这个请求体对应哪个DTO”。自动DTO校验通常还依赖路由方法参数的设计类型元数据。

本节按**能够生成装饰器类型元数据的TypeScript构建**讲解。沿用现有Nest工程配置，并确认：

~~~json
{
  "compilerOptions": {
    "experimentalDecorators": true,
    "emitDecoratorMetadata": true
  }
}
~~~

这只是相关配置片段，不要覆盖整个`tsconfig.json`。使用`tsc`或已正确配置的Nest构建流程编译，再运行编译产物；只给tsx工程加上这两个配置，不能假定tsx就会生成同样的元数据。模块格式、启动脚本和编译输出目录需要在学习工程中配套调整。

DTO在Controller中使用普通导入：

~~~ts
import { CreateUserDto } from './dto/create-user.dto.js';
~~~

不要写成`import type`。DTO必须在运行时可引用；接口、泛型或被擦除的导入都不能直接提供这里所需的类信息。[官方DTO注意事项](https://docs.nestjs.com/techniques/validation#auto-validation)

若怀疑校验没有执行，可以临时在启动时检查已经加载的Controller：

~~~ts
console.log(
  Reflect.getMetadata('design:paramtypes', UsersController.prototype, 'create'),
);
// 应包含CreateUserDto；undefined或Object都值得继续检查。
~~~

这段诊断需要先导入`UsersController`并加载`reflect-metadata`。它检查的是编译链路，不能代替非法请求验收。

## 5. 创建DTO：规则写在哪里

新增`users/dto/create-user.dto.ts`：

~~~ts
import { IsEmail, IsString, Matches, MaxLength } from 'class-validator';

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

`name!`中的`!`只是告诉TypeScript该属性会在之后赋值，不是运行时非空检查。`@IsString()`拒绝数字等类型；`@Matches(/\S/)`要求至少一个非空白字符；长度与邮箱规则分别约束对应字段。

不要把`@IsNotEmpty()`单独当作“禁止纯空格字符串”的完整规则，也不要把邮箱格式校验当作邮箱真实存在的证明。验证装饰器的具体语义见[class-validator说明](https://github.com/typestack/class-validator#validation-decorators)。

## 6. 更新DTO：缺失、undefined与null

更新输入的`name?: string`只表达TypeScript字段可选，不能决定运行时如何对待`null`。

本节字段少，显式写出“只在值不是undefined时校验”。新增`users/dto/update-user.dto.ts`：

~~~ts
import {
  IsEmail,
  IsString,
  Matches,
  MaxLength,
  ValidateIf,
} from 'class-validator';

export class UpdateUserDto {
  @ValidateIf((_object, value) => value !== undefined)
  @IsString()
  @Matches(/\S/, { message: 'name must contain non-whitespace characters' })
  @MaxLength(50)
  name?: string;

  @ValidateIf((_object, value) => value !== undefined)
  @IsEmail()
  @MaxLength(254)
  email?: string;
}
~~~

| 请求体 | 含义 | 本节结果 |
| --- | --- | --- |
| `{"name":"Bob"}` | 只修改姓名 | 通过，保留原邮箱 |
| `{}` | 两个字段都未提交 | 通过，不改变字段 |
| `{"name":null}` | 明确提交null | 400 |
| `{"name":"   "}` | 明确提交纯空白姓名 | 400 |
| `{"email":123}` | 提交错误类型 | 400 |

JSON不能直接表示`undefined`；这里的undefined主要来自“属性未提交”。Repository继续使用第02节的`input.name !== undefined`等判断，只更新提交过的字段。

常见`@IsOptional()`会对null和undefined都跳过该字段的后续验证，因此不能直接满足本节“允许缺失、拒绝null”的规则。`ValidateIf`条件为false时也会跳过该字段的验证。[条件验证与IsOptional语义](https://github.com/typestack/class-validator#conditional-validation)

以后字段多时，可以研究`@nestjs/mapped-types`提供的`PartialType`以继承验证规则，并核对所用版本的null处理选项。不要把纯类型`Partial<T>`误当成同一能力，也不要在未核对null语义时直接替换这里的代码。

## 7. 全局ValidationPipe：真正让规则执行

在现有`main.ts`创建应用后、监听前加入：

~~~ts
import { ValidationPipe } from '@nestjs/common';

// 保留现有reflect-metadata导入、NestFactory和AppModule等启动代码。
const app = await NestFactory.create(AppModule);

app.useGlobalPipes(
  new ValidationPipe({
    transform: true,
    whitelist: true,
    forbidNonWhitelisted: true,
    validationError: { target: false, value: false },
  }),
);

await app.listen(3000);
~~~

| 选项                   | 本节用途                         |
| -------------------- | ---------------------------- |
| transform            | 把请求数据转换为对应DTO实例后交给处理器        |
| whitelist            | 依据验证装饰器识别允许的字段；不是依据TS属性声明    |
| forbidNonWhitelisted | 遇到白名单之外的字段直接拒绝，而非静默删除        |
| validationError      | 不在验证错误对象中附带完整目标和值；不能代替错误消息审查 |

只写`whitelist: true`时，多余字段通常被删除；本节同时开启`forbidNonWhitelisted`，所以`{"name":"Bob","email":"bob@example.com","role":"admin"}`返回400。只在DTO里声明`role?: string`、不提供验证装饰器，也不会让它成为本方案允许的字段。

不要全局开启`skipMissingProperties`来迁就更新接口，否则创建DTO的必填约束也可能被跳过。更新是否可选由更新DTO独立表达。配置行为见[官方校验选项](https://docs.nestjs.com/techniques/validation#using-the-built-in-validationpipe)。

`transform: true`不意味着任意字符串都能变成正确的业务类型。本节JSON中的name、email仍要求字符串，不开启隐式字段转换；路径ID继续显式处理。

## 8. 自定义ID Pipe：解析成功还不够

`ParseIntPipe`能拒绝`abc`等输入，但“能转换为整数”与“可以作为本项目ID”是两件事。负数、0、超出安全整数范围的值都需要额外拒绝。

新增`common/pipes/positive-safe-int.pipe.ts`：

~~~ts
import {
  BadRequestException,
  Injectable,
  type PipeTransform,
} from '@nestjs/common';

@Injectable()
export class PositiveSafeIntPipe implements PipeTransform<number, number> {
  transform(value: number): number {
    if (!Number.isSafeInteger(value) || value <= 0) {
      throw new BadRequestException('id must be a positive safe integer');
    }

    return value;
  }
}
~~~

与内置Pipe组合使用：

~~~ts
@Get(':id')
findOne(
  @Param('id', ParseIntPipe, PositiveSafeIntPipe) id: number,
) {
  return this.usersService.findOne(id);
}
~~~

处理顺序是路径字符串 → `ParseIntPipe`转换 → `PositiveSafeIntPipe`检查范围 → Controller。传入Pipe类时由Nest实例化；这个无依赖Pipe不需要额外手写`new`。Pipe与DI的关系见[官方Pipes](https://docs.nestjs.com/pipes)。

这个规则适用于当前JavaScript number形式的ID。以后数据库若使用可能超出安全范围的BIGINT，应重新约定字符串等表示方式，不能先转成number再希望恢复精度。

## 9. Controller接入DTO，业务层保持原职责

下面替换原Controller中的创建、详情和更新方法；原有列表方法及构造注入保留：

~~~ts
import { Body, Get, Param, ParseIntPipe, Patch, Post } from '@nestjs/common';
import { PositiveSafeIntPipe } from '../common/pipes/positive-safe-int.pipe.js';
import { CreateUserDto } from './dto/create-user.dto.js';
import { UpdateUserDto } from './dto/update-user.dto.js';

// 以下方法位于原UsersController类内。
@Post()
create(@Body() input: CreateUserDto) {
  return this.usersService.create(input);
}

@Get(':id')
findOne(@Param('id', ParseIntPipe, PositiveSafeIntPipe) id: number) {
  return this.usersService.findOne(id);
}

@Patch(':id')
update(
  @Param('id', ParseIntPipe, PositiveSafeIntPipe) id: number,
  @Body() input: UpdateUserDto,
) {
  return this.usersService.update(id, input);
}
~~~

合并导入时保留原来的`Controller`、`Inject`、`Query`等实际使用项，避免复制片段时覆盖已有代码。这些DTO在结构上满足原有`CreateUserInput / UpdateUserInput`，所以Service和Repository不必为了HTTP校验改成依赖请求DTO。

职责现在分成：

- DTO / Pipe：字段类型、格式、长度、ID范围。
- Service：用户是否存在，以及之后加入的业务规则。
- Repository：数据读取和写入。
- Filter：把未处理异常转换成约定的HTTP错误响应。

Pipe主要保护HTTP入口。直接在脚本或测试中调用Service不会自动执行Controller的DTO校验；新增其他入口时，仍需明确它们自己的输入边界。

## 10. 内置异常已经可以返回HTTP错误

第02节的Service保留：

~~~ts
const user = this.usersRepository.findOne(id);
if (!user) throw new NotFoundException('User not found');
return user;
~~~

这里不需要Controller逐个`try/catch`。Nest已有异常处理层，认识`HttpException`及其子类；未识别的异常默认形成500响应。自定义Filter的目的，是学习并统一本项目的错误响应约定，不是让Nest第一次具备错误处理能力。[官方异常处理](https://docs.nestjs.com/exception-filters)

| 异常 | 状态码 | 常见用途 |
| --- | --- | --- |
| BadRequestException | 400 | 输入不符合接口约定 |
| UnauthorizedException | 401 | 尚未通过认证 |
| ForbiddenException | 403 | 已识别身份但无权限 |
| NotFoundException | 404 | 目标记录不存在 |
| ConflictException | 409 | 与当前资源状态冲突，如以后加入重复邮箱规则 |

不要把所有错误都改成400，也不要返回200并在body中塞一个`code: 500`冒充HTTP失败。状态码应当表达本次HTTP请求的处理结果。

## 11. 最小HTTP异常Filter

本节约定错误体为`{ statusCode, message }`，message可以是字符串或字符串数组。已知4xx保留明确设计给客户端的消息；5xx统一隐藏内部信息。

新增`common/filters/http-error.filter.ts`：

~~~ts
import {
  Catch,
  HttpException,
  Logger,
  type ArgumentsHost,
  type ExceptionFilter,
} from '@nestjs/common';
import { HttpAdapterHost } from '@nestjs/core';

@Catch()
export class HttpErrorFilter implements ExceptionFilter {
  private readonly logger = new Logger(HttpErrorFilter.name);

  constructor(private readonly adapterHost: HttpAdapterHost) {}

  catch(exception: unknown, host: ArgumentsHost): void {
    const status = exception instanceof HttpException
      ? exception.getStatus()
      : 500;
    let message: string | string[] = 'Internal server error';

    if (exception instanceof HttpException && status < 500) {
      const body = exception.getResponse();
      const candidate: unknown = typeof body === 'string'
        ? body
        : (body as { message?: unknown }).message;

      message = typeof candidate === 'string'
        ? candidate
        : Array.isArray(candidate) && candidate.every(item => typeof item === 'string')
          ? candidate
          : 'Request failed';
    }

    if (status >= 500) {
      this.logger.error(
        'Unhandled HTTP error',
        exception instanceof Error ? exception.stack : undefined,
      );
    }

    const response = host.switchToHttp().getResponse();
    this.adapterHost.httpAdapter.reply(response, { statusCode: status, message }, status);
  }
}
~~~

`@Catch()`不指定异常类，表示捕获进入该Filter的各类未处理异常。`ArgumentsHost`提供当前执行上下文；本例只处理普通HTTP响应。通过HTTP适配器写响应，避免直接依赖Express的`res.status().json()`。[官方跨平台Filter示例](https://docs.nestjs.com/exception-filters#catch-everything)

这段代码只从已知异常提取message，不把整个异常对象、请求体或数据库错误直接返回。服务端日志用于排查故障，也应限制访问；自定义验证消息和4xx异常消息必须由开发者保证适合公开，不能塞入SQL、密钥或密码。

在`main.ts`中、监听前注册：

~~~ts
import { HttpAdapterHost } from '@nestjs/core';
import { HttpErrorFilter } from './common/filters/http-error.filter.js';

app.useGlobalFilters(new HttpErrorFilter(app.get(HttpAdapterHost)));
~~~

这里明确从容器取出适配器并传给Filter，所以不依赖Filter构造参数的自动推断。以后Filter需要更多容器依赖时，可以学习通过`APP_FILTER`注册；当前只选一种方式，避免重复注册。

错误响应例子：

~~~json
{
  "statusCode": 404,
  "message": "User not found"
}
~~~

ValidationPipe产生的message数组也会保留。数组顺序和默认消息文案不作为本节验收条件。正常请求不进入Filter；本节不会把成功响应统一包成`{ data: ... }`。

## 12. 用四条路径理解执行位置

~~~text
合法创建：请求体 → DTO校验通过 → Controller → Service → Repository → 201用户对象

非法创建：请求体 → ValidationPipe抛400 → Filter → 400错误体
                              Controller与Service方法不执行

用户不存在：路径转换和范围检查通过 → Controller → Service抛404 → Filter

未知故障：Controller/Service/Repository抛未处理Error → Filter → 通用500
~~~

同一个请求包含多个错误时，不依赖“哪个参数的错误一定最先返回”。验收时一次只改变一个条件，更容易确认是哪一层在工作。

Filter并不是任意后台任务的全局兜底，也不能处理发生在Nest请求异常链之外的所有错误。异步业务操作应正确`await`或返回Promise，避免请求早已结束后才出现无人处理的失败。

## 13. 怎么练、怎么自测

把下面场景加入学习工程原有的HTTP请求文件。测试非法更新时，先创建一个用户，再使用实际返回的ID；不要依赖固定执行顺序或开发模式重启前的内存数据。

| 场景 | 输入 | 预期 |
| --- | --- | --- |
| 合法创建 | name=Bob，email=bob@example.com | 201，返回公开用户对象 |
| 缺少姓名 | `{"email":"bob@example.com"}` | 400，不新增记录 |
| 数字姓名 | `{"name":123,"email":"bob@example.com"}` | 400 |
| 纯空格姓名 | `{"name":"   ","email":"bob@example.com"}` | 400 |
| 超长姓名 | 超过50字符 | 400 |
| 非法邮箱 | email为not-an-email | 400 |
| 多余字段 | 合法创建体再加role | 400，不静默接受 |
| 部分更新 | `{"name":"Bob Updated"}` | 200，原邮箱保留 |
| null更新 | `{"name":null}` | 400，原姓名保留 |
| 空更新 | `{}` | 200，存在用户字段保持原值 |
| 非整数ID | `/users/abc`、`/users/1.5` | 400 |
| 范围错误ID | `/users/0`、`/users/-1`、`/users/9007199254740992` | 400 |
| 合法但不存在 | 一个确认不存在的正安全整数ID | 404 |
| 未知异常 | 本地临时让业务方法抛`new Error('internal detail')` | 500，响应无internal detail和堆栈 |

未知异常练习完成后立即恢复代码，不保留专门触发错误的对外接口。非法创建前后比较列表数量，非法更新前后重新查询记录，才能确认数据没有变化。

还可以在学习工程临时写一个断言，单独核对自定义ID Pipe的边界：

~~~ts
import assert from 'node:assert/strict';
import { BadRequestException } from '@nestjs/common';
import { PositiveSafeIntPipe } from './src/common/pipes/positive-safe-int.pipe.js';

const pipe = new PositiveSafeIntPipe();
assert.equal(pipe.transform(1), 1);
for (const value of [0, -1, 1.5, Number.MAX_SAFE_INTEGER + 1, NaN, Infinity]) {
  assert.throws(() => pipe.transform(value), BadRequestException);
}
~~~

这是运行在工程现有TypeScript环境中的小检查，不覆盖Nest路由、DTO元数据或全局Filter。HTTP场景仍要实际发送请求验证。

## 14. 常见问题按哪一层查

| 现象 | 先查什么 |
| --- | --- |
| DTO写好了，非法body仍进入Controller | 全局Pipe是否启用、参数是否使用DTO类、编译元数据是否存在 |
| DTO没有运行时类型信息 | 是否import type、是否使用interface、构建工具是否生成元数据 |
| 正常字段被当成多余字段 | 字段是否有验证装饰器，是否导入正确DTO |
| 创建时缺字段也通过 | 是否误开skipMissingProperties或给创建字段加了可选规则 |
| 更新null被接受 | 是否使用了会跳过null的IsOptional或映射类型默认规则 |
| 非法ID变成404 | 是否只做了查询，没有先做解析和范围检查 |
| 校验失败全部变成500 | Filter是否保留HttpException状态，是否被其他代码重新包装 |
| 返回500但泄露内部错误 | 是否直接返回exception.message、getResponse或异常对象 |
| Service单测没有自动验证DTO | 是否绕过HTTP入口；输入边界需要单独安排 |

## 15. 检查自己是否理解

> [!question]- 1. `class CreateUserDto`为什么仍不等于自动校验？
> 类只提供运行时身份和数据形状。验证规则来自装饰器，执行来自Pipe；还必须让框架能确定路由参数对应哪个DTO。

> [!question]- 2. `@Inject()`已经能启动应用，为什么DTO可能仍校验失败？
> 构造函数注入token与路由参数的设计类型元数据属于不同用途。显式指定依赖token，不会自动补上body对应的DTO类型信息。

> [!question]- 3. whitelist为什么不能直接防止密码哈希泄露？
> 它处理的是请求输入白名单。输出需要独立选择公开字段，返回类型标注也不会删除运行时对象属性。

> [!question]- 4. 为什么本节PATCH不用IsOptional直接跳过字段？
> 本节允许字段未提交，但拒绝明确传入null。IsOptional会同时跳过null与undefined，因此这里用ValidateIf明确条件。

> [!question]- 5. `/users/0`和不存在的正整数ID为什么不同？
> 0不满足本项目ID格式与范围约定，在Pipe中返回400。正安全整数可进入业务查询，查不到才由Service返回404。

> [!question]- 6. 为什么不在每个Controller写try/catch？
> 没有恢复、转换或补偿目的的重复捕获会分散错误约定。让异常进入统一处理链，Service表达业务失败，Filter负责HTTP错误输出即可。

> [!question]- 7. Filter能不能统一成功响应？
> 不能靠这个异常Filter完成。正常返回不会进入catch；需要统一成功响应时再单独评估Interceptor等机制。

> [!question]- 8. 接入数据库后，原始SQL错误能直接包装成BadRequestException吗？
> 不应这样处理。应识别具体业务冲突并转换为安全的已知异常，未知故障保留500且隐藏细节，避免错误归类和信息泄露。

## 16. 本节验收与下一节

- [ ] 能区分TS输入类型、请求DTO、存储记录和公开响应。
- [ ] 能说明验证装饰器、ValidationPipe、编译元数据分别负责什么。
- [ ] 创建时拒绝缺失字段、错误类型、纯空格姓名和非法邮箱。
- [ ] 更新允许省略字段，但拒绝null；多余字段被拒绝。
- [ ] ID经过整数转换以及正数、安全整数范围检查。
- [ ] 输入错误为400，记录不存在为404，未知故障为500。
- [ ] 失败创建或更新不会改变内存数据，响应不泄露内部错误。
- [ ] 正常返回保持原用户对象，Controller没有重复错误处理代码。

完成后进入第04节：配置、MySQL与Repository。届时复用已有数据库和SQL知识，把内存实现替换为连接池支持的数据访问，不同时引入ORM。以上验收均为待核对项，不代表已经完成实践。

通用原理复用：[[20-后端/Express与工程化/04-运行时校验与配置管理]]、[[20-后端/Express与工程化/03-统一异常处理与工程化]]。

返回：[[20-后端/NestJS/00-NestJS学习路线-面向SpringBoot过渡]]、[[20-后端/00-后端学习导航]]。
