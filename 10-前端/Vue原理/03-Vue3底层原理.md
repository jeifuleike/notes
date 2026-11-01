# Vue3 底层原理详解

## 一、响应式系统

### 1.1 Proxy 代理

Vue3 使用 ES6 的 Proxy 替代 Object.defineProperty 实现响应式。

```javascript
function reactive(target) {
  // 如果已经是响应式对象，直接返回
  if (target && target.__v_isReactive) {
    return target
  }
  
  return new Proxy(target, mutableHandlers)
}

const mutableHandlers = {
  get(target, key, receiver) {
    // 标记为响应式
    if (key === '__v_isReactive') {
      return true
    }
    
    // 依赖收集
    track(target, key)
    
    const result = Reflect.get(target, key, receiver)
    
    // 如果是对象，递归转换为响应式
    if (isObject(result)) {
      return reactive(result)
    }
    
    return result
  },
  
  set(target, key, value, receiver) {
    const oldValue = target[key]
    
    // 判断是否是新属性
    const hadKey = Array.isArray(target)
      ? Number(key) < target.length
      : hasOwn(target, key)
    
    const result = Reflect.set(target, key, value, receiver)
    
    // 触发更新
    if (!hadKey) {
      // 新增属性
      trigger(target, TriggerOpTypes.ADD, key, value)
    } else if (hasChanged(value, oldValue)) {
      // 修改属性
      trigger(target, TriggerOpTypes.SET, key, value, oldValue)
    }
    
    return result
  },
  
  deleteProperty(target, key) {
    const hadKey = hasOwn(target, key)
    const result = Reflect.deleteProperty(target, key)
    
    if (result && hadKey) {
      trigger(target, TriggerOpTypes.DELETE, key)
    }
    
    return result
  },
  
  has(target, key) {
    track(target, key)
    return Reflect.has(target, key)
  },
  
  ownKeys(target) {
    track(target, TrackOpTypes.ITERATE)
    return Reflect.ownKeys(target)
  }
}
```

### 1.2 Proxy 的优势

| 特性 | Object.defineProperty | Proxy |
|------|----------------------|-------|
| 监听新增属性 | ❌ 需要手动调用 Vue.set | ✅ 自动监听 |
| 监听删除属性 | ❌ 需要手动调用 Vue.delete | ✅ 自动监听 |
| 监听数组索引 | ❌ 需要特殊处理 | ✅ 自动监听 |
| 监听数组长度 | ❌ 无法监听 | ✅ 自动监听 |
| 监听 Map/Set | ❌ 不支持 | ✅ 支持 |
| 性能 | 初始化时递归遍历 | 惰性代理，按需转换 |

---

## 二、依赖收集与触发

### 2.1 effect（副作用函数）

```javascript
let activeEffect = null
const effectStack = []

function effect(fn, options = {}) {
  const _effect = function reactiveEffect() {
    if (!effectStack.includes(_effect)) {
      cleanup(_effect)
      
      try {
        enableTracking()
        effectStack.push(_effect)
        activeEffect = _effect
        return fn()
      } finally {
        effectStack.pop()
        activeEffect = effectStack[effectStack.length - 1]
        if (options.scheduler) {
          resetTracking()
        }
      }
    }
  }
  
  _effect.deps = []
  _effect.options = options
  
  if (!options.lazy) {
    _effect()
  }
  
  return _effect
}
```

### 2.2 track（依赖收集）

```javascript
const targetMap = new WeakMap()

function track(target, key) {
  if (!shouldTrack || activeEffect === undefined) {
    return
  }
  
  let depsMap = targetMap.get(target)
  if (!depsMap) {
    targetMap.set(target, (depsMap = new Map()))
  }
  
  let dep = depsMap.get(key)
  if (!dep) {
    depsMap.set(key, (dep = new Set()))
  }
  
  if (!dep.has(activeEffect)) {
    dep.add(activeEffect)
    activeEffect.deps.push(dep)
  }
}
```

### 2.3 trigger（触发更新）

