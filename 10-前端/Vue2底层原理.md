# Vue2 底层原理详解

## 一、响应式原理

### 1.1 Object.defineProperty

Vue2 的响应式系统基于 `Object.defineProperty` API 实现。

```javascript
// 简化版的 defineReactive 实现
function defineReactive(obj, key, val) {
  const dep = new Dep() // 依赖收集器
  
  Object.defineProperty(obj, key, {
    enumerable: true,
    configurable: true,
    get() {
      // 依赖收集
      if (Dep.target) {
        dep.depend()
      }
      return val
    },
    set(newVal) {
      if (newVal === val) return
      val = newVal
      // 通知更新
      dep.notify()
    }
  })
}
```

### 1.2 Observer 类

Observer 类用于将普通对象转换为响应式对象。

```javascript
class Observer {
  constructor(value) {
    this.value = value
    this.dep = new Dep()
    
    // 添加 __ob__ 属性，指向 Observer 实例
    Object.defineProperty(value, '__ob__', {
      value: this,
      enumerable: false,
      writable: true,
      configurable: true
    })
    
    if (Array.isArray(value)) {
      // 数组特殊处理
      this.observeArray(value)
    } else {
      // 对象遍历
      this.walk(value)
    }
  }
  
  walk(obj) {
    const keys = Object.keys(obj)
    for (let i = 0; i < keys.length; i++) {
      defineReactive(obj, keys[i], obj[keys[i]])
    }
  }
  
  observeArray(items) {
    for (let i = 0; i < items.length; i++) {
      observe(items[i])
    }
  }
}
```

### 1.3 Dep 类（依赖收集器）

```javascript
class Dep {
  static target = null  // 当前正在收集依赖的 Watcher
  
  constructor() {
    this.subs = []  // 存储所有订阅者（Watcher）
  }
  
  depend() {
    if (Dep.target) {
      this.subs.push(Dep.target)
    }
  }
  
  notify() {
    const subs = this.subs.slice()
    for (let i = 0; i < subs.length; i++) {
      subs[i].update()
    }
  }
}
```

### 1.4 Watcher 类

```javascript
class Watcher {
  constructor(vm, expOrFn, cb) {
    this.vm = vm
    this.getter = parsePath(expOrFn)  // 解析表达式
    this.cb = cb
    this.value = this.get()  // 触发 getter，收集依赖
  }
  
  get() {
    Dep.target = this  // 设置当前 Watcher
    const value = this.getter.call(this.vm, this.vm)
    Dep.target = null  // 重置
    return value
  }
  
  update() {
    const value = this.get()
    if (value !== this.value) {
      const oldValue = this.value
      this.value = value
      this.cb.call(this.vm, value, oldValue)
    }
  }
}
```

---

## 二、数组响应式处理

Vue2 无法直接检测数组的变化，因此对数组方法进行了重写（变异方法）。

### 2.1 重写的数组方法

```javascript
const arrayProto = Array.prototype
const arrayMethods = Object.create(arrayProto)

const methodsToPatch = [
  'push',
  'pop',
  'shift',
  'unshift',
  'splice',
  'sort',
  'reverse'
]

methodsToPatch.forEach(function(method) {
  const original = arrayProto[method]
  
  Object.defineProperty(arrayMethods, method, {
    value: function mutator(...args) {
      const result = original.apply(this, args)
      
      const ob = this.__ob__  // 获取 Observer 实例
      
      // 如果是添加元素的操作，需要对新元素进行响应式处理
      let inserted
      switch (method) {
        case 'push':
        case 'unshift':
          inserted = args
          break
        case 'splice':
          inserted = args.slice(2)
          break
      }
      if (inserted) ob.observeArray(inserted)
      
      // 通知依赖更新
      ob.dep.notify()
      
      return result
    }
  })
})
```

### 2.2 数组响应式的局限性

- **无法检测**：通过索引直接设置项 `arr[index] = newValue`
- **无法检测**：修改数组长度 `arr.length = newLength`
- **解决方案**：使用 `Vue.set()` 或 `this.$set()`

---

## 三、虚拟 DOM

### 3.1 VNode 结构

```javascript
class VNode {
  constructor(
    tag,           // 标签名
    data,          // 属性、class、style 等
    children,      // 子节点
    text,          // 文本内容
    elm,           // 对应的真实 DOM
    context,       // 组件上下文
    componentOptions  // 组件选项
  ) {
    this.tag = tag
    this.data = data
    this.children = children
    this.text = text
    this.elm = elm
    this.context = context
    this.componentOptions = componentOptions
  }
}
```

### 3.2 createElement 函数

