# 权限边界修复设计（S1 / S2 / S3）

> 状态：**待审核**。本文档只描述改动方案，未修改任何业务代码。
> 基线：`4125535`，工作区干净，103 个用例全绿。
> 上游文档：`outputs/CORE_CAPABILITY_AUDIT_2026-10-19.md`（缺陷编号与证据来源）。

---

## 0. 一句话结论

三个缺陷的共同形态是**静默放行**：系统看起来有沙箱和闸门，但三条路径都能不经过任何裁决直接穿透。修复的目标不是"加更多规则"，而是把这三条路径从"默认通过"改成"默认拒绝或必须显式审批"，并把判定收敛到已有的单一裁决点。

改动范围：3 个包、5 个文件、新增 1 个文件；不触碰 ReAct 循环、协议层、网关、TUI。用户可见行为只在"越界访问"这一条路径上发生变化。

---

## 1. 缺陷复核（行级证据）

### S1 — `~/.tide` 整目录在白名单内，密钥可被静默读走

```go
// internal/fsutil/fsutil.go:46-51
// ~/.tide 白名单：全局记忆与配置目录
if home, err := os.UserHomeDir(); err == nil && home != "" {
    if withinPrefix(evalBestEffort(filepath.Join(home, ".tide")), targetReal) {
        return targetReal, true
    }
}
```

穿透链（4 步，全程无审批）：

1. 模型调用 `read_file {"path":"/Users/<user>/.tide/config.json"}`。
2. `read_file.go:58` → `SafePath` → `fsutil.ResolveInWorkspace` 返回 `inside=true`。
3. `permission.go:331` `isPathEscapingWorkspace` 同样得到 `inside=true`，`checkRules` 返回 `needsApproval=false`。
4. `permission.go:216-219` 直接 `return true`。

而 `~/.tide/config.json` 的 `api_key` 字段是明文（`config.go:169`），`SaveConfig` 只保证 `0600` 权限，不影响本进程读取。

**为什么测试没抓到**：`fsutil_test.go:71` 的 `TestResolveInWorkspace_TideHomeWhitelist` 把这个行为**断言成了正确行为**，`builtin_test.go:53-64` 第 5 条同理。测试当前在保护缺陷。

### S2 — bash 子进程继承全部环境变量

```go
// internal/tool/builtin/bash.go:90-97
cmd := createShellCmd(cmdCtx, command)
setupProcessGroup(cmd)
cmd.Dir = t.workDir.Get()

var combinedBuf bytes.Buffer
cmd.Stdout = &combinedBuf
cmd.Stderr = &combinedBuf
```

`cmd.Env` 未赋值 → `os/exec` 使用 `os.Environ()`。因此 `env`、`printenv`、`echo $DEEPSEEK_API_KEY` 都能拿到密钥。

Gate 1（`permission.go:31-42`）与 Gate 2（`permission.go:71-103`）都是**命令文本正则**，`env` 不在任何危险词表内 → 自动放行。

**为什么测试没抓到**：`TestBashTool` 只验证 stdout/超时/截断，从未断言子进程环境。

### S3 — Gate 2 对未登记工具名默认放行

```go
// internal/permission/permission.go:296-341
switch call.Name {
case "bash":            ...
case "read_file", "write_file", "edit_file": ...
case "glob", "grep":    return false, ""
}
return false, ""        // ← 第 340 行：任何未登记的名字都到这里
```

当前 6 个内置工具全部显式覆盖，所以**不是活漏洞**。但它是为未来预留的后门：接 MCP / skill / subagent 后工具名在运行期才出现，任何新名字都自动获得"免审批"待遇。

**为什么测试没抓到**：没有"未知工具名"的用例。

---

## 2. 修复目标与非目标

### 目标

| 编号 | 目标 | 可验证形式 |
|---|---|---|
| G1 | 凭据文件不可被任何工具读取 | `read_file ~/.tide/config.json` 被 Gate 1 拒绝，且不弹审批 |
| G2 | `~/.tide` 不再是隐式可信区 | `read_file ~/.tide/memory/x.md` 触发 Gate 2 审批 |
| G3 | bash 子进程拿不到密钥类环境变量 | 子进程内 `env` 输出不含 `*_API_KEY` / `*_TOKEN` |
| G4 | 未登记工具默认需审批 | 未知工具名触发 approver；无 approver 时拒绝 |
| G5 | 现有 6 个工具行为不变 | 103 个既有用例中仅 2 个"保护缺陷"的用例反转，其余全绿 |

