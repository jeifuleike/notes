# TypeScript Agent 开源项目阅读代办清单

> 目标：先从小而清晰的 TypeScript Agent 项目入手，理解 Agent 的核心执行流，再逐步阅读完整框架和产品级项目。  
> 建议顺序：先看最小 Agent → 再看 Tool Calling / Workflow / Memory → 再看浏览器 Agent / 前端 Agent UI → 最后回头看 OpenClaw。

---

## 第一阶段：理解 Agent 最小执行逻辑

### 1. agents-from-scratch-ts

- [ ] 打开项目仓库，先看 README，理解项目目标
- [ ] 找到主入口文件，理清一次用户输入如何进入 Agent
- [ ] 理解 State / Graph / Node 的关系
- [ ] 看 LLM 是如何决定下一步动作的
- [ ] 看 Tool 是如何定义、注册、调用的
- [ ] 看 Human-in-the-loop 是怎么插入流程的
- [ ] 画一张流程图：用户输入 → 状态更新 → 节点执行 → 工具调用 → 输出结果

**重点理解：**

```text
用户输入
  ↓
状态 State
  ↓
Graph 节点
  ↓
LLM 判断
  ↓
调用 Tool
  ↓
更新 State
  ↓
返回结果 / 等待人工确认
```

**阅读目标：** 搞懂 Agent 不是单纯调用一次大模型，而是“状态 + 工具 + 流程控制”。

---

### 2. run-llama/ts-agents

- [ ] 看最简单的 Agent 示例
- [ ] 理解 Agent 如何调用工具
- [ ] 理解工具调用结果如何回传给模型
- [ ] 看项目如何逐步增加复杂度
- [ ] 找出 RAG 和 Agent 结合的示例
- [ ] 对比它和 agents-from-scratch-ts 的不同

**重点理解：**

```text
最小 Agent
  ↓
Tool Calling
  ↓
RAG 检索
  ↓
多轮任务
  ↓
更复杂的 Agent 行为
```

**阅读目标：** 搞懂一个 TypeScript Agent 的最小实现方式。

---

## 第二阶段：学习前端 AI 应用和工具调用

### 3. Vercel AI SDK

- [ ] 看官方 examples 中的 chat 示例
- [ ] 理解 streamText / generateText 的用法
- [ ] 理解 Tool Calling 的声明方式
- [ ] 看前端如何接收流式输出
- [ ] 看服务端接口如何调用模型
- [ ] 尝试跑一个最小聊天 Demo
- [ ] 尝试加一个简单工具，例如获取当前时间、读取本地 mock 数据

**重点理解：**

```text
前端输入
  ↓
API Route / Server Action
  ↓
AI SDK 调用模型
  ↓
模型选择是否调用工具
  ↓
流式返回给前端
```

**阅读目标：** 学会怎么把 Agent 能力接进真实前端产品。

---

## 第三阶段：学习完整 TypeScript Agent 框架

### 4. Mastra

- [ ] 看 Mastra 的 Agent 基础示例
- [ ] 理解 Agent / Tool / Workflow / Memory 的划分
- [ ] 看 workflow 是如何串联多个步骤的
- [ ] 看 memory 是如何保存和读取上下文的
- [ ] 看 RAG 示例，理解知识库接入方式
- [ ] 看部署和 observability 相关内容

**重点理解：**

```text
Agent：负责思考和决策
Tool：负责执行具体能力
Workflow：负责固定流程编排
Memory：负责长期记忆
RAG：负责查资料
Observability：负责查看运行过程
```

**阅读目标：** 理解一个完整 TS Agent 框架应该包含哪些模块。

---

### 5. LangGraphJS

- [ ] 阅读 LangGraphJS 的基础图示例
- [ ] 理解 StateGraph 的概念
- [ ] 理解节点 Node 如何读写状态
- [ ] 理解条件边 Conditional Edge 如何控制流程
- [ ] 看循环、失败重试、人工介入相关示例
- [ ] 对比它和 Dify 工作流节点的相似点

**重点理解：**

```text
State
  ↓
Node A
  ↓
条件判断
  ↓
Node B / Node C
  ↓
结束或循环
```

**阅读目标：** 搞懂复杂 Agent 为什么常用“状态机 / 图”来编排。

---

## 第四阶段：学习浏览器 Agent 和 Agentic UI

### 6. Stagehand

- [ ] 看 Stagehand 的基础示例
- [ ] 理解它和 Playwright 的关系
- [ ] 看自然语言如何转换成网页操作
- [ ] 看 extract / act / observe 的使用方式
- [ ] 尝试写一个网页自动化小例子：打开网页 → 提取标题 → 点击按钮
- [ ] 思考它和 Manus 浏览器操作能力的关系

**重点理解：**

```text
自然语言任务
  ↓
浏览器环境
  ↓
观察网页元素
  ↓
执行点击 / 输入 / 提取
  ↓
返回结构化结果
```