```javascript
function createElement(
  context,
  tag,
  data,
  children,
  normalizationType,
  alwaysNormalize
) {
  // 参数规范化处理
  if (Array.isArray(data) || isPrimitive(data)) {
    children = data
    data = undefined
  }
  
  // 创建 VNode
  if (typeof tag === 'string') {
    // 普通标签
    return new VNode(tag, data, children, undefined, undefined, context)
  } else {
    // 组件
    return createComponent(tag, data, context, children)
  }
}
```

---

## 四、Diff 算法（patch）

### 4.1 patch 函数

```javascript
function patch(oldVnode, vnode) {
  // 如果 oldVnode 是真实 DOM，先转换为 VNode
  if (isRealElement(oldVnode)) {
    oldVnode = emptyNodeAt(oldVnode)
  }
  
  const elm = vnode.elm = oldVnode.elm
  
  // 如果是同一个 VNode，进行 diff
  if (sameVnode(oldVnode, vnode)) {
    patchVnode(oldVnode, vnode)
  } else {
    // 不同则直接替换
    const parent = elm.parentNode
    const newElm = createElm(vnode)
    parent.insertBefore(newElm, elm)
    parent.removeChild(elm)
  }
  
  return vnode
}

// 判断是否为同一个 VNode
function sameVnode(a, b) {
  return (
    a.key === b.key &&
    a.tag === b.tag &&
    a.isComment === b.isComment &&
    isDef(a.data) === isDef(b.data)
  )
}
```

### 4.2 patchVnode（更新节点）

```javascript
function patchVnode(oldVnode, vnode) {
  const elm = vnode.elm = oldVnode.elm
  const oldCh = oldVnode.children
  const ch = vnode.children
  
  // 更新属性
  if (isDef(vnode.data)) {
    updateAttrs(oldVnode, vnode)
    updateClass(oldVnode, vnode)
    updateEvents(oldVnode, vnode)
    // ... 其他属性更新
  }
  
  // 文本节点处理
  if (isUndef(ch) && isDef(oldCh)) {
    elm.textContent = ''
  } else if (isDef(ch) && isUndef(oldCh)) {
    // 新增子节点
    for (let i = 0; i < ch.length; i++) {
      elm.appendChild(createElm(ch[i]))
    }
  } else if (isDef(ch) && isDef(oldCh)) {
    // 都有子节点，进行 diff
    updateChildren(elm, oldCh, ch)
  }
}
```

### 4.3 updateChildren（核心 Diff）

```javascript
function updateChildren(parentElm, oldCh, newCh) {
  let oldStartIdx = 0
  let newStartIdx = 0
  let oldEndIdx = oldCh.length - 1
  let newEndIdx = newCh.length - 1
  
  let oldStartVnode = oldCh[oldStartIdx]
  let oldEndVnode = oldCh[oldEndIdx]
  let newStartVnode = newCh[newStartIdx]
  let newEndVnode = newCh[newEndIdx]
  
  let oldKeyToIdx, idxInOld, elmToMove, refElm
  
  while (oldStartIdx <= oldEndIdx && newStartIdx <= newEndIdx) {
    if (isUndef(oldStartVnode)) {
      oldStartVnode = oldCh[++oldStartIdx]
    } else if (isUndef(oldEndVnode)) {
      oldEndVnode = oldCh[--oldEndIdx]
    } else if (sameVnode(oldStartVnode, newStartVnode)) {
      // 新旧头头对比
      patchVnode(oldStartVnode, newStartVnode)
      oldStartVnode = oldCh[++oldStartIdx]
      newStartVnode = newCh[++newStartIdx]
    } else if (sameVnode(oldEndVnode, newEndVnode)) {
      // 新旧尾尾对比
      patchVnode(oldEndVnode, newEndVnode)
      oldEndVnode = oldCh[--oldEndIdx]
      newEndVnode = newCh[--newEndIdx]
    } else if (sameVnode(oldStartVnode, newEndVnode)) {
      // 旧头新尾对比
      patchVnode(oldStartVnode, newEndVnode)
      parentElm.insertBefore(oldStartVnode.elm, oldEndVnode.elm.nextSibling)
      oldStartVnode = oldCh[++oldStartIdx]
      newEndVnode = newCh[--newEndIdx]
    } else if (sameVnode(oldEndVnode, newStartVnode)) {
      // 旧尾新头对比
      patchVnode(oldEndVnode, newStartVnode)
      parentElm.insertBefore(oldEndVnode.elm, oldStartVnode.elm)
      oldEndVnode = oldCh[--oldEndIdx]
      newStartVnode = newCh[++newStartIdx]
    } else {
      // 使用 key 进行匹配
      if (isUndef(oldKeyToIdx)) {
        oldKeyToIdx = createKeyToOldIdx(oldCh, oldStartIdx, oldEndIdx)
      }
      idxInOld = isDef(newStartVnode.key)
        ? oldKeyToIdx[newStartVnode.key]
        : findIdxInOld(newStartVnode, oldCh, oldStartIdx, oldEndIdx)
      
      if (isUndef(idxInOld)) {
        // 新元素
        createElm(newStartVnode, parentElm, oldStartVnode.elm)
      } else {
        elmToMove = oldCh[idxInOld]
        if (sameVnode(elmToMove, newStartVnode)) {
          patchVnode(elmToMove, newStartVnode)
          oldCh[idxInOld] = undefined
          parentElm.insertBefore(elmToMove.elm, oldStartVnode.elm)
        }
      }
      newStartVnode = newCh[++newStartIdx]
    }
  }
  
  // 处理剩余节点
  if (oldStartIdx > oldEndIdx) {
    refElm = isUndef(newCh[newEndIdx + 1]) ? null : newCh[newEndIdx + 1].elm
    addVnodes(parentElm, refElm, newCh, newStartIdx, newEndIdx)
  } else if (newStartIdx > newEndIdx) {
    removeVnodes(oldCh, oldStartIdx, oldEndIdx)
  }
}
```