### 非目标（明确不做，避免范围蔓延）

- **不把 bash 变成沙箱**。bash 在能力上等价于"以当前用户身份执行任意程序"，任何文件级白名单对它无效。本方案只关闭"通过环境变量间接泄露"这一条，**不声称关闭 `cat ~/.tide/config.json`**。根治路径见 §9 T1。
- 不改 ReAct 循环、`protocol` 契约、网关、TUI。
- 不改审批交互模型（仍是 allow once / allow session / deny）。
- 不引入新的权限框架或策略引擎。改动全部落在已有的三道闸门上。

---

## 3. 设计原则

1. **fail-closed**：无法静态证明安全的一律升级为审批；审批通道缺失时拒绝。这与现有 `permission.go:236-239` 的既有取向一致，只是把 S3 的缺口补上。
2. **单一裁决点**：路径边界仍只由 `fsutil` 实现（`AGENTS.md` 的硬约束），`SafePath` 与 `permission` 继续转发，不新增第二份路径逻辑。
3. **机制与领域知识分离**：`builtin` 拥有"如何剥离环境变量"的机制；`config` 只提供"本程序认哪些变量名是密钥"这一领域事实。二者不互相 import。
4. **测试先改**：S1 的两条用例当前断言的是错误行为，必须先反转测试再改实现，否则改完测试会"变红"并诱导人回退。

---

## 4. S1 设计 — 收窄 `~/.tide` 白名单

### 4.1 决策：整段删除白名单，不做文件级白名单

**依据**：`~/.tide` 白名单没有任何合法消费者。全局记忆与全局配置都由内核直接用 `os` 读写，不经过工具层：

| 消费者 | 访问方式 | 是否经工具层 |
|---|---|---|
| `internal/memory/storage.go:17-23` 全局记忆目录 | `os.ReadFile` / `os.WriteFile` | 否 |
| `internal/config/config.go:182-191` 全局配置 | `os.ReadFile` / `os.WriteFile` | 否 |
| `internal/middleware/logging.go:37` 日志 | `os` 直接写 | 否 |

也就是说，这个白名单**唯一的作用**就是让模型可以通过工具直接读写 `~/.tide`。删除它不减少任何产品能力。

> 若走"文件级白名单"（保留 `~/.tide/memory/**`、显式排除 `config.json`），等于为一个不存在的需求维护一张例外表，且每加一个 `~/.tide` 下的新文件都要重新审计。**不采用**。

### 4.2 变更

**文件**：`internal/fsutil/fsutil.go`

- 删除第 46-51 行整段白名单分支。
- 修改第 12 行注释：`判定 target 是否位于 workDir 或 ~/.tide 之内` → `判定 target 是否位于 workDir 之内`。
- 函数签名与返回语义不变：`ResolveInWorkspace(workDir, target string) (abs string, inside bool)`。
- `withinPrefix` / `absClean` / `evalBestEffort` 不动。

删除后 `ResolveInWorkspace` 的语义收敛为一句可陈述的规则：**只有工作区内部算内部**。这是本次改动最大的收益——规则从"两段式例外"变成"单一条件"。

### 4.3 追加：凭据文件硬拒绝（Gate 1 扩展）

仅删除白名单只能把 `~/.tide/config.json` 从"静默放行"变成"弹审批"。但密钥文件**不该存在"用户批准后模型可读"的路径**——审批疲劳下这是必然被点"同意"的弹窗。

因此在 `fsutil` 增加一个纯判定函数：

```go
// IsCredentialPath 判定解析后的绝对路径是否属于凭据文件。
// 凭据文件对任何工具一律不可读，不提供审批通道。
func IsCredentialPath(abs string) bool
```

匹配集合（仅 `~/.tide` 下，不做范围蔓延）：

- `~/.tide/config.json`
- `~/.tide/config.local.json`
- `~/.tide/*.local.json`