```javascript
function trigger(target, type, key, newValue, oldValue) {
  const depsMap = targetMap.get(target)
  if (!depsMap) return
  
  const effects = new Set()
  
  // 收集需要执行的 effect
  const add = (effectsToAdd) => {
    if (effectsToAdd) {
      effectsToAdd.forEach(effect => {
        if (effect !== activeEffect) {
          effects.add(effect)
        }
      })
    }
  }
  
  // 属性修改
  if (key !== undefined) {
    add(depsMap.get(key))
  }
  
  // 数组长度变化
  if (type === TriggerOpTypes.ADD && Array.isArray(target)) {
    add(depsMap.get('length'))
  }
  
  // 迭代相关（for...in, Object.keys 等）
  if (type === TriggerOpTypes.ADD || type === TriggerOpTypes.DELETE) {
    add(depsMap.get(ITERATE_KEY))
  }
  
  // 执行 effect
  effects.forEach(effect => {
    if (effect.options.scheduler) {
      effect.options.scheduler(effect)
    } else {
      effect()
    }
  })
}
```

---

## 三、ref 与 shallowReactive

### 3.1 ref

ref 用于包装基本类型值，使其具有响应性。

```javascript
function ref(value) {
  return createRef(value, false)
}

function createRef(rawValue, shallow) {
  if (isRef(rawValue)) {
    return rawValue
  }
  
  return new RefImpl(rawValue, shallow)
}

class RefImpl {
  constructor(value, _shallow) {
    this._shallow = _shallow
    this.__v_isRef = true
    this._rawValue = _shallow ? value : toRaw(value)
    this._value = _shallow ? value : convert(value)
  }
  
  get value() {
    track(toRaw(this), 'value')
    return this._value
  }
  
  set value(newVal) {
    newVal = this._shallow ? newVal : toRaw(newVal)
    if (hasChanged(newVal, this._rawValue)) {
      this._rawValue = newVal
      this._value = this._shallow ? newVal : convert(newVal)
      trigger(toRaw(this), TriggerOpTypes.SET, 'value', newVal)
    }
  }
}
```

### 3.2 shallowReactive

浅层响应式，只代理第一层属性。

```javascript
function shallowReactive(target) {
  return createReactiveObject(
    target,
    false,
    shallowReactiveHandlers,
    shallowCollectionHandlers
  )
}

const shallowReactiveHandlers = extend({}, mutableHandlers, {
  get: shallowGet,
  set: shallowSet
})

function shallowGet(target, key, receiver) {
  track(target, key)
  return Reflect.get(target, key, receiver)
  // 不再递归转换
}
```

---

## 四、computed 计算属性

### 4.1 computed 实现

```javascript
function computed(getterOrOptions) {
  let getter, setter
  
  if (isFunction(getterOrOptions)) {
    getter = getterOrOptions
    setter = () => {}
  } else {
    getter = getterOrOptions.get
    setter = getterOrOptions.set
  }
  
  return new ComputedRefImpl(getter, setter)
}

class ComputedRefImpl {
  constructor(getter, setter) {
    this._setter = setter
    this.__v_isRef = true
    this._dirty = true  // 是否需要重新计算
    
    // 创建 effect，使用 scheduler 实现懒计算
    this.effect = effect(getter, {
      lazy: true,
      scheduler: () => {
        if (!this._dirty) {
          this._dirty = true
          trigger(this, TriggerOpTypes.SET, 'value')
        }
      }
    })
  }
  
  get value() {
    if (this._dirty) {
      this._value = this.effect()
      this._dirty = false
    }
    track(this, 'value')
    return this._value
  }
  
  set value(newValue) {
    this._setter(newValue)
  }
}
```

### 4.2 computed 特点

- **懒计算**：只有在访问 value 时才计算
- **缓存**：依赖不变时返回缓存值
- **自动追踪**：自动收集依赖，依赖变化时标记 dirty

---

## 五、watch 监听器

### 5.1 watch 实现