---

## 五、模板编译

### 5.1 编译流程

```
模板字符串 → parse() → AST → optimize() → 优化后的 AST → generate() → render 函数
```

### 5.2 parse（解析器）

将模板字符串解析为 AST（抽象语法树）。

```javascript
function parse(template, options) {
  const stack = []
  let root
  let currentParent
  
  parseHTML(template, {
    start(tag, attrs, unary) {
      // 创建 AST 元素节点
      const element = createASTElement(tag, attrs, currentParent)
      
      if (!root) {
        root = element
      }
      
      if (!unary) {
        currentParent = element
        stack.push(element)
      }
    },
    end() {
      // 闭合标签
      const element = stack.pop()
      currentParent = stack[stack.length - 1] || null
      closeElement(element)
    },
    chars(text) {
      // 文本节点
      if (currentParent) {
        const child = {
          type: 3,
          text,
          parent: currentParent
        }
        currentParent.children.push(child)
      }
    }
  })
  
  return root
}
```

### 5.3 optimize（优化器）

标记静态节点，提升静态子树。

```javascript
function optimize(root, options) {
  if (!root) return
  
  // 标记静态节点
  markStatic(root)
  
  // 标记静态根节点
  markStaticRoots(root, false)
}

function markStatic(node) {
  node.static = isStatic(node)
  
  if (node.children) {
    for (let i = 0; i < node.children.length; i++) {
      const child = node.children[i]
      markStatic(child)
      if (!child.static) {
        node.static = false
      }
    }
  }
}
```

### 5.4 generate（代码生成器）

```javascript
function generate(ast, options) {
  const state = new CodegenState(options)
  const code = ast ? genElement(ast, state) : '_c("div")'
  
  return {
    render: `with(this){return ${code}}`,
    staticRenderFns: state.staticRenderFns
  }
}

function genElement(el, state) {
  if (el.staticRoot && !el.staticProcessed) {
    return genStatic(el, state)
  }
  if (el.once && !el.onceProcessed) {
    return genOnce(el, state)
  }
  if (el.for && !el.forProcessed) {
    return genFor(el, state)
  }
  if (el.if && !el.ifProcessed) {
    return genIf(el, state)
  }
  // ... 其他指令处理
  
  let code
  if (el.component) {
    code = genComponent(el.component, el, state)
  } else {
    const data = genData(el, state)
    const children = genChildren(el, state, true)
    code = `_c('${el.tag}'${data ? `,${data}` : ''}${children ? `,${children}` : ''})`
  }
  
  return code
}
```

---

## 六、组件化

### 6.1 组件创建流程

```javascript
function createComponent(
  Ctor,
  data,
  context,
  children,
  tag
) {
  if (isUndef(Ctor)) {
    return
  }
  
  const baseCtor = context.$options._base  // Vue 构造函数
  
  // 如果是对象选项，使用 Vue.extend
  if (isObject(Ctor)) {
    Ctor = baseCtor.extend(Ctor)
  }
  
  // 异步组件处理
  if (isTrue(Ctor.options.async)) {
    return resolveAsyncComponent(Ctor, data, context)
  }
  
  data = data || {}
  
  // 处理 props
  const propsData = extractProps(data, Ctor)
  
  // 处理 listeners
  const listeners = data.on
  data.on = data.nativeOn
  
  // 创建组件 VNode
  const vnode = new VNode(
    `vue-component-${Ctor.cid}${tag ? `-${tag}` : ''}`,
    data,
    undefined,
    undefined,
    undefined,
    context,
    { Ctor, propsData, listeners, tag, children },
    undefined
  )
  
  return vnode
}
```

### 6.2 Vue.extend

