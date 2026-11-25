# 第 04 节　从 TypeScript 到 Java：编译、包与运行机制

前面几节使用 `java TaskSummary.java` 或 `java TeamReport.java` 直接运行源码。现在换一种方式：先把 `.java` 源码编译成 `.class` 字节码，再让 JVM 运行编译结果。接着把用户查询程序放进 `study.users` 包，理解目录结构、完整类名和类路径之间的关系。

本节重点不是新增复杂业务，而是回答这些问题：

- JDK、JVM、`javac` 和 `java` 分别负责什么？
- `.java`、`.class`、JAR 分别是什么？
- 为什么改了源码却运行出旧结果？
- `package`、`import`、目录结构和完整类名有什么关系？
- `-cp` 应该指向哪一级目录？
- 编译错误、找不到类和运行时异常有什么区别？

课程环境为 JDK 21、Windows PowerShell。示例命令均从指定的工程目录执行。

## 1　先建立 Java 程序的运行地图

先区分四样东西：

| 名称 | 是什么 | 主要作用 |
| --- | --- | --- |
| `.java` | 源码文件 | 程序员编写和维护的 Java 文本 |
| `javac` | Java 编译器 | 检查源码并生成 JVM 能识别的字节码 |
| `.class` | 字节码文件 | 保存一个类或接口的编译结果 |
| JVM | Java 虚拟机 | 加载、验证并执行字节码 |

JDK 是 Java 开发工具包，包含编译器、启动器和开发工具。`javac` 和 `java` 都是 JDK 提供的命令。JVM 是运行时执行环境，不是让你单独输入的一条编译命令。

### 1.1 JDK、JVM 和 JRE 怎么区分？

- **JVM（Java Virtual Machine）**：负责加载和执行 Java 字节码，并提供运行时内存管理等能力。
- **JRE（Java Runtime Environment）**：传统上指运行 Java 程序所需的 JVM 和运行库集合。现代 JDK 发行版的打包方式有所变化，不一定像早期版本那样单独提供一个可下载的 JRE 安装包。
- **JDK（Java Development Kit）**：开发工具包，除了运行所需组件，还包含 `javac` 等开发工具。

学习和开发时安装 JDK 即可。不要把“安装 JVM”“安装 JRE”“安装 JDK”当成三个必须分别完成的动作。

### 1.2 Java 编译和运行大致发生什么？

```text
UserLookup.java
      │
      │ javac 编译、检查语法和类型
      ▼
UserLookup.class
      │
      │ java 启动 JVM，按类名和类路径查找类
      ▼
JVM 加载并执行字节码
      │
      ▼
程序输出或抛出运行时异常
```

`.class` 中不是普通 Java 源码，也不是直接针对某一种 CPU 的机器码，而是 JVM 字节码。JVM 可以解释执行字节码，也可以在运行过程中使用 JIT（即时编译）把热点代码编译成当前机器更适合执行的机器码。因此“Java 先编译”与“Java 运行时还会做优化”并不矛盾。

## 2　源码启动模式与分开编译运行

在 JDK 11 及之后，可以使用源码文件启动模式：

```powershell
java TaskSummary.java
```

启动器会处理单文件源码并运行程序，适合学习和小实验。它隐藏了显式编译步骤，因此你没有手动指定 `.class` 输出目录。

如果要明确控制编译产物，就分成两步：

```powershell
javac -encoding UTF-8 -d out TaskSummary.java
java -cp out TaskSummary
```

第一条命令调用编译器；第二条命令启动 JVM，从 `out` 目录查找名为 `TaskSummary` 的类。运行时写的是类名，不是源码文件名，也不带 `.java` 或 `.class` 后缀。

### 2.1 做一次“旧产物”实验

在有 `TeamReport.java` 的目录打开 PowerShell。这里沿用第 03 节的完整成员统计示例。

```powershell
New-Item -ItemType Directory -Force out | Out-Null
javac -encoding UTF-8 -d out TeamReport.java
Get-ChildItem out -Name
java -cp out TeamReport
```

预期 `out` 中能看到 `TeamReport.class`，如果 `TeamReport.java` 里还定义了另一个顶层类 `Member`，通常也会生成 `Member.class`。屏幕输出应与上一节相同。

