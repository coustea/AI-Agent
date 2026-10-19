# 构建期密钥注入设计（公开分发场景）

> 状态：**待审核**。本文档只描述改动方案，未修改任何构建脚本或代码。
> 基线：`4125535`，tag `v1.0.0` 已发布，本地 `dist/` 有 5 个平台产物。
> 关联文档：`outputs/SECURITY_FIX_DESIGN_2026-10-19.md`（运行时权限边界）。

---

## 0. 结论先行

**"打包时传入 API Key"这件事，代码里已经做了**——`Makefile` 支持 `SPARK_FREE_KEY` 环境变量，`release.yml` 已接 `secrets.SPARK_API_KEY`，`.gitignore` 已排除 `config.json`。仓库层面确实干净。

但它只解决了四层泄露面里的**第一层**。真正的风险不在 Git 仓库，而在**产物本身**：

> 用 `-ldflags -X` 注入的密钥是**明文字符串常量**，会原样躺在二进制里。`strings tide` 就能取出来。而 GitHub Releases 是公开下载。

实测证据（本机 `dist/tide-darwin-arm64.tar.gz` 解包后扫描，密钥已脱敏）：

| 来源 | 长度 | 是否出现在二进制中 |
|---|---|---|
| `config.api_key` | 35 | **是** |
| `providers.spark.api_key` | 35 | **是** |
| `providers.deepseek.api_key` | 35 | 否（`tail -n 1` 只取了最后一条） |

结论：**当前 `make release` 打出来的包，任何下载者都能从中提取出你的星火密钥。**

---

## 1. 现状盘点

### 1.1 已经做对的部分

| 机制 | 位置 | 评价 |
|---|---|---|
| 仓库忽略 | `.gitignore`：`config.json`、`*.local.json`、`.tide/` | ✅ 到位 |
| 编译期注入点 | `config.go:49` `var DefaultSparkAPIKey = ""` | ✅ 设计正确 |
| 构建参数 | `Makefile:5-6` `SPARK_FREE_KEY ?= ...` → `-X` | ⚠️ 有隐患，见 §1.2 |
| CI 传参 | `release.yml:47-48` `secrets.SPARK_API_KEY` / `MAAS_API_KEY` | ⚠️ 方式对，但产物公开 |
| 权限 | `SaveConfig` 写 `0600` | ✅ 但与本问题无关 |

### 1.2 三个具体隐患

**隐患 A — `Makefile:5` 会从本机配置静默提取密钥**

```make
SPARK_FREE_KEY ?= $(shell if [ -n "$$SPARK_API_KEY" ]; then echo "$$SPARK_API_KEY"; \
  elif [ -n "$$MAAS_API_KEY" ]; then echo "$$MAAS_API_KEY"; \
  else grep -o '"api_key": "[^"]*"' ~/.tide/config.json 2>/dev/null | tail -n 1 | cut -d'"' -f4; fi)
```

后果：开发者在本机执行 `make build`，会把**自己 `~/.tide/config.json` 里的 key** 悄悄打进 `./tide`。如果这个二进制被随手发给别人（或传到群里、传到 Release），key 就泄露了，而且**开发者完全不知情**——没有任何提示。

上表实测的 `IN_BINARY` 就是这么来的。

**隐患 B — 产物无扫描门禁**

CI 只验证"能编译"，从不检查"产物里有没有密钥"。这类问题一旦发生，只有等到有人 `strings` 才发现。

**隐患 C — 源码安装与二进制安装行为不一致**

`install.sh:82` 走 `go install github.com/coustea/AI-Agent/cmd/tide@latest`，这条路径**不经过 Makefile，不注入 key**。所以：

- 下载 Release 的用户：开箱即用（因为内置了 key）
- 用 `go install` 的用户：必须自己配 key

同一个版本，两条安装路径行为不同。这不是 bug，但说明"内置 key"是一个隐式的、未在文档中声明的产品契约。

---

## 2. 四层泄露面

