# Tide 内置免费模型能力设计（含密钥泄露合并治理）

- 文档版本：v1.0
- 日期：2026-10-19
- 基线提交：`4125535`
- 状态：**待审核，未改动任何代码**
- 关联文档：`BUILD_SECRET_DESIGN_2026-10-19.md`、`SECURITY_FIX_DESIGN_2026-10-19.md`、`ARCHITECTURE_ROADMAP_2026-10-19.md`

---

## 0. 一句话结论

> 当前所谓"内置免费模型"，实质是**把你的上游密钥编译进二进制分发给所有人**。它能用，但不可持续：泄露、无法限流、无法按用户吊销、一旦被封所有用户同时失效。
>
> 要实现"内部具备免费模型可调用"，唯一可持续的形态是**双轨**：本地推理自动发现（零密钥零成本）+ 自建代理（服务端持密钥、客户端持可吊销 token）。二者共用一套模型来源解析层，并顺带把密钥泄露、权限边界、架构越界三个旧问题一起收口。

---

## 1. 现状：免费模型是怎么"免费"的

### 1.1 实现链路（行级证据）

| 环节 | 位置 | 行为 |
|---|---|---|
| 声明内置密钥变量 | `config.go:49` | `var DefaultSparkAPIKey = ""`，注释写明"系统内置免费星火 API Key" |
| 环境变量缺失时兜底 | `config.go:291-292` | `applyEnvFallbacks` 中，spark 在无 `SPARK_API_KEY`/`MAAS_API_KEY` 时取 `DefaultSparkAPIKey` |
| 默认配置预置 | `config.go:342-343` | `DefaultConfig()` 把内置 key 写进 `pcfgSpark.APIKey` |
| 默认激活 | `config.go:355-361` | 无 DeepSeek/Gemini 密钥时 `SwitchProvider(ProviderSpark)` |
| 编译期注入 | `Makefile:5-6` | `SPARK_FREE_KEY ?= $(shell grep ... ~/.tide/config.json)` → `-ldflags -X ...DefaultSparkAPIKey=` |
| 发布注入 | `release.yml:47-48` | `secrets.SPARK_API_KEY` / `secrets.MAAS_API_KEY` |
| 落盘 | `config.go:342` → `SwitchProvider:250` | `cfg.APIKey = pcfg.APIKey`，`SaveConfig` 写进 `~/.tide/config.json` |

结论：**"免费"= 你的额度被所有下载者共享**。

### 1.2 四个后果

1. **必然泄露**：`-ldflags -X` 注入的是明文字符串常量，`strings tide | grep sk-` 直接取。已实测确认 `dist/` 产物含真实 key。
2. **无法限流**：所有请求共用同一 key，无法区分用户、无法做配额。
3. **无法吊销**：只能整体换 key，换完所有旧版本立即失效。
4. **运行即落盘**：用户跑一次程序，`~/.tide/config.json` 里就有你的 key，不需要任何技术手段。

### 1.3 已存在的本地路径（被低估的资产）

`llamacpp` provider 已具备完整能力：

- `config.go:24-26`：`DefaultLlamaCppBaseURL = "http://127.0.0.1:8080"`、`DefaultLlamaCppModel = "local-model"`
- `config.go:84-94`：`providerMeta{IsLocal: true}`
- `gateway.go:88-91`：`if cleanKey == "" && !config.IsLocalProvider(p)` → 本地 provider 允许空密钥
- `tui/config_wizard.go:19-46`：已有 `probeLlamaCpp()` 2 秒探测

**这是唯一真正零成本、零泄露、零后端的"免费模型"。** 但它现在有三个缺陷：

1. 探测写死在 TUI 里（`config_wizard.go:18` 直接 `net/http`），违反分层——健康检查属于基础设施关注点。
2. 只探测 llama.cpp 一个端点，不认 Ollama（`:11434`）、LM Studio（`:1234`）。
3. 探测结果只产出提示文案，不驱动选择——用户仍要手动切 provider。

---

## 2. 方案选型：三条路，只有两条可持续

