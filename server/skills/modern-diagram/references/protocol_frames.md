# 计算机网络协议报文与帧结构设计规范 (Protocol Frames)

在计算机专业教学中，TCP/IP 报文、以太网帧、TLS 握手报文的解析极度依赖**位偏移量标尺 (Bit Offset Ruler)** 与清晰的方格对齐。

---

## 1. 位标尺核心设计规范

* **网格比例**：通常以 32-bit (4 字节) 为一行基准，总宽建议设定为 `640px` ~ `720px`（每 1-bit 对应宽约 `20px` ~ `22px`）。
* **标尺行**：
  * 在顶部绘制 `0, 1, 2, ... 15, 16, ... 31` 刻度数字；
  * 使用浅色刻度辅助线（`#e2e8f0`），避免干扰主要字段。
* **字段卡片**：
  * 每个字段矩形 `height="42"` ~ `height="48"`；
  * `rx="4"` 微圆角；
  * 关键字段（如 SYN/ACK 标志位、校验和、端口）使用浅色柔和底色（如 `#eff6ff`, `#ecfdf5`, `#fef3c7`）区分。

---

## 2. 经典 TCP 报头示例模板

```xml
<svg viewBox="0 0 740 380" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="cardShadow" x="-5%" y="-5%" width="110%" height="115%">
      <feDropShadow dx="0" dy="3" stdDeviation="6" flood-color="#0f172a" flood-opacity="0.06" />
    </filter>
  </defs>

  <!-- 背景底板 -->
  <rect x="10" y="10" width="720" height="360" rx="12" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.5" filter="url(#cardShadow)"/>

  <!-- 标尺刻度 0 - 31 位 -->
  <g font-family="ui-monospace, monospace" font-size="11" fill="#64748b" text-anchor="middle">
    <text x="30" y="38">0</text>
    <text x="110" y="38">4</text>
    <text x="190" y="38">8</text>
    <text x="350" y="38">15 16</text>
    <text x="510" y="38">24</text>
    <text x="690" y="38">31</text>
    <line x1="30" y1="44" x2="690" y2="44" stroke="#cbd5e1" stroke-width="1" stroke-dasharray="2 2"/>
  </g>

  <!-- Row 1: 源端口 (16 bit) + 目的端口 (16 bit) -->
  <g transform="translate(30, 52)">
    <rect x="0" y="0" width="325" height="46" rx="6" fill="#eff6ff" stroke="#93c5fd" stroke-width="1.5"/>
    <text x="162" y="24" font-family="system-ui, sans-serif" font-size="13" font-weight="600" fill="#1e3a8a" text-anchor="middle">源端口 (Source Port, 16 bits)</text>
    <text x="162" y="38" font-family="system-ui, sans-serif" font-size="10" fill="#3b82f6" text-anchor="middle">例如: 54321</text>

    <rect x="335" y="0" width="325" height="46" rx="6" fill="#eff6ff" stroke="#93c5fd" stroke-width="1.5"/>
    <text x="497" y="24" font-family="system-ui, sans-serif" font-size="13" font-weight="600" fill="#1e3a8a" text-anchor="middle">目的端口 (Destination Port, 16 bits)</text>
    <text x="497" y="38" font-family="system-ui, sans-serif" font-size="10" fill="#3b82f6" text-anchor="middle">例如: 443 (HTTPS)</text>
  </g>

  <!-- Row 2: 序号 (Sequence Number, 32 bit) -->
  <g transform="translate(30, 106)">
    <rect x="0" y="0" width="660" height="46" rx="6" fill="#f0fdf4" stroke="#86efac" stroke-width="1.5"/>
    <text x="330" y="28" font-family="system-ui, sans-serif" font-size="13" font-weight="600" fill="#14532d" text-anchor="middle">序号 (Sequence Number, 32 bits, 标识本报文段数据首字节)</text>
  </g>

  <!-- Row 3: 确认号 (Acknowledgment Number, 32 bit) -->
  <g transform="translate(30, 160)">
    <rect x="0" y="0" width="660" height="46" rx="6" fill="#fefce8" stroke="#fde047" stroke-width="1.5"/>
    <text x="330" y="28" font-family="system-ui, sans-serif" font-size="13" font-weight="600" fill="#713f12" text-anchor="middle">确认号 (Acknowledgment Number, 32 bits, 期望收到的下一序号)</text>
  </g>

  <!-- Row 4: 数据偏移 + 保留位 + 标志位 + 窗口大小 -->
  <g transform="translate(30, 214)">
    <rect x="0" y="0" width="80" height="46" rx="4" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5"/>
    <text x="40" y="24" font-family="system-ui" font-size="11" font-weight="600" fill="#334155" text-anchor="middle">数据偏移</text>
    <text x="40" y="38" font-family="system-ui" font-size="9" fill="#64748b" text-anchor="middle">4 bits</text>

    <rect x="85" y="0" width="75" height="46" rx="4" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5"/>
    <text x="122" y="24" font-family="system-ui" font-size="11" font-weight="600" fill="#334155" text-anchor="middle">保留位</text>
    <text x="122" y="38" font-family="system-ui" font-size="9" fill="#64748b" text-anchor="middle">6 bits</text>

    <!-- 核心标志位胶囊高亮 (URG/ACK/PSH/RST/SYN/FIN) -->
    <rect x="165" y="0" width="220" height="46" rx="6" fill="#ecfeff" stroke="#67e8f9" stroke-width="1.5"/>
    <text x="275" y="20" font-family="system-ui" font-size="11" font-weight="600" fill="#155e75" text-anchor="middle">控制标志位 (Flags, 6 bits)</text>
    <g font-family="ui-monospace, monospace" font-size="9" font-weight="bold" fill="#0e7490" text-anchor="middle">
      <text x="185" y="36">URG</text>
      <text x="220" y="36">ACK</text>
      <text x="255" y="36">PSH</text>
      <text x="290" y="36">RST</text>
      <text x="325" y="36">SYN</text>
      <text x="360" y="36">FIN</text>
    </g>

    <!-- 窗口大小 (16 bit) -->
    <rect x="390" y="0" width="270" height="46" rx="6" fill="#faf5ff" stroke="#d8b4fe" stroke-width="1.5"/>
    <text x="525" y="24" font-family="system-ui" font-size="12" font-weight="600" fill="#581c87" text-anchor="middle">窗口大小 (Window Size, 16 bits)</text>
    <text x="525" y="38" font-family="system-ui" font-size="9" fill="#7e22ce" text-anchor="middle">流量控制滑动窗口大小</text>
  </g>

  <!-- Row 5: 校验和 + 紧急指针 -->
  <g transform="translate(30, 268)">
    <rect x="0" y="0" width="325" height="46" rx="6" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5"/>
    <text x="162" y="28" font-family="system-ui" font-size="12" font-weight="600" fill="#334155" text-anchor="middle">校验和 (Checksum, 16 bits)</text>

    <rect x="335" y="0" width="325" height="46" rx="6" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5"/>
    <text x="497" y="28" font-family="system-ui" font-size="12" font-weight="600" fill="#334155" text-anchor="middle">紧急指针 (Urgent Pointer, 16 bits)</text>
  </g>

  <!-- 底部注记 -->
  <text x="370" y="342" font-family="system-ui, sans-serif" font-size="11" fill="#94a3b8" text-anchor="middle">TCP 头部标准长度为 20 字节（不含可选字段），以 32-bit (4 字节) 为对齐单位</text>
</svg>
```
