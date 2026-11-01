# WebChat AI Agent 前端技术栈与项目架构设计

## 1. 文档说明

| 字段 | 内容 |
| --- | --- |
| 项目名称 | WebChat AI Agent |
| 文档主题 | 前端技术栈与项目架构文件目录 |
| 推荐架构 | Electron + React + TypeScript + Node.js Agent Runtime |
| 适用阶段 | V0.1 Demo 验证版 / V0.2 基础可用版 |
| 主要目标 | 快速跑通桌面端 AI Agent 最小闭环，并为后续工具扩展、模型接入、权限控制和插件化预留结构 |

---

## 2. 项目定位

WebChat AI Agent 是一个面向个人开发者和小团队的本地桌面端 AI Agent 工具。项目目标是通过桌面端应用连接本地项目目录、AI 模型能力和本地工具能力，实现代码理解、文件读取、代码搜索、命令执行、Diff 预览和文件修改确认等功能。

一期重点不是完整商业化，也不是复杂插件生态，而是先跑通以下核心闭环：

```text
用户输入任务
→ Agent Runtime 接收任务
→ 调用模型
→ 模型判断是否需要工具
→ 调用本地 Tool 工具
→ 工具结果返回模型
→ 模型生成最终回复
→ UI 展示执行过程和结果
```

---

## 3. 总体技术选型

### 3.1 推荐技术栈总览

| 层级 | 技术选型 | 说明 |
| --- | --- | --- |
| 桌面端框架 | Electron | 提供桌面窗口、本地文件、命令执行、系统能力、IPC 通信 |
| 前端框架 | React | 负责工作台 UI、对话区、工具调用卡片、Diff 预览等界面 |
| 构建工具 | Vite | 快速开发和构建 React 渲染进程 |
| 开发语言 | TypeScript | 主进程、渲染进程、共享类型统一使用 TS |
| UI 方案 | shadcn/ui + Tailwind CSS | 适合 AI 工具类产品，现代、简洁、暗色主题友好 |
| 状态管理 | Zustand | 轻量，适合管理任务状态、工作区状态、模型配置 |
| 异步请求管理 | TanStack Query | 适合处理任务列表、日志、工具调用结果等异步状态 |
| 代码编辑器 | Monaco Editor | 代码展示、文件预览、Diff 预览 |
| 终端输出 | xterm.js | 展示命令执行 stdout / stderr 输出 |
| Schema 校验 | Zod | 定义工具参数 Schema、模型调用参数、配置校验 |
| 命令执行 | execa | 在 Electron Main Process 中执行本地命令 |
| 代码搜索 | ripgrep | 快速搜索项目代码、关键字、函数名、报错信息 |
| 文件监听 | chokidar | 监听项目目录变更，后续用于文件树刷新 |
| 本地配置 | electron-store | 保存最近项目、模型配置、权限偏好等本地配置 |
| 日志存储 | JSONL / SQLite | 一期用 JSONL，后期可升级 SQLite |
| 打包工具 | electron-builder | 打包 Windows 安装包 / 便携版 |

---

## 4. 为什么选择 Electron + React

### 4.1 选择 Electron 的原因

本项目需要大量本地系统能力，例如：

- 选择本地项目目录；
- 读取项目文件；
- 写入文件；
- 执行 `npm run build`、`pnpm lint` 等命令；
- 读取命令输出；
- 保存本地配置；
- 后续可能嵌入或控制 AI 页面会话。

Electron 天然具备 Chromium + Node.js 能力，适合快速实现桌面端开发工具。对于当前阶段来说，Electron 比 Tauri 更适合快速验证，因为 Electron 可以直接使用 Node.js 生态，不需要额外学习 Rust 后端开发。

### 4.2 选择 React 的原因

WebChat AI Agent 的 UI 不是普通表单页面，而是一个复杂的工作台：

- 左侧项目目录树；
- 中间对话任务流；
- 右侧工具调用详情；
- Diff 预览面板；
- 命令输出面板；
- 模型设置页；
- 权限确认弹窗；
- 任务状态展示。

React 生态在复杂工具型产品中更成熟，Monaco Editor、xterm.js、Dock 面板、虚拟列表、状态管理方案都非常完善。

---