现在只在源码中把“小林”改成“小林同学”，保存，但先不要执行 `javac`，直接运行：

```powershell
java -cp out TeamReport
```

你仍会看到旧名字。原因是这条命令没有读取刚修改的 `.java`，它运行的是上次编译留下的 `.class`。再执行编译命令和运行命令，才会看到新名字。

**关键结论：改运行参数，不一定要重新编译；改源码后，如果采用分开编译运行的方式，就需要重新编译，再运行新产物。**

### 2.2 JAR 是什么？

`.class` 通常按包目录分别保存。项目类和资源文件变多后，可以把它们打包成一个 `.jar` 文件。JAR 本质上是遵循约定目录结构的 ZIP 格式归档，里面可以包含 `.class`、配置文件、资源和元数据。

需要区分两种常见用途：

- **普通库 JAR：**供其他 Java 程序放进类路径使用，不一定能直接启动。
- **可执行 JAR：**清单文件（Manifest）中声明了入口类等启动信息，才可以通过 `java -jar xxx.jar` 启动。即使可执行 JAR，也要看它是否包含或正确声明了运行所需依赖。

因此，“目录里有一个 JAR”不等于“它一定能双击运行”。第 05 节会通过 Maven 生成 JAR，并认识打包阶段。

### 2.3 IntelliJ IDEA 的运行按钮做了什么？

在 IDEA 中点击绿色运行按钮，本质上也是让 IDE 根据运行配置准备类路径、编译必要源码，再启动 JVM。它替你管理了很多命令行参数，所以看起来只点了一下按钮。

如果运行的是带 `main` 的类，IDEA 会选择对应的主类；如果在 Run Configuration 中填写 Program arguments，内容会进入 `main(String[] args)`。因此命令行里的：

```powershell
java -cp out study.users.UserLookup 1
```

可以在 IDE 中对应理解为：主类 `study.users.UserLookup`、类路径 `out`、程序参数 `1`。IDE 能帮你执行，但不会改变 Java 的编译、类加载和参数传递规则。

## 3　包 package：给类组织命名空间

一个项目通常不只有一个类。若所有类都放在默认位置，名称容易冲突，也不方便组织代码。Java 使用 `package` 把类组织到包中。

例如用户查询类属于 `study.users` 包：

```java
package study.users;

public class UserLookup {
}
```

`package study.users;` 表示这个类的包名是 `study.users`。包名通常使用小写字母，并用点号分隔层级。它应该位于源码文件最前面（注释除外），在普通源码中不能写在类定义之后。

### 3.1 包名与目录结构对应

本例建议使用这样的目录结构：

```text
练习目录/
└── src/
    └── study/
        └── users/
            └── UserLookup.java
```

在 PowerShell 中创建目录：

```powershell
New-Item -ItemType Directory -Force -Path src/study/users | Out-Null
```

包名 `study.users` 通常对应目录 `study/users`。注意：包名中的点号在文件路径里变成目录分隔符，但包名本身仍然写点号。

### 3.2 public 类和文件名

Java 源文件可以包含多个顶层类，但一个源文件最多只能有一个 `public` 顶层类，并且文件名必须与这个公开类名完全一致，包括大小写。

例如：

```java
// 文件名必须是 UserLookup.java
public class UserLookup {
}

class LookupHelper {
}
```

`LookupHelper` 没有声明为 `public`，可以和 `UserLookup` 放在同一个源码文件中。真实项目通常会把不同职责的类拆到不同文件，方便维护和查找。

## 4　import：使用其他包中的类型

如果要使用 Java 标准库中的 `Map`，可以在文件开头导入：

```java
import java.util.Map;
```

之后可以直接写 `Map<Integer, String>`。如果不写 import，也可以使用完整类名：

```java
java.util.Map<Integer, String> users;
```

`import` 只是让源码可以使用较短的类型名称，不是把另一个类的代码复制进当前文件，也不会自动创建对象。`java.lang` 包中的常用类型（如 `String`、`System`、`Integer`）由 Java 自动导入，因此通常不需要手动写 `import java.lang.String;`。

## 5　写一个带包名的用户查询程序

在 `src/study/users/` 下新建 `UserLookup.java`，保存下面的完整代码：

