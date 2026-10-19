# Tide 核心能力落地审计

日期：2026-10-19  
审计对象：`internal/agent`、`internal/tool`、`internal/permission`、`internal/gateway`、`internal/tui`  
基线：`d7165ce`（工作区有 18 个未提交改动，审计以磁盘上的实际代码为准）  
测试基线：`go build ./...` 通过，`go test ./... -count=1` 12 个包全绿

---

## 0. 结论

四项能力**全部已实现且已闭环**，不需要新建骨架。问题不在"有没有"，在"边界够不够硬"。

| 能力 | 判定 | 核心实现位置 | 覆盖测试 | 完成度 |
|---|---|---|---|---|
| Agent Loop | ✅ 已完成 | `agent/loop.go:14` `Run` → `:63` `agentLoop` | 19 个 agent 用例 | 90% |
| 工具调用 | ✅ 已完成 | `tool/tool.go:98` `Registry.Execute` | 9 个 tool 用例 + 11 个 builtin 用例 | 85% |
| ReAct 循环 | ✅ 已完成 | `agent/loop.go:99-123` + `:134` `executeStep` | `TestCoreAgent_ReAct_*` 3 个 | 80% |
| 权限钩子 | ⚠️ 已完成但有缺陷 | `permission/permission.go:208` + `agent/permission_bridge.go:79` | 7 个 permission 用例 + 3 个桥接用例 | 75% |

**一句话**：循环和工具是干净的，权限钩子是"结构正确、边界有洞"——两道闸门可以被合法路径绕过，取到 API Key。

---

## 1. Agent Loop

### 实现链路

```
Run(ctx, prompt)                       loop.go:14
 ├─ 空 prompt 拒绝                       :15-18
 ├─ ctx nil 兜底                         :20-22
 ├─ 网关就绪检查                         :24-29
 ├─ 单轮互斥 (running 标志)              :31-37
 ├─ goroutine + defer close(outCh)      :41-42
 ├─ panic 兜底 → EventError + running 复位 :43-54
 └─ agentLoop(ctx, prompt, outCh)       :56
```

`agentLoop` 承担的是**单轮状态机**，不是"调一次模型"：

| 阶段 | 代码 | 说明 |
|---|---|---|
| 事件通道注入 context | `:65` `withEventSink` | 让权限桥能在工具钩子里回传事件，而不需要把 channel 塞进 Registry |
| 轮次追踪 | `:67-87` | `turnID` + `defer dispatchTurnEnd`，无论成功/失败/取消都收敛 |
| 用户输入归档 | `:90-91` | 先写 Memory 再进循环，保证失败轮次也有提问记录 |
| 提示词合成 | `:95` | 每轮重新合成，长期记忆改动即时生效 |
| ReAct 驱动 | `:99-123` | `maxSteps` 默认 10（`builder.go:159`） |
| 取消检查 | `:101-107` | 每步开始前检查 `ctx.Done()` |

失败路径已覆盖：`ErrEmptyPrompt`、`ErrRunInProgress`、`ErrMaxSteps`、`ctx.Err()`、panic、网关未配置。

生命周期钩子有 6 个切点（`agent/trace.go:11-29`）：`OnTurnStart` / `OnLLMRequest` / `OnLLMResponse` / `OnToolStart` / `OnToolEnd` / `OnTurnEnd`，`main.go:60` 把 `middleware.NewLoggingMiddleware` 挂上去，内核零侵入。

### 缺口

| # | 缺口 | 证据 | 影响 |
|---|---|---|---|
| L1 | 会话不持久化 | `builder.go:156` 用进程内 `NewSlidingWindowMemory`；`agent.go:33` 无落盘字段 | 重启即失忆，`--resume` 无从实现 |
| L2 | 事件无轮次标识 | `protocol.go:116-125` 只有 `Type`，无 `TurnID/Seq` | 宿主只能靠 `messages[lastIdx]` 推断（`tui/app.go:309`） |
| L3 | 取消是硬中断 | `loop.go:101` 只在步首检查 | 已发出的流式请求靠 ctx 传播中断，无"跑完当前工具再停"的软停 |

L1/L2 是路线图阶段 2（会话运行时）的内容，不影响当前"能跑"。

---

## 2. 工具调用

### 实现链路

```
Tool 接口 (Name/Description/Schema/Execute)      tool/tool.go:13-18
Registry.Register                                 :38
Registry.Definitions → 发给模型的 tools[]          :78
Registry.Execute                                  :98
 ├─ 查找工具（不存在 → IsError 结果，不 panic）      :100-112
 ├─ PreToolUse 链（任一 error 短路）                :115-124
 ├─ ValidateArguments（required + 类型）            :131-138
 ├─ executeTool（recover → IsError）               :141-157
 └─ PostToolUse 链（可改写结果）                    :160-162
```