| 层 | 载体 | 当前状态 | 风险 | 谁能拿到 |
|---|---|---|---|---|
| **L1** | Git 仓库 / 提交历史 | 已忽略 | 低 | 无（除非历史里曾经提交过） |
| **L2** | 构建命令行 / CI 日志 | `-X ...=key` 在命令行 | 中 | 同机进程、CI 日志（secrets 已屏蔽） |
| **L3** | **二进制产物** | **明文常量** | **高** | **任何下载者** |
| **L4** | 运行时落盘 | `DefaultConfig` 把 key 复制进 `cfg.APIKey` | **高** | 任何运行过该二进制的人 |

L4 的代码路径（`config.go:342-344` → `SwitchProvider:250`）：

```go
if pcfgSpark.APIKey == "" && strings.TrimSpace(DefaultSparkAPIKey) != "" {
    pcfgSpark.APIKey = strings.TrimSpace(DefaultSparkAPIKey)   // 342-344
}
...
c.APIKey = pcfg.APIKey                                          // 250
```

随后只要触发一次 `SaveConfig`，key 就以明文写进用户的 `~/.tide/config.json`。也就是说**用户不需要 `strings`，运行一次程序、打开配置文件就能看到你的 key**。

这条路径让 L3 的严重性再上一层：不是"需要一点技术手段才能提取"，而是"打开一个 JSON 文件就能看到"。

---

## 3. 关键判断：公开分发与内置密钥不可兼得

这是本文档最重要的一句话：

> **只要产物是公开可下载的，产物里就不可能有任何真实密钥。**
> 这不是实现问题，是分发模型的问题。加密、混淆、拆分常量都只是提高提取成本，不改变结论。

原因：二进制必须在本地解密才能使用密钥，而解密逻辑和密钥材料都在同一个文件里。攻击者只需要运行它，或者 hook 解密函数。业界所有"内置密钥的客户端"最终都靠**服务端鉴权**解决，而不是靠藏。

因此需要先确定分发模型：

| 模型 | 描述 | 内置密钥 | 可行性 |
|---|---|---|---|
| **A（当前）** | 公开 GitHub Releases + 内置真实上游 key | 有 | ❌ 结构性错误：key 必然泄露，且无法限流、无法按用户吊销 |
| **B（推荐）** | 公开 Releases，**不含任何密钥**；用户首次运行配置 | 无 | ✅ 唯一正确的公开分发形态 |
| **C** | 公开 Releases，内置**自建代理**的公共 token；真实上游 key 只在服务端 | 有（可吊销、可限流） | ✅ 若必须"开箱即用"，这是唯一安全解，但需要后端 |
| **D** | 私自分发（只给自己/内网），内置 key | 有 | ⚠️ 可接受，但必须有门禁防止误发布 |

---

## 4. 推荐方案：模型 B + 可选 C

### 4.1 `Makefile`：删除本地配置回退，注入必须显式

```make
# 版本与编译参数
VERSION ?= v1.0.0

# 内置密钥只接受显式传入。绝不从 ~/.tide/config.json 回退：
# 回退会让 make build 把开发者本机密钥静默打进二进制，且无任何提示。
SPARK_FREE_KEY ?=

LDFLAGS := -s -w -X my-agent/internal/config.Version=$(VERSION)

ifneq ($(strip $(SPARK_FREE_KEY)),)
  # 含空格的密钥会破坏 -ldflags 的参数解析，提前失败而不是产出坏包
  ifneq ($(words $(SPARK_FREE_KEY)),1)
    $(error SPARK_FREE_KEY 必须是单个不含空格的字符串)
  endif
  LDFLAGS += -X my-agent/internal/config.DefaultSparkAPIKey=$(SPARK_FREE_KEY)
endif
```

行为变化：

| 命令 | 修复前 | 修复后 |
|---|---|---|
| `make build`（本机有 config.json） | 静默注入本机 key | 不注入，产物不含密钥 |
| `SPARK_FREE_KEY=xxx make build` | 注入 xxx | 注入 xxx |
| `make release`（本机） | 静默注入本机 key | 不注入 |
| `make release`（CI 传 secret） | 注入 | 注入（但见 4.2） |