| 路径 | 客户端持有什么 | 谁付成本 | 可吊销 | 需后端 | 判定 |
|---|---|---|---|---|---|
| **A 内置上游密钥**（现状） | 你的真实 key | 你，且无限 | ❌ | 否 | ❌ 必须废弃 |
| **B 本地推理** | 无 | 用户自己的算力 | N/A | 否 | ✅ 零风险，推荐默认 |
| **C 自建代理** | 可吊销的 device token | 你，但可配额 | ✅ | 是 | ✅ 唯一能"真内置"的形态 |
| **D BYOK 免费额度** | 用户自己的 key | 用户 | N/A | 否 | ✅ 兜底，需引导 |

**关键判断**：只要产物公开可下载，产物里就不可能有不可吊销的真实密钥。这是分发模型约束，不是实现技巧问题。加密、混淆、拆分常量都只提高提取成本。

因此目标形态是 **B + C + D 组合**，A 彻底移除。

---

## 3. 目标设计：FreeTier 三层 + 模型来源解析层

### 3.1 分层结构

```
                    ┌─────────────────────────────┐
                    │   modelroute.Resolver       │  新增：来源发现/健康/选择/降级
                    │   （唯一决策点，可测试）      │
                    └──────────────┬──────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
   ┌────▼─────┐              ┌─────▼──────┐            ┌──────▼─────┐
   │ L1 本地   │              │ L2 内置代理 │            │ L3 BYOK    │
   │ 零密钥    │              │ device token│            │ 用户密钥    │
   │ Ollama    │              │ 可吊销/配额 │            │ Spark/Gemini│
   │ llama.cpp │              │ 需部署      │            │ keyring 存储│
   │ LM Studio │              └─────────────┘            └────────────┘
   └───────────┘
```

**优先级**：显式配置 > L1 本地（探测到即用）> L2 代理 > L3 引导用户配置。

理由：本地优先是因为它零成本、零隐私外泄、零网络依赖；只有在本地不可用时才消耗你的代理配额。

### 3.2 新增包 `internal/modelroute`

**职责单一**：回答"现在能用哪个模型来源"。不持有配置、不发请求、不渲染 UI。

```go
// Package modelroute 负责模型来源的发现、健康检查与选择。
// 本包不持有配置、不执行对话，只回答"当前可用的来源是什么"。
package modelroute

// Kind 标识来源类型
type Kind int

const (
	KindLocal Kind = iota // 本地推理服务，无需鉴权
	KindProxy             // 内置代理，持有可吊销 device token
	KindBYOK              // 用户自带密钥
)

// Source 描述一个可用的模型来源
type Source struct {
	ID      string   // "local:ollama" | "local:llamacpp" | "proxy:tide" | "byok:spark"
	Kind    Kind
	BaseURL string   // 例如 "http://127.0.0.1:11434/v1"
	Model   string   // 首选模型
	Models  []string // 探测到的可用模型（本地来源）
	Latency time.Duration
}

// Probe 探测单一来源。实现必须尊重 ctx 且不阻塞超过 500ms。
type Probe interface {
	// Name 返回来源标识前缀，用于日志与去重
	Name() string
	// Probe 返回 nil, nil 表示该来源不可用（不是错误）
	Probe(ctx context.Context) (*Source, error)
}

// Resolver 并发探测全部来源并按优先级选择
type Resolver struct {
	probes  []Probe
	timeout time.Duration // 总预算，默认 1s
}

func New(probes ...Probe) *Resolver
// Discover 并发探测，返回按优先级排序的可用来源
func (r *Resolver) Discover(ctx context.Context) []Source
// Pick 返回最高优先级来源；全部不可用时返回 ErrNoSource
func (r *Resolver) Pick(ctx context.Context) (*Source, error)
```

**内置 Probe 实现**（全部走 OpenAI 兼容 `/v1/models`，只有 Ollama 需要额外适配）：

| Probe | 探测地址 | 说明 |
|---|---|---|
| `probeOllama` | `GET :11434/api/tags` | 返回 `models[].name`，需转成 OpenAI 兼容形态 |
| `probeLlamaCpp` | `GET :8080/v1/models` | 已有逻辑，从 TUI 下沉 |
| `probeLMStudio` | `GET :1234/v1/models` | 标准 OpenAI 兼容 |
| `probeProxy` | `GET {proxy}/healthz` | 内置代理可用性 |

