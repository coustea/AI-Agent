## Context

当前后端 prompt 体系由 [server/app/prompts/__init__.py](/Users/apple/Code/software/server/app/prompts/__init__.py) 中的全局 `PromptRegistry` 统一扫描 `app/prompts/**/*.md` 并通过字符串 key 暴露给所有模块。这个设计在项目体量较小时方便，但随着 `chat`、`resource`、`path`、`memory` 逐渐演化出独立业务边界，问题已经很明显：

- prompt 内容的归属与业务模块不一致，阅读和维护时需要跨目录跳转；
- `chat` 中仍存在 `registry.get(...).format(...)` 这类分散渲染逻辑；
- `path` 中仍有大段内联 prompt 常量和手工拼装方法，没有进入统一文件化管理；
- 全局 key 让业务代码依赖 prompt 文件命名细节，不利于重构和批量迁移。

这次重构的目标不是取消共享机制，而是把共享的范围降到“底层加载能力”。业务模块应当拥有自己的 prompt 资产、命名和 facade；`infra` 只负责通用 mechanics。

## Goals / Non-Goals

**Goals:**
- 将 prompt 内容从全局共享目录迁移到所属业务模块目录下。
- 提供一套共享的 `infra` prompt loader，统一负责文件读取、缓存、模板渲染和缺失变量日志。
- 为 `chat`、`resource`、`path`、`memory` 建立模块级 prompt facade，避免业务代码直接使用全局 key 或原始 `.format(...)`。
- 把 `path` 模块的内联 prompt 和手工 prompt 构造迁移为文件化、可复用的模块 prompt。
- 为后续模块继续新增 prompt 提供稳定、可预测的目录结构和调用约定。

**Non-Goals:**
- 不改变 prompt 文本本身的业务语义，除非迁移过程中必须做最小修正。
- 不引入远程 prompt 配置平台、数据库化 prompt 存储或运行时热更新。
- 不在本次重构中统一各模块的 prompt 文案风格，只统一管理方式和调用边界。
- 不要求前端参与改造；本次变更限定在后端 prompt 架构与相关调用点。

## Decisions

### 1. 使用“模块拥有 prompt 资产 + infra 提供共享 loader”的双层结构
- **Decision:** 新建 `server/app/infra/prompts/` 作为共享基础设施层，提供 loader / renderer；同时在 `chat`、`resource`、`path`、`memory` 下分别建立 `prompts/` 目录和模块级 prompt facade。
- **Why:** 这样既能保持一套统一的加载和日志逻辑，又能让 prompt 内容跟随领域模块自然归位。
- **Alternatives considered:**
  - 保留 `app/prompts/<module>` 目录结构，仅对外包装新 API：迁移成本低，但 prompt 内容仍由全局目录“拥有”，没有真正解决归属问题。
  - 每个模块各自实现 loader：隔离最强，但会复制缓存、渲染和错误处理逻辑，后续容易漂移。

### 2. 业务代码只调用模块 facade，不直接碰共享 loader
- **Decision:** 模块内部提供明确的调用入口，例如 `chat.prompt_manager.render_tutor_system(...)`、`path.prompt_manager.render_tutorial(...)`，业务层不得直接通过字符串 key 访问共享 loader。
- **Why:** facade 可以隐藏文件名、默认变量、上下文拼装和后续重构细节，让业务代码依赖“模块语义”而不是“prompt 文件路径”。
- **Alternatives considered:**
  - 让业务代码直接调用 `infra` loader 并传模块名与文件名：虽然能工作，但 key/filename 细节仍然散落在业务层。
  - 继续使用全局 registry，仅约定少用 `.format(...)`：约束太软，无法从结构上阻止回退。

### 3. 共享 loader 保留现有安全渲染策略，但按模块根目录实例化
- **Decision:** 复用现有基于占位符正则替换的渲染思路，避免 `str.format()` 误伤 JSON 示例；loader 接受模块 prompt 根目录路径，并可缓存该目录下的 prompt 文件内容。
- **Why:** 现有 `PromptRegistry.render()` 已解决一部分 JSON-heavy prompt 的格式化问题，这部分机制值得保留，但应从“全项目单例扫描”改为“按模块根目录加载”。
- **Alternatives considered:**
  - 恢复 `str.format()`：实现简单，但已经证明会对 prompt 中的 JSON 模板造成风险。
  - 引入 Jinja2 等模板引擎：功能更强，但当前需求只有简单变量替换，引入外部依赖和模板语法并不划算。

