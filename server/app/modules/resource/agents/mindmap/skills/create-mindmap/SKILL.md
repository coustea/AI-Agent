---
name: create-mindmap
description: Create concise Markdown mindmaps for course topics, weak-point diagnosis, review planning, exam prep, deep understanding, or practice-oriented learning. Use when Codex needs to turn a topic plus learner context (`topic`, `gap`, `need`, `extra`, profile hints) into a clean hierarchical Markdown tree, then hand that Markdown to a renderer such as `markdown_to_mindmap`.
---

# Create Mindmap

Build the mindmap as Markdown first. Then call the rendering tool with the final Markdown. Do not stop at an outline if a renderer is available.

## Follow this workflow

1. Extract the task anchors:
   - `topic`: the real root node
   - `gap`: the weak point that must be made visible in the tree
   - `need`: the learning mode that changes branch weight
   - `extra`: explicit branch requests, examples, or constraints
   - learner/profile hints: whether to add prerequisite review or advanced extension
2. Choose one main organizing spine. Do not mix multiple unrelated structures in the same level.
3. Draft a balanced tree in Markdown:
   - usually 3-5 first-level branches
   - usually 2-4 children per branch
   - usually 3-5 total levels including the root
4. Make the weak point explicit:
   - add a dedicated branch when the weakness is central
   - or inject contrast, pitfalls, bottom-layer explanation, or examples into the relevant branch
5. Merge `extra` naturally into the tree. Do not append a random catch-all branch just to satisfy it.
6. Run a final scan:
   - all nodes are short
   - sibling branches are parallel
   - no duplicate branches
   - the Markdown can be passed directly to `markdown_to_mindmap`

## Output contract

Produce Markdown that satisfies all of the following:

1. Use exactly one root heading: `# Topic`
2. Use unordered lists only: `- `
3. Use two spaces per indentation level
4. Do not use tabs for indentation
5. Do not use numbered lists, tables, blockquotes, or code fences
6. Do not add any explanation before or after the Markdown
7. Do not output prose plus Markdown in the same answer

The current renderer parses only:

- one `# ` root line
- nested `- ` list items
- indentation depth derived from leading spaces

If you add free-form prose lines, mixed bullets, or tabs, the rendered tree may lose nodes or collapse structure.

## Map `need` to structure

If `need` is one of the known modes, bias the tree accordingly:

- `review`: prioritize 知识框架, 核心概念, 关键联系, 易错点, 快速回顾
- `exam`: prioritize 高频考点, 易错点, 对比辨析, 题型思路, 快速记忆
- `deep`: prioritize 概念定义, 底层原理, 机制链路, 边界限制, 延伸拓展
- `practice`: prioritize 操作流程, 关键步骤, 示例场景, 常见错误, 实战建议

If `need` is unknown, fall back to a general-learning structure:

- 概念定义
- 核心结构
- 关键机制
- 应用场景
- 易错点或拓展

For reusable branch patterns and example skeletons, read [references/branch-patterns.md](references/branch-patterns.md).

## Handle `gap` correctly

Treat `gap` as a mandatory design constraint, not optional decoration.

- If `gap` is a misunderstood concept, add a branch such as `难点突破`, `对比辨析`, or `原理拆解`
- If `gap` is a process problem, add `步骤详解`, `常见卡点`, or `调试思路`
- If `gap` is an exam weakness, add `易错点`, `陷阱识别`, or `题型策略`
- If `gap` is empty or `无`, do not fabricate a fake weak-point branch

Prefer making the weak point teachable through:

- contrast: what it is vs what it is not
- causal chain: why it works
- prerequisite recall: what must be understood first
- error pattern: where learners usually fail

## Personalize by learner level

Use user/profile hints only when they materially improve the tree.

- If the learner is weak on foundations, add a compact `前置知识` branch
- If the learner is advanced, add a compact `进阶拓展` branch
- If the learner prefers examples, place more `示例场景` or `应用案例`
- If the learner prefers reasoning, place more `原理链路` or `因果关系`

Keep personalization secondary. The main tree should still center on the topic.

## Node-writing rules

1. Keep each node short and scan-friendly
2. Prefer noun phrases or short action phrases over full sentences
3. Keep sibling labels in the same style and granularity
4. Avoid vague labels such as `其他`, `补充`, `说明`, `相关内容`
5. Avoid repeating the same idea across branches unless the repetition is intentionally comparative

Good labels:

- 概念定义
- 核心机制
- 关键步骤
- 应用场景
- 对比辨析
- 易错点
- 题型策略
- 工程实践

Weak labels:

- 介绍一下
- 一些内容
- 更多知识
- 其他补充

## Quality bar

Before calling the renderer, verify:

1. The root topic matches the request exactly
2. The branch structure matches the learning goal implied by `need`
3. The weak point from `gap` is visible when one exists
4. The tree is balanced enough to render cleanly
5. Every branch adds learning value: understanding, recall, comparison, or application
6. The final answer is Markdown only and ready for `markdown_to_mindmap`

## Recover from common failures

If a previous attempt failed validation or rendered poorly, fix the structure before calling the renderer again.

- If the tree is too flat, convert long sibling lists into grouped branches
- If one branch is too deep, compress details into parallel summary nodes
- If labels are verbose, shorten them before retrying
- If `gap` is not visible, add one focused weak-point branch instead of scattering tiny fixes
- If `extra` caused clutter, merge it into the nearest relevant branch

## Minimal example

# 递归
- 概念定义
  - 函数自调用
  - 终止条件
- 核心结构
  - 递推关系
  - 返回过程
- 难点突破
  - 递归与循环
  - 调用栈理解
- 常见题型
  - 树遍历
  - 分治问题
- 易错点
  - 缺少出口
  - 状态混乱