`permission.go` 的 `checkHardDeny` 在 bash 分支之前插入路径检查：

```go
func (m *Manager) checkHardDeny(call protocol.ToolCall) (blocked bool, denyReason string) {
    // 凭据文件硬拒绝：任何工具、任何参数形态都不得读取
    if p := extractStringArg(call.Arguments, "path"); p != "" {
        if abs, _ := fsutil.ResolveInWorkspace(m.workDirSnapshot(), p); fsutil.IsCredentialPath(abs) {
            return true, fmt.Sprintf("blocked by Gate 1 (Hard Deny): credential file access: %s", abs)
        }
    }
    if call.Name != "bash" { return false, "" }
    // ... 原有 bash 硬拒绝逻辑不变
}
```

要点：

- 复用 `ResolveInWorkspace` 的软链解析，`ln -s ~/.tide/config.json ./cfg` 也会被解析到真实路径后命中。
- 只取 `path` 参数（`read_file` / `write_file` / `edit_file` / `grep` 都用这个键名），不猜其他键名。
- 需要新增一个 `workDirSnapshot()` 小方法（`m.mu.RLock` 读 `workDir`），因为 `checkHardDeny` 目前不持锁。这是 5 行以内的机械改动。

### 4.4 行为影响

| 场景 | 修复前 | 修复后 |
|---|---|---|
| `read_file ~/.tide/config.json` | 静默读取 | **Gate 1 拒绝**，无审批通道 |
| `read_file ~/.tide/memory/notes.md` | 静默读取 | Gate 2 审批（批准后可读） |
| `read_file <workDir>/.tide/memory/notes.md` | 允许 | 允许（仍在工作区内，不变） |
| `write_file ~/.tide/config.json` | 静默写入 | Gate 1 拒绝 |

注意最后一条：项目内的 `.tide/memory`（`memory/storage.go:26-36` 的项目记忆）不受影响，因为它位于 `workDir` 之内。

### 4.5 测试改造

**必须反转的两条（当前在保护缺陷）**：

| 文件:行 | 现状 | 改为 |
|---|---|---|
| `fsutil_test.go:71` `TestResolveInWorkspace_TideHomeWhitelist` | 断言 `~/.tide/memory/notes.md` 必须 inside | 重命名为 `TestResolveInWorkspace_TideHomeRejected`，断言 outside |
| `builtin_test.go:53-64` `TestSafePath` 第 5 条 | 断言 `SafePath` 允许 `~/.tide/memory/preferences.md` | 改为断言返回 error |

**新增用例**（`fsutil_test.go`）：

- `TestResolveInWorkspace_TideConfigRejected`：`~/.tide/config.json` → outside。
- `TestIsCredentialPath`：表驱动，覆盖 `config.json` / `config.local.json` / 任意 `*.local.json` / `memory/x.md`（否）/ 工作区内同名文件（否）。
- `TestResolveInWorkspace_TideSymlinkEscape`：`ln -s ~/.tide/config.json <workDir>/cfg` → outside（复用已有软链手法）。

**新增用例**（`permission_test.go`）：

- `TestPermission_Gate1_CredentialFileDenied`：`read_file` 指向 `~/.tide/config.json`，配置一个"永远批准"的 approver，断言 `allowed=false` 且 **approver 未被调用**。这条用例是 S1 的核心断言——硬拒绝必须绕过审批。

---

## 5. S2 设计 — bash 子进程环境变量剥离

### 5.1 决策：denylist + 领域名注入（不采用最小白名单）

| 方案 | 优点 | 缺点 | 结论 |
|---|---|---|---|
| A. 最小白名单（PATH/HOME/LANG/TMPDIR…） | 默认安全，未知变量一律不传 | 会破坏用户既有构建环境（`GOPATH`、`HTTP_PROXY`、`JAVA_HOME`、`CARGO_HOME`、各类 SDK 变量），表现为"agent 突然跑不了 `make verify`"，排查成本高 | 否 |
| B. denylist（后缀/精确/前缀） | 兼容性零损失；覆盖实际密钥命名习惯 | 理论可漏（`MYAPP_CRED`） | **是** |
| C. B + 从 `config` 注入本程序已知的密钥名 | 本程序认作密钥的变量**必然**被剥离，不依赖命名约定 | 多一个函数 | **是（推荐）** |