**性能约束**：先 `net.DialTimeout("tcp", host, 300ms)` 判端口，端口不通直接跳过，不发 HTTP。并发探测，总预算 1s。启动不因此变慢。

### 3.3 L1：本地推理自动发现

**用户体验**：

```
$ tide
[就绪] 检测到本地模型：ollama/qwen2.5-coder:7b（127.0.0.1:11434，12ms）
> 帮我看下这个仓库的结构
```

**无本地模型时**：

```
$ tide
未检测到本地模型服务。
  · 安装 Ollama 后运行 `ollama pull qwen2.5-coder:7b`（约 4.7GB，永久免费）
  · 或配置免费云端额度（讯飞星辰 / Gemini，按 1 键引导）
  · 或使用内置免费通道（需联网，有配额限制）
```

**关键设计**：探测结果**不写回 config.json**。每次启动重新探测，避免"配置说本地可用但服务已停"的僵尸状态。这是有意的取舍——本地服务生命周期不受我们控制，缓存只会带来误判。

### 3.4 L2：内置免费代理（"真内置"的唯一形态）

#### 3.4.1 客户端协议

新增 provider `tide`（别名 `free`）：

```go
// config.go 新增
const (
	ProviderTide          Provider = "tide"
	DefaultTideBaseURL             = "https://free.tide.dev/v1"
	DefaultTideModel               = "spark-x2.5"
)
```

> `free.tide.dev` 为占位域名，实际由部署决定；必须支持通过 `TIDE_FREE_BASE_URL` 覆盖，便于自建与测试。

**注册（首次启动，一次性）**：

```
POST {base}/enroll
Content-Type: application/json
{
  "client_id": "<随机 UUID，存 keyring>",
  "version": "v1.0.1",
  "platform": "darwin/arm64"
}
→ 200 {"token":"<opaque，30 天>","expires_at":"...","quota":{"rpm":20,"daily_tokens":200000}}
```

**对话**：

```
POST {base}/chat/completions
Authorization: Bearer <device token>
→ SSE 透传，与现有 wire 协议完全一致
```

**为什么客户端只持 device token 而不是上游 key**：token 是**可吊销、可限额、可归因**的。泄露一个 token 只损失一个设备额度，不影响全体。

#### 3.4.2 服务端最小实现

部署形态建议 Cloudflare Worker（免费额度足够小规模使用），约 200 行：

| 端点 | 职责 |
|---|---|
| `POST /enroll` | 签发 token，写 KV（`token → {client_id, created_at, revoked:false}`） |
| `POST /chat/completions` | 校验 token → 限流 → 注入上游 key → 转发 SSE |
| `GET /healthz` | 返回 `{"ok":true,"upstream":"spark"}` |

**必须实现的三件事**：

1. **限流**：token bucket，20 RPM + 200k tokens/日/设备。超限返回 `429` 并带 `Retry-After`。
2. **吊销**：KV 里 `revoked=true` 立即生效，无需重发版本。
3. **隐私**：不记录 prompt 正文，只记 `{token_hash, tokens_in, tokens_out, ts}`。

**必须接受的两个代价**：

- 你要为所有用户承担上游成本（可通过配额控制上限）。
- 用户 prompt 经过你的服务器。**必须在 README 和首次引导中明示**，并提供关闭方式（`tide config set free.enabled=false`）。

#### 3.4.3 降级行为

代理不可用（网络/429/吊销）时，`Resolver` 自动降级到 L1；L1 也没有则提示 L3 引导。**不允许静默失败**——必须让用户看到"为什么没走代理"。

### 3.5 L3：BYOK 免费额度引导

首次启动向导提供三个选项，按"零门槛"排序：

| 选项 | 门槛 | 免费额度 |
|---|---|---|
| 本地 Ollama | 装 4.7GB 模型 | 永久免费 |
| 讯飞星辰 Spark | 注册即得 | `spark-x2.5` 免费体验 |
| Google Gemini | 需 Google 账号 | `gemini-2.5-flash` 免费层 |

### 3.6 凭据存储：keyring 化

**这是本次设计与密钥泄露问题的交汇点。**

