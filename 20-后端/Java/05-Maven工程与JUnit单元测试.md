# 第 05 节　Maven 工程与 JUnit 单元测试：让程序自动证明结果正确

上一节已经能运行 `UserLookup 1`，并看到 `Tom`。但程序还有另一个重要行为：查询不存在的 ID 时，应该返回 `User not found`。如果只手动测试一次已知用户，别人修改代码后，很容易漏掉未知用户的情况。

本节把这两个行为写成自动化测试，并让 Maven 负责工程构建和测试执行。学完后，你应该能够：

- 理解 Maven、JUnit 和 Maven Wrapper 分别解决什么问题。
- 看懂一个 Maven 项目的目录结构和 `pom.xml` 的主要部分。
- 理解依赖、插件、生命周期和常用 Maven 命令。
- 编写 JUnit 5 测试，使用断言验证方法行为。
- 让测试先失败，再修复代码，并读懂测试报告。
- 知道单元测试能证明什么、不能证明什么。

本节沿用 JDK 21、Maven Wrapper 3.9.9、JUnit Jupiter 5.11.4、Maven Compiler Plugin 3.13.0 和 Surefire 3.5.2。版本固定是为了让练习结果可复现，不表示它们永远是最新版本。

## 1　先区分构建和测试

**构建（build）**关注源码能否按工程配置编译、资源能否处理、产物能否打包。**测试（test）**关注给定输入时，程序是否表现出预期行为。

| 传给 `findName` 的 ID | 预期返回值 | 对应测试场景 |
| --- | --- | --- |
| `1` | `"Tom"` | 已知用户应返回姓名 |
| `99` | `"User not found"` | 未知用户应返回约定提示 |

一个程序可能完全能编译，却把所有用户都返回成 `"Tom"`。编译成功无法证明业务结果正确；测试就是把业务规则变成可重复执行的检查。

## 2　先认清 Maven、JUnit 和 Wrapper

| 名称 | 是什么 | 负责什么 |
| --- | --- | --- |
| Maven | Java 项目构建与依赖管理工具 | 按生命周期编译、测试、打包、安装等 |
| JUnit Jupiter | JUnit 5 的编程模型和测试 API | 提供 `@Test`、断言等测试能力 |
| Maven Wrapper | 项目自带的 Maven 启动脚本和配置 | 让团队成员使用项目约定的 Maven 版本 |
| POM（`pom.xml`） | Maven 项目对象模型配置文件 | 声明项目坐标、依赖、插件和构建配置 |
| Surefire | Maven 测试插件 | 在 `test` 阶段发现并运行单元测试 |

Maven 不等于 JUnit：Maven 负责安排构建过程，JUnit 负责描述和执行测试。JUnit 本身也不会自动知道项目要用哪个 JDK、从哪里找业务源码；这些由 Maven 工程和构建配置组织起来。

### 2.1 和 Node 项目做一个有限的对照

如果你用过 `pnpm test`，可以先把它们理解成团队统一执行测试的入口。但机制不完全相同：Node 项目通常由 `package.json` 的 scripts 定义 `test` 脚本；Maven 的 `test` 是标准构建生命周期中的一个阶段，执行时会自动经过它之前需要的阶段。

| Node 项目中常见内容 | Maven 中相近的内容 | 说明 |
| --- | --- | --- |
| `package.json` | `pom.xml` | 项目元数据和依赖配置，但字段结构不同 |
| npm / pnpm | Maven | 包管理与构建工具，工作方式不同 |
| `node_modules` | 本地 Maven 仓库 | 都会缓存依赖，但目录组织和解析机制不同 |
| `pnpm test` | `mvn test` | 团队执行测试的入口，底层流程不同 |
| Jest / Vitest | JUnit | 测试框架，API 和运行模型不同 |

## 3　把上一节的用户查询程序放进 Maven 工程

在第 04 节练习目录（能看到 `src/study/users/UserLookup.java` 的位置）打开 PowerShell。创建一个新的 Maven 工程目录：

```powershell
New-Item -ItemType Directory -Force -Path user-lookup-maven/src/main/java/study/users, user-lookup-maven/src/test/java/study/users | Out-Null
Copy-Item src/study/users/UserLookup.java user-lookup-maven/src/main/java/study/users/
Set-Location user-lookup-maven
```

