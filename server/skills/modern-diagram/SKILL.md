---
name: modern-diagram
description: 现代 UI 设计级图解说明指南，教导 Agent 输出现代工业级矢量图解（SVG / 协议报文网格 / 系统架构图 / 内存排布 / 数据流向），包含即拿即用的纯 SVG 计算机图标库与精密排版规范。
---

# Modern Diagram & Architecture Visualizer Skill

本技能旨在为面向计算机学科与现代工程领域的 AI 导师与智能体，建立一套**高质量、现代化、无需外部运行时依赖的原生矢量图解输出体系**。

---

## 1. 核心定位与技术决策矩阵

在面对用户的图解需求时，遵循以下决策树选择最佳输出形态：

```
用户的图解需求
│
├── 纯简单逻辑判断 / 状态转移（< 6 个节点）──> 使用 Mermaid 代码块（flowchart / stateDiagram）
│
└── 具备以下任一特征 ──> 必须使用原生 ```svg 代码块输出高保真图解：
    ├── ① 协议报文 / 帧结构（需要 0~31 位偏移量刻度标尺、细分位段、标志位）
    ├── ② 复杂系统架构 / 微服务拓扑（需要分层容器、立体卡片、服务图标、流动箭头）
    ├── ③ 操作系统内存分布 / 虚拟地址空间（需要堆栈生长方向、内存基地址标注）
    ├── ④ 复杂数据结构与指针（带有平滑三次贝塞尔曲线的指针指向、复合节点）
    └── ⑤ 用户明确要求"精美"、"高颜值"、"现代化 UI"、"架构图"
```

---

## 2. 现代 UI 设计黄金法则（Modern Visual Standards）

大模型手绘 SVG 最常犯的错误是**“线条生硬直角、颜色过度饱和刺眼、缺少呼吸感、字体粗暴”**。必须严格遵守以下五大设计规范：

### ① 调色系统：采用现代低饱和搭配（Tailwind Zinc / Slate + Accent）
* **背景底板**：白色 (`#ffffff`) 或极浅灰白 (`#f8fafc`)；
* **边框线条**：纤细微边框 `stroke="#e2e8f0"`，选中或重点区域使用 `stroke="#818cf8"` 或 `stroke="#93c5fd"`；线条粗细控制在 `1.25` ~ `1.75px`；
* **卡片填充**：
  * 主卡片：纯白搭配软阴影；
  * 强调区域：浅色色相（如 Indigo 浅底 `#e0e7ff`、Emerald 浅底 `#ecfdf5`、Sky 浅底 `#f0f9ff`、Amber 浅底 `#fef3c7`）；
  * **严禁**使用纯红 (`#ff0000`)、纯绿 (`#00ff00`)、纯蓝 (`#0000ff`)、纯黑粗边框。

### ② 视觉层次与柔和阴影（Depth & Drop Shadows）
在 `<svg><defs>` 中定义现代软阴影滤镜，避免扁平死板：
```xml
<defs>
  <filter id="softShadow" x="-10%" y="-10%" width="125%" height="125%">
    <feDropShadow dx="0" dy="4" stdDeviation="8" flood-color="#0f172a" flood-opacity="0.06"/>
  </filter>
</defs>
```

### ③ 几何与圆角规范
* 大容器外框：`rx="12"` 或 `rx="14"`；
* 内部组件卡片：`rx="8"` 或 `rx="10"`；
* 状态胶囊标签：`rx="9999"`（纯圆角胶囊）；
* 报文字段格：`rx="4"`（微圆角）。

### ④ 字体与排版层级（Typography Hierarchy）
* 根字体统一指定：`font-family="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"`；
* 代码与十六进制地址指定：`font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"`；
* **标题文字**：`font-size="13"` ~ `14`，`font-weight="600"`，`fill="#0f172a"`；
* **副标题 / 说明**：`font-size="10"` ~ `11`，`font-weight="normal"`，`fill="#64748b"`；
* **标尺刻度与微标注**：`font-size="9"` ~ `10`，`fill="#94a3b8"`。

### ⑤ 连接线与流向（Fluid Connectors）
* 严禁生硬直角折线，优先使用三次贝塞尔曲线：
  `d="M x1 y1 C cx1 cy1, cx2 cy2, x2 y2"`
* 连线末端配上精细箭头：
  ```xml
  <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M 0 1 L 8 5 L 0 9 z" fill="#64748b"/>
  </marker>
  ```

---

## 3. 图标嵌入规范

图解中切忌只有纯文字方框。组件卡片必须在标题左侧放置标准 24x24 矢量微图标。
详见参考文档：[icon_library.md](references/icon_library.md)

典型图标类型：
- **服务器 / 算力节点**：`references/icon_library.md#1-服务器与计算节点`
- **数据库 / 持久层**：`references/icon_library.md#2-数据库与存储`
- **云 / 网关网络**：`references/icon_library.md#3-云与网络服务`
- **客户端 / 浏览器**：`references/icon_library.md#4-客户端与浏览器`
- **消息队列 / 管道**：`references/icon_library.md#5-消息队列与流管道`
- **鉴权 / 锁安全**：`references/icon_library.md#6-安全鉴权与锁`
- **CPU / 寄存器**：`references/icon_library.md#7-cpu--核心处理器`
- **内存 / 缓存**：`references/icon_library.md#8-内存与缓存`

---

## 4. 专项计算机领域实战参考

根据具体讲解主题，按需阅读以下专项目录与模板：

1. **计算机网络协议报文（TCP/IP、以太网、TLS、HTTP/2 帧）**：
   * 查阅 [references/protocol_frames.md](references/protocol_frames.md)
   * 包含：0~31 位刻度标尺、标志位胶囊高亮、自动换行与字节对齐。
2. **分布式系统与微服务架构（网关、服务集群、缓存中间件、数据库）**：
   * 查阅 [references/system_architecture.md](references/system_architecture.md)
   * 包含：多层系统泳道、贝塞尔发散/收敛流向、服务状态徽章。
3. **操作系统与内存管理（虚拟地址空间、堆栈生长、指针与数据结构）**：
   * 查阅 [references/memory_and_pointers.md](references/memory_and_pointers.md)
   * 包含：高低地址刻度、内存分段着色、链表与树节点贝塞尔指针指向。

---

## 5. 输出格式与质量校验清单

当输出 SVG 图解时，必须自我校验以下 6 项标准：

* [ ] 是否包裹在标准的 ```` ```svg ```` 代码块中？
* [ ] 是否包含 `viewBox="0 0 W H"` 且 `width="100%"`，杜绝写死固定像素宽度？
* [ ] 是否在 `<defs>` 中声明了阴影滤镜 (`softShadow`) 与平滑箭头 (`arrow`)？
* [ ] 关键卡片是否附带了 24x24 矢量微图标（避免纯白秃方框）？
* [ ] 颜色是否符合 Tailwind 柔和调色体系（无刺眼荧光纯色）？
* [ ] 图表下方是否有 1~2 句话点出图解的核心关键逻辑（图文互补，不重复长篇废话）？