```javascript
function watch(source, cb, options = {}) {
  return doWatch(source, cb, options)
}

function doWatch(source, cb, { immediate, deep, flush } = {}) {
  let getter
  let isMultiSource = false
  
  // 处理不同类型的 source
  if (isRef(source)) {
    getter = () => source.value
  } else if (isReactive(source)) {
    getter = () => source
    deep = true
  } else if (isArray(source)) {
    isMultiSource = true
    getter = () => source.map(s => {
      if (isRef(s)) return s.value
      if (isReactive(s)) return traverse(s)
      return s
    })
  } else if (isFunction(source)) {
    getter = source
  }
  
  // 深度监听
  if (deep) {
    const baseGetter = getter
    getter = () => traverse(baseGetter())
  }
  
  let oldValue = isMultiSource ? [] : undefined
  
  // 定义 scheduler
  const job = () => {
    const newValue = runner()
    if (deep || hasChanged(newValue, oldValue)) {
      cb(newValue, oldValue)
      oldValue = newValue
    }
  }
  
  let scheduler
  if (flush === 'sync') {
    scheduler = job
  } else if (flush === 'post') {
    scheduler = () => Promise.resolve().then(job)
  } else {
    scheduler = () => queueJob(job)
  }
  
  // 创建 effect
  const runner = effect(getter, {
    scheduler,
    onTrack: options.onTrack,
    onTrigger: options.onTrigger
  })
  
  // 立即执行
  if (immediate) {
    job()
  } else {
    oldValue = runner()
  }
  
  // 返回停止函数
  return () => {
    stop(runner)
  }
}
```

### 5.2 watchEffect

```javascript
function watchEffect(effect, options = {}) {
  return doWatch(effect, null, options)
}
```

---

## 六、虚拟 DOM 与 Diff 算法

### 6.1 VNode 结构

```typescript
interface VNode {
  __v_isVNode: true
  type: string | Component | typeof Text | typeof Comment
  props: VNodeProps | null
  key: string | number | null
  children: VNodeChildren
  component: ComponentInternalInstance | null
  shapeFlag: number  // 节点类型标识
  patchFlag: number  // 更新标识（优化）
  dynamicProps: string[] | null  // 动态属性
  dirs: DirectiveBinding[] | null  // 指令
  // ...
}
```

### 6.2 PatchFlags（静态标记）

Vue3 通过 PatchFlags 标记动态内容，实现靶向更新。

```typescript
export const enum PatchFlags {
  TEXT = 1,           // 动态文本内容
  CLASS = 2,          // 动态 class
  STYLE = 4,          // 动态 style
  PROPS = 8,          // 动态属性（非 class/style）
  FULL_PROPS = 16,    // 有动态 key 的属性
  HYDRATE_EVENTS = 32, // 有需要水合的事件
  STABLE_FRAGMENT = 64, // 稳定的 fragment
  KEYED_FRAGMENT = 128, // 有 key 的 fragment
  UNKEYED_FRAGMENT = 256, // 无 key 的 fragment
  NEED_PATCH = 512,  // 需要 patch（ref 或指令）
  DYNAMIC_SLOTS = 1024, // 动态插槽
  HOISTED = -1,       // 静态提升的节点
  BAIL = -2           // 退出优化模式
}
```

### 6.3 Diff 算法（最长递增子序列）

Vue3 使用最长递增子序列（LIS）算法优化列表 Diff。

