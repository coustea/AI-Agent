# 操作系统内存布局与数据结构指针图解规范 (Memory & Pointers)

在讲解操作系统（虚拟内存、堆栈增长、段页式管理）和数据结构（链表、树、图、跳表、LRU 缓存）时，需要精确表达**内存地址连续性、高低地址生长方向与贝塞尔指针指向**。

---

## 1. 内存排布设计原则

* **垂直/水平地址轴**：
  * 必须在侧边或顶部提供标尺说明 `0x00000000 (低地址)` → `0xFFFFFFFF (高地址)`；
  * 标明增长方向箭头（如 `栈向下增长 ↓`，`堆向上增长 ↑`）。
* **内存分段颜色编码**：
  * **代码段 (.text)**：淡蓝底色 (`#eff6ff`)；
  * **数据段 (.data / .bss)**：淡紫底色 (`#faf5ff`)；
  * **堆区 (Heap)**：淡绿底色 (`#f0fdf4`)；
  * **栈区 (Stack)**：淡橙底色 (`#fff7ed`)；
  * **内核空间 (Kernel)**：淡红/灰底色 (`#fef2f2`)。
* **数据结构节点与指针箭头**：
  * 节点采用复合矩形：`[ 数据域 (Data) | 指针域 (Next) ]`；
  * 指针从指针域圆心出发，使用平滑三次贝塞尔曲线 `<path d="M ... C ..." />` 优雅地指向下一个节点的数据域；
  * `NULL` 空指针以标准的下划线地线符号或 `NULL` 胶囊标识。

---

## 2. 经典进程虚拟内存空间布局模板

```xml
<svg viewBox="0 0 680 460" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="boxShadow" x="-5%" y="-5%" width="110%" height="115%">
      <feDropShadow dx="0" dy="2" stdDeviation="5" flood-color="#0f172a" flood-opacity="0.05"/>
    </filter>
    <marker id="ptrArrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#0284c7"/>
    </marker>
    <marker id="stackArrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#ea580c"/>
    </marker>
    <marker id="heapArrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#16a34a"/>
    </marker>
  </defs>

  <!-- 地址轴标尺 (左侧) -->
  <g transform="translate(40, 20)">
    <line x1="60" y1="20" x2="60" y2="400" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="3 3"/>
    <text x="50" y="24" font-family="ui-monospace, monospace" font-size="11" fill="#64748b" text-anchor="end">0xFFFFFFFF</text>
    <text x="50" y="38" font-family="system-ui" font-size="9" fill="#94a3b8" text-anchor="end">(高地址)</text>
    
    <text x="50" y="404" font-family="ui-monospace, monospace" font-size="11" fill="#64748b" text-anchor="end">0x00000000</text>
    <text x="50" y="418" font-family="system-ui" font-size="9" fill="#94a3b8" text-anchor="end">(低地址)</text>
  </g>

  <!-- 内存主柱体 (中央) -->
  <g transform="translate(140, 30)">
    <!-- 1. 内核空间 (Kernel Space) -->
    <rect x="0" y="0" width="380" height="60" rx="6" fill="#fee2e2" stroke="#fca5a5" stroke-width="1.5" filter="url(#boxShadow)"/>
    <text x="190" y="28" font-family="system-ui" font-size="13" font-weight="600" fill="#991b1b" text-anchor="middle">内核空间 (Kernel Space, 1GB)</text>
    <text x="190" y="46" font-family="system-ui" font-size="10" fill="#b91c1c" text-anchor="middle">用户代码不可直接访问 (Ring 0)</text>

    <!-- 2. 用户栈区 (Stack) -->
    <rect x="0" y="70" width="380" height="70" rx="6" fill="#ffedd5" stroke="#fdba74" stroke-width="1.5" filter="url(#boxShadow)"/>
    <text x="190" y="98" font-family="system-ui" font-size="13" font-weight="600" fill="#9a3412" text-anchor="middle">用户栈区 (Stack)</text>
    <text x="190" y="116" font-family="system-ui" font-size="10" fill="#c2410c" text-anchor="middle">局部变量、函数调用栈帧、返回地址</text>

    <!-- 生长方向指示: 栈向下增长 -->
    <line x1="420" y1="85" x2="420" y2="135" stroke="#ea580c" stroke-width="2" marker-end="url(#stackArrow)"/>
    <text x="435" y="114" font-family="system-ui" font-size="11" font-weight="600" fill="#ea580c">向下增长 ↓</text>

    <!-- 3. 内存映射区与共享库 (Memory Mapping / mmap) -->
    <rect x="0" y="150" width="380" height="50" rx="6" fill="#f1f5f9" stroke="#cbd5e1" stroke-width="1.5" stroke-dasharray="4 4"/>
    <text x="190" y="174" font-family="system-ui" font-size="12" font-weight="600" fill="#475569" text-anchor="middle">共享内存映射区 (mmap)</text>
    <text x="190" y="190" font-family="system-ui" font-size="10" fill="#64748b" text-anchor="middle">动态链接库 (libc.so)、共享内存段</text>

    <!-- 生长方向指示: 堆向上增长 -->
    <line x1="420" y1="265" x2="420" y2="215" stroke="#16a34a" stroke-width="2" marker-end="url(#heapArrow)"/>
    <text x="435" y="244" font-family="system-ui" font-size="11" font-weight="600" fill="#16a34a">向上增长 ↑</text>

    <!-- 4. 用户堆区 (Heap) -->
    <rect x="0" y="210" width="380" height="65" rx="6" fill="#dcfce7" stroke="#86efac" stroke-width="1.5" filter="url(#boxShadow)"/>
    <text x="190" y="238" font-family="system-ui" font-size="13" font-weight="600" fill="#166534" text-anchor="middle">动态堆区 (Heap)</text>
    <text x="190" y="256" font-family="system-ui" font-size="10" fill="#15803d" text-anchor="middle">malloc / free, new / delete 动态分配</text>

    <!-- 5. 数据段 (BSS + Data) -->
    <rect x="0" y="285" width="380" height="55" rx="6" fill="#f3e8ff" stroke="#d8b4fe" stroke-width="1.5" filter="url(#boxShadow)"/>
    <text x="190" y="310" font-family="system-ui" font-size="12" font-weight="600" fill="#6b21a8" text-anchor="middle">数据段 (.data / .bss)</text>
    <text x="190" y="326" font-family="system-ui" font-size="10" fill="#7e22ce" text-anchor="middle">全局变量与 static 静态变量 (已初始化/未初始化)</text>

    <!-- 6. 代码段 (.text) -->
    <rect x="0" y="350" width="380" height="45" rx="6" fill="#dbeafe" stroke="#93c5fd" stroke-width="1.5" filter="url(#boxShadow)"/>
    <text x="190" y="372" font-family="system-ui" font-size="12" font-weight="600" fill="#1e40af" text-anchor="middle">代码段 (.text, 只读)</text>
    <text x="190" y="386" font-family="system-ui" font-size="9" fill="#2563eb" text-anchor="middle">二进制机器指令、字面量常量</text>
  </g>
</svg>
```
