# Repository Guidelines

`tide` is a single-user terminal AI agent (Bubble Tea TUI) in Go 1.26.2+. Code comments, user-facing strings, and docs are Chinese — keep new comments in Chinese.

## Architecture

Call chain: **LLM → Gateway → Agent → Protocol → TUI (or Desktop/Wails)**.

- `cmd/tide/main.go` is the sole entrypoint (this is what the Makefile builds and runs).
- `internal/protocol` — 纯数据契约层：零依赖定义流式事件 (Event)、无闭包异步权限请求 (RequestID)、配置视图与 Token 统计，原生支持跨端与序列化。
- `internal/gateway` — Router plus four providers (`llamacpp`, `deepseek`, `gemini`, `spark` = 讯飞星辰 MaaS), all over the OpenAI Chat Completions wire protocol. Router picks by model-name prefix (`gemini*`, `deepseek*`, `spark*`, `llama*`/`local`) then falls back to the active provider. Adding a provider means touching `initProviderGateway` in `internal/gateway/router.go` and the aliases/defaults in `internal/config/config.go`; keep the gateway boundary intact.
- `internal/agent` — Harness core: ReAct loop (default 10 steps, `WithMaxSteps`), system-prompt assembly, streaming events, tool pipeline.
- `internal/tool` + `internal/tool/builtin` — tool registry/hooks and builtins (`bash`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`) with the `SafePath` workspace sandbox.
- `internal/permission` — three gates: Gate 1 hard-deny substrings for `bash`; Gate 2 regexes for destructive commands (`rm`, `git reset --hard`, `chmod`, `kill`, `curl|sh`, system-dir writes, disk tools) and workspace-escaping file paths — only risky calls need approval, safe ones pass; Gate 3 interactive approval with session trust. With no approver configured, risky calls are denied. `WithAutoApprove(true)` bypasses Gate 3 (tests/non-interactive only).
- `internal/config` — discovery order: explicit path → `./config.json` → `~/.tide/config.json`. Env fallback: `DEEPSEEK_API_KEY` → `GEMINI_API_KEY`/`GOOGLE_API_KEY` → `SPARK_API_KEY`/`MAAS_API_KEY` → llamacpp. Aliases: `llama`/`local`→llamacpp, `ds`→deepseek, `google`→gemini, `maas`/`xfyun`→spark.
- `internal/memory` — sliding window plus two-level Markdown memory under `.tide/memory/`.

README.md is user-facing and lags the code: it still lists three providers and claims every `bash` call requires confirmation. Trust the code.

## Build, Test, Run

- `make build`, `make run`, `make test` (= `go test -v ./internal/...`), `make clean`
- `go test ./...` also covers the command packages
- Single test: `go test ./internal/agent -run TestName`
- Tests must not require credentials — use `httptest` servers or small fakes, matching existing patterns. They can write `test_config.json` and `.tide/memory` artifacts (both gitignored).
- No linter config; use `gofmt` / `go fmt ./...`.

## Conventions

- README contribution rules apply: structural changes need a design doc reviewed before code (historically under `outputs/`), and do NOT keep compatibility shims, aliases, or deprecated paths for old internal implementations — rewrite to the single correct implementation.
- Commits use Chinese `主题：描述` style, one change each, e.g. `网关扩展：接入讯飞星辰MaaS平台与动态模型路由支持` or `权限优化：重构为危险命令精准拦截与非危险命令自主放行`.
- PRs: state the user-visible/architectural change, list verification commands/results (`go build ./...`, `go test ./...`), and attach a terminal screenshot for TUI changes.
- Never commit `config.json`, `*.local.json`, or `test_config.json`; `SaveConfig` writes files with `0600`.