选 B+C 的核心理由：这是本地单用户 agent，功能可用性的权重高于理论完备性；而 C 补上了 B 最大的不确定性——"本程序自己用的密钥变量名"不再靠正则猜。

### 5.2 新增文件：`internal/tool/builtin/env.go`

```go
package builtin

// 敏感环境变量匹配规则（大小写不敏感）。
// 后缀命中：*_API_KEY / *_APIKEY / *_TOKEN / *_SECRET / *_SECRET_KEY
//           *_PASSWORD / *_PASSWD / *_CREDENTIALS / *_PRIVATE_KEY
// 精确命中：AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN
//           GH_TOKEN / GITHUB_TOKEN / NPM_TOKEN / BASH_ENV / ENV
// 前缀命中：AWS_ / OPENAI_ / ANTHROPIC_ / DEEPSEEK_ / GEMINI_ / SPARK_ / MAAS_
var sensitiveEnvSuffixes = []string{...}
var sensitiveEnvExact    = map[string]bool{...}
var sensitiveEnvPrefixes = []string{...}

// sanitizeEnv 返回剔除敏感变量后的环境变量列表。
// extra 为调用方显式声明的额外敏感变量名（来自 config.SensitiveEnvNames）。
func sanitizeEnv(environ []string, extra []string) []string
```

实现要点：

- 输入用 `os.Environ()`，逐条按第一个 `=` 切分取名字，**不解析值**（避免值里含 `=` 时误判）。
- `extra` 先并入精确匹配集。
- 保留顺序与重复项（`os/exec` 对同名变量取最后一个，保持原序语义不变）。
- 大小写不敏感：统一 `strings.ToUpper` 后比较。

**为什么必须包含 `BASH_ENV` 和 `ENV`**：`bash -c` 虽不读 `.bashrc`，但若 `BASH_ENV` 存在会在启动时 source 该文件，等于把被剥离的密钥重新加载回来。这是"剥离"逻辑自身的闭环。

### 5.3 `BashTool` 改造

**文件**：`internal/tool/builtin/bash.go`

```go
type BashTool struct {
    workDir      *WorkDirRef
    sensitiveEnv []string   // 额外敏感变量名（领域注入）
}

type BashOption func(*BashTool)

// WithSensitiveEnv 声明额外的敏感环境变量名，将在子进程中被剔除。
func WithSensitiveEnv(names ...string) BashOption

func NewBashTool(workDir *WorkDirRef, opts ...BashOption) *BashTool
```

`Execute` 中在 `cmd.Dir = ...` 之后插入一行：

```go
cmd.Env = sanitizeEnv(os.Environ(), t.sensitiveEnv)
```

其余逻辑（超时夹取、进程组、输出截断、错误包装）全部不动。

**为什么用 variadic option 而不是改签名**：现有 3 处调用（`builder.go:95` + 2 处测试）零改动即可编译；同时这是可扩展的正向设计（后续若要加 `WithEnvWhitelist` 不必再改签名），不是为了兼容旧实现而留的壳。

### 5.4 领域注入：`config.SensitiveEnvNames()`

**文件**：`internal/config/config.go`

```go
// SensitiveEnvNames 返回本程序认作密钥的环境变量名，
// 供工具层在派生子进程时剔除。
func SensitiveEnvNames() []string
```

实现：遍历 `envFallbacks`（`config.go:277-281`）收集全部 `envKeys`，返回去重切片。当前结果为：

```
DEEPSEEK_API_KEY, GEMINI_API_KEY, GOOGLE_API_KEY, SPARK_API_KEY, MAAS_API_KEY
```

这是**唯一**需要随 Provider 增加而维护的地方，且它已经在维护（新增厂商必须往 `envFallbacks` 加条目）。

### 5.5 装配点

**文件**：`internal/agent/builder.go:95`

```go
builtin.NewBashTool(a.workDirRef, builtin.WithSensitiveEnv(config.SensitiveEnvNames()...)),
```