```java
package study.users;

import java.util.Map;

public class UserLookup {
    private static final Map<Integer, String> USERS =
            Map.of(1, "Tom", 2, "Alice");

    static String findName(int id) {
        return USERS.getOrDefault(id, "User not found");
    }

    public static void main(String[] args) {
        if (args.length != 1) {
            System.out.println("Usage: UserLookup <id>");
            return;
        }

        int id = Integer.parseInt(args[0]);
        System.out.println(findName(id));
    }
}
```

从上到下理解：

1. `package study.users;` 声明包名。
2. `import java.util.Map;` 导入标准库的 `Map` 接口。
3. `public class UserLookup` 定义公开类，文件名因此必须是 `UserLookup.java`。
4. `Map<Integer, String>` 表示键是整数包装类型 `Integer`，值是 `String`。泛型和集合会在后续课程深入。
5. `Map.of(...)` 创建一份不可修改的样例映射。
6. `getOrDefault(id, "User not found")` 表示存在这个键就返回对应姓名，不存在就返回默认提示。
7. `args` 是命令行参数数组；命令行传入的参数最初都是文本，所以 `args[0]` 是字符串。
8. `Integer.parseInt(args[0])` 把文本解析为整数。如果传入 `abc`，它会抛出 `NumberFormatException`。