## 5. 前端核心技术栈说明

## 5.1 React

React 负责渲染桌面端应用的主要界面，包括：

- 工作台页面；
- 对话区；
- 项目目录树；
- 工具调用卡片；
- 文件引用区；
- Diff 预览区；
- 命令输出区；
- 设置页。

推荐使用函数组件 + Hooks，不建议使用 class 组件。

---

## 5.2 TypeScript

项目建议全量使用 TypeScript，包括：

- Electron Main Process；
- Electron Preload；
- React Renderer；
- Agent Runtime；
- Tool 工具层；
- Model Adapter；
- Shared 类型定义。

统一使用 TypeScript 的好处：

- 主进程和渲染进程共享类型；
- 工具调用参数可被类型约束；
- Agent 状态流转更清晰；
- 后期扩展工具和模型时更安全。

---

## 5.3 Vite

Vite 用于构建 React 渲染进程，提供快速启动和热更新能力。

推荐使用 Electron + Vite 的工程方案，例如：

```text
electron-vite
```

这样可以同时管理：

- Electron Main Process；
- Preload Script；
- React Renderer Process。

---

## 5.4 shadcn/ui + Tailwind CSS

推荐使用：

```text
shadcn/ui + Tailwind CSS + Radix UI
```

原因：

- 风格更现代，适合 AI 工具产品；
- 暗色主题更容易做；
- 组件可复制到本地项目中，方便二次修改；
- 不会被固定组件库风格限制；
- 适合做类似 Cursor、Claude Code、Trae 一类的工作台界面。

常用组件：

- Button；
- Dialog；
- Sheet；
- Tabs；
- ScrollArea；
- Tooltip；
- DropdownMenu；
- Resizable Panel；
- Card；
- Input；
- Textarea。

如果前期想更快出 Demo，也可以选择 Ant Design。但如果希望产品更有 AI 工具质感，推荐优先使用 shadcn/ui。

---

## 5.5 Zustand

Zustand 用于管理前端全局状态。

建议拆分以下 store：

```text
useWorkspaceStore   当前工作区、项目路径、目录树
useTaskStore        当前任务、任务状态、工具调用记录
useChatStore        对话消息、输入状态、消息流
useModelStore       模型来源、模型配置、API Key 配置状态
useSettingStore     UI 设置、主题、权限偏好
```

Zustand 比 Redux 更轻量，适合个人项目和中小型桌面端工具。

---

## 5.6 TanStack Query

TanStack Query 用于处理异步数据，例如：

- 任务历史；
- 工具调用详情；
- 日志记录；
- 模型配置读取；
- 工作区文件树刷新；
- 命令执行结果查询。

如果一期功能较简单，可以先不用 TanStack Query，直接用 Zustand + IPC 调用即可。等任务历史、日志列表、设置页复杂后再接入。

---

## 5.7 Monaco Editor

Monaco Editor 用于代码类内容展示。

主要应用场景：

- 文件内容预览；
- Diff 预览；
- 修改前后对比；
- 搜索结果代码片段展示；
- 后续支持直接编辑文件。

推荐优先实现：

```text
Monaco Diff Editor
```

用于文件写入前的变更确认。

---

## 5.8 xterm.js

xterm.js 用于展示命令执行输出。

应用场景：

- `npm run build` 输出；
- `pnpm lint` 输出；
- 测试命令输出；
- Git 命令输出；
- Agent 执行工具日志输出。

命令执行实际发生在 Electron Main Process，xterm.js 只负责在 Renderer 中展示输出。

---

## 5.9 Zod

Zod 用于定义工具参数 Schema。

例如：

```ts
import { z } from 'zod'

export const readFileSchema = z.object({
  path: z.string().min(1)
})
```

好处：

- Tool 参数可校验；
- Model 返回的工具调用参数可验证；
- 后期接 OpenAI function calling 或 MCP 时更容易转换；
- 防止模型生成非法参数直接执行。

---

## 6. Electron 架构说明

Electron 项目建议分为三个部分：

```text
Main Process       主进程，负责系统能力和 Agent Runtime
Preload Script     安全桥接层，负责暴露有限 IPC API 给前端
Renderer Process   渲染进程，负责 React UI
```

---

