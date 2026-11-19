# 第 01 节　同一个用户查询，Java 怎样编译和运行？

这节课做一个小程序：在终端输入用户 ID，程序打印名字。你已经会写查询逻辑。这次要亲手看到的是，**哪一步把源码变成能执行的产物，哪个错误在编译时就会被拦下来，哪个要等到输入真正到来才出现。**

## 先从熟悉的 TypeScript 看起

```ts
const users = new Map<number, string>([[1, "Tom"], [2, "Alice"]]);

function findName(id: number): string {
  return users.get(id) ?? "User not found";
}
```

在常见的 Node 项目中，可以用 `tsc` 把 TypeScript 编译成 JavaScript，再让 Node 运行生成的文件。Java 也可以分两步观察：

| 你想做什么  | TypeScript / Node     | 本节的 Java 工具                                    |
| ------ | --------------------- | ---------------------------------------------- |
| 编译源文件  | `tsc` 可以做类型检查并生成 JS   | `javac` 检查 Java 源码，成功后生成含 JVM 字节码的 `.class` 文件 |
| 执行编译产物 | 例如 `node dist/app.js` | `java` 启动 JVM，加载指定的类并调用入口方法                    |

这个类比有一个边界。JS 产物仍然是可以打开阅读的脚本，Java 的字节码由 JVM 加载执行。启动时通常给 `java` 一个**类名**，并告诉它从哪个目录寻找类。

## 准备工作

在 PowerShell 中分别执行：

```powershell
java -version
javac -version
```

两条命令都应报告版本，本课程以 **JDK 21** 为基准。JDK 是 Java 开发工具包，包含编译器和运行工具。如果命令找不到，可以安装 Windows x64 的 JDK 21，或者解压 JDK 并在当前终端使用它的 `bin`。安装后重开终端再核对；两条命令指向不同版本时，用 `Get-Command java,javac` 查看各自位置。[Temurin JDK 21 下载](https://adoptium.net/temurin/releases/?version=21)

找一个空的练习目录打开 PowerShell，接下来的命令都从这个目录执行。先创建源码目录：

```powershell
New-Item -ItemType Directory -Force -Path src/study/users | Out-Null
```

## 写第一份源码

在编辑器中新建 **`src/study/users/UserLookup.java`**，保存为 UTF-8。Java 的公开类 `UserLookup` 和文件名要一致。

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

从 `main` 往里读就行：

1. **谁调用它？** Java 启动器调用 `public static void main(String[] args)`。`public` 让入口可访问，`static` 表示可以直接通过类调用，`void` 表示没有返回值。命令行传来的参数在字符串数组 `args` 里，第一个业务参数就是 `args[0]`。
2. **为什么要转换？** 终端传来的 `"1"` 是文本，像 Nest 路径参数抵达 Pipe 之前一样。`Integer.parseInt` 从文本解析出整数，`findName(int id)` 才接到数值。解析失败的位置就在这一行。
3. **数据放在哪里？** `Map<Integer, String>` 对应上面的数字到姓名映射。Java 泛型参数使用引用类型，所以键写 `Integer`；方法参数可以写基本类型 `int`。这里 `Map.of` 创建固定的只读样例数据，`getOrDefault` 在键不存在时给出默认值。类型与集合分别在第 03、05 节展开。

## 编译一次，换几组输入运行

```powershell
javac -encoding UTF-8 --release 21 -d out src/study/users/UserLookup.java
Get-ChildItem out/study/users
java -cp out study.users.UserLookup 1
java -cp out study.users.UserLookup 9
java -cp out study.users.UserLookup
```

编译成功时 `javac` 通常没有输出。目录里应能看到 `UserLookup.class`。三次运行的输出依次是：

```text
Tom
User not found
Usage: UserLookup <id>
```

**`-d out` 决定产物写到哪里，`-cp out` 告诉 JVM 从哪里查找类。** 源文件首行的 `package study.users` 使完整类名成为 `study.users.UserLookup`，对应产物路径 `out/study/users/UserLookup.class`。改参数只需重新运行，改源码才需要重新编译。若出现“找不到或无法加载主类”，先核对当前目录、`out` 的位置和完整类名。

## 两种错误，分别停在哪一步？

| 先预测 | 怎么验证 | 要观察的结果 |
| --- | --- | --- |
| 编译器能看出字符串不能直接传给整数参数吗？ | 临时把最后一行打印改成 `System.out.println(findName(args[0]));`，再执行原来的 `javac` 命令 | 编译失败，诊断指出 `String` 不能转换为 `int`。旧的 `.class` 可能还留在 `out` 中；此时运行它会看到旧行为。恢复源码并重新编译 |
| 源码类型都正确，输入一定合法吗？ | 使用恢复后的程序执行 `java -cp out study.users.UserLookup abc` | 程序已经启动，运行到 `Integer.parseInt` 时抛出 `NumberFormatException`。在堆栈里找到 `UserLookup.main` 对应的源码行 |

对比一下 `9` 和 `abc`：前者是合法整数，查询完成但没有记录；后者在查询之前就解析失败。这个差别以后会直接影响 HTTP 接口该返回怎样的错误。

## 轮到你

给样例增加用户 `3 → Lin`，先猜改完源码但还没编译时，运行 `java -cp out study.users.UserLookup 3` 会看到什么。然后重新编译，再执行相同命令。**能用“这一次 JVM 加载的是哪份产物”解释两次结果，就过了第一关。**

第 02 节会把“找到用户”和“没有记录”写成 JUnit 测试，交给 Maven Wrapper 一次执行。[[20-后端/Java/00-Java后端学习路线|返回学习路线]]