现状：`config.json` 明文存 `api_key`（`config.go:150`），`SaveConfig` 只保证 `0600` 权限（`config.go:442+`）。`0600` 防不了同用户进程——模型自己 `read_file` 就能读。

目标：

```go
// internal/secret 新增包
package secret

// Store 抽象凭据存储。优先系统 keyring，不可用时降级为加密文件。
type Store interface {
	Get(key string) (string, error)
	Set(key, value string) error
	Delete(key string) error
}

// 实现优先级：
// 1. macOS: Keychain (security 命令或 Security.framework)
// 2. Windows: Credential Manager (syscall)
// 3. Linux: Secret Service (dbus) — 无桌面环境时降级
// 4. 降级: ~/.tide/secrets.enc（AES-GCM，密钥由机器指纹派生）
```

**config.json 只存引用，不存值**：

```json
{
  "provider": "spark",
  "providers": {
    "spark": { "base_url": "...", "model_name": "spark-x2.5", "api_key_ref": "tide:spark" }
  }
}
```

**收益**：`read_file ~/.tide/config.json` 拿不到任何密钥。S1 漏洞的实际危害从"直接泄露"降为"泄露一个引用名"。

**代价**：Linux 无桌面环境时仍需降级方案，那层加密只是提高门槛，不是绝对安全。这一点必须写进文档，不能假装解决。

---

## 4. 与既有三个问题的合并处理

本次设计与三份旧文档不是并列关系，而是**一次收敛**。

### 4.1 与 `BUILD_SECRET_DESIGN`（密钥泄露）

| 旧结论 | 本次处理 |
|---|---|
| Makefile `~/.tide/config.json` 回退必须删 | ✅ 保留，且优先级提高：**F0 阶段第一件事** |
| release.yml 移除 key 注入 | ✅ 保留 |
| 新增 `make check-secrets` | ✅ 保留，并扩展为比对 keyring + config 双来源 |
| `DefaultSparkAPIKey` 机制 | ✅ **整体删除**（`config.go:46-49`、`:291-292`、`:342-343` 三处） |
| K1 分发模型选 B（不含密钥） | ⚠️ **升级为 B+C**：B 用于公开产物，C 用于"内置免费"诉求 |

**唯一实质变化**：原来建议"公开产物不含任何密钥"，现在增加 C 轨——产物仍不含上游密钥，但含**可吊销的 device token 获取能力**。这在安全性上是等价的（token 可吊销、可限额），在体验上实现了"开箱即用"。

### 4.2 与 `SECURITY_FIX_DESIGN`（权限边界）

| 编号 | 旧方案 | 本次联动 |
|---|---|---|
| S1 `~/.tide` 白名单 | 整段删除 + 凭据文件 Gate 1 硬拒绝 | ✅ 不变，但**紧迫性下降**：keyring 化后 config.json 无密钥。仍要修，因为 `~/.tide/memory/**` 不该被工具层任意读写 |
| S2 bash 环境变量 | denylist + `SensitiveEnvNames()` | ✅ 不变。注意：keyring 化后进程内仍持有解密后的密钥，环境变量泄露面依旧存在 |
| S3 未知工具 | switch 补 default → 升级审批 | ✅ 不变，与本次无耦合 |

**结论**：S1/S2/S3 仍按原设计执行，但顺序可调——**F3（keyring）先落地会让 S1 的危害降级**，因此 S1 可以从 P0 降为 P1，与 F3 并行。

### 4.3 与 `ARCHITECTURE_ROADMAP`（架构收敛）

| 旧问题 | 本次如何顺带解决 |
|---|---|
| `tui/config_wizard.go:18` 直连 `net/http` | ✅ `modelroute` 接管探测，TUI 回归纯适配器 |
| `config` 是 586 行上帝包 | ⚠️ 部分缓解：来源选择逻辑外移。但 provider 元数据表仍在 config，完整拆分仍按原路线图阶段 1 执行 |
| `gateway → config` 反向依赖 | ⚠️ 不解决。本次新增的 `tide` provider 仍走 `config.Provider` 枚举，与原设计一致 |
| 无会话标识 | ❌ 不涉及 |

---

## 5. 分阶段实施

### 关键顺序约束

