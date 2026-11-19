# 第 06 节　Interceptor 能看到哪一段请求？

第 03 节的 `GET /users/:id` 已经会校验 ID、查询用户。现在有个小需求：给用户接口统一记录处理耗时，包括参数校验失败的那次。把计时写进 `findOne()` 会漏掉一种情况：Pipe 拒绝参数时，Nest 根本不会调用这个方法。[原有用户接口](../../../node/node-backend-study/labs/nest-03-dto-validation/src/users/users.controller.ts)

## 用 Interceptor 包住处理过程

下面的拦截器可以挂在 `UsersController` 类上。Nest 每次调用它时，`context.getHandler()` 指向这次匹配的方法，例如 `findOne`。`next.handle()` 提供后续处理的结果流，包含参数 Pipe、Controller 以及它调用的 Service。

```ts
import { Injectable, type CallHandler, type ExecutionContext, type NestInterceptor } from '@nestjs/common';
import { finalize } from 'rxjs';

@Injectable()
export class TimingInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler) {
    const method = context.getHandler().name;
    const start = performance.now();
    return next.handle().pipe(
      finalize(() => console.log(method, Math.round(performance.now() - start), 'ms')),
    );
  }
}
```

这里的 `.pipe(finalize(...))` 是 RxJS 给结果流附加结束动作的写法。成功返回、下游抛错或订阅取消都会触发它。参数上的 `ParseIntPipe` 则由 Nest 用来转换输入。计时范围从进入拦截器开始，到这段处理结束为止。

## 把两个装饰器挂在不同位置

在原 Controller 的类上加 `@UseInterceptors(TimingInterceptor)`，列表和详情都会计时。只在 `findOne` 方法上加 `@UseGuards(AccessGuard)`，访问详情时才做这项检查。这里假设 Guard 的 `canActivate()` 返回布尔值。

| 请求 | 执行到哪里 | 有耗时日志吗？ |
| --- | --- | --- |
| 放行，`GET /users/1` | Guard → Interceptor → 两个 Pipe → `findOne` → Service 返回用户，响应 200 | 有 |
| 拒绝，`GET /users/0` | Guard 返回 `false`，Nest 返回 403，ID 校验还未开始 | 没有 |
| 放行，`GET /users/0` | Interceptor 已进入。`ParseIntPipe` 把字符串转成数字 0，正整数 Pipe 抛错，响应 400 | 有，虽然 `findOne` 没有执行 |

把请求换成列表 `GET /users` 再想一次：它会经过类上的计时拦截器，方法级的详情 Guard 对它没有作用。以后要统计所有被 Guard 拒绝的请求，就要把观测点放到更早的位置，例如 Express Middleware。

[[20-后端/NestJS/00-NestJS学习路线-面向SpringBoot过渡|学习路线]] · [[20-后端/NestJS/03-DTO校验Pipe与统一异常|回看 Pipe 与异常]] · [[20-后端/NestJS/13-Nest常用装饰器分类速查|装饰器速查]]