```javascript
function patchKeyedChildren(
  c1,
  c2,
  container,
  parentAnchor,
  parentComponent,
  parentSuspense,
  isSVG,
  optimized
) {
  let i = 0
  const l2 = c2.length
  let e1 = c1.length - 1
  let e2 = l2 - 1
  
  // 1. 从头部开始同步
  while (i <= e1 && i <= e2) {
    const n1 = c1[i]
    const n2 = c2[i]
    if (isSameVNodeType(n1, n2)) {
      patch(n1, n2, container, parentAnchor, parentComponent, parentSuspense, isSVG, optimized)
    } else {
      break
    }
    i++
  }
  
  // 2. 从尾部开始同步
  while (i <= e1 && i <= e2) {
    const n1 = c1[e1]
    const n2 = c2[e2]
    if (isSameVNodeType(n1, n2)) {
      patch(n1, n2, container, parentAnchor, parentComponent, parentSuspense, isSVG, optimized)
    } else {
      break
    }
    e1--
    e2--
  }
  
  // 3. 只有新增节点
  if (i > e1) {
    if (i <= e2) {
      const nextPos = e2 + 1
      const anchor = nextPos < l2 ? c2[nextPos].el : parentAnchor
      while (i <= e2) {
        patch(null, c2[i], container, anchor, parentComponent, parentSuspense, isSVG)
        i++
      }
    }
  }
  
  // 4. 只有删除节点
  else if (i > e2) {
    while (i <= e1) {
      unmount(c1[i], parentComponent, parentSuspense, true)
      i++
    }
  }
  
  // 5. 未知序列
  else {
    const s1 = i
    const s2 = i
    const keyToNewIndexMap = new Map()
    
    // 5.1 建立 key -> index 映射
    for (i = s2; i <= e2; i++) {
      const nextChild = c2[i]
      if (nextChild.key != null) {
        keyToNewIndexMap.set(nextChild.key, i)
      }
    }
    
    let j
    let patched = 0
    const toBePatched = e2 - s2 + 1
    let moved = false
    let maxNewIndexSoFar = 0
    
    const newIndexToOldIndexMap = new Array(toBePatched)
    for (i = 0; i < toBePatched; i++) newIndexToOldIndexMap[i] = 0
    
    // 5.2 遍历旧节点，尝试匹配
    for (i = s1; i <= e1; i++) {
      const prevChild = c1[i]
      if (patched >= toBePatched) {
        // 新节点都已处理，删除剩余旧节点
        unmount(prevChild, parentComponent, parentSuspense, true)
        continue
      }
      let newIndex
      if (prevChild.key != null) {
        newIndex = keyToNewIndexMap.get(prevChild.key)
      } else {
        // 无 key，尝试查找相同类型节点
        for (j = s2; j <= e2; j++) {
          if (newIndexToOldIndexMap[j - s2] === 0 && isSameVNodeType(prevChild, c2[j])) {
            newIndex = j
            break
          }
        }
      }
      if (newIndex === undefined) {
        unmount(prevChild, parentComponent, parentSuspense, true)
      } else {
        newIndexToOldIndexMap[newIndex - s2] = i + 1
        if (newIndex >= maxNewIndexSoFar) {
          maxNewIndexSoFar = newIndex
        } else {
          moved = true
        }
        patch(prevChild, c2[newIndex], container, null, parentComponent, parentSuspense, isSVG, optimized)
        patched++
      }
    }
    
    // 5.3 移动和挂载
    const increasingNewIndexSequence = moved
      ? getSequence(newIndexToOldIndexMap)
      : EMPTY_ARR
    
    j = increasingNewIndexSequence.length - 1
    for (i = toBePatched - 1; i >= 0; i--) {
      const nextIndex = s2 + i
      const nextChild = c2[nextIndex]
      const anchor = nextIndex + 1 < l2 ? c2[nextIndex + 1].el : parentAnchor
      
      if (newIndexToOldIndexMap[i] === 0) {
        // 新节点
        patch(null, nextChild, container, anchor, parentComponent, parentSuspense, isSVG)
      } else if (moved) {
        if (j < 0 || i !== increasingNewIndexSequence[j]) {
          // 需要移动
          move(nextChild.el, container, anchor)
        } else {
          j--
        }
      }
    }
  }
}
```

### 6.4 最长递增子序列算法

```javascript
function getSequence(arr) {
  const p = arr.slice()
  const result = [0]
  let i, j, u, v, c
  const len = arr.length
  
  for (i = 0; i < len; i++) {
    const arrI = arr[i]
    if (arrI !== 0) {
      j = result[result.length - 1]
      if (arr[j] < arrI) {
        p[i] = j
        result.push(i)
        continue
      }
      u = 0
      v = result.length - 1
      while (u < v) {
        c = ((u + v) / 2) | 0
        if (arr[result[c]] < arrI) {
          u = c + 1
        } else {
          v = c
        }
      }
      if (arrI < arr[result[u]]) {
        if (u > 0) {
          p[i] = result[u - 1]
        }
        result[u] = i
      }
    }
  }
  
  u = result.length
  v = result[u - 1]
  while (u-- > 0) {
    result[u] = v
    v = p[v]
  }
  
  return result
}
```

---

## 七、模板编译

### 7.1 编译流程

```
模板字符串 → parse() → AST → transform() → 转换后的 AST → generate() → render 函数
```

### 7.2 静态提升

Vue3 将静态节点提升到 render 函数外部，避免重复创建。

```javascript
// 模板
<div>
  <span class="static">静态内容</span>
  <span :class="dynamic">{{ msg }}</span>
</div>

// 编译结果
const _hoisted_1 = /*#__PURE__*/_createElementVNode("span", { class: "static" }, "静态内容", -1)

function render(_ctx, _cache) {
  return (_openBlock(), _createElementBlock("div", null, [
    _hoisted_1,
    _createElementVNode("span", {
      class: _normalizeClass(_ctx.dynamic)
    }, _toDisplayString(_ctx.msg), 3 /* TEXT, CLASS */)
  ]))
}
```