依赖方向检查：`agent` 已依赖 `config`（`agent/config.go`），`builtin` 仍不依赖 `config`，`config` 不依赖任何内部包。**无新增跨层依赖**。

### 5.6 行为影响与边界声明

| 场景 | 修复前 | 修复后 |
|---|---|---|
| `bash: env \| grep API_KEY` | 输出真实密钥 | 无输出 |
| `bash: echo $DEEPSEEK_API_KEY` | 真实密钥 | 空 |
| `bash: make verify`（依赖 `GOPATH`/`HTTP_PROXY`） | 正常 | 正常（denylist 不误伤） |
| `bash: git push`（依赖 `HOME`/`SSH_AUTH_SOCK`） | 正常 | 正常（两者都不在 denylist） |
| `bash: cat ~/.tide/config.json` | 读到密钥 | **仍然读到** ← 见 §9 T1 |

最后一行必须在文档里写明：**S2 关闭的是"环境变量泄露"，不是"文件读取"。** 把 S2 当作凭据隔离的完整解会得出错误的安全结论。

### 5.7 测试

**新增 `TestBashTool_SensitiveEnvStripped`**（`builtin_test.go`）：

```go
t.Setenv("DEEPSEEK_API_KEY", "sk-should-not-leak")
t.Setenv("MY_CUSTOM_TOKEN", "tok-should-not-leak")
t.Setenv("SAFE_BUILD_FLAG", "keep-me")
tool := NewBashTool(NewWorkDirRef(tmpDir), WithSensitiveEnv("DEEPSEEK_API_KEY"))
out, err := tool.Execute(ctx, json.RawMessage(`{"command":"env"}`))
// 断言：不含 sk-should-not-leak / tok-should-not-leak；含 keep-me
```

三个断言缺一不可——只测"密钥不出现"无法发现"过度剥离把正常变量也删了"。

**新增 `TestSanitizeEnv`**（表驱动，纯函数，无需起进程）：覆盖后缀/精确/前缀/大小写/`=` 在值中/空 `extra`。

---

## 6. S3 设计 — Gate 2 fail-closed

### 6.1 决策：未知工具名 → 需要审批（不是直接拒绝）

| 选项 | 后果 | 结论 |
|---|---|---|
| 未知 → 直接拒绝 | 新增任何工具（含 MCP）在未登记前完全不可用，错误信息对用户不可解释 | 否 |
| 未知 → 需要审批 | 首次使用时用户看到"未登记工具 xxx"，批准一次后会话内放行；无 approver 时拒绝（既有 fail-closed 逻辑自动生效） | **是** |

### 6.2 变更

**文件**：`internal/permission/permission.go:340`

```go
    case "glob", "grep":
        // glob 与 grep 搜索默认属于安全只读操作，直接放行
        return false, ""

    default:
        // 未登记工具：无法静态判定风险，一律升级审批。
        // 无 approver 时由 Gate 3 的 fail-closed 分支拒绝。
        return true, fmt.Sprintf("unregistered tool: %s (no permission policy declared)", call.Name)
    }
```

### 6.3 行为影响

| 场景 | 修复前 | 修复后 |
|---|---|---|
| 现有 6 个工具 | 各自策略 | **完全不变**（switch 已有分支优先命中） |
| 未来新增工具（如 `mcp__github__create_issue`） | 静默免审批 | 首次使用弹审批，reason 显示"unregistered tool" |
| 无 approver 的非交互运行 + 未知工具 | 静默执行 | 拒绝并说明原因 |

### 6.4 测试

**新增 `TestPermission_Gate2_UnknownToolRequiresApproval`**：

- 子用例 1：有 approver，调用 `Name: "unknown_tool"`，断言 approver 被调用且 `Reason` 含 `unregistered tool`。
- 子用例 2：无 approver，断言 `allowed=false` 且 reason 含 `no approver configured`。
- 子用例 3（回归保护）：`glob` / `grep` 仍直接放行，**不**触发 approver。这条防止将来误把 default 分支提到前面。

### 6.5 演进预留（本次不实现）

当 H4 阶段接入 MCP 时，"switch 里加 case"会退化成新的登记负担。届时应把策略变成工具自身的声明：