这一条改动**单独就能消除隐患 A**，且不依赖任何产品决策。

### 4.2 `release.yml`：移除真实密钥注入

```yaml
      - name: Build Multi-Platform Release Assets
        run: |
          sudo apt-get update && sudo apt-get install -y zip
          VERSION="${{ env.VERSION }}" make release
```

删除 `env: SPARK_API_KEY / MAAS_API_KEY` 两行。

如果坚持要保留"开箱即用"，则应改为模型 C：注入的不是上游 key，而是一个**专门用于公开分发的低权限 token**，并满足：

- 可在服务端按 token 限流（每日 N 次）
- 可随时吊销并让旧版本失效
- 泄露后损失有上限（配额封顶）

在满足这三条之前，不要注入任何真实 key。

### 4.3 新增 CI 门禁：产物密钥扫描

**`Makefile` 新增目标**：

```make
# 发布前最后一道闸门：产物中不得出现明文密钥
check-secrets:
	@echo "==> 扫描产物密钥特征..."
	@fail=0; \
	for f in tide dist/*/tide dist/*/tide.exe; do \
	  [ -f "$$f" ] || continue; \
	  if strings "$$f" | grep -aqE "(sk|ak)-[A-Za-z0-9_-]{20,}"; then \
	    echo "错误：$$f 中包含疑似 API Key"; fail=1; \
	  fi; \
	done; \
	if [ $$fail -ne 0 ]; then exit 1; fi; \
	echo "==> 未发现明文密钥"
```

**更强的断言（推荐同时加）**：CI 里用 secrets 做精确值比对——

```yaml
      - name: Assert no secret in artifacts
        if: ${{ secrets.SPARK_API_KEY != '' }}
        env:
          KEY: ${{ secrets.SPARK_API_KEY }}
        run: |
          for f in dist/*/tide dist/*/tide.exe; do
            [ -f "$f" ] || continue
            if grep -aqF "$KEY" "$f"; then
              echo "错误：$f 包含真实密钥"; exit 1
            fi
          done
```

精确比对不会误报（模式扫描可能命中 prompt 里的示例字符串），所以它能作为硬门禁；模式扫描只作为兜底告警。

`make verify` 与 `release` 都应依赖 `check-secrets`。

### 4.4 运行时：`DefaultSparkAPIKey` 为空时不预置

当前 `DefaultConfig()` 在 key 为空时本来就不会预置（`config.go:342` 有 `!= ""` 判断），**这一处不需要改**。需要确认的是：

- 首次运行、无配置文件、无环境变量时，`SwitchProvider(ProviderSpark)` 会把 spark 设为激活厂商，但 `APIKey` 为空。
- 此时用户发起对话，网关会收到空 key 的请求，返回 401。

这个错误信息对用户不友好。建议在 `cmd/tide/main.go` 启动时增加一次检查：**若激活厂商的 APIKey 为空，直接进入 `/model` 配置向导**，而不是让用户先撞一次 401。这属于产品体验改动，不在本次构建改造范围内，列为后续项。

### 4.5 首次运行引导（已有能力，无需开发）

`install.sh:146` 已经提示"首次启动输入 `/model` 可配置 API Key"。模型 B 下这条提示从"可选"变成"必选"，只需把文案从"可配置"改为"需要配置"。

---

## 5. 备选方案：模型 C（代理端点）

若产品目标是"下载即用、零配置"，正确做法是自建中转：

```
tide 二进制  ──(公共 token，可吊销)──▶  你的代理服务  ──(真实上游 key)──▶  星火/DeepSeek
```

改动点：

| 位置 | 改动 |
|---|---|
| `config.go` `DefaultSparkBaseURL` | 指向代理域名 |
| `DefaultSparkAPIKey` | 改为代理签发的公共 token（非上游 key） |
| 服务端 | 限流、按 IP/日配额、token 吊销列表 |

