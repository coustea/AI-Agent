# 纯数据契约（Protocol）解耦与规范化重构方案

> **核心目标**：针对前期遗留的 6 项架构问题，彻底消除“闭包不可序列化、通道伪造 Done 事件、接口泄漏底层网关、配置职责混淆在前端、测试绑定内核类型、缺乏独立纯数据契约”等硬伤。  
> **指导思想**：**零兼容包袱、杜绝过度封装、纯数据契约、降低复杂度、大幅提高代码可读性与健壮性**。专为**单机/桌面端（Wails / 跨端）**场景量身打造。

---

## 一、 核心痛点与重构原则

| 现存缺陷 | 根因剖析 | 重构对策（规范化） |
|---|---|---|
| **1. 权限闭包锁死单进程** | `PermissionPrompt.Respond func(...)` 为 Go 内存函数指针，无法跨进程序列化 | 改为纯文本 `RequestID string`，通过 `agent.RespondPermission(id, decision)` 异步传回 |
| **2. 事件双轨与伪造** | 既有 `Type` 枚举，又有 `Done bool` / `Err error`；通道关闭前端伪造 `{Done: true}` | 统一由 `Type` 驱动，错误统一为 `Error string`，内核保证发射 `EventDone`，前端不伪造 |
| **3. 接口泄漏实现类型** | `Agent` 接口导出 `SetGateway(gateway.Gateway)`、`History() []gateway.Message` | 剔除底层细节方法，外部只需关注交互流与配置；不泄露 `gateway` 包类型 |
| **4. 配置职责倒挂** | TUI 前端持有 `Config`，并在 `model.go` 中直接读写磁盘与硬编码默认模型 | 配置生命周期收拢到 Agent 内核（加载/校验/持久化/热切网关），前端只读视图与传参 |
| **5. 测试耦合内核** | `tui_test.go` 手工构造 `gateway.ToolCall`、`permission.Request` 等内部结构 | 测试与 UI 仅依赖纯数据契约 `protocol` 包，使用纯结构体解耦测试 |
| **6. 缺少独立协议包** | 契约寄生在 `internal/agent` 中，外部引用时连带拉入全量内核实现 | 新建独立包 `internal/protocol`（约 80 行无依赖纯数据结构），作为唯一交互媒介 |

---

## 二、 架构全景图

```
┌────────────────────────────────────────────────────────┐
│                   前端展示与交互层                      │
│   (Bubble Tea TUI  /  未来 Wails 桌面端  /  CLI 宿主)    │
└───────────┬────────────────────────────────┬───────────┘
            │ 1. 订阅纯数据事件流              │ 2. 异步应答权限 / 切换配置
            │    <-chan protocol.Event       │    RespondPermission(id, d)
            ▼                                │    UpdateConfig(p, key, m)
┌────────────────────────────────────────────┴───────────┐
│              internal/protocol (纯数据契约包)            │
│  - Event / EventType (Delta, Tool, Perm, Done, Error)  │
│  - PermissionRequest (RequestID, ToolName, Args, ...)  │
│  - ConfigView (Provider, ModelName, Available...)      │
│  - Decision (AllowOnce, AllowSession, Deny)            │
└───────────────────────────▲────────────────────────────┘
                            │ 驱动与装配
┌───────────────────────────┴────────────────────────────┐
│              internal/agent (智能体运行引擎)            │
│  - CoreAgent (实现 Agent 接口)                          │
│  - 自治管理: config.json 读写校验、默认模型映射          │
│  - 权限应答表: map[string]chan protocol.Decision       │
└────────────────────────────────────────────────────────┘
```
