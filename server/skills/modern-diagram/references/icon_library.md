# 常用计算机与系统纯 SVG Path 图标库

在生成现代化架构图或模块图解时，不要留空或手绘复杂形状。直接在 `<svg>` 中嵌入以下经过严谨对齐的标准 24x24 视口纯 `<path>` 图标（使用 `<g transform="translate(X, Y) scale(...)">` 放置），赋予图解专业设计感。

---

## 1. 服务器与计算节点 (Server / Compute)

```xml
<!-- 24x24 viewBox -->
<g class="icon-server" stroke="#4f46e5" stroke-width="1.75" fill="none" stroke-linecap="round" stroke-linejoin="round">
  <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
  <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
  <line x1="6" y1="6" x2="6.01" y2="6"/>
  <line x1="6" y1="18" x2="6.01" y2="18"/>
</g>
```

---

## 2. 数据库与存储 (Database / Storage)

```xml
<g class="icon-database" stroke="#0284c7" stroke-width="1.75" fill="none" stroke-linecap="round" stroke-linejoin="round">
  <ellipse cx="12" cy="5" rx="9" ry="3"/>
  <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
  <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
</g>
```

---

## 3. 云与网络服务 (Cloud / Network)

```xml
<g class="icon-cloud" stroke="#0ea5e9" stroke-width="1.75" fill="none" stroke-linecap="round" stroke-linejoin="round">
  <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>
</g>
```

---

## 4. 客户端与浏览器 (Client / Browser / User)

```xml
<g class="icon-client" stroke="#475569" stroke-width="1.75" fill="none" stroke-linecap="round" stroke-linejoin="round">
  <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
  <line x1="8" y1="21" x2="16" y2="21"/>
  <line x1="12" y1="17" x2="12" y2="21"/>
</g>
```

---

## 5. 消息队列与流管道 (Message Queue / Pipeline)

```xml
<g class="icon-queue" stroke="#d97706" stroke-width="1.75" fill="none" stroke-linecap="round" stroke-linejoin="round">
  <rect x="2" y="5" width="4" height="14" rx="1"/>
  <rect x="10" y="5" width="4" height="14" rx="1"/>
  <rect x="18" y="5" width="4" height="14" rx="1"/>
  <path d="M6 12h4m4 0h4"/>
</g>
```

---

## 6. 安全、鉴权与锁 (Lock / Security / Auth)

```xml
<g class="icon-lock" stroke="#059669" stroke-width="1.75" fill="none" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
  <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
</g>
```

---

## 7. CPU / 核心处理器 (CPU / Processor)

```xml
<g class="icon-cpu" stroke="#7c3aed" stroke-width="1.75" fill="none" stroke-linecap="round" stroke-linejoin="round">
  <rect x="4" y="4" width="16" height="16" rx="2"/>
  <rect x="9" y="9" width="6" height="6"/>
  <line x1="9" y1="1" x2="9" y2="4"/>
  <line x1="15" y1="1" x2="15" y2="4"/>
  <line x1="9" y1="20" x2="9" y2="23"/>
  <line x1="15" y1="20" x2="15" y2="23"/>
  <line x1="20" y1="9" x2="23" y2="9"/>
  <line x1="20" y1="14" x2="23" y2="14"/>
  <line x1="1" y1="9" x2="4" y2="9"/>
  <line x1="1" y1="14" x2="4" y2="14"/>
</g>
```

---

## 8. 内存与缓存 (RAM / Cache)

```xml
<g class="icon-memory" stroke="#e11d48" stroke-width="1.75" fill="none" stroke-linecap="round" stroke-linejoin="round">
  <path d="M6 19v-3"/>
  <path d="M10 19v-3"/>
  <path d="M14 19v-3"/>
  <path d="M18 19v-3"/>
  <rect x="2" y="5" width="20" height="11" rx="2"/>
</g>
```

---

## 9. 终端与代码 (Terminal / CLI)

```xml
<g class="icon-terminal" stroke="#334155" stroke-width="1.75" fill="none" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="4 17 10 11 4 5"/>
  <line x1="12" y1="19" x2="20" y2="19"/>
</g>
```

---

### 使用技巧：在卡片标题旁放置图标
只需在组件卡片左上角嵌入：
```xml
<!-- 放置在卡片 (x=50, y=50) 的标题行 -->
<g transform="translate(62, 62) scale(0.85)">
  <ellipse cx="12" cy="5" rx="9" ry="3" fill="none" stroke="#0284c7" stroke-width="1.75"/>
  <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" fill="none" stroke="#0284c7" stroke-width="1.75"/>
  <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" fill="none" stroke="#0284c7" stroke-width="1.75"/>
</g>
<text x="88" y="77" font-family="system-ui, sans-serif" font-size="14" font-weight="600" fill="#0f172a">MySQL 主从集群</text>
```
