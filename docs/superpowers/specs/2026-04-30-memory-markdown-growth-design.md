# Markdown-First Growth Memory Architecture Design

Date: 2026-04-30
Status: Draft for review
Scope: `server/app/memory/`, memory-facing chat context composition, and memory HTTP APIs

## Goal

Build a high-availability memory architecture that lets the chat agent become more familiar with each user over time. The system should preserve what the user said, what the user corrected, what the agent must avoid repeating, and what should continue after old chat messages are compressed.

The memory body format is Markdown-first. Long-term memory, student profile, and conversation summaries must be generated and stored as Markdown, not as LLM-produced JSON. Database metadata such as `memory_type`, `importance`, `source`, `evidence_count`, and timestamps remains available for retrieval, ranking, auditing, and API filtering.

## Product Requirements

The student profile must support conversational autonomous construction:

- Avoid traditional long forms.
- Extract profile signals from natural-language dialogue.
- Use the student's major, learning goals, learning history, and ongoing dialogue as first-class inputs.
- Build a dynamic student profile with no fewer than six dimensions.
- Required profile dimensions include knowledge foundation, cognitive style, error-prone areas, and preferences.
- Support continuous updates as the student learns and chats.

## Current State

The existing memory subsystem already stores the main content as Markdown:

- Long-term memories use `UserMemory.content_markdown`.
- Student profiles use `UserProfile.profile_markdown` and `UserProfileHistory.profile_markdown`.
- Conversation compression saves Markdown summaries as `memory_type=summary`.

The main gaps are retrieval and prompt quality:

- `summary` memories are stored but are not reliably included in future context.
- `correction` memories exist as a type but are not treated as high-priority context.
- The extraction gate mostly detects learning facts and preferences, but misses many user corrections such as "you misunderstood", "don't answer like that", or "remember that I meant X".
- Parsed importance from the extraction output is not propagated into storage, so high-value corrections do not affect ranking enough.
- The profile prompt has useful structure but does not yet satisfy the full conversational autonomous profile requirement.

## Architecture

The target architecture has five cooperating layers:

```text
ChatMessage short-term dialogue
        ↓
Markdown memory extraction
        ↓
UserMemory long-term Markdown pool
        ↓
Profile builder and conversation compressor
        ↓
Context composer for the chat agent
```

Conversation compression remains a separate lifecycle step, but its output becomes a first-class memory source for later context composition.

## Memory Types

Expand the single source of truth in `memory_types.py` to support richer behavior:

```text
preference    User's stable learning or response preferences
goal          Long-term or stage-specific learning goals
weakness      Recurring weak points and misconceptions
fact          Stable reusable facts about the user
background    Major, grade, project background, learning history
summary       Conversation compression summaries
correction    User corrections of AI answers or behavior
interaction   User's preferred interaction style
constraint    Explicit boundaries, disliked patterns, or prohibitions
strategy      Tutoring strategies proven effective for this user
```

`summary` remains generated only by compression. The fact extraction flow may produce all other types.

## Long-Term Memory Extraction

The extraction prompt should be upgraded from "fact extraction" to "growth memory extraction". It should capture facts, preferences, corrections, constraints, and effective tutoring strategies.

The LLM output remains Markdown. Each memory block should use this template:

```md
# Memory Title

类型：correction
重要度：0.9
稳定性：长期
置信度：高

## 内容
The core memory in natural language.

## 用户原意
What the user wants the agent to remember.

## AI 应遵守的规则
- What the agent should do in similar future situations.
- What the agent should avoid.

## 适用场景
When this memory should be used.

## 证据
Brief evidence from recent dialogue without copying long source text.

## 更新关系
新增 / 修正旧记忆 / 强化已有记忆.
```

Extraction rules:

- Save corrections aggressively when the user says the AI was wrong, misunderstood them, omitted something, or should behave differently.
- Save constraints when the user says not to do something or dislikes a response pattern.
- Save interaction memories when the user requests a format, tone, pacing, level of detail, or teaching style.
- Save strategy memories when a tutoring method clearly helped the user.
- Do not invent profile traits from weak evidence.
- Do not save one-off task instructions unless they reveal a stable preference or ongoing context.
- Do not output JSON or code fences.

Storage rules:

- Propagate parsed `importance` into `save_user_fact()` so high-value memories rank correctly.
- Give `correction` and `constraint` high default importance.
- Use `evidence_count` and `last_seen_at` to reinforce repeated memories.
- Merge similar Markdown memories conservatively, keeping the more informative version.

## Student Profile

The profile prompt should be upgraded to satisfy the conversational autonomous profile requirement. The generated profile must start with `# 学生画像` and use this fixed Markdown structure:

```md
# 学生画像

## 基础信息与专业背景

## 学习目标

## 学习历史

## 知识基础

## 认知风格

## 学习偏好

## 易错点与薄弱点

## 交互偏好与禁忌

## AI 纠正记录

## 当前学习状态

## 推荐辅导策略

## 最近变化

## 不确定信息
```

Profile rules:

- Build from natural-language dialogue, long-term memories, summaries, and the existing profile.
- Do not ask the user to fill a form.
- Preserve stable profile information unless newer evidence corrects it.
- Mark uncertain details explicitly under `不确定信息` instead of inventing facts.
- Record user corrections and interaction constraints in the profile so the agent can avoid repeating mistakes.
- Update the profile as learning progresses, especially goals, weak points, cognitive style, current state, and effective strategies.

## Conversation Compression

Conversation compression should become a context recovery package, not just a learning summary. The compressor should write Markdown with this structure:

```md
# 对话压缩摘要

## 本段对话核心结论

## 用户明确纠正

## 用户画像增量

## 已完成事项

## 未完成事项

## 当前学习状态

## 后续回复约束

## 可丢弃内容
```

Compression rules:

- Preserve unresolved tasks and continuation points.
- Preserve user corrections and behavior constraints.
- Preserve profile increments that may not yet have been promoted to the profile.
- Preserve learning state and weak points.
- Explicitly identify disposable content so future context stays compact.
- Save the summary before deleting old messages.
- Store as `memory_type=summary`, `source=<module>`, and `content_markdown=<summary markdown>`.

## Context Composition

The most important change is making stored memory visible to the chat agent. The context composer should inject memory in priority order:

```md
# 用户画像
Current profile Markdown.

# 必须遵守的用户规则
High-priority correction, constraint, interaction, and strategy memories.

# 当前目标与薄弱点
Goal, weakness, preference, and background memories.

# 会话压缩摘要
Recent high-value summary memories, especially unresolved tasks and response constraints.

# 最近原始对话
Latest short-term messages.
```

Retrieval requirements:

- Include `correction`, `constraint`, `interaction`, and `strategy` in default context memory retrieval.
- Include recent `summary` memories even though their source is the module name rather than `fact_agent`.
- Rank memories by type priority, importance, evidence count, and recency.
- Keep the context bounded with per-type limits.
- Prefer explicit user corrections over inferred profile information when they conflict.

## HTTP APIs

Enhance memory APIs so the system is observable and controllable:

```http
GET /api/v1/memory/profile
```

Returns the current Markdown student profile.

```http
GET /api/v1/memory/long-term?type=correction&limit=20
```

Returns Markdown long-term memories, optionally filtered by type.

```http
GET /api/v1/memory/context-preview?session_id=...
```

Returns the memory context that would be injected into the next chat turn. This is a debugging and evaluation endpoint for verifying whether the model can see profile, corrections, summaries, and recent messages.

```http
POST /api/v1/memory/extract
```

Manually triggers long-term memory extraction for a session.

```http
POST /api/v1/memory/rebuild-profile
```

Manually rebuilds the user profile from available memories and recent dialogue.

```http
POST /api/v1/memory/compress-session
```

Manually triggers conversation compression for a session.

All endpoints must preserve the existing `HttpResponse` envelope and user-scope checks.

## High-Availability Behavior

Memory processing must never block or break the main chat path:

- Extraction failures are logged and do not fail the chat response.
- Profile rebuild failures are logged and do not fail the chat response.
- Compression failures are logged and do not delete messages.
- Old messages are deleted only after the summary is saved successfully.
- Empty or malformed Markdown outputs are skipped safely.
- Code-fence wrappers around Markdown outputs are stripped.
- Existing user changes and unrelated modules are not reverted.

## Testing Plan

Backend tests should cover:

- Memory type constants include `interaction`, `constraint`, and `strategy`.
- Long-term memory extraction prompt requires Markdown and forbids JSON.
- Extraction prompt includes correction, interaction, constraint, and strategy requirements.
- Profile prompt contains all required profile dimensions.
- Compression prompt contains context recovery sections including unresolved tasks and response constraints.
- Parsed importance is passed into storage and affects saved memory importance.
- Context building includes correction and summary memories.
- Context preview endpoint returns profile, high-priority memories, summaries, and recent chat context.

Run targeted tests first:

```bash
cd server
uv run pytest tests/memory/ tests/profile/ tests/resource/test_profile_structured_fallback.py
```

Then run the broader backend suite if the changes cross API or chat context boundaries:

```bash
cd server
uv run pytest
```

## Rollout Notes

This design intentionally prioritizes final behavior over conservative compatibility. Adding new memory types changes persisted type values, but the project already stores `memory_type` as a string rather than a database enum, so no schema migration is required for the type list itself. Tests and prompts must still be updated together to keep the type constants, context retrieval, and extraction outputs aligned.