### 7.3 Block（动态节点收集）

```javascript
function openBlock(disableTracking = false) {
  blockStack.push((currentBlock = []))
}

function closeBlock() {
  blockStack.pop()
  currentBlock = blockStack[blockStack.length - 1] || null
}

function createElementBlock(
  type,
  props,
  children,
  patchFlag,
  dynamicProps,
  shapeFlag
) {
  return setupBlock(
    createBaseVNode(type, props, children, patchFlag, dynamicProps, shapeFlag, true)
  )
}

function setupBlock(vnode) {
  // 收集动态子节点
  vnode.dynamicChildren = currentBlock || null
  closeBlock()
  return vnode
}
```

---

## 八、组件实例

### 8.1 组件实例结构

```typescript
interface ComponentInternalInstance {
  uid: number
  type: Component
  parent: ComponentInternalInstance | null
  root: ComponentInternalInstance
  vnode: VNode
  subTree: VNode
  scope: EffectScope
  props: Data
  attrs: Data
  slots: InternalSlots
  refs: Data
  emit: Emit
  ctx: Data  // 渲染上下文
  setupState: Data  // setup 返回的状态
  setupContext: SetupContext | null
  data: Data  // Options API data
  proxy: ComponentPublicInstance | null  // 代理对象
  // 生命周期
  isMounted: boolean
  isUnmounted: boolean
  // ...
}
```

### 8.2 组件挂载流程

```javascript
function mountComponent(
  initialVNode,
  container,
  anchor,
  parentComponent,
  parentSuspense,
  isSVG,
  optimized
) {
  // 1. 创建组件实例
  const instance = createComponentInstance(
    initialVNode,
    parentComponent,
    parentSuspense
  )
  
  // 2. 设置组件
  setupComponent(instance)
  
  // 3. 设置副作用渲染
  setupRenderEffect(
    instance,
    initialVNode,
    container,
    anchor,
    parentSuspense,
    isSVG,
    optimized
  )
  
  return instance.proxy
}

function setupComponent(instance) {
  // 处理 props
  initProps(instance)
  
  // 处理 slots
  initSlots(instance)
  
  // 执行 setup
  if (instance.type.setup) {
    const setupResult = instance.type.setup(
      instance.props,
      {
        attrs: instance.attrs,
        slots: instance.slots,
        emit: instance.emit,
        expose: (exposed) => { instance.exposed = exposed }
      }
    )
    
    handleSetupResult(instance, setupResult)
  } else {
    finishComponentSetup(instance)
  }
}
```

### 8.3 setupRenderEffect

```javascript
function setupRenderEffect(
  instance,
  initialVNode,
  container,
  anchor,
  parentSuspense,
  isSVG,
  optimized
) {
  const componentUpdateFn = () => {
    if (!instance.isMounted) {
      // 挂载
      const subTree = (instance.subTree = renderComponentRoot(instance))
      
      patch(null, subTree, container, anchor, instance, parentSuspense, isSVG)
      
      initialVNode.el = subTree.el
      instance.isMounted = true
    } else {
      // 更新
      const nextTree = renderComponentRoot(instance)
      const prevTree = instance.subTree
      
      patch(prevTree, nextTree, container, anchor, instance, parentSuspense, isSVG)
      
      instance.subTree = nextTree
    }
  }
  
  // 创建响应式副作用
  instance.update = effect(componentUpdateFn, {
    scheduler: queueJob
  })
}
```

---

## 九、生命周期

### 9.1 Options API 生命周期

| Vue2 | Vue3 |
|------|------|
| beforeCreate | beforeCreate / setup() |
| created | created / setup() |
| beforeMount | onBeforeMount |
| mounted | onMounted |
| beforeUpdate | onBeforeUpdate |
| updated | onUpdated |
| beforeDestroy | onBeforeUnmount |
| destroyed | onUnmounted |
| errorCaptured | onErrorCaptured |

### 9.2 Composition API 生命周期钩子