三个关键设计点：

1. **错误即观察，不是异常**。`Execute` 不返回 `error`，所有失败都变成 `IsError=true` 的 `ToolResult` 回灌给模型（`tool.go:93-97` 注释明确）。这是 ReAct 能自愈的前提。
2. **钩子先于参数校验**（`:114-124` vs `:131`）。权限看到的是原始调用，不会因为 JSON 畸形而被跳过——这是刻意的安全顺序，`TestRegistry_PreToolUse_SeesRawCallBeforeValidation` 守着它。
3. **流式 tool_call 增量合并正确**。`gateway/wire.go:250-269` 按 `index` 累积 `id/name/arguments`，`:272-287` 按 index 排序后一次性随 `Done` 块下发。多工具并行调用不会被粘成一条。

内置 6 个工具（`builder.go:87-98`）：`read_file` `write_file` `edit_file` `glob` `grep` `bash`，共享同一个 `WorkDirRef`，所以装配顺序无关。

### 缺口

| # | 缺口 | 证据 | 影响 |
|---|---|---|---|
| T1 | 工具是编译期注册 | `builder.go:87` 硬编码 6 个 `New*Tool` | 加 MCP/技能必须改内核发版 |
| T2 | 工具串行执行 | `loop.go:241` 单层 `for` | 一次返回 3 个独立调用时耗时线性叠加 |
| T3 | 仅 bash 有超时 | `bash.go:87`；其余工具只受 ctx 约束 | 病态 grep/glob 可能拖住整轮 |

T1 属于路线图阶段 4（能力扩展），T2/T3 是可选优化。

---

## 3. ReAct 循环

### 一步的完整时序（`executeStep`）

```
① 快照配置 + 工具定义            loop.go:135-146
② BuildContext（system + 历史）   :149      memory/sliding_window.go:57
③ OnLLMRequest 钩子               :156
④ ChatStream（流式）              :167
⑤ 消费 chunk：
     reasoning → EventReasoningDelta   :192-198
     content   → EventDelta            :199-205
     tool_calls → 累积                 :206-208
     usage     → 累加                  :209-211
⑥ OnLLMResponse 钩子              :215
⑦ assistant 消息（含 ToolCalls）入 Memory  :225-230
⑧ 无 tool_calls → finished=true   :233-235
⑨ 有 tool_calls → 逐个执行：
     dispatchToolStart              :260
     EventToolCallStart             :262
     Registry.Execute               :283
     dispatchToolEnd                :286
     Tool 结果入 Memory              :294
     EventToolCallResult            :299
⑩ 返回 finished=false，外层进入下一步
```

它满足 ReAct 的判定标准：**模型的"动作"被真实执行，执行结果作为观察进入下一轮上下文**。`TestCoreAgent_ReAct_ToolExecution` 直接验证了这一点——第二步请求的最后一条消息必须是 `RoleTool` 且 `IsError=false`，否则用例失败。

### 值得肯定的两个细节

1. **流式异常回滚**（`:183-191`）：chunk 出错时本步 assistant 消息**不入** Memory，避免历史里出现"有 tool_calls 没有 tool_result"的残缺轮次（这类残缺会让下一次请求直接 400）。
2. **取消时补齐孤儿 tool_result**（`:242-258`、`:266-280`、`:303-317`）：三条取消路径都会为剩余未执行的调用补一条 `[Execution cancelled by user]`。这不是防御性编程的洁癖，是 OpenAI 协议硬要求——`assistant.tool_calls` 必须与 `tool` 消息一一对应。

### 缺口

| # | 缺口 | 证据 | 影响 |
|---|---|---|---|
| R1 | 思考链不回灌 | `wire.go:88` 明确"reasoning_content 只进不出" | 正确（DeepSeek 回传即 400），但意味着 ReAct 的 "Thought" 只存在于展示层，上下文里只有最终文本 |
| R2 | 无显式终止信号 | `:233` 以"没有 tool_calls"判定结束 | 与主流实现一致；但模型若想"先说话再继续"无法表达 |
| R3 | 上下文只截断不压缩 | `sliding_window.go:73-121` 按条数/字符预算整轮丢弃 | 长任务会静默丢掉最早的约束，且模型不知道被丢了什么 |

R3 是路线图阶段 3 的内容。

---

## 4. 权限钩子

### 两层钩子，各管一段

| 层 | 类型 | 挂载点 | 职责 |
|---|---|---|---|
| 工具级 | `tool.PreToolUse` / `PostToolUse` | `builder.go:171` / `main.go:61` | 拦截执行、改写结果（大结果落盘） |
| 轮次级 | `agent.AgentHook` | `main.go:60` | 观测全链路，不可阻断 |

