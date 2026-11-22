# 第 05 节　用 Maven 和 JUnit 验证用户查询

上一节你可以运行 `UserLookup 1`，看终端是否打印 `Tom`。现在有人改了 `findName`，已知用户仍然能查到，但未知用户会得到 `null`。只试一遍 `1`，你能发现这次改动吗？这节把两个输入各写成一条可执行的规则，让同事拿到项目后，在 PowerShell 里运行一条命令就能检查它们。

| 传给 `findName` 的 ID | 预期返回值 | 手动怎么检查 |
| --- | --- | --- |
| `1` | `"Tom"` | 查已知 ID，看姓名是否正确 |
| `99` | `"User not found"` | 查不存在的 ID，看是否仍给出约定提示 |

## 把手动检查变成两条可以重复执行的规则

先区分两个目标。**构建**是把源码变成可用的产物，关注“能不能编译、能不能打包”；**测试**是给一段程序输入并检查行为，关注“即使能编译，结果对不对”。一个能成功编译但把所有名字都改成 `"未知"` 的程序，就是两者不能混为一谈的例子。下面始终沿用第 04 节的查询方法，不一边换工具一边换业务。

| 你将遇到的名字 | 它是什么 | 这里为什么需要它 |
| --- | --- | --- |
| Maven / Wrapper | 构建工具 / 工程自带的启动脚本 | 一个安排步骤，另一个让大家用约定的 Maven 版本；都不是业务代码 |
| POM / 依赖 / 插件 | 工程说明文件 / 代码要用的库 / 构建时执行工作的工具 | POM 说明需要 JUnit；编译插件和 Surefire 插件分别负责编译、组织测试运行 |
| 用例 / 断言 | 一个具体输入场景 / 这个场景中必须成立的判断 | “不存在的用户”是一种场景；“返回指定文字而不是 null”才是可检查的判断 |
| JAR / 测试报告 | 一包构建产物 / 测试的运行记录 | 交付程序看前者，定位哪条规则失败看后者；有旧 JAR 不证明本次成功 |

第 04 节的做法是运行 `java -cp out study.users.UserLookup 1`，然后用眼睛看输出。把这件事拆开：**输入**是 `1`，**预期**是 `"Tom"`，**实际结果**来自 `UserLookup.findName(1)`。JUnit 用 `assertEquals("Tom", UserLookup.findName(1))` 比较两者；不相等就报告失败。第二个输入也照样检查。这里先看懂这一行，不用动原来的程序。

为什么还要 Maven？JUnit 负责比较结果，却不替你准备工程。上节你手动指定源文件和输出目录；这节用 `pom.xml` 告诉 Maven 工程需要什么依赖，再用约定的目录区分业务代码和测试代码。以后在工程根目录运行 `.\mvnw.cmd test`，Maven 就会先编译代码，再通过 Surefire 插件运行 JUnit 测试。Wrapper（`mvnw.cmd`）负责启动工程指定版本的 Maven。

