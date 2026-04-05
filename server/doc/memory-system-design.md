# 记忆管理系统 — 架构设计与实现方案

## 1. 设计决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 记忆层级 | 两层：短期(MySQL) + 长期(MySQL) | 减少外部依赖，MySQL 完全满足性能需求，事务保证数据安全 |
| 短期记忆存储 | MySQL ChatMessage 表 | 支持多会话、灵活查询、事务安全 |
| 长期记忆存储 | MySQL UserMemory 表，按轮次生成多条总结 | 多条总结共存，可追溯记忆演变过程 |
| 总结触发阈值 | 短期记忆达到 20 条消息 | 积累足够上下文后再总结，避免频繁调用 LLM |
| 长期记忆粒度 | 每达到阈值生成一条独立总结 | 保留记忆的时间线信息，方便追溯 |
| 画像更新判断 | 轻量级 LLM 调用 | 比规则判断更灵活，比完整分析更省资源 |
| Agent 状态 | 无状态，每次传入聊天记录 + 记忆 | 简化部署，所有状态由外部存储管理 |

---

## 2. 整体架构

```
┌────────────────────────────────────────────────────────────┐
│                      API 层 (router.py)                     │
│              POST /chat, GET /profile, ...                  │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│              Profile Builder Service                        │
│         协调 MemoryService + Agent + 画像更新                │
└──────────┬───────────────────────────────────┬─────────────┘
           │                                   │
┌──────────▼──────────┐             ┌──────────▼─────────────┐
│   MemoryService     │             │  LangGraph Agent        │
│                     │             │  (无状态)                │
│ ┌─────────────────┐ │             │                        │
│ │ 短期记忆 (MySQL) │ │             │  输入:                  │
│ │ ChatMessage 表   │ │◄───────────►│  - messages (短期记忆)   │
│ └─────────────────┘ │             │  - long_term_memories   │
│ ┌─────────────────┐ │             │  - current_profile      │
│ │ 长期记忆 (MySQL) │ │             │                        │
│ │ UserMemory 表    │ │             │  输出:                  │
│ └─────────────────┘ │             │  - reply                │
│ ┌─────────────────┐ │             │  - should_summarize     │
│ │ 画像 (MySQL)     │ │             └────────────────────────┘
│ │ UserProfile 表   │ │
│ └─────────────────┘ │
└─────────────────────┘
```

---

## 3. 数据模型

### 3.1 短期记忆 — MySQL ChatMessage 表

```python
class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id: int | None = Field(default=None, primary_key=True)   # 自增主键
    user_id: int = Field(index=True)                         # 关联用户
    session_id: str = Field(default="", index=True)          # 对话会话 ID
    role: str                                                 # 消息角色：user / assistant / system
    content: str                                              # 消息内容
    created_at: datetime = Field(default_factory=datetime.now, index=True)
```

### 3.2 长期记忆 — MySQL UserMemory 表

```python
class UserMemory(SQLModel, table=True):
    __tablename__ = "user_memory"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)                    # 关联用户
    session_id: str = Field(default="", index=True)     # 本次总结对应的会话 ID
    content: str                                        # LLM 总结内容
    memory_type: str                                    # knowledge/error/behavior/interest/question/answer
    dimension: str | None = None                        # 对应的画像维度
    importance: float = Field(default=0.5)              # 重要性评分 0~1
    source: str = Field(default="conversation")         # 来源模块
    source_message_count: int = Field(default=0)        # 本次总结覆盖的消息条数
    attachments: str | None = None                      # JSON 关联资源
    created_at: datetime = Field(default_factory=datetime.now)
```

### 3.3 画像 — MySQL UserProfile / UserProfileHistory 表

保持现有设计不变（见 `app/models/profile_builder.py`），包含 8 个维度：

1. `knowledge_level` — 知识水平
2. `learning_goal` — 学习目标
3. `learning_history` — 学习历史
4. `cognitive_style` — 认知风格
5. `error_pattern` — 错误模式
6. `learning_pace` — 学习节奏
7. `interest_preference` — 兴趣偏好
8. `cognitive_level` — 认知水平

---

## 4. MemoryService 接口设计