`PreToolUse` 只有 3 行签名（`tool/hook.go:16`），策略全在 `permission` 包里。Registry 不认识"权限"这个词——这个分离是干净的。

### 三道闸门

```
Evaluate(call)                                    permission.go:208
 ├─ Gate 1 硬拒绝表（正则，5 条）                  :210  → 命中即 false，无审批
 ├─ Gate 2 规则匹配                                 :215
 │    ├─ 会话信任表命中 → 放行                      :222-228
 │    ├─ autoApprove → 放行                        :231-233
 │    ├─ bash：normalize 展开包装/间接执行 → 叶子段跑危险正则
 │    │        + 重定向覆盖已有文件                   :297-323
 │    ├─ read/write/edit：路径越界 → 需审批          :325-334
 │    └─ glob/grep：直接放行                        :335-337
 └─ Gate 3 交互审批                                  :235-267
      ├─ 无 approver → 拒绝（fail-closed）           :236-239
      └─ AllowOnce / AllowSession / 其余一律拒绝      :254-267
```

`normalize.go` 的展开链（引号感知分段、剥 `env`/`nohup`/`timeout`、递归展开 `sh -c`/`eval`、命令替换与解释器 `-c` 检测）是这套闸门里最有价值的部分——`TestPermission_NormalizationPipeline` 覆盖了。

### 审批闭环（端到端）

```
Registry.Execute
  → permissionPreHook (permission_bridge.go:79)
    → Manager.Evaluate
      → bridgeApproval (:26)
        → 生成 RequestID (:32)
        → pendingPerms[reqID] = respCh (:36-38)
        → EventPermissionReq 推入事件流 (:46)
          → TUI app.go:440 收到 → 渲染卡片 → 阻塞其他输入 (chat.go:140)
            → 用户按 y/a/n/Esc (chat.go:60-141)
              → agent.RespondPermission(reqID, decision) (:62)
                → respCh <- decision
        → 等待 respCh 或 ctx.Done (:53-58)
      → AllowSession 写信任表 / AllowOnce 放行 / 其余拒绝
```

这条链是**无闭包、纯 RequestID 关联**的（`protocol.go:83-91` 的 `PermissionRequest.RequestID`），所以跨端可行——桌面端/headless 只要能消费事件流并回传决策即可。

### P0-1：`~/.tide` 整目录白名单 = 凭据可读

`fsutil.go:46-51` 把 `~/.tide` 整个目录判为"工作区内"：

```go
// ~/.tide 白名单：全局记忆与配置目录
if withinPrefix(evalBestEffort(filepath.Join(home, ".tide")), targetReal) {
    return targetReal, true
}
```

而配置文件就在 `~/.tide/config.json`（`config.DefaultConfigPath()`），里面是明文 API Key。

**复现路径**：模型调用 `read_file`，`path` 传绝对路径 `/Users/<user>/.tide/config.json` →
`SafePath` 放行（fsutil 判 inside）→ Gate 2 的 `isPathEscapingWorkspace` 也判不越界 → **自动放行，无需审批** → 密钥原文进入上下文，并可能被写进 `.tide/memory/` 或 `latest.json`。

注意这不是"需要用户点同意"的高危操作，是**静默通过**：`checkRules` 里 `read_file` 分支只在越界时才升级审批。

**修复方向**（S 级改动）：白名单从"目录级"收窄到"文件级"——允许 `~/.tide/memory/**`（长期记忆需要被读写），显式拒绝 `~/.tide/config.json` 与 `*.local.json`。更彻底的做法是直接删掉 fsutil 里的 `~/.tide` 白名单，改由 memory 包自己读写（它本来就不经过工具层）。需同步改 `fsutil_test.go:TestResolveInWorkspace_TideHomeWhitelist`。

### P0-2：bash 继承全部环境变量

`bash.go:90-97` 只设置了 `Dir` / `Stdout` / `Stderr`，**没有设置 `cmd.Env`**，因此子进程完整继承父进程环境，包括 `DEEPSEEK_API_KEY` / `GEMINI_API_KEY` / `SPARK_API_KEY`（`config.go` 支持从环境变量回退）。

**复现路径**：`bash` 执行 `env | grep -i api_key` → Gate 1 无命中、Gate 2 的危险正则也不匹配 `env`/`grep` → **自动放行** → 密钥出现在工具输出里。

**修复方向**（S 级改动）：构造最小环境白名单（`PATH` `HOME` `LANG` `TERM` `TMPDIR` `SHELL` `USER` + `git`/`go` 必需项），其余一律不传；需要透传的变量由配置显式声明。需补一条断言"`env` 输出不含 `*_API_KEY`"的用例。