代价：需要一个常驻服务 + 计费监控。收益：二进制泄露的只是可吊销的公共 token，上游 key 永不落地客户端。

**本次不实施**，但如果"开箱即用"是硬需求，这是唯一可行路径，应单独立项。

---

## 6. 变更清单

| 文件 | 操作 | 风险 |
|---|---|---|
| `Makefile` | 删 `SPARK_FREE_KEY` 的 `~/.tide` 回退；加空值条件与空格校验；新增 `check-secrets`；`verify`/`release` 依赖它 | 低 |
| `.github/workflows/release.yml` | 删 `SPARK_API_KEY`/`MAAS_API_KEY` 注入；加精确断言步骤 | 低 |
| `.github/workflows/ci.yml` | `make build` 后加 `make check-secrets` | 低 |
| `install.sh` | 文案从"可配置"改为"需要配置"（模型 B） | 极低 |
| `README.md` | 补充"密钥来源"一节：三种方式（首次运行 / 环境变量 / 编译期注入）及其适用场景 | 低 |

**不需要改**：`config.go` 的 `DefaultSparkAPIKey` 变量、`applyEnvFallbacks`、`SaveConfig`。注入点设计本身是对的，问题只在"注入什么"和"注入后是否公开"。

---

## 7. 验收

```bash
# 1. 默认构建不含密钥
make clean && make build
strings tide | grep -aE "(sk|ak)-[A-Za-z0-9_-]{20,}"    # 期望无输出
make check-secrets                                      # 期望通过

# 2. 显式注入生效
SPARK_FREE_KEY=test-key-not-real make build
./tide --version                                        # 正常
make check-secrets                                      # 期望失败（test-key 不是 sk- 前缀，用精确断言验证）

# 3. 全量
make verify
```

CI 侧验收：在 PR 里故意注入一个假 key，确认 `Assert no secret in artifacts` 步骤失败。

---

## 8. 立即行动：轮换已泄露的密钥

这是本文档里唯一有时效性的一条。

`v1.0.0` 已发布。如果发布时 `secrets.SPARK_API_KEY` 已配置，那么：

1. 该 Release 的 5 个平台二进制里都含明文 key；
2. 任何人下载后可提取，或直接运行后从 `~/.tide/config.json` 读到；
3. 该 key 应视为**已泄露**。

建议动作（按顺序）：

1. 到星火控制台**吊销当前 key，签发新 key**；
2. 检查账户用量，确认是否有异常调用；
3. 用新 key 更新 GitHub Secrets；
4. 按 §4 改造后重新发布一个 patch 版本；
5. 考虑删除或标记 `v1.0.0` 的 Release 资产（已下载的无法追回，但能减少后续暴露）。

即使当时 secret 未配置（注入空串），也建议确认一次——成本很低，误判的代价很高。

---

## 9. 待确认决策

| 编号 | 决策 | 推荐 | 备选 |
|---|---|---|---|
| **K1** | 分发模型 | **B：公开 Releases 不含任何密钥** | C：自建代理（需后端）；D：私自分发 |
| **K2** | `Makefile` 是否删除 `~/.tide/config.json` 回退 | **是**（单独就能消除隐患 A） | 保留但加显式警告 |
| **K3** | 是否加 `check-secrets` 硬门禁 | **是**，精确断言 + 模式兜底 | 仅告警 |
| **K4** | 是否立即轮换已发布版本的 key | **是**（见 §8） | 先确认 secret 当时是否配置 |
| **K5** | 首次运行空 key 时是否直接进 `/model` 向导 | 是（后续项，不在本次） | 保持现状（撞 401） |

K1 是根决策，K2–K4 在 K1 选 B 的前提下都成立。若你选 C 或 D，§4.2 与 §8 的处理方式需要相应调整。

确认后我按 `Makefile` → `release.yml` → `ci.yml` → 文档的顺序改，每步跑 `make verify`。K4 的轮换需要你在星火控制台操作，我无法代劳。