### 4. `path` 模块优先迁移并拆掉内联 prompt
- **Decision:** 在实现阶段优先迁移 `path`，将 [server/app/path/agents/planner.py](/Users/apple/Code/software/server/app/path/agents/planner.py:273) 的内联系统 prompt、研究提示词，以及 [server/app/path/service.py](/Users/apple/Code/software/server/app/path/service.py:788) 的教程 prompt 构造迁移到 `server/app/path/prompts/`。
- **Why:** `path` 当前是最不模块化的一块，也是最适合验证新结构是否顺手的试金石。
- **Alternatives considered:**
  - 先迁 `resource`：改动轻，但收益感不强，因为 `resource` 已经比较接近目标形态。
  - 先迁 `chat`：也可行，但 `path` 的问题更典型，更适合作为第一块整治对象。

### 5. `memory` 视为独立业务模块，而不是继续挂在“全局共享 prompts”之下
- **Decision:** `memory` prompt 文件与 facade 一并迁到 `server/app/memory/prompts/` 下。
- **Why:** `memory` 虽被多个模块使用，但它本身是独立领域能力，应该和 `chat/resource/path` 一样拥有自己的 prompt 资产。
- **Alternatives considered:**
  - 让 `memory` 继续留在全局共享目录：短期省事，但会让“模块拥有 prompt”原则出现例外，削弱整体一致性。

## Risks / Trade-offs

- **[Risk] 模块迁移过程中容易出现导入路径与 prompt 文件路径不匹配** → **Mitigation:** 每个模块增加单一 facade 入口，避免在多个业务文件里直接拼文件路径。
- **[Risk] 清理旧全局 registry 时可能遗漏调用点，导致运行时找不到 prompt** → **Mitigation:** 在实现前先通过全文检索收敛所有 `registry.get/render` 和内联 prompt 常量调用点，再分模块迁移。
- **[Risk] 模块 facade 设计过重，最后只是把简单字符串读取包了很多层** → **Mitigation:** facade 只承担三件事：命名稳定、上下文注入、共享 loader 适配；不承载额外业务逻辑。
- **[Risk] 一次性迁移所有模块可能拉高回归成本** → **Mitigation:** 按 `path -> chat -> resource -> memory -> 删除旧 registry` 的顺序渐进迁移，并在每步结束后做最小回归验证。

## Migration Plan

1. 在 `server/app/infra/prompts/` 中抽出共享 loader，并保留当前安全变量替换与日志策略。
2. 在 `chat`、`resource`、`path`、`memory` 下建立 `prompts/` 目录与模块 facade。
3. 先迁移 `path` 的内联 prompt 和手工拼装 prompt，验证新结构可覆盖复杂场景。
4. 迁移 `chat` 当前直接 `.format(...)` 的 prompt 调用，统一通过模块 facade 渲染。
5. 迁移 `resource` 和 `memory` 到模块本地 prompt 目录，仅保留底层 loader 共享。
6. 删除旧 `server/app/prompts/` 内容目录和旧全局 registry 暴露方式，清理死代码与过时导入。
7. 运行后端测试与针对 `chat/resource/path` 的最小手动回归，确认 prompt 加载、渲染与日志行为正常。

## Open Questions

- 共享 loader 是提供“每模块一个 loader 实例”还是“一个 loader 支持多根目录并按 namespace 缓存”。当前更倾向前者，因为概念更直接。
- 模块 facade 命名是否统一为 `prompt_manager.py`，还是按更轻量的 `prompts.py` 暴露。当前更倾向 `prompts.py` 或 `prompt_manager.py` 二选一保持全项目一致。
- 是否保留一个仅用于启动自检的 prompt status/debug 接口。当前不是必须项，可以在实现时根据已有调试需求决定。