这里的 `findName` 没有写 `public`，属于包级访问。后续测试类也放在 `study.users` 包中，因此能够访问它。访问权限的完整规则已在 [[20-后端/Java/03-类对象与列表#6 封装与 Getter / Setter：不要让外部随意修改对象内部数据|第 03 节]] 介绍。

## 6　编译、查看产物，再运行

下面所有命令都从包含 `src` 目录的练习根目录执行：

```powershell
New-Item -ItemType Directory -Force out | Out-Null
javac -encoding UTF-8 --release 21 -d out src/study/users/UserLookup.java
Get-ChildItem out/study/users
java -cp out study.users.UserLookup 1
java -cp out study.users.UserLookup 9
java -cp out study.users.UserLookup
```

编译成功时，`javac` 通常没有成功提示输出。`out/study/users/` 中应出现 `UserLookup.class`。三次运行的输出依次是：

```text
Tom
User not found
Usage: UserLookup <id>
```

命令拆解：

```powershell
java -cp out study.users.UserLookup 1
```

- `java`：启动 JVM 的命令。
- `-cp out`：设置类路径（classpath），告诉 JVM 从 `out` 这个根目录查找类。
- `study.users.UserLookup`：要启动的完整类名，即包名加类名。
- `1`：类名后面的内容才是传给 `main` 的业务参数，所以 `args[0]` 是文本 `"1"`。

### 6.1 为什么 -cp 要指向 out，而不是 out/study/users？

JVM 根据完整类名，把点号转换成目录层级，再到类路径根目录下查找：

```text
类路径根目录：out
完整类名：study.users.UserLookup
查找相对路径：study/users/UserLookup.class
最终位置：out/study/users/UserLookup.class
```

因此 `-cp` 应该指向包目录的上一级根目录 `out`，而不是已经进入包内部的 `out/study/users`。

**只改一个参数验证：**保持源码和产物不变，把命令中的 `-cp out` 临时改为 `-cp out/study/users`。预期 JVM 报告找不到主类，因为它会尝试在错误的根目录下继续寻找 `study/users/UserLookup.class`。改回 `-cp out` 即可。

### 6.2 args 与业务参数

命令：

```powershell
java -cp out study.users.UserLookup 1
```

`-cp out` 是 JVM 启动选项，`study.users.UserLookup` 是主类名，主类名后面的 `1` 才会放入 `args`。如果不传参数，`args.length` 为 0；因此程序先检查长度，再访问 `args[0]`，避免数组越界。

## 7　编译错误、类加载错误、运行时异常和逻辑错误

它们发生在不同阶段，排查时不要混在一起：

| 阶段 | 例子 | 发生了什么 | 应该先检查什么 |
| --- | --- | --- | --- |
| 编译阶段 | 把 `String` 传给要求 `int` 的方法 | `javac` 无法生成当前源码对应的有效字节码 | 类型、拼写、括号、分号、方法签名 |
| 启动/类加载阶段 | `Could not find or load main class` | JVM 找不到指定的主类或依赖类 | 当前目录、`-cp` 根目录、完整类名、包目录 |
| 运行阶段 | `NumberFormatException` | 程序已经启动，执行到解析文本时失败 | 输入值和异常堆栈指出的源码行 |
| 逻辑阶段 | 输入 `9` 返回错误姓名 | 程序能编译和运行，但业务结果不正确 | 数据、条件、算法和预期规则 |

### 7.1 编译器能不能发现 String 不能传给 int？

临时把 `main` 最后一行改成：

```java
System.out.println(findName(args[0]));
```

然后重新执行 `javac`。预期编译失败，诊断指出 `String` 不能转换为 `int`。因为方法参数要求整数，而 `args[0]` 是字符串。恢复原代码并重新编译。

### 7.2 源码类型正确，输入就一定合法吗？

执行：

```powershell
java -cp out study.users.UserLookup abc
```

程序可以成功启动，但执行 `Integer.parseInt("abc")` 时会抛出 `NumberFormatException`。编译器知道 `args[0]` 是 `String`，但不知道用户运行时会输入什么文本。

### 7.3 为什么编译失败后，旧 class 可能还在？

如果上一次编译成功，`out` 已经有 `.class` 文件。后来你改坏源码，编译失败时，旧 `.class` 不一定会被自动删除。因此目录里还存在 `.class`，不代表当前源码编译成功。可以先清理输出目录，再完整编译：

```powershell
Remove-Item out -Recurse -Force
New-Item -ItemType Directory -Force out | Out-Null
javac -encoding UTF-8 --release 21 -d out src/study/users/UserLookup.java
```

`Remove-Item` 会删除 `out`，只在确认它是本次练习的构建输出目录时使用，不要把命令指向项目源码目录。

## 8　一次编译多个源文件

当一个类使用另一个类时，可以让编译器同时读取多个源文件。例如目录中有：

```text
src/
└── study/
    └── users/
        ├── UserLookup.java
        └── UserFormatter.java
```

可以显式把两个文件交给 `javac`：

```powershell
javac -encoding UTF-8 --release 21 -d out src/study/users/UserFormatter.java src/study/users/UserLookup.java
```

也可以在适当情况下让编译器根据源码引用查找依赖源码；初学时显式列出文件更直观。真实项目中通常交给 Maven 或 Gradle 管理源码目录、依赖和编译步骤，第 05 节会开始使用 Maven。

## 9　与 TypeScript / Node 的对照

| Java | TypeScript / Node 中相近的概念 | 需要注意的差别 |
| --- | --- | --- |
| `.java` 源码 | `.ts` 源码 | 都是人维护的源文件 |
| `javac` | `tsc` | 都能做编译期检查，但目标产物不同 |
| `.class` 字节码 | 编译后的 `.js`（不是完全等价） | Java 字节码由 JVM 执行；JS 通常由 JavaScript 引擎执行 |
| JVM | V8 等 JavaScript 引擎 | 两者运行模型不同，不能简单视为同一种虚拟机 |
| `java -cp ...` | `node dist/...` | Java 需要按类路径和完整类名定位类 |
| `package` | 模块/目录组织 | Java package 是类型命名空间，不等同 npm package |

如果你熟悉 TypeScript，可以把“修改源码后要重新生成运行产物”作为一个粗略类比；但 Java 的 `.class`、JVM、类加载和运行时类型体系都有自己的机制。

## 10　独立练习

1. 在 `USERS` 中增加 `3 -> "Lin"`。先只修改源码，不重新编译，运行 `UserLookup 3`，记录旧产物的表现；再重新编译并运行，比较结果。
2. 分别执行不传参数、传入 `99`、传入 `abc`。解释三种情况分别在哪一步结束。
3. 把 `-cp out` 改成错误目录，观察错误发生在 `main` 之前还是之后。
4. 解释文件路径 `src/study/users/UserLookup.java`、包名 `study.users`、完整类名 `study.users.UserLookup` 和类路径根目录 `out` 的区别。

**完成标准：**你能不看命令表，自己从源码目录编译程序、指出 `.class` 的位置、使用正确类路径启动它，并能区分编译错误、类加载错误和运行时异常。

下一节会把手动核对 `Tom` 和 `User not found` 的过程变成自动化测试：[[20-后端/Java/05-Maven工程与JUnit单元测试|第 05 节：Maven 工程与 JUnit 单元测试]]。