```go
// 草案，不在本次范围
type PermissionPolicy int
const (
    PolicyAuto PermissionPolicy = iota  // 只读、无副作用
    PolicyAsk                            // 需审批（默认）
    PolicyDeny                           // 永不允许
)

type Tool interface {
    ...
    PermissionPolicy() PermissionPolicy
}
```

`checkRules` 的 `default` 分支改为查询注册表；查不到 → `PolicyAsk`。这样"策略随能力走"，新增工具只需在 `Name()` 旁边声明一行。

**本次先落 fail-closed 的 switch default**，因为声明式策略要动 `tool.Tool` 接口（影响 6 个内置工具 + 9 个测试），不属于"最小修复"。

---

## 7. 实施顺序

三个缺陷存在依赖：S3 是兜底，S1 是收窄，S2 独立。推荐顺序：

```
① 反转两条保护缺陷的测试（先红）
② S1 实现（删白名单 + IsCredentialPath + Gate1 扩展）→ 测试转绿
③ S3 实现（default 分支）→ 新增用例
④ S2 实现（env.go + BashTool option + config 注入）→ 新增用例
⑤ make verify 全量
```

理由：先做 ① 是为了让"删除白名单"有测试支撑，避免实现后测试变红被误判为回归。S3 成本最低（3 行）且立刻降低后续风险，放在 S2 前。S2 需要新文件与装配改动，放最后。

每一步都是独立可提交的原子变更，符合仓库"一个提交一个逻辑变更"的约定：

- `安全修复：收窄工作区边界并硬拒绝凭据文件访问`
- `权限加固：未登记工具默认升级审批`
- `安全修复：bash 子进程剔除敏感环境变量`

---

## 8. 变更清单

| 文件 | 操作 | 估算行数 | 风险 |
|---|---|---|---|
| `internal/fsutil/fsutil.go` | 删 6 行白名单 + 改 1 行注释 + 新增 `IsCredentialPath` | −4 / +18 | 中（影响所有路径裁决） |
| `internal/fsutil/fsutil_test.go` | 反转 1 例 + 新增 3 例 | +60 | 低 |
| `internal/permission/permission.go` | `checkHardDeny` 插入凭据检查 + `workDirSnapshot` + `default` 分支 | +15 | 中（闸门语义变化） |
| `internal/permission/permission_test.go` | 新增 2 例 | +70 | 低 |
| `internal/tool/builtin/env.go` | **新增** | +60 | 低 |
| `internal/tool/builtin/bash.go` | 结构体 + option + 1 行 `cmd.Env` | +18 | 低 |
| `internal/tool/builtin/builtin_test.go` | 反转 1 例 + 新增 2 例 | +55 | 低 |
| `internal/config/config.go` | 新增 `SensitiveEnvNames` | +12 | 低 |
| `internal/agent/builder.go` | 1 行装配 | +1 | 低 |

合计：生产代码 +120 行左右，测试 +185 行左右。用例数 103 → 111。

---

## 9. 验收标准

### 9.1 自动化

```bash
make verify          # gofmt + go vet + go test -race + build
```

必须满足：gofmt 无输出、vet 无告警、111 个用例全绿、`-race` 无竞争（新增的 `workDirSnapshot` 与 `sanitizeEnv` 均需无共享状态）。

### 9.2 手工验证（三条，各自对应一个缺陷）

```bash
# S1：凭据文件应被 Gate 1 拒绝，且不弹审批
tide
> 读取 ~/.tide/config.json
# 期望：工具返回 "blocked by Gate 1 (Hard Deny): credential file access: ..."

# S2：子进程环境不应含密钥
> 运行 env | grep -i api_key
# 期望：(no output)

# S3：未知工具应要求审批
# 由测试覆盖；手工难以构造，验收以 TestPermission_Gate2_UnknownToolRequiresApproval 为准
```

### 9.3 回归确认

```bash
go test ./internal/fsutil ./internal/permission ./internal/tool/... -count=1 -v
```

重点确认 `TestResolveInWorkspace_BasicBoundary`、`TestResolveInWorkspace_SymlinkEscape`、`TestPermission_Gate2_WorkspaceEscape`、`TestSafePath` 的第 1-4 条**未被误伤**。