## 6.1 Main Process

Main Process 可以理解为 Electron 应用的 Node.js 后端。

负责：

- 创建窗口；
- 选择目录；
- 读取文件；
- 写入文件；
- 执行命令；
- 管理 Agent Runtime；
- 管理 Tool Registry；
- 管理权限确认；
- 管理模型调用；
- 保存日志和配置。

本项目中，Agent Runtime 建议放在 Main Process 中。

---

## 6.2 Renderer Process

Renderer Process 就是 React 页面。

负责：

- 展示工作台；
- 展示聊天消息；
- 展示工具调用过程；
- 展示文件树；
- 展示 Diff；
- 展示命令输出；
- 触发用户确认；
- 展示最终结果。

Renderer 不应该直接读写本地文件，也不应该直接执行命令。

---

## 6.3 Preload Script

Preload 是 Main 和 Renderer 之间的安全桥。

Renderer 不能直接访问 Node.js API，因此需要通过 Preload 暴露有限能力。

示例：

```ts
import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electronAPI', {
  selectDirectory: () => ipcRenderer.invoke('workspace:select-directory'),
  readFile: (path: string) => ipcRenderer.invoke('tool:read-file', { path }),
  runTask: (input: string) => ipcRenderer.invoke('agent:run-task', { input })
})
```

Renderer 中调用：

```ts
const result = await window.electronAPI.readFile('package.json')
```

---

## 7. Agent Runtime 架构

Agent Runtime 不是第三方库，而是项目内部的 Agent 执行引擎。

它负责把用户自然语言任务转成可执行流程。

### 7.1 Agent Runtime 核心职责

```text
接收用户任务
→ 创建任务状态
→ 组装上下文
→ 调用模型
→ 判断工具调用
→ 执行工具
→ 处理工具结果
→ 再次调用模型
→ 返回最终结果
```

### 7.2 Agent Runtime 模块拆分

| 模块 | 职责 |
| --- | --- |
| AgentRuntime | Agent 总入口，负责任务执行主流程 |
| TaskManager | 创建任务、更新任务状态、取消任务 |
| ContextManager | 管理对话上下文、文件摘要、工具结果 |
| ModelAdapter | 统一模型调用接口 |
| ToolRegistry | 注册和查找工具 |
| ToolExecutor | 执行工具并返回结果 |
| PermissionManager | 判断工具风险等级，触发确认 |
| LogManager | 记录任务日志、工具日志、异常信息 |
| EventBus | 向 Renderer 推送任务状态、工具状态、命令输出 |

---

## 8. Tool 工具层设计

一期建议实现以下工具：

| 工具名 | 功能 | 权限等级 |
| --- | --- | --- |
| list_directory | 读取项目目录结构 | L0 |
| read_file | 读取指定文件 | L0 / L1 |
| search_code | 搜索代码关键字 | L0 |
| generate_diff | 生成文件变更 Diff | L0 |
| apply_patch | 应用文件修改 | L2 |
| run_command | 执行本地命令 | L3 |

### 8.1 Tool 定义示例

```ts
import { z } from 'zod'

export interface ToolDefinition<T = unknown> {
  name: string
  description: string
  permission: 'L0' | 'L1' | 'L2' | 'L3' | 'L4'
  schema: z.ZodSchema<T>
  execute: (args: T, context: ToolContext) => Promise<ToolResult>
}
```

### 8.2 read_file 工具示例

```ts
import { z } from 'zod'
import fs from 'node:fs/promises'
import path from 'node:path'

const schema = z.object({
  path: z.string()
})

export const readFileTool = {
  name: 'read_file',
  description: '读取当前工作区内的指定文件内容',
  permission: 'L0',
  schema,
  async execute(args, context) {
    const targetPath = path.resolve(context.workspaceRoot, args.path)

    if (!targetPath.startsWith(context.workspaceRoot)) {
      throw new Error('禁止读取工作区外的文件')
    }

    const content = await fs.readFile(targetPath, 'utf-8')

    return {
      success: true,
      data: {
        path: args.path,
        content
      }
    }
  }
}
```

---

## 9. 推荐项目目录结构