**阅读目标：** 学会 AI 如何操作网页，为以后做浏览器 Agent 打基础。

---

### 7. CopilotKit

- [ ] 看 CopilotKit 的 React 示例
- [ ] 理解 Copilot 侧边栏如何接入应用
- [ ] 看 Agent 如何读取前端应用状态
- [ ] 看 Agent 如何修改前端状态
- [ ] 理解 Human-in-the-loop 和 Generative UI
- [ ] 思考如何接入自己的 AI 笔记/工作区项目

**重点理解：**

```text
前端应用状态
  ↓
Copilot 读取上下文
  ↓
Agent 生成操作建议
  ↓
用户确认
  ↓
修改页面状态 / 生成内容
```

**阅读目标：** 学会 Agent 怎么真正嵌入产品 UI，而不是只停留在命令行。

---

## 第五阶段：回头阅读 OpenClaw

### 8. OpenClaw

- [ ] 先不要从全局硬啃，按模块拆开看
- [ ] 找到 Agent 执行层入口
- [ ] 找到 Tool 注册和调用逻辑
- [ ] 找到 Gateway / Runtime / Channel 的边界
- [ ] 找到权限、安全、沙箱相关逻辑
- [ ] 找到前端和后端进程通信方式
- [ ] 对照前面学过的 Agent 核心概念重新理解 OpenClaw

**重点区分：**

```text
Agent 核心逻辑
桌面端工程复杂度
本地进程通信
工具系统
安全隔离
权限管理
产品 UI
```

**阅读目标：** 看懂 OpenClaw 复杂在哪里，哪些是 Agent 核心，哪些只是产品工程复杂度。

---

## 推荐阅读顺序总表

| 顺序 | 项目 | 重点 | 难度 |
|---:|---|---|---|
| 1 | agents-from-scratch-ts | Agent 执行流、状态图、工具调用 | 低-中 |
| 2 | run-llama/ts-agents | 最小 Agent、Tool、RAG | 低-中 |
| 3 | Vercel AI SDK | 前端 AI 应用、流式输出、Tool Calling | 中 |
| 4 | Mastra | TS Agent 框架、Workflow、Memory | 中 |
| 5 | LangGraphJS | 状态机、图编排、复杂 Agent 流程 | 中-高 |
| 6 | Stagehand | 浏览器 Agent、网页自动化 | 中 |
| 7 | CopilotKit | Agentic UI、前端产品集成 | 中 |
| 8 | OpenClaw | 产品级 Agent 系统、桌面端工程 | 高 |

---

## 每个项目阅读时都要回答的问题

- [ ] 这个项目的 Agent 输入是什么？
- [ ] Agent 的状态保存在哪里？
- [ ] 工具 Tool 是怎么定义的？
- [ ] LLM 是怎么决定调用工具的？
- [ ] 工具调用失败怎么处理？
- [ ] 多轮上下文怎么传递？
- [ ] 是否有长期记忆 Memory？
- [ ] 是否有固定 Workflow？
- [ ] 是否支持 Human-in-the-loop？
- [ ] 最终输出是文本、代码、文件，还是 UI 操作？

---

## 最小学习目标

- [ ] 能自己写一个最小 TypeScript Agent
- [ ] 能注册 2-3 个工具给 Agent 调用
- [ ] 能让 Agent 根据用户问题选择工具
- [ ] 能把工具结果回传给模型生成最终回答
- [ ] 能给 Agent 加一个简单 Memory
- [ ] 能用前端页面和 Agent 交互
- [ ] 能理解 OpenClaw 中 Agent、Tool、Runtime、Gateway 的边界

---

## 自己动手练习项目

### 练习 1：最小工具调用 Agent

- [ ] 用户输入问题
- [ ] Agent 判断是否需要调用工具
- [ ] 工具返回结果
- [ ] Agent 总结回答

可选工具：

```text
getCurrentTime
calculator
searchMockDocs
readLocalNote
```

---

### 练习 2：AI 笔记助手 Agent

- [ ] 支持读取 Markdown 笔记
- [ ] 支持总结笔记
- [ ] 支持润色选中文本
- [ ] 支持生成修改建议
- [ ] 支持输出 diff
- [ ] 支持记录用户偏好

---

### 练习 3：产品需求 Agent

- [ ] 用户输入需求
- [ ] Agent 判断信息是否完整
- [ ] 信息不完整时只提补充问题
- [ ] 信息完整时生成简易初稿
- [ ] 用户确认后生成详细需求文档
- [ ] 支持用户明确要求时输出多个方案

---

## 备注

不要一开始就追求完整产品。先把下面这条链路跑通：

```text
用户输入
  ↓
Agent 判断
  ↓
Tool 调用
  ↓
状态更新
  ↓
最终回答
```

等这个链路理解清楚，再研究 Memory、Workflow、浏览器自动化、Agentic UI 和 OpenClaw 这种复杂系统。