如果用过 `pnpm test`，两者都能作为团队统一的命令。区别是 Node 项目由 `package.json` 的脚本决定执行顺序；这里 `test` 是 Maven 生命周期中的阶段，后面的 `package` 默认会先经过测试，再打包。[Maven 构建生命周期](https://maven.apache.org/guides/introduction/introduction-to-the-lifecycle.html) · [对照 Nest 工程的 scripts](../../../node/node-backend-study/labs/nest-05-transactions/package.json)

## 把上一节的程序放进工程

在第 04 节练习目录（能看到 `src/study/users/UserLookup.java` 的位置）打开 PowerShell，执行下面三行。`user-lookup-maven` 是本节新目录。第一次做这节时使用一个尚未存在的同名目录，方便对照上节源码。

```powershell
New-Item -ItemType Directory -Path user-lookup-maven/src/main/java/study/users, user-lookup-maven/src/test/java/study/users | Out-Null
Copy-Item src/study/users/UserLookup.java user-lookup-maven/src/main/java/study/users/
Set-Location user-lookup-maven
```

如果你只看过上一节笔记，可以直接创建上面两个目录，再把 [[20-后端/Java/04-从TypeScript到Java-编译与运行#写一个带包名的用户查询|第 04 节的完整 UserLookup.java]] 放进 `src/main/java/study/users/`。后面的命令都在 `user-lookup-maven` 根目录执行。

```text
user-lookup-maven/
├── pom.xml                                     构建配置，下一步创建
├── src/main/java/study/users/UserLookup.java    上节的业务代码
└── src/test/java/study/users/UserLookupTest.java  本节新增的测试
```

在根目录新建 `pom.xml`，写入下面的完整配置。先只看三处：`release` 让编译器按 Java 21 编译；`scope` 为 `test` 使 JUnit 仅进入测试用的类路径；`artifactId` 和 `version` 一起决定默认 JAR 文件名。这里把关键工具版本写死，便于复现实验。

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
        <configuration><failIfNoTests>true</failIfNoTests></configuration>
      </plugin>
    </plugins>
  </build>
</project>
```

### 只在新工程里生成一次 Wrapper

**怎样读上面的 XML？** 从 `<project>` 到 `</project>` 是整个工程。先找 `groupId`、`artifactId`、`version`：三个值一起标识这份工程，本例默认产物名是 `user-lookup-1.0.0.jar`。再找两个不同的位置：`<dependencies>` 里是程序或测试需要引用的库；`<build><plugins>` 里是替构建过程做事的工具。`<scope>test</scope>` 表示 JUnit 提供给测试代码，不是运行用户查询所必需的库。`maven.compiler.release` 设为 21 是选用的 Java 目标版本，不会替你安装 JDK。第一次练习不需要背整份 XML，但要能指出“改业务版本”“加测试库”“改编译目标”分别该看哪里。

沿用上节的 JDK 21。首次从零创建工程还需要一个能运行的 Maven。Windows 可以下载 Apache Maven 的 binary zip，解压后把它的 `bin` 加入当前终端的 `Path`。先用 `mvn -v` 确认它显示 Java 21，再生成 Wrapper。如果拿到的项目根目录已经有 `mvnw.cmd` 和 `.mvn/wrapper/`，直接使用下面最后一行。[Maven 安装说明](https://maven.apache.org/install.html) · [Wrapper 官方说明](https://maven.apache.org/tools/wrapper/)

```powershell
mvn -v
mvn org.apache.maven.plugins:maven-wrapper-plugin:3.3.2:wrapper "-Dmaven=3.9.9" "-Dtype=only-script"
.\mvnw.cmd -v
```

最后一条应显示 `Apache Maven 3.9.9` 和 Java 21。工程把 `mvnw`、`mvnw.cmd` 和 `.mvn/wrapper/maven-wrapper.properties` 一起交给其他人；其中 `distributionUrl` 记录要用哪个 Maven。首次运行需要联网下载 Maven、插件和测试依赖。Wrapper 固定的是 Maven 版本，JDK 仍由本机提供。

## 写两条断言，谁来调用它们？

先别写测试。在新工程里、`pom.xml` 所在目录执行 `.\mvnw.cmd compile`。这一步相当于上节手动运行 `javac`，只是目录由 Maven 约定。借这个机会确认工程搬迁后还能运行：

```powershell
.\mvnw.cmd compile
java -cp target/classes study.users.UserLookup 1
```

预期输出姓名 `Tom`。以前类路径根是 `out`，这里换成 `target/classes`，完整类名没变。到目前为止，你只是把程序放进了工程，**还没有证明未知 ID 的结果正确**。下一步才让工具替你核对答案。

新建 `src/test/java/study/users/UserLookupTest.java`。你在 Nest 的 Pipe 测试里写过 `assert.equal(pipe.transform(1), 1)`。Node 这行把实际调用写在前面；换成 JUnit 的 `assertEquals`，顺序刚好调过来，**期望值在前，实际调用在后**。记住顺序，下一步才读得懂失败报告里的 `expected` 和 `actual`。[回看 Pipe 的原测试](../../../node/node-backend-study/labs/nest-03-dto-validation/src/common/pipes/positive-safe-int.pipe.test.ts)

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

顺着第二条测试读一遍。Surefire 按命名约定发现 `UserLookupTest`，通过 JUnit Platform 运行它。JUnit Jupiter 默认给每条测试创建一个测试类实例，调用标了 `@Test` 的方法。`import static` 让你可以直接写 `assertEquals(...)`。这行代码把 `99` 传给真实的 `findName`，拿到返回值再比较。测试与业务类都声明在 `study.users` 包，所以能访问上一节没有写 `public` 的 `findName`，即使两个文件位于不同源码目录。[JUnit 测试方法与断言](https://docs.junit.org/5.11.4/user-guide/) · [Surefire 默认发现规则](https://maven.apache.org/surefire/maven-surefire-plugin/examples/inclusion-exclusion.html)

这里刻意绕过了 `main`。如果有人改坏了 `Integer.parseInt(args[0])`，这两条测试仍可能通过：它们直接传入整数，没有经过命令行参数解析。看一条单测能证明什么，先看它从哪里进入程序。

## 让测试真的失败一次

先把四条常用命令按目的分开，避免遇到问题就全部重跑。下面的顺序特指本章没有跳过测试的工程配置：

| 命令（工程根目录） | 做到哪里 | 本步能证明什么 |
| --- | --- | --- |
| `.\mvnw.cmd compile` | 编译业务源码到 `target/classes` | 业务源码能编译；还没检查测试代码和行为 |
| `.\mvnw.cmd test` | 继续编译测试并执行，报告放入 `target/surefire-reports` | 发现并运行的用例通过或失败；看汇总数量，不只看颜色 |
| `.\mvnw.cmd package` | 经过测试后生成 JAR | 本轮成功才说明能打包；测试失败时先读报告 |
| `.\mvnw.cmd clean package` | 先清理旧 `target`，再从头走到打包 | 适合验证交付不是复用了旧文件，不必每次改代码都先清理 |

**怎样读一条失败？** 从用例名定位场景，再看 `expected`（约定的答案）和 `actual`（业务方法真的返回了什么）。如果提示连 `mvnw.cmd` 都找不到，测试还没开始，先查当前目录和脚本；如果停在下载依赖，查联网与仓库配置；如果测试源码无法编译，先查导入和依赖。只有报告明确说某条断言失败时，才回到那条业务规则，不要为让构建变绿就把预期值改成错误结果。

1. **先跑原版。** 在 `pom.xml` 所在目录执行 `.\mvnw.cmd test`。在汇总行找 `Tests run: 2, Failures: 0, Errors: 0`。数量也要核对；配置里的 `failIfNoTests` 会让零条测试直接报错。
2. **预测哪一条会红。** 只在新工程的 `UserLookup.java` 里把 `return USERS.getOrDefault(id, "User not found");` 改成 `return USERS.get(id);`。先写下 `1` 和 `99` 各会返回什么，再执行 `.\mvnw.cmd package`。
3. **读失败报告。** 本例实测失败的方法是 `returnsFallbackForUnknownUser`，断言会显示 `expected: <User not found> but was: <null>`，汇总里有 `Tests run: 2, Failures: 1`。`Map.get` 在键缺失时返回 `null`。这行代码能编译，因此错误出现在测试阶段，后面的打包阶段不会执行。完整报告在 `target/surefire-reports/study.users.UserLookupTest.txt`。
4. **修复并交付。** 恢复原来的 `getOrDefault`，保留两条断言。执行下面命令，从干净的输出目录重新测试、打包，再用上一节认识的类名启动入口。

```powershell
.\mvnw.cmd clean package
java -cp target/user-lookup-1.0.0.jar study.users.UserLookup 1
java -cp target/user-lookup-1.0.0.jar study.users.UserLookup 99
```

本例在 Windows、JDK 21 和 Maven 3.9.9 下实测，恢复代码后 Maven 显示 `BUILD SUCCESS`，两次运行分别打印 `Tom` 和 `User not found`。`clean` 清除 `target/` 的旧产物，`package` 负责本次构建。以后排查“打包明明失败了，为什么目录里还有 JAR”，先查那份 JAR 是否出自上一次成功构建。

## 独立练习

产品要新增一名用户 `3 → Mina`。先只写第三条测试，运行 `test` 并记录实际值；再自行修改业务数据，让三条测试一起通过。最后从打好的 JAR 查询 `3`。验收看三个现象：新用例第一次确实失败，修复后报告显示三条通过，命令行打印 `Mina`。

合上笔记，试着回答：同事只改了缺失用户的提示，为什么 `compile` 会成功而 `package` 会失败？能指出是哪条断言阻止打包，就可以进入第 06 节，比较 Java 中的值、引用与 `null`。[[20-后端/Java/00-Java后端学习路线|返回 Java 学习路线]]