```javascript
Vue.extend = function(extendOptions) {
  extendOptions = extendOptions || {}
  const Super = this
  const SuperId = Super.cid
  
  const cachedCtors = extendOptions._Ctor || (extendOptions._Ctor = {})
  if (cachedCtors[SuperId]) {
    return cachedCtors[SuperId]
  }
  
  const name = extendOptions.name || Super.options.name
  
  // 定义子类构造函数
  const Sub = function VueComponent(options) {
    this._init(options)
  }
  
  // 原型继承
  Sub.prototype = Object.create(Super.prototype)
  Sub.prototype.constructor = Sub
  Sub.cid = cid++
  
  // 合并选项
  Sub.options = mergeOptions(Super.options, extendOptions)
  
  // 保留父类引用
  Sub['super'] = Super
  
  // 初始化 props
  if (Sub.options.props) {
    initProps(Sub)
  }
  
  // 初始化 computed
  if (Sub.options.computed) {
    initComputed(Sub)
  }
  
  // 继承 Vue 的方法
  Sub.extend = Super.extend
  Sub.mixin = Super.mixin
  Sub.use = Super.use
  
  // 缓存
  cachedCtors[SuperId] = Sub
  
  return Sub
}
```

### 6.3 组件生命周期

```
new Vue() / new Component()
    ↓
_init() (beforeCreate)
    ↓
initProps(), initMethods(), initData(), initComputed(), initWatch()
    ↓
created
    ↓
$mount() / render()
    ↓
beforeMount
    ↓
创建 VNode → patch → 创建真实 DOM
    ↓
mounted
    ↓
数据变化
    ↓
beforeUpdate
    ↓
重新渲染 → patch
    ↓
updated
    ↓
$destroy()
    ↓
beforeDestroy
    ↓
清理依赖、解绑事件、移除 DOM
    ↓
destroyed
```

---

## 七、nextTick 原理

Vue2 使用异步更新策略，通过 nextTick 批量更新 DOM。

```javascript
const callbacks = []
let pending = false

function nextTick(cb, ctx) {
  callbacks.push(() => {
    if (cb) {
      try {
        cb.call(ctx)
      } catch (e) {
        handleError(e, ctx, 'nextTick')
      }
    }
  })
  
  if (!pending) {
    pending = true
    timerFunc()
  }
}

// 选择异步实现方式
let timerFunc

// 优先使用 Promise
if (typeof Promise !== 'undefined') {
  timerFunc = () => {
    Promise.resolve().then(flushCallbacks)
  }
}
// 其次使用 MutationObserver
else if (typeof MutationObserver !== 'undefined') {
  let counter = 1
  const observer = new MutationObserver(flushCallbacks)
  const textNode = document.createTextNode(String(counter))
  observer.observe(textNode, { characterData: true })
  timerFunc = () => {
    counter = (counter + 1) % 2
    textNode.data = String(counter)
  }
}
// 再次使用 setImmediate
else if (typeof setImmediate !== 'undefined') {
  timerFunc = () => {
    setImmediate(flushCallbacks)
  }
}
// 最后使用 setTimeout
else {
  timerFunc = () => {
    setTimeout(flushCallbacks, 0)
  }
}

function flushCallbacks() {
  pending = false
  const copies = callbacks.slice(0)
  callbacks.length = 0
  for (let i = 0; i < copies.length; i++) {
    copies[i]()
  }
}
```

---

## 八、Vue2 的局限性

### 8.1 响应式局限

| 局限 | 示例 | 解决方案 |
|------|------|----------|
| 对象属性新增 | `obj.newProp = value` | `Vue.set(obj, 'newProp', value)` |
| 对象属性删除 | `delete obj.prop` | `Vue.delete(obj, 'prop')` |
| 数组索引修改 | `arr[0] = value` | `Vue.set(arr, 0, value)` |
| 数组长度修改 | `arr.length = 0` | `arr.splice(0)` |

### 8.2 性能问题

- **递归响应式**：初始化时递归遍历所有属性，大对象性能差
- **无法检测 Map/Set**：不支持 Map、Set 等数据结构
- **重复依赖收集**：每次 getter 都需要收集依赖

---

## 九、总结

Vue2 的核心原理可以概括为：

1. **响应式系统**：基于 `Object.defineProperty` 实现数据劫持
2. **依赖收集**：通过 Dep 和 Watcher 建立数据与视图的映射关系
3. **虚拟 DOM**：通过 VNode 抽象真实 DOM，实现跨平台
4. **Diff 算法**：双端比较算法，最小化 DOM 操作
5. **模板编译**：将模板编译为 render 函数
6. **组件化**：通过 Vue.extend 创建子类，实现组件复用
7. **异步更新**：通过 nextTick 批量更新，提升性能

这些原理共同构成了 Vue2 的高效响应式更新机制。