如果你没有保留第 04 节的练习目录，也可以直接创建下面的目录，并把上一节的完整 `UserLookup.java` 放到 `src/main/java/study/users/`。

```text
user-lookup-maven/
├── pom.xml
└── src/
    ├── main/
    │   └── java/
    │       └── study/users/UserLookup.java
    └── test/
        └── java/
            └── study/users/UserLookupTest.java
```

Maven 默认采用约定目录：

- `src/main/java`：业务 Java 源码。
- `src/main/resources`：业务运行时需要的资源文件。
- `src/test/java`：测试源码。
- `src/test/resources`：测试所需资源。
- `target`：构建输出目录，通常不提交到 Git。

为什么要把测试代码与业务代码分开？这样打包业务程序时，不会把测试类当成正常业务类交付；测试可以使用额外依赖，也能按测试阶段单独执行。

## 4　pom.xml：告诉 Maven 项目如何构建

在工程根目录创建 `pom.xml`，写入下面的完整配置：

```xml
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>study.users</groupId>
  <artifactId>user-lookup</artifactId>
  <version>1.0.0</version>

  <properties>
    <maven.compiler.release>21</maven.compiler.release>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
  </properties>

  <dependencies>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter</artifactId>
      <version>5.11.4</version>
      <scope>test</scope>
    </dependency>
  </dependencies>

  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-compiler-plugin</artifactId>
        <version>3.13.0</version>
      </plugin>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-surefire-plugin</artifactId>
        <version>3.5.2</version>
        <configuration>
          <failIfNoTests>true</failIfNoTests>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>
```

### 4.1 项目坐标：groupId、artifactId、version

```xml
<groupId>study.users</groupId>
<artifactId>user-lookup</artifactId>
<version>1.0.0</version>
```

这三个字段构成 Maven 项目的坐标：

- `groupId`：通常表示组织或项目所属分组。
- `artifactId`：当前项目或模块名称。
- `version`：当前版本。

本例打出的默认 JAR 名称是 `user-lookup-1.0.0.jar`。坐标也用于依赖引用：其他 Maven 项目可以通过这三个值定位一个构件。

### 4.2 properties：统一配置值

```xml
<properties>
  <maven.compiler.release>21</maven.compiler.release>
  <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
</properties>
```

`maven.compiler.release` 告诉编译器按 Java 21 的语言规则和平台 API 目标进行编译。它不会替你安装 JDK；本机仍需要可用的 JDK。`project.build.sourceEncoding` 指定源码编码，避免不同环境下中文注释和字符串出现乱码。

### 4.3 dependencies：项目依赖

```xml
<dependency>
  <groupId>org.junit.jupiter</groupId>
  <artifactId>junit-jupiter</artifactId>
  <version>5.11.4</version>
  <scope>test</scope>
</dependency>
```

依赖是项目代码需要使用的外部库。Maven 根据坐标下载并管理它们。`scope` 表示依赖在哪些阶段、哪些类路径中可用。

本例使用 `test` 作用域：JUnit 用于编译和运行测试，不是用户查询程序运行时必须携带的业务依赖。常见 scope 还有 `compile`（默认，主要业务代码也可使用）、`runtime`（运行时需要但编译业务源码不一定需要）和 `provided`（由运行环境提供）。现在先掌握 `test`，其他作用域在 Spring 项目里再结合实际场景学习。

### 4.4 plugins：构建过程的工具

依赖是项目代码要调用的库；插件是 Maven 在构建过程中调用的工具。

- `maven-compiler-plugin`：负责 Java 源码编译。
- `maven-surefire-plugin`：负责 `test` 阶段发现和运行测试。
- `failIfNoTests=true`：如果没有发现测试，不要静默显示成功，而是让构建失败，避免误以为测试已经执行。

不要把 JUnit 依赖和 Surefire 插件混为一谈：前者提供测试 API，后者负责把测试运行起来。

## 5　Maven Wrapper：为什么项目里会有 mvnw.cmd？