> **F0（删内置密钥）不能在 F1/F2 之前单独发布**，否则用户升级后完全无法使用。
> 必须先让替代路径可用，再撤掉旧路径。

### F1：模型来源解析层 + 本地自动发现（M）

| 步骤 | 内容 | 影响面 |
|---|---|---|
| 1 | 新增 `internal/modelroute`：`Source`/`Probe`/`Resolver` + 3 个本地 probe | 新包，约 260 行 |
| 2 | `tui/config_wizard.go` 删除 `probeLlamaCpp`，改用 `modelroute` | 删除 30 行，TUI 不再 import `net/http` |
| 3 | 启动时探测，就绪则自动选中本地来源（不写 config） | `main.go` + `builder.go` 装配 |
| 4 | 无来源时输出引导文案（三选一） | TUI 首屏 |

**用户可见变化**：装过 Ollama 的用户**零配置直接可用**。

### F2：内置免费代理（L，含服务端）

| 步骤 | 内容 |
|---|---|
| 1 | 新增 provider `tide`（`config.go` 元数据 + `IsProxy: true`） |
| 2 | `internal/modelroute/probe_proxy.go`：`GET /healthz` 探测 |
| 3 | `internal/secret` + enroll 流程（device token 存 keyring） |
| 4 | 服务端 Worker：`/enroll`、`/chat/completions`、`/healthz` |
| 5 | 429/吊销时降级到 L1 并提示原因 |

**前置条件**：你需要先决定是否承担上游成本、部署域名。

### F3：凭据 keyring 化（M）

| 步骤 | 内容 |
|---|---|
| 1 | 新增 `internal/secret`：`Store` 接口 + macOS/Windows/Linux 三实现 |
| 2 | `ProviderConfig` 新增 `APIKeyRef`，`APIKey` 标 `omitempty` 并在读取时迁移 |
| 3 | `SaveConfig` 前剥离明文，写入 keyring |
| 4 | 一次性迁移：读到旧明文 key → 写 keyring → 清空字段 |

### F0：拆除内置密钥（S，须与 F1 同批发布）

| 步骤 | 内容 |
|---|---|
| 1 | 删除 `DefaultSparkAPIKey` 变量与三处引用 |
| 2 | `Makefile` 删除 `~/.tide/config.json` 回退 |
| 3 | `release.yml` 移除 `SPARK_API_KEY`/`MAAS_API_KEY` 注入 |
| 4 | 新增 `make check-secrets`（精确值比对 + `sk-` 兜底扫描） |
| 5 | `install.sh` 文案改为"需要配置或使用本地模型" |

### 建议发布节奏

```
Release v1.1.0  = F1 + F3        （本地自动发现 + keyring，内置 key 仍在但不新增）
Release v1.2.0  = F2（若部署完成）+ F0（彻底拆除）
```

**紧急动作（与代码无关）**：`v1.0.0` / `v1.0.1` 的发布产物已含明文 key，应视为已泄露，立即轮换。

---

## 6. 测试与验收

### 6.1 新增测试

| 包 | 用例 | 断言 |
|---|---|---|
| `modelroute` | `TestResolver_Priority` | 本地可用时优先于代理 |
| `modelroute` | `TestResolver_AllDown` | 全部不可用返回 `ErrNoSource`，不 panic |
| `modelroute` | `TestProbeOllama_ParsesTags` | `httptest` 返回 Ollama 格式，正确映射模型名 |
| `modelroute` | `TestResolver_TimeoutBudget` | 慢 probe 不阻塞，总耗时 ≤ 1.5s |
| `modelroute` | `TestProbePortClosed_FastSkip` | 端口关闭时 ≤ 350ms 返回，不发 HTTP |
| `secret` | `TestStore_RoundTrip` | Set/Get/Delete 一致 |
| `secret` | `TestStore_FallbackFile` | keyring 不可用时降级，密文不可明文读 |
| `config` | `TestConfig_NoPlaintextKey` | 保存后文件不含明文 key |
| `config` | `TestConfig_MigrateLegacyKey` | 旧明文 key 迁移后字段清空、keyring 有值 |
| `config` | `TestConfig_DefaultSparkAPIKey_Removed` | 该符号不存在（编译期断言，改为删除原用例） |