```text
webchat-ai-agent/
├─ package.json
├─ pnpm-lock.yaml
├─ electron.vite.config.ts
├─ tsconfig.json
├─ tsconfig.node.json
├─ tsconfig.web.json
├─ tailwind.config.ts
├─ postcss.config.js
├─ components.json
├─ README.md
│
├─ build/                              # 打包相关资源
│  ├─ icon.ico
│  ├─ icon.icns
│  └─ installer.nsh
│
├─ resources/                          # 应用资源
│  └─ ripgrep/                         # 可选：内置 rg 可执行文件
│
├─ src/
│  ├─ main/                            # Electron Main Process
│  │  ├─ index.ts                      # 主进程入口
│  │  ├─ window.ts                     # 窗口创建与管理
│  │  ├─ app-lifecycle.ts              # 应用生命周期
│  │  │
│  │  ├─ ipc/                          # IPC 处理器
│  │  │  ├─ index.ts
│  │  │  ├─ workspace.ipc.ts           # 工作区相关 IPC
│  │  │  ├─ agent.ipc.ts               # Agent 任务相关 IPC
│  │  │  ├─ tool.ipc.ts                # 工具调用相关 IPC
│  │  │  ├─ command.ipc.ts             # 命令执行相关 IPC
│  │  │  ├─ model.ipc.ts               # 模型配置相关 IPC
│  │  │  └─ setting.ipc.ts             # 设置相关 IPC
│  │  │
│  │  ├─ agent/                        # Agent Runtime
│  │  │  ├─ agent-runtime.ts           # Agent 执行入口
│  │  │  ├─ task-manager.ts            # 任务管理
│  │  │  ├─ context-manager.ts         # 上下文管理
│  │  │  ├─ tool-executor.ts           # 工具执行器
│  │  │  ├─ agent-events.ts            # Agent 事件定义
│  │  │  └─ prompts.ts                 # 系统提示词和工具提示词
│  │  │
│  │  ├─ model/                        # 模型适配层
│  │  │  ├─ model-adapter.ts           # 统一模型接口
│  │  │  ├─ api-model-adapter.ts       # API Key 模型调用
│  │  │  ├─ web-session-adapter.ts     # AI 页面会话模式
│  │  │  └─ model-config.ts            # 模型配置处理
│  │  │
│  │  ├─ tools/                        # 本地 Tool 工具层
│  │  │  ├─ tool-registry.ts           # 工具注册中心
│  │  │  ├─ tool-types.ts              # 工具类型定义
│  │  │  ├─ list-directory.tool.ts
│  │  │  ├─ read-file.tool.ts
│  │  │  ├─ search-code.tool.ts
│  │  │  ├─ generate-diff.tool.ts
│  │  │  ├─ apply-patch.tool.ts
│  │  │  └─ run-command.tool.ts
│  │  │
│  │  ├─ workspace/                    # 工作区管理
│  │  │  ├─ workspace-manager.ts
│  │  │  ├─ file-indexer.ts
│  │  │  ├─ ignore-rules.ts
│  │  │  └─ path-guard.ts              # 路径越界校验
│  │  │
│  │  ├─ permission/                   # 权限与安全
│  │  │  ├─ permission-manager.ts
│  │  │  ├─ permission-level.ts
│  │  │  ├─ command-risk.ts
│  │  │  └─ sensitive-file.ts
│  │  │
│  │  ├─ command/                      # 命令执行
│  │  │  ├─ command-runner.ts
│  │  │  ├─ command-session.ts
│  │  │  └─ command-output.ts
│  │  │
│  │  ├─ diff/                         # Diff 与 Patch
│  │  │  ├─ diff-manager.ts
│  │  │  ├─ patch-applier.ts
│  │  │  └─ backup-manager.ts
│  │  │
│  │  ├─ store/                        # 本地配置存储
│  │  │  ├─ app-store.ts
│  │  │  ├─ model-store.ts
│  │  │  └─ setting-store.ts
│  │  │
│  │  ├─ log/                          # 日志
│  │  │  ├─ log-manager.ts
│  │  │  ├─ task-log.ts
│  │  │  └─ jsonl-writer.ts
│  │  │
│  │  └─ utils/
│  │     ├─ error.ts
│  │     ├─ uuid.ts
│  │     └─ time.ts
│  │
│  ├─ preload/                         # Electron Preload Script
│  │  ├─ index.ts
│  │  └─ electron-api.ts               # 暴露给 Renderer 的安全 API
│  │
│  ├─ renderer/                        # React Renderer Process
│  │  ├─ index.html
│  │  └─ src/
│  │     ├─ main.tsx                   # React 入口
│  │     ├─ App.tsx
│  │     ├─ router.tsx
│  │     ├─ global.css
│  │     │
│  │     ├─ pages/                     # 页面
│  │     │  ├─ workspace/
│  │     │  │  ├─ WorkspacePage.tsx
│  │     │  │  └─ components/
│  │     │  ├─ settings/
│  │     │  │  └─ SettingsPage.tsx
│  │     │  └─ welcome/
│  │     │     └─ WelcomePage.tsx
│  │     │
│  │     ├─ layouts/                   # 布局
│  │     │  ├─ AppLayout.tsx
│  │     │  ├─ WorkspaceLayout.tsx
│  │     │  └─ PanelLayout.tsx
│  │     │
│  │     ├─ components/                # 通用组件
│  │     │  ├─ ui/                     # shadcn/ui 组件
│  │     │  ├─ chat/
│  │     │  │  ├─ ChatPanel.tsx
│  │     │  │  ├─ MessageList.tsx
│  │     │  │  ├─ MessageItem.tsx
│  │     │  │  ├─ MessageInput.tsx
│  │     │  │  └─ ToolCallCard.tsx
│  │     │  ├─ workspace/
│  │     │  │  ├─ ProjectTree.tsx
│  │     │  │  ├─ FileReferencePanel.tsx
│  │     │  │  └─ WorkspaceSelector.tsx
│  │     │  ├─ diff/
│  │     │  │  ├─ DiffViewer.tsx
│  │     │  │  ├─ DiffFileList.tsx
│  │     │  │  └─ DiffConfirmBar.tsx
│  │     │  ├─ terminal/
│  │     │  │  ├─ CommandOutput.tsx
│  │     │  │  └─ TerminalPanel.tsx
│  │     │  ├─ tool/
│  │     │  │  ├─ ToolCallList.tsx
│  │     │  │  ├─ ToolCallDetail.tsx
│  │     │  │  └─ PermissionDialog.tsx
│  │     │  └─ common/
│  │     │     ├─ EmptyState.tsx
│  │     │     ├─ LoadingState.tsx
│  │     │     └─ ErrorView.tsx
│  │     │
│  │     ├─ stores/                    # Zustand 状态
│  │     │  ├─ useWorkspaceStore.ts
│  │     │  ├─ useTaskStore.ts
│  │     │  ├─ useChatStore.ts
│  │     │  ├─ useModelStore.ts
│  │     │  └─ useSettingStore.ts
│  │     │
│  │     ├─ hooks/                     # React Hooks
│  │     │  ├─ useIpc.ts
│  │     │  ├─ useAgentTask.ts
│  │     │  ├─ useCommandOutput.ts
│  │     │  ├─ useWorkspaceTree.ts
│  │     │  └─ useTheme.ts
│  │     │
│  │     ├─ services/                  # Renderer 侧服务封装
│  │     │  ├─ agent.service.ts
│  │     │  ├─ workspace.service.ts
│  │     │  ├─ model.service.ts
│  │     │  ├─ command.service.ts
│  │     │  └─ setting.service.ts
│  │     │
│  │     ├─ lib/                       # 工具函数
│  │     │  ├─ electron-api.ts
│  │     │  ├─ format.ts
│  │     │  ├─ cn.ts
│  │     │  └─ constants.ts
│  │     │
│  │     └─ types/                     # Renderer 局部类型
│  │        └─ global.d.ts
│  │
│  └─ shared/                          # 主进程和渲染进程共享代码
│     ├─ types/
│     │  ├─ task.ts
│     │  ├─ message.ts
│     │  ├─ tool.ts
│     │  ├─ model.ts
│     │  ├─ workspace.ts
│     │  ├─ command.ts
│     │  └─ permission.ts
│     ├─ schemas/
│     │  ├─ tool.schema.ts
│     │  ├─ model.schema.ts
│     │  └─ task.schema.ts
│     └─ constants/
│        ├─ ipc-channel.ts
│        ├─ task-status.ts
│        └─ permission-level.ts
│
├─ scripts/                            # 开发脚本
│  ├─ dev.ts
│  ├─ build.ts
│  └─ postinstall.ts
│
├─ docs/                               # 项目文档
│  ├─ product.md
│  ├─ architecture.md
│  ├─ tool-protocol.md
│  └─ security.md
│
└─ tests/                              # 测试
   ├─ unit/
   ├─ integration/
   └─ e2e/
```