如果每个人本机安装的 Maven 版本不同，构建行为可能不一致。Maven Wrapper 把 Maven 版本信息和启动脚本放进项目，让成员从项目根目录使用约定版本。

首次从零创建 Wrapper 需要本机已有 Maven。先确认：

```powershell
mvn -v
```

输出应显示 Maven 版本和 Java 版本；本例要求 JDK 21。然后在工程根目录生成 Wrapper：

```powershell
mvn org.apache.maven.plugins:maven-wrapper-plugin:3.3.2:wrapper "-Dmaven=3.9.9" "-Dtype=only-script"
```

生成后，项目根目录通常会出现：

```text
mvnw
mvnw.cmd
.mvn/
└── wrapper/
    └── maven-wrapper.properties
```

其中 `maven-wrapper.properties` 保存 Maven 分发包的下载地址和版本信息。之后在 Windows PowerShell 中使用：

```powershell
.\mvnw.cmd -v
```

首次运行可能需要联网下载 Maven 发行包、插件和依赖。Wrapper 固定 Maven 版本，但不会替你固定或安装 JDK。项目提交时通常应把 Wrapper 脚本和 `.mvn/wrapper` 配置一起提交。

## 6　先编译业务代码，确认迁移没有破坏程序

在 `pom.xml` 所在目录执行：

```powershell
.\mvnw.cmd compile
```

Maven 会按约定找到 `src/main/java` 中的业务源码，编译结果放在 `target/classes`。再运行：

```powershell
java -cp target/classes study.users.UserLookup 1
```

预期输出 `Tom`。这一步只证明业务源码能够编译，并且当前编译产物可以启动；它还没有自动检查未知 ID 的行为。

## 7　JUnit 测试：把预期结果写成断言

在 `src/test/java/study/users/` 新建 `UserLookupTest.java`：

```java
package study.users;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class UserLookupTest {
    @Test
    void returnsNameForKnownUser() {
        assertEquals("Tom", UserLookup.findName(1));
    }

    @Test
    void returnsFallbackForUnknownUser() {
        assertEquals("User not found", UserLookup.findName(99));
    }
}
```

### 7.1 测试类、测试方法和 @Test

- `UserLookupTest` 是测试类。JUnit 5 不要求它一定是 `public`，包级访问即可。
- `@Test` 是注解，告诉 JUnit 这个方法是一条测试用例。
- 测试方法通常不需要参数，也不需要写 `main`；JUnit 测试引擎会发现并调用它们。
- `assertEquals(expected, actual)` 比较期望值和实际值。第一个参数是预期，第二个参数是调用业务方法得到的结果。
- `import static` 允许直接写 `assertEquals(...)`，不必写完整的 `Assertions.assertEquals(...)`。

为什么测试类也声明 `package study.users`？因为 `findName` 在业务类中没有声明为 `public`，它只允许同包访问。测试源码与业务源码位于不同目录，但只要包声明相同，仍然属于同一个 Java 包。

### 7.2 为什么测试不直接调用 main？

`main` 负责读取命令行参数、检查参数数量、把文本转换成整数，再调用业务方法。这里要验证的是 `findName` 对不同 ID 的业务行为，因此直接调用它更简单、更稳定。

这也意味着当前两条测试没有验证命令行参数解析逻辑。测试能证明什么，要看测试实际经过了哪些代码路径。以后可以把参数解析拆成可单独测试的方法，或者通过集成测试验证整个程序入口。

### 7.3 常见断言与测试准备

除了 `assertEquals`，JUnit 还提供了其他常见断言：

```java
assertTrue(condition);                 // 期望条件为 true
assertFalse(condition);                // 期望条件为 false
assertNull(value);                     // 期望为 null
assertNotNull(value);                  // 期望不为 null
assertThrows(IllegalArgumentException.class, () -> {
    // 执行预期会抛出异常的代码
});
```

断言应该对应业务规则，而不是为了让测试看起来丰富而堆数量。比如待办数不能为负数，就可以用 `assertThrows` 检查构造或业务方法是否按约定拒绝非法输入。

当多条测试都需要相同的准备数据时，可以使用 `@BeforeEach`：

```java
@BeforeEach
void setUp() {
    // 每条测试执行前准备独立的测试数据
}
```

