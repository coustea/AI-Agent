# Repository Guidelines

`tide` is a single-user terminal AI agent (Bubble Tea TUI) in Go 1.26.2+. Code comments, user-facing strings, and docs are Chinese — keep new comments in Chinese.

## Architecture

Call chain: **LLM (pkg/llm) → Agent → Protocol → TUI (or Desktop/Wails)**.

- `cmd/tide/main.go` is the sole entrypoint (this is what the Makefile builds and runs).
- `pkg/llm` — 纯净独立、零外部依赖的大模型调用库，支持通过 `Config` 显式传入 Provider/APIKey/BaseURL/Model 直连任意 OpenAI 兼容服务及四大预设厂商，天然支持跨项目整包复制。
- `internal/protocol` — 纯数据契约层：零依赖定义流式事件 (Event)、无闭包异步权限请求 (RequestID)、配置视图与 Token 统计，原生支持跨端与序列化；核心大模型实体类型 (Message/Request/Chunk/Usage) 零成本直绑 `pkg/llm`。
- `internal/agent` — Harness core: ReAct loop (default 10 steps, `WithMaxSteps`), system-prompt assembly, streaming events, tool pipeline. 核心直接面向 `pkg/llm`，由 `CoreAgent.UpdateConfig` 完成模型热装配。
- `internal/tool` + `internal/tool/builtin` — tool registry/hooks and builtins (`bash`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`). All builtins share one `builtin.WorkDirRef`, so assembly order never affects the sandbox root.
- `internal/fsutil` — the single implementation of workspace-boundary checks (`ResolveInWorkspace`, symlink-resolving). `SafePath` and the permission gate both forward to it; do not re-implement path checks elsewhere.
- `internal/middleware` — cross-cutting concerns: turn logging (`latest.json` snapshot at turn end, `0600`) and large-result spill. `internal/agent` holds mechanism only.
- `internal/textutil` — `TruncateUTF8` for byte-safe truncation (never slice strings by bytes).
- `internal/permission` — three gates: Gate 1 regex hard-deny (only root-level `rm` is refused outright); Gate 2 command-normalization pipeline (`normalize.go`: quote-aware segmentation, unwrapping `env`/`nohup`/`timeout`, recursive `sh -c`/`eval` expansion, command-substitution and interpreter `-c` detection, redirect-target stat) — anything not statically provable escalates to approval; Gate 3 interactive approval with session trust. With no approver configured, risky calls are denied. `WithAutoApprove(true)` bypasses Gate 3 (tests/non-interactive only).
- `internal/config` — discovery order: explicit path → `./config.json` → `~/.tide/config.json`. Env fallback: `DEEPSEEK_API_KEY` → `GEMINI_API_KEY`/`GOOGLE_API_KEY` → `SPARK_API_KEY`/`MAAS_API_KEY` → llamacpp. Aliases: `llama`/`local`→llamacpp, `ds`→deepseek, `google`→gemini, `maas`/`xfyun`→spark.
- `internal/memory` — sliding window plus two-level Markdown memory under `.tide/memory/`.

README.md is user-facing and lags the code: verify claims against the source before quoting them.

## Build, Test, Run

- `make build`, `make run`, `make test` (= `go test -v ./internal/...`), `make clean`
- `make verify` is the single pre-commit gate: gofmt check + `go vet` + `go test -race` + build. Run it before every PR.
- `make lint` runs `golangci-lint` (config in `.golangci.yml`, v2 schema; CI runs it non-blocking while legacy warnings are burned down).
- `go test ./...` also covers the command packages
- Single test: `go test ./internal/agent -run TestName`
- Tests must not require credentials — use `httptest` servers or small fakes, matching existing patterns. They can write `test_config.json` and `.tide/memory` artifacts (both gitignored).

## Conventions

- **Code review**: every change follows `outputs/CODE_REVIEW_STANDARD.md` — change tiers T0–T3 decide whether a design doc and how many reviewers are required; severity P0–P3 decides blocking. Any P0/P1 found must become a test case, a lint rule, or a checklist entry within 48h.
- README contribution rules apply: structural changes need a design doc reviewed before code (historically under `outputs/`), and do NOT keep compatibility shims, aliases, or deprecated paths for old internal implementations — rewrite to the single correct implementation.
- Commits use Chinese `主题：描述` style, one change each, e.g. `网关扩展：接入讯飞星辰MaaS平台与动态模型路由支持` or `权限优化：重构为危险命令精准拦截与非危险命令自主放行`. Splitting one commit per logical change is enforced by review, not just convention.
- PRs: state the user-visible/architectural change, list verification commands/results (`make verify`), and attach a terminal screenshot for TUI changes. Use `.github/pull_request_template.md`.
- Never commit `config.json`, `*.local.json`, or `test_config.json`; `SaveConfig` writes files with `0600`.
