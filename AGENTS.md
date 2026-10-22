# Repository Guidelines

`tide` is a single-user terminal AI agent (Bubble Tea TUI) in Go 1.26.2+. The module path is `my-agent` (imports are `my-agent/...`) while the binary is `tide` — don't guess a GitHub-style import path. Code comments, user-facing strings, and docs are Chinese — keep new comments in Chinese.

## Architecture

Call chain: **LLM (pkg/llm) → Agent → Protocol → TUI**.

- `cmd/tide/main.go` is the sole entrypoint (what the Makefile builds/runs); it handles `update` / `--version` / `--help`, otherwise assembles the agent and starts the TUI. There is no desktop host in the tree yet.
- `pkg/llm` — 纯净独立、零外部依赖的标准 OpenAI 兼容大模型通信库（源自 HyperWeaver），仅需 BaseURL/APIKey/Model 三要素即可直连任意兼容端点与本地服务。Keep it stdlib-only: no `internal/*` imports and no new third-party modules.
- `internal/protocol` — 纯数据契约层：零依赖定义流式事件 (Event)、无闭包异步权限请求 (RequestID)、配置视图与 Token 统计，原生支持跨端与序列化；核心大模型实体类型 (Message/Request/Chunk/Usage) 零成本直绑 `pkg/llm`。
- `internal/agent` — Harness core: ReAct loop (default 10 steps, `WithMaxSteps`), system-prompt assembly, streaming events, tool pipeline. 核心直接面向 `pkg/llm`，由 `CoreAgent.UpdateConfig` 完成模型热装配。
- `internal/tool` + `internal/tool/builtin` — tool registry/hooks and builtins (`bash`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`). All builtins share one `builtin.WorkDirRef`, so assembly order never affects the sandbox root.
- `internal/fsutil` — the single implementation of workspace-boundary checks (`ResolveInWorkspace`, symlink-resolving). `SafePath` and the permission gate both forward to it; do not re-implement path checks elsewhere.
- `internal/middleware` — cross-cutting concerns: turn logging (`.tide/logs/latest.json` snapshot at turn end, `0600`; append-only `.tide/logs/agent.jsonl`) and large-result spill to `.tide/tool-results/`. `internal/agent` holds mechanism only; the host wires these in `main.go`.
- `internal/textutil` — `TruncateUTF8` for byte-safe truncation (never slice strings by bytes).
- `internal/permission` — three gates: Gate 1 regex hard-deny (only root-level `rm` is refused outright); Gate 2 command-normalization pipeline (`normalize.go`: quote-aware segmentation, unwrapping `env`/`nohup`/`timeout`, recursive `sh -c`/`eval` expansion, command-substitution and interpreter `-c` detection, redirect-target stat) — anything not statically provable escalates to approval; Gate 3 interactive approval with session trust. With no approver configured, risky calls are denied. `WithAutoApprove(true)` bypasses Gate 3 (tests/non-interactive only).
- `internal/config` — discovery order: explicit path → `./config.json` → `~/.tide/config.json`. Env: `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`. 统一由 BaseURL, APIKey, ModelName 三要素驱动，不内置厂商或别名映射，本地端点（127.0.0.1/localhost）免密直连。
- `internal/memory` — sliding window plus two-level Markdown memory under `.tide/memory/`.

README.md is user-facing and lags the code: verify claims against the source before quoting them.

## Build, Test, Run

- `make build`, `make run`, `make test` (= `go test -v ./internal/...` only — it skips `pkg/llm`), `make clean`
- `make verify` is the single pre-commit gate: gofmt check (`cmd internal pkg`) + `go vet` + `go test -race -count=1 ./...` + build. Run it before every PR.
- `make lint` runs `golangci-lint` (config in `.golangci.yml`, v2 schema). CI's lint job is `continue-on-error` + `only-new-issues`, so local `make lint` is stricter than CI; the format/vet/test/build CI jobs are hard gates.
- `go test ./...` covers `pkg/llm` and `internal/...`; use it when touching the LLM library (the Makefile target does not).
- Single test: `go test ./internal/agent -run TestName`, or `go test ./pkg/llm -run TestName`
- Tests are colocated `*_test.go` and must not require credentials — use `httptest` servers or small fakes. `internal/agent/integration_test.go` is the reference for a fake SSE gateway + `WithWorkDir(t.TempDir())`. Tests may write `test_config.json` and `.tide/memory` artifacts (both gitignored).

## Conventions

- **Code review**: every change follows `outputs/CODE_REVIEW_STANDARD.md` — change tiers T0–T3 decide whether a design doc and how many reviewers are required; severity P0–P3 decides blocking. Any P0/P1 found must become a test case, a lint rule, or a checklist entry within 48h.
- README contribution rules apply: structural changes need a design doc reviewed before code (historically under `outputs/`), and do NOT keep compatibility shims, aliases, or deprecated paths for old internal implementations — rewrite to the single correct implementation.
- Commits use Chinese `主题：描述` style, one change each, e.g. `网关扩展：接入讯飞星辰MaaS平台与动态模型路由支持` or `权限优化：重构为危险命令精准拦截与非危险命令自主放行`. Splitting one commit per logical change is enforced by review, not just convention.
- PRs: state the user-visible/architectural change, list verification commands/results (`make verify`), and attach a terminal screenshot for TUI changes. Use `.github/pull_request_template.md`.
- Never commit `config.json`, `*.local.json`, or `test_config.json`; `SaveConfig` writes files with `0600`.
- A workspace's `.tide/` directory is runtime state (turn logs, memory, spilled tool output) and is gitignored — don't edit or commit it, and don't treat it as source.
- `golangci-lint` also enforces `gofmt` + `goimports` with `local-prefixes: my-agent`, so group `my-agent/...` imports separately.
