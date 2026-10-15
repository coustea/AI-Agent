# Repository Guidelines

## Project Structure

This is a Go terminal chat application. `cmd/coustea/` contains the executable entry point; `internal/` holds the application packages: `agent/` for conversation orchestration, `config/` for JSON configuration, `gateway/` for Gemini and DeepSeek providers, and `tui/` for the Bubble Tea interface. Package tests live beside their code as `*_test.go`. `main.go` is a root-level entry point; use `cmd/coustea/` for the normal build and run workflow. `Makefile` defines common development commands.

## Build, Test, and Run

- `make build` builds `./cmd/coustea` into the local `coustea` executable.
- `make run` starts the terminal UI with `go run ./cmd/coustea`.
- `make test` runs package tests under `internal/` with verbose output.
- `go test ./...` runs tests across all Go packages, including command packages.
- `make clean` removes the executable and `test_config.json`.

Run these from the repository root. The app loads provider settings from `config.json` in the current working directory; keep real API keys out of commits.

## Style and Testing

Use standard Go formatting (`gofmt`) and idiomatic Go naming: exported identifiers use `MixedCaps`, unexported identifiers use `mixedCaps`, and package names stay short and lowercase. Keep application logic in the relevant `internal/` package and preserve the gateway boundary when adding providers. Add tests next to changed code with descriptive `TestXxx` names. Prefer `httptest` servers or small fakes for provider and agent behavior so tests do not require live credentials.

## Commits and Pull Requests

The available history contains only the initial commit (`初始化项目`), so no established commit format is visible. Use a short imperative subject that describes one change, for example `Add DeepSeek stream error handling`. A pull request should explain the user-visible or architectural change, list verification commands and results, link related issues when applicable, and include a terminal screenshot for visible TUI changes.

## Configuration and Secrets

`config.json` stores provider, model, and API key fields. Do not commit populated credentials or test fixtures containing secrets. Use mock keys and local test servers in automated tests.