```python
class MemoryService:
    def __init__(self, session: Session):
        self.session = session  # SQLModel MySQL session

    # ─── 短期记忆（ChatMessage 表） ───

    def save_message(self, user_id: int, session_id: str, role: str, content: str) -> int:
        """存入一条消息，返回当前会话消息总数"""

    def get_recent_messages(self, user_id: int, session_id: str, limit: int | None = None) -> list[ChatMessage]:
        """获取最近 N 条消息（按时间正序），limit=None 取全部"""

    def get_message_count(self, user_id: int, session_id: str) -> int:
        """获取当前会话的消息条数"""

    def clear_short_term_memory(self, user_id: int, session_id: str) -> None:
        """删除指定会话的所有短期记忆消息"""

    def get_user_sessions(self, user_id: int) -> list[str]:
        """获取用户的所有会话 ID 列表"""

    # ─── 长期记忆（UserMemory 表） ───

    def save_long_term_memory(self, ...) -> UserMemory:
        """保存 LLM 总结到 UserMemory 表"""

    def get_long_term_memories(self, user_id: int, limit: int = 10) -> list[UserMemory]:
        """获取用户的长期记忆列表（按时间倒序）"""

    # ─── 总结触发 ───

    def should_summarize(self, user_id: int, session_id: str, threshold: int = 20) -> bool:
        """判断短期记忆是否达到总结阈值"""

    async def summarize_short_term(self, user_id, session_id, llm_summary_func) -> UserMemory | None:
        """执行短期→长期记忆的总结"""
```

---

## 5. 记忆生命周期流程

```
用户发送消息
    │
    ▼
① MemoryService.save_message()
   → 消息存入 ChatMessage 表
   → 返回消息总数 count
    │
    ▼
② MemoryService.should_summarize(count)
   → count >= 20 ?
    │
    ├── 否 → 等待更多消息
    │
    └── 是 → ③ MemoryService.summarize_short_term(llm_summary_func)
             │
             ├── a. get_recent_messages()     → 从 ChatMessage 取出全部消息
             ├── b. llm_summary_func(messages) → LLM 生成总结
             ├── c. save_long_term_memory()    → 总结存入 UserMemory 表
             └── d. clear_short_term_memory()  → 删除 ChatMessage 记录
                    │
                    ▼
             ④ judge_profile_update()
                → 轻量 LLM 判断新记忆是否需要更新画像
                → 若需要：更新 UserProfile + 记录 UserProfileHistory
```

---

## 6. 画像更新判断机制

### 触发时机
每次完成短期→长期记忆总结后触发。

### LLM 输入
- 当前 UserProfile 的 8 个维度值
- 新产生的长期记忆内容

### LLM 输出格式

```json
{
    "should_update": true,
    "dimensions_to_update": {
        "knowledge_level": "Python 中级，熟悉数据结构基础",
        "learning_goal": "掌握数据结构与算法，准备期末考试"
    },
    "reason": "用户明确表示正在学习数据结构，并提到准备考试"
}
```

### 更新逻辑
- `should_update == true`：仅更新 `dimensions_to_update` 中指定的维度（增量更新），旧值快照写入 `UserProfileHistory`
- `should_update == false`：不做任何操作

---

## 7. 无状态 Agent 设计

### Graph State

```python
class ProfileBuilderState(TypedDict):
    messages: list[BaseMessage]       # 当前对话消息（从 ChatMessage 加载）
    long_term_memories: list[str]     # 长期记忆摘要（从 UserMemory 加载）
    current_profile: dict | None      # 当前画像（从 UserProfile 加载）
    reply: str                        # Agent 回复
    user_id: int
    session_id: str
```

### 调用方式

```python
# 每次请求构造 state，graph 不保持任何内部状态
state = {
    "messages": memory_svc.get_recent_messages(user_id, session_id),
    "long_term_memories": [m.content for m in memory_svc.get_long_term_memories(user_id)],
    "current_profile": profile_dict,
    "user_id": user_id,
    "session_id": session_id,
}
result = graph.invoke(state)
```

### Graph 节点

```
chat_node          → 主对话节点：注入记忆上下文，LLM 生成回复
summarize_node     → 条件触发（消息数 >= 20）：调用 LLM 总结短期记忆
profile_judge_node → 条件触发（总结完成后）：轻量 LLM 判断画像更新
```

---

## 8. API 设计

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/v1/profile/chat` | 发送消息，Agent 回复 | 需要 |
| GET | `/api/v1/profile` | 获取当前画像 | 需要 |
| GET | `/api/v1/profile/history` | 获取画像变更历史 | 需要 |
| GET | `/api/v1/profile/memories` | 获取长期记忆列表 | 需要 |

---

## 9. 文件结构

```
server/app/
├── models/
│   ├── common.py              # ChatMessage(短期) + UserMemory(长期)
│   ├── profile_builder.py     # UserProfile, UserProfileHistory
│   └── user.py                # User
├── modules/
│   ├── memory/
│   │   ├── __init__.py
│   │   └── service.py         # MemoryService（纯 MySQL）
│   └── profile_builder/
│       ├── __init__.py
│       ├── graph.py           # [待建] LangGraph 无状态 graph
│       ├── router.py          # [待建] API 路由
│       ├── schemas.py         # [待建] 请求/响应模型
│       └── service.py         # [待建] ProfileBuilderService
└── main.py
```
