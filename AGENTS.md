# Repository Guidelines

## Project Structure & Module Organization
`src/` contains the Vue 3 + TypeScript frontend. Major feature areas are grouped by domain, for example `src/chat/`, `src/resource/`, `src/path/`, `src/profile/`, and `src/evaluation/`. Shared app wiring lives in `src/main.ts`, `src/router/`, `src/components/`, and `src/utils/`.

`server/` contains the FastAPI backend. Runtime code is under `server/app/`, organized by capability (`auth`, `chat`, `resource`, `path`, `evaluation`, `avatar`, `memory`, `infra`). Static files live in `public/`; generated frontend output goes to `dist/`; design and implementation notes live in `docs/` and `server/docs/`.

## Build, Test, and Development Commands
Frontend:
- `npm run dev` starts the Vite dev server.
- `npm run build` runs `vue-tsc` and produces a production build in `dist/`.
- `npm run preview` serves the built frontend locally.

Backend:
- `cd server && uv sync` installs Python dependencies from `pyproject.toml` and `uv.lock`.
- `cd server && uv run fastapi dev app/main.py` starts the API with reload.
- `cd server && uv run pytest` runs backend tests.

## Coding Style & Naming Conventions
Follow the existing style in each area instead of introducing a new formatter.

- Frontend uses TypeScript, Vue SFCs, 2-space indentation, and no semicolons.
- Vue components use `PascalCase.vue`; composables use `useXxx.ts`; API/helper modules use lowercase names such as `auth.ts` or `resource-history.ts`.
- Backend Python uses 4-space indentation, type hints, snake_case module names, and short docstrings where helpful.

No ESLint, Prettier, or Ruff config is currently committed, so validate frontend changes with `npm run build` and backend changes with `uv run pytest`.

## Testing Guidelines
Backend testing is configured with `pytest` and `pytest-asyncio`. Add new tests under `server/tests/`, mirroring `server/app/` paths when possible, and name files `test_*.py`. Prioritize service, API, and regression coverage for changed modules.

Frontend automated tests are not yet configured; for UI changes, include manual verification steps in the PR.

## Commit & Pull Request Guidelines
Recent history favors short conventional prefixes such as `feat:`, `refactor:`, and `fix:`; concise Chinese or English summaries are both already used. Prefer the format `<type>: <summary>` and keep commits focused.

PRs should describe scope, affected modules, config or schema changes, and verification performed. Include screenshots or short recordings for frontend changes, and link the related issue or design note when available.

## Security & Configuration Tips
Do not commit secrets. Keep runtime configuration in backend config files or environment variables, and review changes to `server/config.yaml`, database setup, and external model credentials carefully before merging.