---

## 10. 核心目录说明

### 10.1 `src/main`

主进程目录。

放置所有和本地系统能力有关的代码：

- 文件读取；
- 文件写入；
- 命令执行；
- Agent Runtime；
- 模型调用；
- 日志存储；
- 权限校验；
- Electron 窗口管理。

原则：

```text
凡是涉及 Node.js、系统权限、本地文件、命令执行的代码，都放在 main。
```

---

### 10.2 `src/preload`

安全桥接层。

用于向 React 前端暴露有限 API。

原则：

```text
Renderer 不直接访问 Node.js，只能通过 preload 暴露的 API 调用主进程能力。
```

---

### 10.3 `src/renderer`

React 前端目录。

负责所有 UI 展示和用户交互。

原则：

```text
Renderer 只负责界面和交互，不直接操作本地文件，不直接执行命令。
```

---

### 10.4 `src/shared`

共享类型和常量。

用于 Main、Preload、Renderer 之间共享：

- Task 类型；
- Tool 类型；
- Message 类型；
- IPC Channel 常量；
- Permission Level；
- Zod Schema。

这样可以避免主进程和渲染进程类型不一致。

---

## 11. IPC 通信设计

### 11.1 IPC Channel 命名规范

推荐使用：

```text
模块名:动作名
```