需要先导入 `org.junit.jupiter.api.BeforeEach`。JUnit Jupiter 默认采用每条测试方法一个测试类实例的生命周期；`@BeforeEach` 则明确表达每条测试前都要执行的准备动作。初学阶段先理解“每条测试应该能独立运行”，不要让某条测试依赖另一条测试先执行。

## 8　运行测试：test 阶段究竟做了什么？

在工程根目录执行：

```powershell
.\mvnw.cmd test
```

Maven 会按生命周期执行必要的前置阶段，大致包括：编译业务代码、处理测试源码、编译测试代码，然后调用 Surefire 运行测试。测试报告一般放在 `target/surefire-reports/`。

预期汇总类似：

```text
Tests run: 2, Failures: 0, Errors: 0, Skipped: 0
BUILD SUCCESS
```

关注测试数量和失败数量，不要只看最后的 `BUILD SUCCESS`。本例配置了 `failIfNoTests=true`，如果一条测试都没被发现，也会失败，避免“测试没有运行却误以为全部通过”。

### 8.1 断言失败和测试执行错误

- **Failure（失败）**：测试正常执行到了断言，但实际结果不符合预期。例如期望 `User not found`，实际得到 `null`。
- **Error（错误）**：测试执行过程中抛出了未被测试预期处理的异常，导致用例无法按预期完成。
- **Skipped（跳过）**：测试被配置或注解跳过，没有真正执行。

这几个统计项的含义不同。读报告时先定位测试方法，再看 expected、actual 或异常堆栈。

## 9　让测试先失败一次：红—绿循环

测试不是为了让构建显示绿色而随便写的。一个可靠过程是：先写出预期，再运行测试确认它能发现问题，修复业务代码后再运行。

### 第一步：运行正确版本

```powershell
.\mvnw.cmd test
```

确认两条测试都执行且通过。

### 第二步：故意制造一个业务错误

只在 `UserLookup.java` 中把：

```java
return USERS.getOrDefault(id, "User not found");
```

改为：

```java
return USERS.get(id);
```

先预测：已知 ID 1 会怎样？未知 ID 99 会怎样？然后执行：

```powershell
.\mvnw.cmd test
```

预期 `returnsFallbackForUnknownUser` 失败，报告类似：

```text
expected: <User not found> but was: <null>
```

为什么？`Map.get` 在键不存在时返回 `null`；`Map.getOrDefault` 才会在键不存在时返回给定默认值。

### 第三步：恢复正确实现

把代码恢复为：

```java
return USERS.getOrDefault(id, "User not found");
```

再次运行 `test`，确认两条用例通过。这个过程就是常见的 Red-Green：先看到测试因预期行为不满足而失败（红），修复后通过（绿）。后续可以再重构代码，并确保测试继续通过。

## 10　Maven 生命周期和常用命令

Maven 的 Default 生命周期由多个阶段组成。执行靠后的阶段时，通常会依次执行同一生命周期中它前面的阶段。可以先把常见顺序记成：

```text
validate
   ↓
compile
   ↓
test-compile
   ↓
test
   ↓
package
   ↓
verify
   ↓
install
   ↓
deploy
```

这不是说每个项目每个阶段都会产生可见文件，而是 Maven 按阶段调用绑定的插件目标。当前最重要的是理解：`test` 之前会先编译业务代码和测试代码；`package` 会先经过 `test`；`install` 和 `deploy` 则是更靠后的发布/共享阶段。

| 命令 | 主要作用 | 适合什么时候用 |
| --- | --- | --- |
| `mvnw.cmd -v` | 查看 Wrapper 实际使用的 Maven 版本和 Java 版本 | 环境检查 |
| `mvnw.cmd compile` | 编译业务源码 | 先确认业务代码能否编译 |
| `mvnw.cmd test` | 编译并运行单元测试 | 日常改代码后的快速检查 |
| `mvnw.cmd package` | 执行前置阶段并打包 | 需要生成 JAR 等构建产物 |
| `mvnw.cmd verify` | 执行到验证阶段 | 运行更完整的构建检查 |
| `mvnw.cmd clean` | 清理 `target` 构建输出 | 想从干净目录重新构建 |
| `mvnw.cmd clean package` | 清理后重新构建并打包 | 验证不是误用了旧产物 |