```javascript
function onBeforeMount(hook, target = currentInstance) {
  injectHook(LifecycleHooks.BEFORE_MOUNT, hook, target)
}

function onMounted(hook, target = currentInstance) {
  injectHook(LifecycleHooks.MOUNTED, hook, target)
}

function onBeforeUpdate(hook, target = currentInstance) {
  injectHook(LifecycleHooks.BEFORE_UPDATE, hook, target)
}

function onUpdated(hook, target = currentInstance) {
  injectHook(LifecycleHooks.UPDATED, hook, target)
}

function onBeforeUnmount(hook, target = currentInstance) {
  injectHook(LifecycleHooks.BEFORE_UNMOUNT, hook, target)
}

function onUnmounted(hook, target = currentInstance) {
  injectHook(LifecycleHooks.UNMOUNTED, hook, target)
}

function injectHook(type, hook, target) {
  if (target) {
    const hooks = target[type] || (target[type] = [])
    const wrappedHook = () => {
      setCurrentInstance(target)
      try {
        return hook()
      } finally {
        setCurrentInstance(null)
      }
    }
    hooks.push(wrappedHook)
  }
}
```

---

## 十、Tree Shaking

Vue3 支持 Tree Shaking，未使用的 API 不会打包。

```javascript
// Vue2 - 全量引入
import Vue from 'vue'
Vue.nextTick()  // 即使不用也会打包

// Vue3 - 按需引入
import { nextTick, ref, computed } from 'vue'
nextTick()  // 只打包用到的 API
```

### 10.1 全局 API 改造

```javascript
// Vue2
Vue.directive('focus', {
  inserted: (el) => el.focus()
})

// Vue3
import { createApp } from 'vue'
const app = createApp(App)
app.directive('focus', {
  mounted: (el) => el.focus()
})
```

---

## 十一、Fragment 与 Teleport

### 11.1 Fragment（多根节点）

```javascript
// Vue2 - 必须单根节点
<template>
  <div>
    <span>1</span>
    <span>2</span>
  </div>
</template>

// Vue3 - 支持多根节点
<template>
  <span>1</span>
  <span>2</span>
</template>
```

### 11.2 Teleport（传送门）

```javascript
const TeleportImpl = {
  process(
    n1,
    n2,
    container,
    anchor,
    parentComponent,
    parentSuspense,
    isSVG,
    optimized
  ) {
    const target = document.querySelector(n2.props.to)
    
    if (n1 == null) {
      // 挂载到目标位置
      mountChildren(
        n2.children,
        target,
        null,
        parentComponent,
        parentSuspense,
        isSVG,
        optimized
      )
    } else {
      // 更新
      patchChildren(
        n1,
        n2,
        target,
        null,
        parentComponent,
        parentSuspense,
        isSVG,
        optimized
      )
    }
  }
}
```

---

## 十二、Suspense

异步组件加载状态处理。

```javascript
const SuspenseImpl = {
  name: 'Suspense',
  setup(props, { slots }) {
    const suspense = {
      deps: 0,
      isResolved: false,
      isHydrating: false,
      asyncQueue: null
    }
    
    return () => {
      if (suspense.isResolved) {
        return slots.default ? slots.default() : null
      } else {
        return slots.fallback ? slots.fallback() : null
      }
    }
  }
}
```

---

## 十三、Vue2 vs Vue3 对比总结

| 特性 | Vue2 | Vue3 |
|------|------|------|
| 响应式原理 | Object.defineProperty | Proxy |
| 响应式性能 | 递归遍历，初始化开销大 | 惰性代理，按需转换 |
| 数组监听 | 变异方法重写 | 原生支持 |
| 新增/删除属性 | 需要 Vue.set/delete | 自动监听 |
| Map/Set 支持 | ❌ | ✅ |
| Diff 算法 | 双端比较 | 最长递增子序列 |
| 静态提升 | ❌ | ✅ |
| PatchFlags | ❌ | ✅ |
| Tree Shaking | ❌ | ✅ |
| Fragment | ❌ | ✅ |
| Teleport | ❌ | ✅ |
| Suspense | ❌ | ✅ |
| Composition API | ❌ | ✅ |
| TypeScript 支持 | 需要额外配置 | 原生支持 |

---

## 十四、总结

Vue3 的核心改进：

1. **响应式系统**：基于 Proxy，更强大、更高效
2. **编译优化**：静态提升、PatchFlags、Block 缓存
3. **Diff 算法**：最长递增子序列，减少移动次数
4. **Composition API**：更好的逻辑复用和代码组织
5. **新特性**：Fragment、Teleport、Suspense
6. **TypeScript**：原生支持，类型友好
7. **Tree Shaking**：更小的打包体积

这些改进使得 Vue3 在性能、开发体验和可维护性上都有显著提升。
