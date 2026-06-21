## 1. Build shared prompt infrastructure

- [x] 1.1 Create `server/app/infra/prompts/` with a shared loader that supports file loading, caching, safe placeholder rendering, and missing-variable logging
- [x] 1.2 Replace direct dependencies on `server/app/prompts/__init__.py` with the new shared `infra` prompt loading entrypoints
- [x] 1.3 Add or update focused backend tests for shared prompt loading and rendering behavior

## 2. Move prompt assets to owning modules

- [x] 2.1 Create module-local prompt directories and facades for `chat`, `resource`, `path`, and `memory`
- [x] 2.2 Move existing file-backed prompt assets from `server/app/prompts/` into their owning module directories without changing intended prompt behavior
- [x] 2.3 Migrate `path` inline prompt constants and tutorial prompt templates into file-backed prompts under `server/app/path/prompts/`

## 3. Migrate business code to module prompt APIs

- [x] 3.1 Update `chat` services and agents to use the `chat` module prompt facade instead of global registry keys and direct `.format(...)`
- [x] 3.2 Update `resource` agents to use the `resource` module prompt facade instead of global registry keys
- [x] 3.3 Update `path` services and agents to use the `path` module prompt facade for planning, research, tutorial, and question-generation prompts
- [x] 3.4 Update `memory` services to use the `memory` module prompt facade instead of global registry keys

## 4. Remove old prompt wiring and verify migration

- [x] 4.1 Delete the old global prompt-content directory and obsolete registry code after all modules are migrated
- [x] 4.2 Remove dead imports, unused prompt constants, and no-longer-needed helper functions introduced by the old prompt structure
- [x] 4.3 Run backend verification for `chat`, `resource`, `path`, and `memory` prompt flows and document any required manual regression checks