注意：`clean` 属于独立的 Clean 生命周期；`package` 属于 Default 生命周期。`clean package` 是连续请求执行两个生命周期阶段。`package` 会经过 `test` 阶段，因此本例测试失败时，不会正常完成后面的打包。

`install` 会把构建产物安装到本机 Maven 仓库，供本机其他 Maven 项目依赖；`deploy` 通常用于把构件发布到远程仓库。当前阶段先掌握 `compile`、`test`、`package`、`verify` 和 `clean`。

## 11　测试到底能证明什么？

当前两条测试直接调用 `UserLookup.findName`，它们能证明在给定映射和输入下，这个方法返回预期结果。但它们不能证明所有系统行为都正确。

| 测试类型 | 主要验证什么 | 本例对应的例子 |
| --- | --- | --- |
| 单元测试 | 一个方法或小范围逻辑的行为 | `findName(1)` 和 `findName(99)` |
| 集成测试 | 多个组件组合后的行为 | Repository、数据库连接和 SQL 一起工作 |
| 端到端测试 | 从外部入口走完整条业务链路 | 启动 HTTP 服务并发送真实请求 |

单元测试通常运行快、定位直接，但它不能代替真实数据库、HTTP 序列化、权限和并发测试。后续 Spring Boot 课程会逐步加入 MockMvc、真实数据库测试和 Testcontainers。

测试也不是“测试越多就一定没有 bug”。要优先覆盖业务规则、边界条件、异常路径和容易回归的历史问题。不要只测试 happy path，也不要写只验证 `true == true` 这种没有业务价值的断言。

## 12　常见问题排查

| 现象 | 可能原因 | 排查顺序 |
| --- | --- | --- |
| 找不到 `mvnw.cmd` | 当前目录不是工程根目录，或 Wrapper 未生成 | `Get-ChildItem -Name`，确认能看到 `pom.xml` 和 `mvnw.cmd` |
| `mvn` 找不到 | 本机尚未安装 Maven，或 PATH 未配置 | 先用 `mvn -v` 检查；如果已有 Wrapper，后续直接使用 Wrapper |
| 下载依赖失败 | 网络、代理、仓库镜像或证书问题 | 看失败 URL 和具体连接错误，不要先改业务代码 |
| 测试源码无法编译 | JUnit 依赖、import、包名或方法签名错误 | 先看 `testCompile` 附近的编译错误 |
| `Tests run: 0` | 测试命名或 Surefire 发现规则不匹配 | 检查测试类名、`@Test`、插件配置；本例要求零测试时失败 |
| 断言失败 | 实际结果与业务预期不一致 | 先看 expected / actual，再定位方法实现 |
| 目录里有 JAR 但本轮失败 | 可能是上次构建留下的旧产物 | 执行 `clean package`，再确认本轮构建结果 |

## 13　独立练习

1. 在 `USERS` 中新增用户 `3 -> "Mina"`。先只新增一条测试，执行 `test`，记录它第一次的实际结果；再修改业务数据，让测试通过。
2. 为未知 ID 增加一个边界测试，确认 `findName(-1)` 返回什么。先写下业务规则，再决定预期值。
3. 临时把测试类改名为不符合默认发现规则的名称，观察 Maven 是否还会运行它；恢复名称后再验证。
4. 故意删掉一个 `@Test`，看测试数量如何变化；再恢复。理解“测试全部通过”和“测试确实执行了预期数量”是两件事。
5. 分别执行 `compile`、`test`、`package`，观察 `target` 目录中生成的内容，并说明每个命令能证明什么。

**完成标准：**你能从空目录创建 Maven 工程，解释 `pom.xml` 的依赖和插件，使用 Wrapper 执行测试，读懂一条失败报告，并通过先失败、再修复的方式证明测试确实能发现业务错误。

下一节进入 Java 语言进阶：包装类型、`null`、`equals` / `hashCode`、`Object`、枚举、泛型、集合和异常。课程总览见 [[20-后端/Java/00-Java后端学习路线|Java 后端学习路线]]。