示例：

```text
workspace:select-directory
workspace:get-tree
agent:run-task
agent:cancel-task
tool:call
command:run
command:stop
model:get-config
model:set-config
setting:get
setting:set
```

---

### 11.2 IPC 调用示例

Renderer：

```ts
const result = await window.electronAPI.workspace.selectDirectory()
```

Preload：

```ts
contextBridge.exposeInMainWorld('electronAPI', {
  workspace: {
    selectDirectory: () => ipcRenderer.invoke('workspace:select-directory')
  }
})
```

Main：

```ts
ipcMain.handle('workspace:select-directory', async () => {
  const result = await dialog.showOpenDialog({
    properties: ['openDirectory']
  })

  if (result.canceled) {
    return null
  }

  return result.filePaths[0]
})
```

---

## 12. 页面结构设计

### 12.1 一期工作台布局

一期推荐使用三栏布局：

```text
┌──────────────────────────────────────────────┐
│ 顶部栏：项目路径 / 模型来源 / 设置入口         │
├───────────────┬────────────────┬─────────────┤
│ 左侧文件树     │ 中间对话区       │ 右侧详情区    │
│ Project Tree  │ Chat Panel      │ Detail Panel│
│               │                 │ Tool / Diff │
├───────────────┴────────────────┴─────────────┤
│ 底部输入框：Message Input                     │
└──────────────────────────────────────────────┘
```

### 12.2 页面模块

| 区域 | 功能 |
| --- | --- |
| 顶部栏 | 展示当前项目、模型来源、设置入口 |
| 左侧栏 | 展示项目目录树和文件引用 |
| 中间区 | 展示用户消息、Agent 回复、工具调用卡片 |
| 右侧栏 | 展示工具调用详情、Diff、命令输出 |
| 底部栏 | 输入任务、发送、停止任务 |

---

## 13. 状态管理设计

### 13.1 任务状态

```ts
export type TaskStatus =
  | 'pending'
  | 'running'
  | 'waiting_confirm'
  | 'tool_running'
  | 'success'
  | 'failed'
  | 'cancelled'
```

### 13.2 useTaskStore 示例

```ts
interface TaskState {
  currentTaskId: string | null
  tasks: Record<string, AgentTask>
  setCurrentTask: (taskId: string) => void
  updateTaskStatus: (taskId: string, status: TaskStatus) => void
  appendToolCall: (taskId: string, toolCall: ToolCallRecord) => void
}
```

