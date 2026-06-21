## Why

当前后端 prompt 资产虽然部分已经按 `chat`、`resource`、`memory` 分类存放，但真实的管理方式仍然是一个全局 `app/prompts` 注册中心加跨模块字符串 key 调用。`chat` 仍有直接 `.format(...)` 的调用点，`path` 仍保留大段内联 prompt，导致 prompt 内容归属不清、迁移成本高，也让路径规划这类模块难以独立演进。

现在需要把 prompt 的“内容归属”还给业务模块，同时保留一套共享的底层加载能力。这样可以在不重复实现加载、缓存、渲染和日志逻辑的前提下，让 `chat`、`resource`、`path`、`memory` 各自维护自己的 prompt 资产和模块级 API。

## What Changes

- 新增模块级 prompt 管理能力，要求 `chat`、`resource`、`path`、`memory` 各自拥有本模块的 prompt 目录与模块级 prompt facade。
- 新增 `infra` 层共享 prompt loader，统一负责 prompt 文件发现、读取、缓存、模板渲染与缺失变量日志。
- **BREAKING** 废弃 `app/prompts` 作为全局 prompt 内容归属目录，模块业务代码不再直接依赖全局字符串 key，如 `"chat/tutor_system"`。
- 将 `path` 模块中的内联 prompt 常量与手工拼装 prompt 迁移到模块 prompt 文件中。
- 将 `chat` 模块中直接对 prompt 文本调用 `.format(...)` 的做法收敛到模块 prompt facade 中。
- 保留共享底层机制，但将 prompt 内容的命名、默认上下文和渲染入口收敛到模块边界内。

## Capabilities

### New Capabilities
- `module-prompt-management`: 定义模块拥有 prompt 资产、通过共享 `infra` loader 加载和渲染 prompt 的后端架构约束。

### Modified Capabilities
- None.

## Impact

- 影响后端 `server/app/infra/`、`server/app/chat/`、`server/app/resource/`、`server/app/path/`、`server/app/memory/` 的 prompt 相关目录与调用方式。
- 需要迁移现有 prompt 文件位置，并新增模块级 facade 或 manager。
- 不引入新的外部依赖，但会调整现有 prompt 初始化与导入路径。
- 需要删除旧的全局 prompt 内容目录及不再使用的内联 prompt 常量。
