# 分布式系统与微服务架构图设计规范 (System Architecture)

系统架构图要求层次清晰（分层泳道）、卡片立体（投影与描边）、连线流畅（贝塞尔曲线与动态流向点）以及模块语义化标识（图标与状态徽章）。

---

## 1. 架构图核心设计法则

* **画布布局**：推荐 `viewBox="0 0 860 H"`，采用自顶向下（用户端 → 网关 → 核心业务服务 → 存储/中间件）或从左到右的架构流向。
* **分层背景框 (Subsystem Containers)**：
  * 使用极淡的背景色区分层次：如客户端层 (`#f8fafc`)、网关层 (`#f1f5f9`)、微服务集群 (`#f8fafc` 虚线框)、持久层 (`#f0fdf4`)；
  * 左上角放置小胶囊标签（如 `[API Gateway Layer]`）。
* **卡片设计**：
  * 圆角 `rx="10"`；
  * 采用双层边框或立体软阴影 (`feDropShadow`)；
  * 左侧放置 24x24 矢量图标，右侧放置组件名 + 简要职责（2行文字排版）。
* **流动连线 (Connectors & Arrows)**：
  * 使用 `<path d="M x1 y1 C cx1 cy1, cx2 cy2, x2 y2" ... />` 平滑贝塞尔曲线，避免僵硬直角；
  * 在 `<defs>` 中定义现代箭头 `<marker id="arrow" ...>`；
  * 协议与端口标签放置在连线中点小白底矩形内（例如 `gRPC :50051`, `HTTPS :443`）。

---

## 2. 现代微服务架构示例模板