### 13.3 useWorkspaceStore 示例

```ts
interface WorkspaceState {
  rootPath: string | null
  fileTree: FileTreeNode[]
  recentProjects: string[]
  setWorkspace: (path: string) => void
  setFileTree: (tree: FileTreeNode[]) => void
}
```

---

## 14. 权限安全设计

### 14.1 权限等级

| 等级 | 类型 | 示例 | 是否确认 |
| --- | --- | --- | --- |
| L0 | 只读低风险 | 读取普通代码文件、读取目录 | 默认不确认 |
| L1 | 只读敏感 | 读取 `.env`、密钥文件 | 需要确认 |
| L2 | 写入风险 | 修改文件、新建文件、删除文件 | 必须确认 |
| L3 | 命令风险 | 执行 build、test、lint | 必须确认 |
| L4 | 高危操作 | 删除目录、系统命令、破坏性 Git 命令 | 默认禁止或强确认 |

### 14.2 路径安全原则

所有文件操作都必须满足：

```text
目标路径必须在 workspaceRoot 内
```

禁止：

```text
../ 越界访问
读取系统目录
写入工作区外文件
读取敏感密钥后完整输出给模型
```

---

## 15. 一期开发顺序

### V0.1 Demo 验证版

目标：跑通最小 Agent 工具调用闭环。

开发顺序：

```text
1. 初始化 Electron + React + TypeScript 项目
2. 创建主窗口
3. 搭建基础工作台 UI
4. 实现选择项目目录
5. 实现 read_file 工具
6. 实现最小 Tool Registry
7. 实现最小 Agent Runtime
8. 接入一个 API Model Adapter
9. 跑通读取 package.json Demo
10. UI 展示工具调用过程和最终回复
```

---

### V0.2 基础可用版

目标：支持代码理解、代码搜索和命令验证。

功能：

```text
1. 项目目录树
2. list_directory 工具
3. search_code 工具
4. run_command 工具
5. 命令执行确认
6. xterm.js 命令输出
7. 任务日志展示
8. 基础异常提示
```

---

### V0.3 修改辅助版

目标：支持代码修改建议和确认写入。

功能：

```text
1. generate_diff 工具
2. Diff 预览
3. apply_patch 工具
4. 文件写入确认
5. 修改摘要
6. 修改后验证命令建议
7. 写入失败处理
```

---

## 16. 推荐安装依赖

### 16.1 核心依赖

```bash
pnpm add react react-dom zustand @tanstack/react-query zod
pnpm add @monaco-editor/react xterm xterm-addon-fit
pnpm add electron-store execa chokidar
```

### 16.2 UI 依赖

```bash
pnpm add tailwindcss postcss autoprefixer
pnpm add class-variance-authority clsx tailwind-merge lucide-react
pnpm add @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-tabs @radix-ui/react-tooltip @radix-ui/react-scroll-area
```

### 16.3 开发依赖

```bash
pnpm add -D electron electron-builder electron-vite vite typescript
pnpm add -D @types/node @types/react @types/react-dom
pnpm add -D eslint prettier
```

---

## 17. 技术选型结论

WebChat AI Agent 当前阶段最推荐的前端和桌面端技术栈是：

```text
Electron + React + Vite + TypeScript + shadcn/ui + Tailwind CSS
```

配套 Agent 和本地能力使用：

```text
Node.js Agent Runtime + Zod + execa + ripgrep + electron-store + electron-builder
```

整体架构建议：

```text
React Renderer 负责 UI
Electron Preload 负责安全 API 暴露
Electron Main 负责系统能力和 Agent Runtime
Tool Registry 负责本地工具调用
Model Adapter 负责统一模型接入
Permission Manager 负责权限确认和风险控制
```

最终目标是先跑通一期最小闭环：

```text
选择项目目录
→ 输入任务
→ Agent 调用模型
→ 模型请求读取文件
→ Tool 读取 package.json
→ 模型总结 scripts
→ UI 展示工具过程和最终结果
```

在这个闭环稳定后，再逐步扩展代码搜索、命令执行、Diff 预览、文件写入、AI 页面会话接入和插件化能力。