---

## 10. 风险与回滚

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| denylist 误伤正常变量导致构建失败 | 中 | 用户体感"agent 坏了" | 只匹配后缀/精确/前缀三类；`SAFE_BUILD_FLAG` 这类正向断言用例守住；出问题可用 `WithSensitiveEnv()` 收紧或临时清空 |
| `IsCredentialPath` 漏了某个凭据文件 | 中 | 仍需审批但非硬拒 | 匹配集合集中在 `fsutil` 一处，后续扩展只改一个函数 |
| Gate 1 扩展后 `glob`/`grep` 被误拦 | 低 | 搜索功能异常 | 只检查 `path` 参数；`glob` 无 `path` 参数天然不命中；`grep` 的 `path` 在工作区内不会命中凭据集合 |
| 删除白名单破坏了某个未发现的合法用途 | 低 | 某功能读不到 `~/.tide` | §4.1 已用 grep 确认三个消费者都走 `os` 直读；若仍出现，属实现遗漏，补该消费者而非恢复白名单 |

**回滚**：三个改动互相独立，可单独 revert。`fsutil` 的删除是纯删减，回滚即恢复 6 行；`env.go` 是新增文件，回滚即删除并还原 `NewBashTool` 签名。

---

## 11. 遗留问题（本次不做，必须记录）

按严重度排序，均为本次方案**明确不覆盖**的部分：

| 编号 | 问题 | 为什么不在本次范围 | 建议归属 |
|---|---|---|---|
| **T1** | `bash: cat ~/.tide/config.json` 仍可读密钥 | 需要 shell 级文件访问分析，启发式必然可绕过（变量拼接、`base64`、子 shell）。真正的解是**让密钥不落明文盘**：`config.json` 只存非敏感项，密钥走 keyring 或仅环境变量、进程内持有 | 独立安全专项，优先级高于 H2 |
| **T2** | `bash: echo x > ~/Documents/new.txt` 可写工作区外的新文件 | `checkRules` 的 `redirectTargets` 只对"已存在文件"升级审批（`permission.go:316-321`），不存在则放行；`systemDirWritePattern` 只覆盖 `/etc`/`/usr` 等系统目录 | 与 T1 合并为"bash 写路径治理" |
| **T3** | 会话信任表按 `tool:signature` 精确匹配，粒度偏细 | `permission.go:370-381`；`bash` 的 signature 是完整命令文本，改一个空格就要重新审批。这是体验问题不是安全问题 | H3 能力池阶段一并调整 |
| **T4** | `config.json` 明文密钥 + `0600` | 文件权限在单用户本机上不构成隔离（同 uid 可读）。与 T1 同根 | 与 T1 同批 |

**T1 是本次方案最重要的诚实声明**：S1 + S2 修完后，模型仍然可以通过 bash 读到密钥。本方案把"顺手读走"（`read_file` 一个 JSON 路径）和"顺手打印"（`env`）这两条**零成本**路径关掉了，但保留了"主动构造命令"这条**有成本**的路径。这是有意的取舍：在没有 OS 级隔离的前提下，试图用正则封堵 shell 是安全剧场。

---

## 12. 待确认决策

| 编号 | 决策 | 推荐 | 备选 |
|---|---|---|---|
| **E1** | S1 是否整段删除 `~/.tide` 白名单 | **是**（§4.1 已证明无合法消费者） | 文件级白名单（保留 `memory/**`） |
| **E2** | 是否追加"凭据文件 Gate 1 硬拒绝" | **是**（否则密钥文件仍可被审批放行） | 仅靠 Gate 2 审批 |
| **E3** | S2 环境变量策略 | **denylist + `config.SensitiveEnvNames()` 注入** | 最小白名单 |
| **E4** | S3 未知工具处理 | **升级审批** | 直接拒绝 |
| **E5** | 是否接受 T1/T2 本次不修 | **接受**（§11 已说明理由） | 一并处理（范围扩大约 3 倍） |

E1–E5 确认后，我按 §7 的顺序实施，每步跑 `make verify` 并单独提交。若你希望先看某一项的完整 diff 再动手，也可以指定先从 S3（3 行）开始验证节奏。