```xml
<svg viewBox="0 0 840 440" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- 柔和现代卡片阴影 -->
    <filter id="cardShadow" x="-10%" y="-10%" width="125%" height="125%">
      <feDropShadow dx="0" dy="4" stdDeviation="8" flood-color="#0f172a" flood-opacity="0.06"/>
    </filter>
    <!-- 平滑连线端点箭头 -->
    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#64748b"/>
    </marker>
    <!-- 渐变色定义 -->
    <linearGradient id="primaryBadge" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#4f46e5"/>
      <stop offset="100%" stop-color="#06b6d4"/>
    </linearGradient>
  </defs>

  <!-- 1. 客户端访问层 -->
  <g transform="translate(40, 30)">
    <rect x="0" y="0" width="160" height="72" rx="10" fill="#ffffff" stroke="#cbd5e1" stroke-width="1.5" filter="url(#cardShadow)"/>
    <!-- 浏览器图标 -->
    <g transform="translate(16, 22) scale(0.9)" stroke="#475569" stroke-width="1.75" fill="none" stroke-linecap="round" stroke-linejoin="round">
      <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
      <line x1="8" y1="21" x2="16" y2="21"/>
      <line x1="12" y1="17" x2="12" y2="21"/>
    </g>
    <text x="50" y="36" font-family="system-ui, sans-serif" font-size="13" font-weight="600" fill="#0f172a">Web / App 客户端</text>
    <text x="50" y="54" font-family="system-ui, sans-serif" font-size="10" fill="#64748b">Vue 3 / Flutter 终端</text>
  </g>

  <!-- 连线: 客户端 -> API 网关 -->
  <path d="M 200 66 L 310 66" fill="none" stroke="#64748b" stroke-width="1.75" marker-end="url(#arrow)"/>
  <rect x="225" y="54" width="60" height="18" rx="4" fill="#ffffff" stroke="#e2e8f0"/>
  <text x="255" y="67" font-family="ui-monospace, monospace" font-size="9" fill="#475569" text-anchor="middle">HTTPS</text>

  <!-- 2. API 网关层 -->
  <g transform="translate(310, 20)">
    <rect x="0" y="0" width="180" height="92" rx="12" fill="#ffffff" stroke="#818cf8" stroke-width="1.5" filter="url(#cardShadow)"/>
    <!-- 顶部彩色饰条 -->
    <path d="M 0 12 Q 0 0 12 0 L 168 0 Q 180 0 180 12 L 180 6 L 0 6 Z" fill="url(#primaryBadge)"/>
    <text x="18" y="36" font-family="system-ui, sans-serif" font-size="14" font-weight="600" fill="#1e1b4b">API 网关 (Gateway)</text>
    <text x="18" y="56" font-family="system-ui, sans-serif" font-size="11" fill="#475569">• 统一鉴权 &amp; JWT 白名单</text>
    <text x="18" y="74" font-family="system-ui, sans-serif" font-size="11" fill="#475569">• 流量调度 &amp; SSE 流式转发</text>
  </g>

  <!-- 连线: 网关 -> 后端微服务集群 (贝塞尔发散) -->
  <path d="M 490 66 C 530 66, 540 160, 570 160" fill="none" stroke="#64748b" stroke-width="1.75" marker-end="url(#arrow)"/>
  <path d="M 490 66 C 530 66, 540 260, 570 260" fill="none" stroke="#64748b" stroke-width="1.75" marker-end="url(#arrow)"/>

  <!-- 3. 后端服务集群大容器 (Cluster Zone) -->
  <g transform="translate(560, 100)">
    <rect x="0" y="0" width="240" height="210" rx="12" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5" stroke-dasharray="4 4"/>
    <rect x="12" y="-10" width="96" height="20" rx="4" fill="#e2e8f0"/>
    <text x="60" y="4" font-family="system-ui" font-size="10" font-weight="600" fill="#475569" text-anchor="middle">业务服务集群</text>

    <!-- 服务卡片 A: Chat / Tutor Agent -->
    <g transform="translate(15, 20)">
      <rect x="0" y="0" width="210" height="70" rx="8" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.5" filter="url(#cardShadow)"/>
      <circle cx="24" cy="35" r="14" fill="#e0e7ff"/>
      <text x="24" y="40" font-family="ui-monospace" font-size="12" font-weight="bold" fill="#4338ca" text-anchor="middle">AI</text>
      <text x="50" y="30" font-family="system-ui" font-size="12" font-weight="600" fill="#0f172a">Tutor Agent Service</text>
      <text x="50" y="48" font-family="system-ui" font-size="10" fill="#64748b">上下文滚动压缩 / ReAct 循环</text>
    </g>

    <!-- 服务卡片 B: Resource MAS Subagents -->
    <g transform="translate(15, 110)">
      <rect x="0" y="0" width="210" height="70" rx="8" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.5" filter="url(#cardShadow)"/>
      <circle cx="24" cy="35" r="14" fill="#ecfdf5"/>
      <text x="24" y="40" font-family="ui-monospace" font-size="12" font-weight="bold" fill="#047857" text-anchor="middle">MAS</text>
      <text x="50" y="30" font-family="system-ui" font-size="12" font-weight="600" fill="#0f172a">Resource Agent Cluster</text>
      <text x="50" y="48" font-family="system-ui" font-size="10" fill="#64748b">PPT / 视频 Subagent 并行流水线</text>
    </g>
  </g>

  <!-- 连线: 服务集群 -> 存储与持久层 (向左下回流) -->
  <path d="M 665 310 C 665 380, 520 380, 480 380" fill="none" stroke="#64748b" stroke-width="1.75" marker-end="url(#arrow)"/>
  <path d="M 665 310 C 665 380, 320 380, 240 380" fill="none" stroke="#64748b" stroke-width="1.75" marker-end="url(#arrow)"/>

  <!-- 4. 存储与中间件层 -->
  <g transform="translate(80, 340)">
    <rect x="0" y="0" width="160" height="74" rx="10" fill="#ffffff" stroke="#93c5fd" stroke-width="1.5" filter="url(#cardShadow)"/>
    <g transform="translate(16, 22) scale(0.9)" stroke="#0284c7" stroke-width="1.75" fill="none">
      <ellipse cx="12" cy="5" rx="9" ry="3"/>
      <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
    </g>
    <text x="50" y="36" font-family="system-ui" font-size="13" font-weight="600" fill="#0f172a">MySQL 8.0</text>
    <text x="50" y="54" font-family="system-ui" font-size="10" fill="#64748b">会话记录 / 用户画像 / 事实</text>
  </g>

  <g transform="translate(320, 340)">
    <rect x="0" y="0" width="160" height="74" rx="10" fill="#ffffff" stroke="#fca5a5" stroke-width="1.5" filter="url(#cardShadow)"/>
    <g transform="translate(16, 22) scale(0.9)" stroke="#e11d48" stroke-width="1.75" fill="none">
      <path d="M6 19v-3"/>
      <path d="M10 19v-3"/>
      <path d="M14 19v-3"/>
      <path d="M18 19v-3"/>
      <rect x="2" y="5" width="20" height="11" rx="2"/>
    </g>
    <text x="50" y="36" font-family="system-ui" font-size="13" font-weight="600" fill="#0f172a">向量索引 / 缓存</text>
    <text x="50" y="54" font-family="system-ui" font-size="10" fill="#64748b">ChromaDB / RAG 知识检索</text>
  </g>
</svg>
```
