# 第 04 节　同一个用户查询，Java 怎样编译和运行？

在 [[20-后端/Java/03-类对象与列表|上一节]]，你用 `java TeamReport.java` 打印了有待办的成员。一个文件里明明写了 `TeamReport` 和 `Member` 两个类，为什么没看到两个产物？那条命令使用的是源码启动模式：它替你编译并运行，不把 `.class` 文件留在练习目录。这一节先不写新逻辑，只换一种运行方式。

## 先把已经写好的程序分两步运行

先分清三样东西。**源码**是你编辑的文本（`.java`）；**字节码**是编译器按 Java 虚拟机的指令格式写出的内容（通常在 `.class` 中）；**正在运行的程序**则是 JVM（Java 虚拟机）加载类、调用方法后的执行过程。前两种是留在磁盘上的文件，最后一种是一次执行，结束后不会继续等你改源码。JDK 是开发工具包，`javac` 和 `java` 都是里面的命令；JVM 不是另一个需要你手敲的编译命令。

| 想做什么 | 给谁什么输入 | 做完看哪里 |
| --- | --- | --- |
| 像前三节一样直接看结果 | `java TeamReport.java`：给启动器源码文件 | 屏幕上的业务输出；不用自己管理字节码文件 |
| 把一次构建的结果留在磁盘 | `javac -d out TeamReport.java`：给编译器源码和输出目录 | `out` 中的 `.class` 文件，不期待成员姓名 |
| 不碰源码，只运行刚才的产物 | `java -cp out TeamReport`：给启动器查找目录和类名 | 屏幕上的成员姓名；这里不写 `.java` 或 `.class` 后缀 |

在有 `TeamReport.java` 的目录打开 PowerShell，用 JDK 21 执行：

```powershell
javac -encoding UTF-8 -d out TeamReport.java
Get-ChildItem out -Name
java -cp out TeamReport
```

预期能看到 `TeamReport.class` 和 `Member.class`，运行结果仍与上一节相同。`javac` 读取源码，`-d out` 指定产物目录；第二条命令让你亲眼看到文件；最后的 `java` 从 `out` 加载类，这次并不读取 `TeamReport.java`。

**先猜再试：**只在源码里把「小林」改成「小林同学」，保存，先只执行最后一行。为什么还是旧名字？再执行第一行和最后一行，对照两次输出。能解释差异，就抓住了编译和运行的区别。如果熟悉 TypeScript，这类似改了 `.ts` 后直接运行旧的 `dist` 文件；不需要会 TypeScript 才能做这个实验。

接下来换成按 ID 查询用户的小程序。它多了一行 `package study.users`：当类有了包名，启动时该写哪个名字，`-cp` 又该指向哪一级目录？

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

## 写一个带包名的用户查询

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
3. **数据放在哪里？** 上一节的 `List<Member>` 适合逐个遍历成员。现在输入是 ID，想直接取名字，改用 `Map<Integer, String>`：键是整数 ID，值是姓名。泛型参数要写引用类型 `Integer`，普通方法参数仍可写 `int`。`Map.of` 建立不可修改的样例映射；`getOrDefault` 在键不存在时返回约定的提示。

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

### 先手推一次：为什么命令里是 `1`，方法收到的却是整数？

以 `java -cp out study.users.UserLookup 1` 为例，按空格分开读。`java` 是命令；`-cp out` 是给启动器的选项，表示类路径（classpath）的根目录；`study.users.UserLookup` 是要启动的完整类名。**类名后面的** `1` 才交给业务程序。因此 `args.length` 等于 1，`args[0]` 是文本 `"1"`，不是 `out`，也还不是整数。`Integer.parseInt` 把文本解析为整数 1；`findName(1)` 在映射中取到 `"Tom"` 并返回；最后才由 `println` 显示姓名。

| 只换输入 | 最后走到哪里 | 怎么判断 |
| --- | --- | --- |
| 不传 ID | 参数个数检查，打印用法后 `return` | 没有读取 `args[0]`，所以不会因空数组越界 |
| `9` | 已经调用 `findName`，但没有这条记录 | 看见约定的提示；程序正常结束 |
| `abc` | 开始解析，但没能得到整数 | 看见解析异常；还没有查用户 |

### 再分清三种名字：文件路径、包名、完整类名

`src/study/users/UserLookup.java` 是编译时要打开的**文件路径**；`study.users` 是源码声明的**包名**，把相关类放进同一命名空间；`study.users.UserLookup` 是程序启动时要找的**完整类名**。可以把查找过程写成一道拼接题：根目录 `out` ＋ 完整类名对应的相对路径 `study/users/UserLookup.class` ＝ 磁盘上的目标文件。所以不能因为 `.class` 躺在 `out/study/users` 就把这一层当作 `-cp` 的根。

**只动一个参数：**保持源码和产物不变，把运行命令中的 `-cp out` 临时换成 `-cp out/study/users`。预期提示找不到主类，此时连 `main` 都还没进入。还原为 `-cp out` 即可，不必改代码，也不必重新编译。下面两个实验则分别在编译时和进入 `main` 后才失败：

| 先预测                   | 怎么验证                                                                   | 要观察的结果                                                                                    |
| --------------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| 编译器能看出字符串不能直接传给整数参数吗？ | 临时把最后一行打印改成 `System.out.println(findName(args[0]));`，再执行原来的 `javac` 命令 | 编译失败，诊断指出 `String` 不能转换为 `int`。旧的 `.class` 可能还留在 `out` 中；此时运行它会看到旧行为。恢复源码并重新编译            |
| 源码类型都正确，输入一定合法吗？      | 使用恢复后的程序执行 `java -cp out study.users.UserLookup abc`                   | 程序已经启动，运行到 `Integer.parseInt` 时抛出 `NumberFormatException`。在堆栈里找到 `UserLookup.main` 对应的源码行 |

对比一下 `9` 和 `abc`：前者是合法整数，查询完成但没有记录；后者在查询之前就解析失败。这个差别以后会直接影响 HTTP 接口该返回怎样的错误。

## 轮到你

先不看命令表，回答：改了命令行 ID，要不要重编？改了源码里的姓名，要不要重编？提示：看你用的是源码启动，还是分开构建与启动。若按本章的 `-cp out` 启动，ID 是每次运行时提供的，换 ID 不必重新编译；姓名保存在编译产物中，改源码后要重编才能看到新值。

给样例增加用户 `3 → Lin`，先猜改完源码但还没编译时，运行 `java -cp out study.users.UserLookup 3` 会看到什么。然后重新编译，再执行相同命令。**能用“这一次 JVM 加载的是哪份产物”解释两次结果，就掌握了分开编译与运行的关键区别。**

[[20-后端/Java/05-Maven工程与JUnit单元测试|第 05 节：Maven 与 JUnit]] 会把“找到用户”和“没有记录”写成 JUnit 测试，交给 Maven Wrapper 一次执行。[[20-后端/Java/00-Java后端学习路线|返回学习路线]]