### 6.2 需要改造的既有用例

| 文件:行 | 现状 | 改造 |
|---|---|---|
| `config_test.go:218` | `TestConfig_DefaultSparkAPIKey_Fallback` 断言内置 key 生效 | **删除**（随 F0 移除符号） |
| `builtin_test.go:53-64` | 断言 `~/.tide` 在白名单内 | 按 S1 方案反转 |
| `fsutil_test.go:71` | 同上 | 按 S1 方案反转 |
| `tui/*_test.go` | 可能覆盖 `probeLlamaCpp` | 迁移到 `modelroute` 包测试 |

### 6.3 验收标准

- [ ] `make verify` 全绿（gofmt + vet + `-race` + build）
- [ ] `make check-secrets` 在含内置 key 时**必然失败**（用已知串验证门禁有效）
- [ ] `strings tide | grep -aE "sk-[A-Za-z0-9_-]{16,}"` 无命中
- [ ] 安装 Ollama 后，`tide` 首次启动**无需任何配置**即可对话
- [ ] 停掉 Ollama 后，`tide` 明确提示"本地服务已停止"，不静默失败
- [ ] 代理返回 429 时，自动降级到本地并提示原因
- [ ] `~/.tide/config.json` 中不存在任何 `api_key` 明文字段
- [ ] `internal/tui` 不再 import `net/http`（`go list` 断言）

---

## 7. 待决策项

| 编号 | 决策 | 选项 | 推荐 |
|---|---|---|---|
| **F-1** | 是否接受"双轨"（本地 + 代理）而非单一路径 | 是 / 只做本地 / 只做代理 | **是**：单轨都不满足"开箱即用 + 安全" |
| **F-2** | 是否部署内置代理 | 是 / 暂缓（先只做本地） | **暂缓亦可**：F1+F3 已能消除泄露，代理是体验增强 |
| **F-3** | 代理的上游选谁 | 讯飞 Spark / Gemini free tier / 两者按负载 | 讯飞（国内直连、有免费层、已是现有 provider） |
| **F-4** | 代理配额 | 20 RPM / 200k tokens 日 | 按预期用户数调整 |
| **F-5** | keyring 不可用时的降级 | 加密文件 / 拒绝保存并每次输入 | 加密文件（否则 Linux 服务器场景不可用） |
| **F-6** | 是否接受"本地优先于代理" | 是 / 代理优先 | **是**：省你的成本，且 prompt 不出本机 |
| **F-7** | 是否与 F0 同批发布 | 是 / 分开 | **是**：否则升级即不可用 |
| **F-8** | 旧版 `v1.0.0`/`v1.0.1` 发布资产是否删除 | 删除 / 保留但轮换 | 轮换后删除，避免继续分发泄露产物 |

---

## 8. 明确不做的事

1. **不做密钥加密混淆后仍内置**。提高提取成本不等于安全，且会让人误以为已解决。
2. **不做"每次启动向服务器换临时 key"**。这与代理等价但更复杂，且临时 key 仍可被截获。
3. **不在 `modelroute` 里做模型路由/负载均衡**。本地单用户场景无此需求，属于过度设计。
4. **不缓存本地探测结果到磁盘**。服务生命周期不受控，缓存只会产生僵尸状态。
5. **不为代理做多地域/多上游故障转移**。首版单上游 + 降级到本地已足够。

---

## 9. 风险登记

| 风险 | 等级 | 缓解 |
|---|---|---|
| 代理被滥用打爆上游额度 | 高 | 设备级配额 + 吊销 + 日限额；监控异常设备 |
| 用户隐私顾虑（prompt 过代理） | 中 | 明示 + 默认本地优先 + 可关闭 |
| keyring 在无桌面 Linux 不可用 | 中 | 加密文件降级，文档说明其局限 |
| 本地模型能力弱于云端，用户失望 | 中 | 引导文案明确模型规格；推荐 7B+ coder 模型 |
| 删除内置 key 后老用户"突然不能用" | 高 | 发布说明 + 首次启动引导 + 保留一个版本的兼容提示 |
| 代理域名不可用导致全量失败 | 中 | 探测失败即降级本地，不阻塞启动 |
