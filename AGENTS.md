# Mentorly 开发规则

@/Users/apple/.codex/RTK.md

## Eino 优先，避免重复实现

- 所有新增功能和重构，先核对 `go.mod` 中实际使用的 Eino / eino-ext 版本、官方文档和源码。框架已有且满足需求的能力，必须直接复用，不再自建同功能实现。
- Agent 运行中的消息直接使用 `schema.Message`、`schema.MessageInputPart`、`schema.ToolCall` 等官方类型，不复制一套消息协议。用户多模态输入使用 `UserInputMultiContent`，模型多模态输出使用 `AssistantGenMultiContent`，不新增对已弃用 `MultiContent` 的依赖。
- Agent 执行、工具调用、流式处理、消息拼接、Skills、上下文压缩及中间件等，优先使用 Eino 官方实现及扩展；先查现有能力再写代码，不自行实现框架已有的执行循环、调度器或压缩框架。
- 只有核实框架没有相应能力或确实不能满足需求时，才补充最小必要实现，并说明具体缺口。禁止为未来假设添加抽象层、通用框架或仅转发调用的封装。
- 数据库记录和前后端 DTO 可以保留必要的业务字段，但不要重复定义框架协议或在多层之间反复转换。转换只放在必要边界，保留恢复消息所需的工具调用关联及实际使用的内容字段。
- 框架消息字段存在，不代表所用模型和适配器支持该模态；接入前核对实际支持范围，不自行假定或模拟能力。
- 用户与会话归属、附件与消息关联、文件存储、数据库事务和 HTTP/SSE 契约属于项目业务。复用框架时必须保留这些约束，不能用模型输出代替权限校验，不能因删封装而丢失错误处理。
- 保持顺序清晰：Service 校验和会话互斥 → Harness 读取历史并装配上下文 → Service 保存用户消息 → Agent 运行 → Service 保存结果。Service 不持有 Harness 或 Agent 实例；依赖统一在 `cmd/server` 装配。
- 修改现有功能时检查所有调用方，删除已被框架实现替代的重复代码，验证编译及相关测试。不逐项测试资源真实生成效果，除非用户另行要求。

## Skills 只读约束

- 严禁任何 Agent 修改、删改或向 `internal/agent/skills/` 下的任何文件追加本地补丁（包括但不限于 `SKILL.md` 和附带脚本）。
- 宿主机运行依赖统一在 `README.md` 中声明并在部署环境中预装，不得侵入或修改官方 Skill 文件。
- 运行期 TutorAgent 对 `/skills` 与 `$SKILLS_DIR` 必须保持严格只读（文件工具层 `ErrReadOnly` + Shell 沙箱内核级只读）。

## 官方文档核对

- 涉及库、框架、SDK、API 或 CLI 的用法、配置、迁移和特定问题时，使用 Context7：先 `resolve-library-id`，再 `query-docs`；用户提供准确库 ID 时可直接查询。
- Context7 不可用时明确说明，改查官方文档及当前项目依赖源码，不凭印象宣称框架缺少能力。
- 纯业务逻辑、一般编程概念和不涉及库用法的代码审查或重构，不必调用 Context7。