### P1：未分类工具 fail-open

`checkRules` 的 `switch` 没有 `default` 分支，落到末尾 `return false, ""`（`permission.go:340`）——**未登记的工具名一律放行**。当前 6 个内置工具全部显式覆盖，所以不是活漏洞；但一旦接入 MCP 或技能（工具名运行期才知道），这条默认分支就是后门。

修复：`default` 返回 `true, "unclassified tool: <name>"`，走审批。

### 其他已确认没有问题的点

- `glob` 只遍历工作区（`glob.go:82` `WalkDir(workDirAbs)`），不接路径参数，无越界面。
- `grep` 的 `path` 参数走 `SafePath`（`grep.go:95`），沙箱有效。
- Gate 3 无 approver 时拒绝（`:236-239`），未知决策也拒绝（`:264-267`），两处都 fail-closed。
- 取消审批请求时 `bridgeApproval` 返回 `DecisionDeny`（`:56-58`），不会悬挂。

---

## 5. 四能力串联

```
用户输入
  │
  ▼
Run ──► agentLoop ──► [for step < maxSteps]
                          │
                          ▼
                     executeStep
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
     BuildContext    ChatStream      流式 chunk 解析
     (Memory)        (Gateway)       reasoning/text/tool_calls
          │               │                │
          └───────────────┴────────────────┘
                          │
                 有 tool_calls?
                    │           │
                   否           是
                    │           ▼
                    │      Registry.Execute
                    │           │
                    │      PreToolUse ──► Permission.Evaluate
                    │           │            │
                    │           │      Gate1/2/3 ──► EventPermissionReq
                    │           │            │            │
                    │           │            │         TUI y/a/n
                    │           │            ▼            │
                    │           │      放行/拒绝 ◄────────┘
                    │           │            │
                    │           │      执行工具 → PostToolUse
                    │           │            │
                    │           │      结果入 Memory + EventToolCallResult
                    │           │            │
                    │           └────► 回到 for（下一 step）
                    │
                    ▼
              EventDone + Usage
```

---

## 6. 缺口清单与修复优先级

| 优先级 | 编号 | 缺口 | 修复量 | 是否改变用户可见行为 |
|---|---|---|---|---|
| **P0** | S1 | `~/.tide` 白名单导致配置文件可读 | S | 否（除非用户依赖模型读自己配置） |
| **P0** | S2 | bash 继承全部环境变量 | S | 否（正常命令不受影响） |
| P1 | S3 | 未分类工具 fail-open | XS | 否（当前无未分类工具） |
| P1 | S4 | 无轮次标识，宿主推断轮次 | S | 否 |
| P2 | S5 | 会话不持久化 | L | 是（新增能力） |
| P2 | S6 | 上下文只截断不压缩 | M | 是（长任务行为变化） |
| P2 | S7 | 工具编译期注册 | L | 是（新增能力） |

**建议的下一步**：只做 S1 + S2 + S3，三个都是 S/XS 级、都不改变正常使用行为、都能用一条测试守住。做完这四项能力就从"能跑"变成"可信"。S4 之后的属于能力增强，等这四个确认后再排。

---

## 7. 验证方式

```bash
# 全量基线
cd /Users/apple/Code/Golang/my-agent
go build ./... && go test ./... -count=1

# 单独验证四能力
go test ./internal/agent -run 'TestCoreAgent_ReAct|TestCoreAgent_Permission' -v
go test ./internal/tool -run 'TestRegistry' -v
go test ./internal/permission -v
go test ./internal/tui -run 'TestTUI_PermissionApproval_InteractiveFlow' -v
```

手工验证审批闭环：启动 `make run`，让模型执行 `rm -rf ./tmp/x`，应弹出权限卡片，按 `n` 后模型收到拒绝观察并继续。

---

## 8. 需要你决策

- **D1** 是否授权我先修 S1 + S2 + S3（P0 凭据边界 + P1 默认放行）？三项都只改 `fsutil` / `builtin/bash` / `permission` 三处，配套改 3 个用例，不动循环与协议。
- **D2** S1 采用哪种收窄方式：**(a) 文件级白名单**（保留 `~/.tide/memory/**`，显式拒绝 `config.json`）还是 **(b) 直接删除 fsutil 的 `~/.tide` 白名单**（memory 包本就不经工具层读写，更干净但需确认没有其他调用方依赖）？
- **D3** S2 的环境变量策略：**最小白名单**（默认安全，个别工具可能因缺变量报错）还是 **黑名单剔除 `*_API_KEY`/`*_TOKEN`/`*_SECRET`**（兼容性更好，但新命名仍可能漏）？

确认后我按 S1 → S2 → S3 的顺序逐个提交，每个提交独立跑 `make verify`。
