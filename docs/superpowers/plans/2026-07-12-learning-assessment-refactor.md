# 学习效果评估重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以可审计的学习事实快照和 Markdown 报告实现手动学习效果评估，并且只更新用户的当前辅导策略，不触发画像重新评分。

**Architecture:** `evaluation` 模块负责事件采集、SQL 事实聚合、报告生成和策略定向写入。报告表保存不可变 `facts_snapshot` 与 `report_markdown`；策略保存在 `UserProfile`，由独立接口读取。新的一级学习评估页展示数据图表和 Markdown，个人中心只展示策略摘要与入口。

**Tech Stack:** Vue 3、TypeScript、Vite、FastAPI、SQLModel、PostgreSQL JSONB、Pydantic、现有 LLM 基础设施、pytest。

**Read first:** [设计规格](../specs/2026-07-12-learning-assessment-design.md)。这是破坏式重构：删除旧周摘要、旧汇总接口与个人中心旧看板；不做兼容层。`resource` 与 `path` 的业务记录、详情页和模型必须保持分离。

---

## 文件结构

| 路径 | 责任 |
| --- | --- |
| `server/app/infra/models.py` | `UserProfile` 策略字段、报告/事件/会话 SQLModel 与注册 |
| `server/init_schema.sql`、`server/migrations/20260712_learning_assessment_refactor.sql` | 全新初始化和已有数据库的同一 schema |
| `server/app/evaluation/request.py`、`response.py` | 严格请求与 API 响应契约 |
| `server/app/evaluation/facts.py` | 只读 SQL 事实聚合和快照类型 |
| `server/app/evaluation/reporting.py`、`prompts/learning_assessment.md` | Markdown 报告契约、LLM 调用与校验 |
| `server/app/evaluation/service.py`、`api.py` | 幂等采集、报告事务、策略定向更新、HTTP 端点 |
| `server/tests/evaluation/test_learning_assessment_*.py` | 聚合、服务、API 回归测试 |
| `src/features/learning-assessment/*` | 报告页、图表适配、API 和类型 |
| `src/features/evaluation/*` | 仅保留学习事件/会话采集客户端，删除旧摘要类型/API |
| `src/features/profile/views/Profile.vue` | 删除旧评估看板，仅保留策略摘要入口 |

### Task 1: 建立迁移、模型与策略的不变式

**Files:**
- Create: `server/migrations/20260712_learning_assessment_refactor.sql`
- Modify: `server/init_schema.sql`
- Modify: `server/app/infra/models.py:345-630,867+`
- Create: `server/tests/evaluation/test_learning_assessment_models.py`

- [ ] **Step 1: 写出失败的模型与迁移契约测试。**

```python
def test_assessment_report_has_markdown_not_json_report_content():
    fields = LearningAssessmentReport.model_fields
    assert "facts_snapshot" in fields
    assert "report_markdown" in fields
    assert "report_content" not in fields

def test_user_profile_strategy_fields_do_not_replace_score_fields():
    fields = UserProfile.model_fields
    assert {"guidance_strategy", "guidance_updated_at", "last_assessment_report_id"} <= set(fields)
    assert {"overall_score", "scored_at"} <= set(fields)
```

- [ ] **Step 2: 运行测试，确认因模型不存在失败。**

Run: `rtk cd server && uv run pytest tests/evaluation/test_learning_assessment_models.py -q`

Expected: FAIL，提示 `LearningAssessmentReport` 或字段尚不存在。

- [ ] **Step 3: 实现模型和迁移。**

在 `models.py` 新建 `LearningAssessmentReport`，包含 `user_id`、`range_days`、窗口、`status`、`facts_snapshot: dict | None`、`report_markdown: str | None`、生成/失败/时间字段。将其加入 `REGISTERED_MODELS`。给 `UserProfile` 添加：

```python
guidance_strategy: dict = Field(default_factory=dict, sa_type=JSONB)
guidance_updated_at: datetime | None = Field(default=None)
last_assessment_report_id: int | None = Field(default=None, foreign_key="learning_assessment_reports.id")
```

迁移必须：回填 `learning_events.occurred_at = created_at`；增加 `client_event_id` 与 `learning_sessions.client_session_id`；建立用户内部分唯一幂等索引、单用户 `generating` 部分唯一索引和报告历史索引；创建报告表；删除 `weekly_learning_digests`。`init_schema.sql` 写出相同的最终状态，不能只依赖迁移。

- [ ] **Step 4: 将事件与会话约束写入模型。**

```python
class LearningEvent(SQLModel, table=True):
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    client_event_id: str | None = Field(default=None, max_length=64)

class LearningSession(SQLModel, table=True):
    client_session_id: str | None = Field(default=None, max_length=64)
```

在 SQL 中对报告 `range_days IN (7, 14, 30)`、合法状态、窗口顺序、`ready` 行同时有快照与 Markdown、`failed` 行有失败码加 `CHECK`。用 `WHERE client_event_id IS NOT NULL` 和 `WHERE status = 'generating'` 创建部分唯一索引。

- [ ] **Step 5: 运行测试并检查迁移。**

Run: `rtk cd server && uv run pytest tests/evaluation/test_learning_assessment_models.py -q && rtk rg -n "report_content|weekly_learning_digests" app/infra/models.py ../init_schema.sql migrations/20260712_learning_assessment_refactor.sql`

Expected: 测试 PASS；只有迁移中的显式 `DROP` 可提及旧表，最终 schema 不含 `report_content`。

- [ ] **Step 6: 提交。**

```bash
git add server/app/infra/models.py server/init_schema.sql server/migrations/20260712_learning_assessment_refactor.sql server/tests/evaluation/test_learning_assessment_models.py
git commit -m "refactor: add learning assessment persistence"
```

### Task 2: 规范采集请求并实现幂等写入

**Files:**
- Modify: `server/app/evaluation/request.py`
- Modify: `server/app/evaluation/service.py`
- Modify: `server/app/evaluation/api.py`
- Modify: `server/tests/evaluation/test_evaluation_service.py`
- Create: `server/tests/evaluation/test_learning_assessment_events_api.py`

- [ ] **Step 1: 写失败测试，锁定事件字典、必填元数据与幂等。**

```python
async def test_duplicate_client_event_returns_original_row(session, user):
    payload = LearningEventCreate(
        module="quiz", event_type="quiz_submitted", client_event_id="evt-1",
        event_metadata={"is_correct": True, "attempt_index": 1},
    )
    first = await service.record_event(session, user.id, payload)
    second = await service.record_event(session, user.id, payload)
    assert second.id == first.id

def test_quiz_event_requires_correctness_metadata():
    with pytest.raises(ValidationError):
        LearningEventCreate(module="quiz", event_type="quiz_submitted")
```

- [ ] **Step 2: 运行新测试。**

Run: `rtk cd server && uv run pytest tests/evaluation/test_learning_assessment_events_api.py tests/evaluation/test_evaluation_service.py -q`

Expected: FAIL，现有请求类型允许缺失答题事实且服务每次都插入。

- [ ] **Step 3: 收紧请求模式并删除旧的心跳/反馈文本依赖。**

使用 `Literal` 定义模块和固定事件类型；增加 `client_event_id`、`occurred_at`、`client_session_id`。用 `model_validator(mode="after")` 强制：`quiz_submitted` 与 `path_quiz_answered` 含布尔 `is_correct`；`resource_feedback` 含枚举 `helpful|not_helpful`；时长仅接受 1 至 14,400 秒。不要把自然语言反馈、答题文本或聊天内容复制到评估事件。

- [ ] **Step 4: 实现幂等查询后插入。**

```python
existing = await session.scalar(
    select(LearningEvent).where(
        LearningEvent.user_id == user_id,
        LearningEvent.client_event_id == payload.client_event_id,
    )
)
if existing is not None:
    return existing
event = LearningEvent(user_id=user_id, **payload.model_dump())
session.add(event)
await session.commit()
await session.refresh(event)
return event
```

会话按 `client_session_id` 使用等价逻辑。捕获唯一约束冲突后回滚并重新查询同一键，避免并发重复。

- [ ] **Step 5: 将 API 响应明确为 `{ id, deduplicated }`。**

保留 `POST /evaluation/events` 和 `POST /evaluation/sessions` 路径，但删除旧汇总读接口。路径专属 `POST /path-plan/{path_id}/events` 的适配必须仍把路径 ID 写进事件，而不是改为全局报告 API。

- [ ] **Step 6: 运行测试。**

Run: `rtk cd server && uv run pytest tests/evaluation/test_evaluation_service.py tests/evaluation/test_learning_assessment_events_api.py tests/path/test_path_api.py -q`

Expected: PASS。

- [ ] **Step 7: 提交。**

```bash
git add server/app/evaluation/request.py server/app/evaluation/service.py server/app/evaluation/api.py server/tests/evaluation/test_evaluation_service.py server/tests/evaluation/test_learning_assessment_events_api.py
git commit -m "refactor: standardize learning event collection"
```

### Task 3: 实现只读事实聚合器

**Files:**
- Create: `server/app/evaluation/facts.py`
- Create: `server/tests/evaluation/test_learning_assessment_facts.py`
- Modify: `server/app/evaluation/service.py`

- [ ] **Step 1: 写失败测试，覆盖时长、正确率、样本不足和资源/路径隔离。**

```python
async def test_facts_use_sessions_not_event_counts_for_minutes(session, user):
    await insert_session(session, user.id, seconds=1500)
    await insert_event(session, user.id, module="resource", event_type="resource_viewed")
    facts = await build_assessment_facts(session, user.id, window_start, window_end)
    assert facts["activity"]["total_minutes"] == 25

async def test_topic_is_insufficient_before_five_answers_in_two_attempts(session, user):
    await insert_quiz_events(session, user.id, topic="图", answers=4, attempts={1})
    facts = await build_assessment_facts(session, user.id, window_start, window_end)
    topic = facts["practice"]["by_topic"][0]
    assert topic["enough_evidence"] is False
```

- [ ] **Step 2: 运行测试。**

Run: `rtk cd server && uv run pytest tests/evaluation/test_learning_assessment_facts.py -q`

Expected: FAIL，聚合器不存在。

- [ ] **Step 3: 实现纯读取 `build_assessment_facts`。**

函数签名固定：

```python
async def build_assessment_facts(
    session: AsyncSession, user_id: int, window_start: datetime, window_end: datetime
) -> dict[str, Any]: ...
```

以 `Asia/Shanghai` 计算活跃日；时长只求 `LearningSession.duration_seconds`；用受控事件分别计算资源、路径、测验与可视化；只以有 `is_correct` 的事件算正确率。主题至少 5 题且至少 2 个 `attempt_index` 才设置 `enough_evidence=True`。空窗口返回完整、可渲染的零/空结构，绝不返回 `None`。

- [ ] **Step 4: 对快照做结构校验。**

在同文件定义 Pydantic `AssessmentFacts` 及嵌套类型，并在返回前调用 `AssessmentFacts.model_validate(...).model_dump(mode="json")`。禁止在该文件调用 LLM、写报告、更新画像或读取资源正文。

- [ ] **Step 5: 运行测试。**

Run: `rtk cd server && uv run pytest tests/evaluation/test_learning_assessment_facts.py -q`

Expected: PASS，包含空数据、跨用户隔离和时区日边界。

- [ ] **Step 6: 提交。**

```bash
git add server/app/evaluation/facts.py server/app/evaluation/service.py server/tests/evaluation/test_learning_assessment_facts.py
git commit -m "feat: aggregate assessment facts"
```

### Task 4: 生成 Markdown 报告并仅更新策略字段

**Files:**
- Create: `server/app/evaluation/reporting.py`
- Create: `server/app/evaluation/prompts/learning_assessment.md`
- Modify: `server/app/evaluation/service.py`
- Create: `server/tests/evaluation/test_learning_assessment_service.py`

- [ ] **Step 1: 写失败测试，锁定报告和画像分数不变式。**

```python
async def test_ready_report_updates_only_guidance_fields(session, user, monkeypatch):
    before = await load_profile_snapshot(session, user.id)
    monkeypatch.setattr(reporting, "generate", fake_markdown_and_strategy)
    report = await service.generate_report(session, user.id, range_days=7)
    after = await load_profile_snapshot(session, user.id)
    assert report.report_markdown.startswith("## 学习概览")
    assert after["guidance_strategy"] != before["guidance_strategy"]
    assert after["overall_score"] == before["overall_score"]
    assert after["scored_at"] == before["scored_at"]
    assert after["dimensions"] == before["dimensions"]
```

- [ ] **Step 2: 运行测试。**

Run: `rtk cd server && uv run pytest tests/evaluation/test_learning_assessment_service.py -q`

Expected: FAIL，报告服务尚不存在。

- [ ] **Step 3: 定义内部 LLM 契约和 Markdown 校验。**

`reporting.py` 的内部返回类型只能有 `report_markdown` 和 `guidance_strategy`。要求 Markdown 按顺序包含七个固定二级标题，最多 4,000 字，拒绝原始 HTML、`<script`、远程图片、`javascript:` 链接。提示词只能传事实快照和显式学科资料，必须要求“无证据即数据不足”。

- [ ] **Step 4: 实现报告状态机和独立策略写入。**

```python
async def update_guidance_strategy_only(session, user_id, strategy, report_id):
    profile = await session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if profile is None:
        profile = UserProfile(user_id=user_id)
        session.add(profile)
    profile.guidance_strategy = strategy
    profile.guidance_updated_at = datetime.now(timezone.utc)
    profile.last_assessment_report_id = report_id
    profile.updated_at = datetime.now(timezone.utc)
```

该函数不得导入或调用 `app.profile.service`。在一个事务中将报告置为 `ready` 并调用该函数；失败则置 `failed` 和失败码，保留旧策略。创建 `generating` 前检查部分唯一约束；已有生成中报告抛出领域错误，供 API 映射为 409。

- [ ] **Step 5: 运行测试。**

Run: `rtk cd server && uv run pytest tests/evaluation/test_learning_assessment_service.py -q`

Expected: PASS，覆盖成功、LLM 无效 Markdown、LLM 异常、并发生成和没有画像行的用户。

- [ ] **Step 6: 提交。**

```bash
git add server/app/evaluation/reporting.py server/app/evaluation/prompts/learning_assessment.md server/app/evaluation/service.py server/tests/evaluation/test_learning_assessment_service.py
git commit -m "feat: generate markdown learning assessments"
```

### Task 5: 公开报告与策略 API，删除旧汇总 API

**Files:**
- Modify: `server/app/evaluation/api.py`
- Modify: `server/app/evaluation/response.py`
- Modify: `server/app/evaluation/schemas.py`
- Create: `server/tests/evaluation/test_learning_assessment_api.py`
- Modify: `server/tests/dashboard/test_home_api.py`

- [ ] **Step 1: 写 API 失败测试。**

```python
async def test_strategy_endpoint_returns_only_strategy_fields(client, auth_headers):
    response = await client.get("/api/v1/ai/evaluation/guidance-strategy", headers=auth_headers)
    assert response.status_code == 200
    assert set(response.json()["data"]) == {
        "guidance_strategy", "guidance_updated_at", "last_assessment_report_id"
    }

async def test_other_user_report_returns_404(client, auth_headers, other_report):
    response = await client.get(f"/api/v1/ai/evaluation/reports/{other_report.id}", headers=auth_headers)
    assert response.status_code == 404
```

- [ ] **Step 2: 运行测试。**

Run: `rtk cd server && uv run pytest tests/evaluation/test_learning_assessment_api.py -q`

Expected: FAIL，路由不存在。

- [ ] **Step 3: 实现五个新 API。**

实现 `POST /evaluation/reports`、`GET /evaluation/reports/latest`、分页 `GET /evaluation/reports`、详情 `GET /evaluation/reports/{report_id}`、`GET /evaluation/guidance-strategy`。全部用 `HttpResponse`。详情返回 `facts_snapshot` 和 `report_markdown`；列表不返回两个大字段；查不到或非本人均返回 404；范围不是 7/14/30 返回 422；生成冲突返回 409 和 `assessment_generation_in_progress`。

- [ ] **Step 4: 删除旧读端点和响应模型。**

删除 `/evaluation/summary`、`/evaluation/time-stats`、`/dashboard/study-stats`、`EvaluationSummaryResponse`、`LearningTimeStatsResponse` 及其服务方法。不要删除路径专属 `GET /path-plan/{path_id}/evaluation`。

- [ ] **Step 5: 运行测试。**

Run: `rtk cd server && uv run pytest tests/evaluation/test_learning_assessment_api.py tests/dashboard/test_home_api.py tests/path/test_path_api.py -q`

Expected: PASS；首页测试不再期待已删除的 study-stats API，路径专属测试仍通过。

- [ ] **Step 6: 提交。**

```bash
git add server/app/evaluation/api.py server/app/evaluation/response.py server/app/evaluation/schemas.py server/tests/evaluation/test_learning_assessment_api.py server/tests/dashboard/test_home_api.py
git commit -m "feat: expose learning assessment reports"
```

### Task 6: 删除周摘要与画像读取副作用

**Files:**
- Delete: `server/app/profile/weekly/`
- Delete: `server/app/profile/prompts/weekly_digest.md`
- Delete: `server/app/profile/prompts/digest_update.md`
- Modify: `server/app/profile/service.py`
- Modify: `server/app/profile/api.py`
- Modify: `server/app/profile/__init__.py`
- Modify: `server/tests/profile/test_infer_profile_from_digest.py`
- Modify: `server/tests/profile/test_profile_v2_no_legacy_contracts.py`

- [ ] **Step 1: 写或改造失败测试，明确读取画像不写入。**

```python
async def test_get_profile_has_no_digest_or_score_side_effect(session, user):
    profile = await service.get_profile(user_id=user.id, db=session)
    assert profile.user_id == user.id
    assert await count_rows(session, WeeklyLearningDigest) == 0
```

- [ ] **Step 2: 运行测试。**

Run: `rtk cd server && uv run pytest tests/profile/test_infer_profile_from_digest.py tests/profile/test_profile_v2_no_legacy_contracts.py -q`

Expected: FAIL 或仍依赖旧周摘要。

- [ ] **Step 3: 删除旧周摘要调用链。**

从 `ProfileService` 删除 `get_or_create_weekly_digest`、周摘要构建和“读取时更新画像”逻辑。`get_profile` 只查询/必要时创建默认 profile 行；不调用 LLM、不改动 `overall_score`、`scored_at` 或维度。移除 API 中对 `infer_profile_from_digest` 的入口和所有导入。

- [ ] **Step 4: 删除文件、调整测试并验证无死引用。**

Run: `rtk cd server && uv run pytest tests/profile/test_infer_profile_from_digest.py tests/profile/test_profile_v2_no_legacy_contracts.py -q && rtk rg -n "WeeklyLearningDigest|weekly_digest|profile\.weekly|infer_profile_from_digest" app tests`

Expected: 测试 PASS；搜索无结果。

- [ ] **Step 5: 提交。**

```bash
git add -A server/app/profile server/tests/profile
git commit -m "refactor: remove weekly profile digest"
```

### Task 7: 更新前端采集契约并清除旧评估客户端

**Files:**
- Modify: `src/features/evaluation/model/evaluation.ts`
- Modify: `src/features/evaluation/api/evaluation.ts`
- Modify: `src/features/evaluation/model/useLearningTracker.ts`
- Modify: `src/app/providers/learningTracker.ts`
- Modify: 所有 `recordLearningEvent` 调用点（由 `rg` 列表逐个处理）

- [ ] **Step 1: 写出 TypeScript 编译预期，先删除旧摘要导出。**

从类型文件删除 `EvaluationSummary`、`LearningTimeStats` 和 `tutor_helpful`；加入 `client_event_id`、`occurred_at`、`client_session_id`。运行构建应失败并列出仍使用旧类型/方法的页面。

Run: `rtk npm run build`

Expected: FAIL，指出 `getEvaluationSummary`、`getLearningTimeStats` 或旧字段调用。

- [ ] **Step 2: 实现浏览器幂等键与受控元数据。**

```ts
const newEventId = () => crypto.randomUUID()

recordLearningEvent({
  client_event_id: newEventId(),
  occurred_at: new Date().toISOString(),
  module: 'quiz',
  event_type: 'quiz_submitted',
  event_metadata: { is_correct, attempt_index }
})
```

会话上报使用 `client_session_id`，时长仍由现有追踪器计算并限制在后端允许范围。资源反馈改为受控 `helpful|not_helpful`，不要上报自由文本。

- [ ] **Step 3: 仅删除旧汇总调用，保留路径事件适配。**

删除 `getEvaluationSummary` 和 `getLearningTimeStats` API 函数及其类型。保留 `recordPathLearningEvent`，确保 `PathNodeStudy.vue` 仍调用路径专属事件端点。

- [ ] **Step 4: 验证。**

Run: `rtk rg -n "getEvaluationSummary|getLearningTimeStats|EvaluationSummary|LearningTimeStats|tutor_helpful" src && rtk npm run build`

Expected: 搜索无结果，构建 PASS。

- [ ] **Step 5: 提交。**

```bash
git add src/features/evaluation src/app/providers/learningTracker.ts src/features/learning-path/views/PathNodeStudy.vue
git commit -m "refactor: align learning tracking events"
```

### Task 8: 新建学习评估页面、导航和报告 API 客户端

**Files:**
- Create: `src/features/learning-assessment/api/assessment.ts`
- Create: `src/features/learning-assessment/model/assessment.ts`
- Create: `src/features/learning-assessment/views/LearningAssessment.vue`
- Modify: `src/app/router/routes.ts`
- Modify: `src/app/layouts/MainLayout.vue`

- [ ] **Step 1: 写前端类型和 API 客户端。**

```ts
export interface AssessmentReportDetail {
  id: number
  range_days: 7 | 14 | 30
  window_start: string
  window_end: string
  status: 'generating' | 'ready' | 'failed'
  facts_snapshot: AssessmentFacts | null
  report_markdown: string | null
  generated_at: string | null
}

export const generateAssessmentReport = (range_days: 7 | 14 | 30) =>
  http.post<ApiResponse<AssessmentReportDetail>>('/ai/evaluation/reports', { range_days })
```

- [ ] **Step 2: 实现页面状态和安全展示。**

页面加载最新报告与历史列表；点击生成后禁用按钮直到请求结束；409 时提示“已有报告生成中”。图表只绑定 `facts_snapshot`，Markdown 用现有项目依赖或经白名单配置的渲染器展示，必须关闭原始 HTML。无报告显示明确空状态，不展示模拟数字。

- [ ] **Step 3: 实现页面布局。**

顺序固定为：范围选择/生成、四个概览指标、每日时长趋势、模块分布、资源与路径、主题正确率、Markdown 报告、当前辅导策略、历史列表。每张图缺数据时显示原因而非空白坐标轴。使用现有 Glacier Teal 主题变量，白底并按数据含义使用克制的辅助色。

- [ ] **Step 4: 增加路由与导航。**

在路由定义中增加 `{ path: '/learning-assessment', name: 'learning-assessment', component: () => import(...) }`，并在主导航增加“学习评估”。不要改动 `Home.vue`，不要将新页面嵌入 `Profile.vue`。

- [ ] **Step 5: 验证构建。**

Run: `rtk npm run build`

Expected: PASS。

- [ ] **Step 6: 提交。**

```bash
git add src/features/learning-assessment src/app/router/routes.ts src/app/layouts/MainLayout.vue
git commit -m "feat: add learning assessment page"
```

### Task 9: 清理个人中心旧看板，改为策略摘要

**Files:**
- Modify: `src/features/profile/views/Profile.vue`
- Modify: `src/features/profile/api/profile.ts`（仅当其错误承载评估请求时）
- Modify: `src/features/learning-assessment/api/assessment.ts`

- [ ] **Step 1: 删除个人中心评估状态和旧接口引用。**

删除 `Profile.vue` 中 `evaluationSummary`、`studyStats`、`evaluationLoading`、旧图表计算属性、`getEvaluationSummary`、`getLearningTimeStats` 和对应样式。账号/学业资料编辑功能不得受影响。

- [ ] **Step 2: 以独立策略 API 增加小型摘要卡。**

```ts
const strategy = ref<GuidanceStrategy | null>(null)
onMounted(async () => {
  const response = await getGuidanceStrategy()
  strategy.value = response.data.data.guidance_strategy || null
})
```

卡片只显示重点主题、建议学习时长和一条目标；无策略时显示“生成第一份学习评估后将提供建议”；按钮跳转 `/learning-assessment`。不得请求画像雷达、报告详情或事实快照。

- [ ] **Step 3: 验证没有把评估页放回个人中心。**

Run: `rtk rg -n "EvaluationSummary|LearningTimeStats|getEvaluationSummary|getLearningTimeStats|facts_snapshot|report_markdown" src/features/profile && rtk npm run build`

Expected: 搜索无结果，构建 PASS。

- [ ] **Step 4: 提交。**

```bash
git add src/features/profile/views/Profile.vue src/features/profile/api/profile.ts src/features/learning-assessment/api/assessment.ts
git commit -m "refactor: simplify profile learning guidance"
```

### Task 10: 有选择地向生成模块传递当前策略并做全量验收

**Files:**
- Create: `server/app/evaluation/guidance.py`
- Modify: `server/app/resource/api.py`
- Modify: `server/app/resource/service.py`
- Modify: `server/app/path/service.py`
- Modify: `server/app/chat/agent/nodes.py`
- Create: `server/tests/evaluation/test_guidance_strategy.py`
- Modify/Create: 对应 resource、path、chat 测试

- [ ] **Step 1: 写失败测试，证明策略只影响新生成输入。**

```python
async def test_effective_strategy_returns_safe_default(session, user):
    assert await get_effective_guidance_strategy(session, user.id) == DEFAULT_GUIDANCE_STRATEGY

async def test_resource_prompt_receives_strategy_for_new_request(monkeypatch, session, user):
    await set_strategy(session, user.id, {"focus_topics": ["图"]})
    prompt = await build_resource_prompt_for_test(session, user.id)
    assert "图" in prompt
```

- [ ] **Step 2: 实现唯一策略读取器。**

```python
async def get_effective_guidance_strategy(session: AsyncSession, user_id: int) -> dict[str, Any]:
    profile = await session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    return profile.guidance_strategy if profile and profile.guidance_strategy else DEFAULT_GUIDANCE_STRATEGY
```

它只读数据库，不创建画像行，不更新评分。`resource/api.py` 在创建 `request_snapshot_json` 前读取策略并将其冻结在请求快照；`path/service.py` 在创建新的 `PathState` 前读取策略并作为规划上下文；`chat/agent/nodes.py` 在渲染 `tutor_agent` 提示词前读取策略并注入受控字段。题库只有在存在独立的生成上下文装配点时才接入；算法可视化不接入。策略只影响新请求，禁止批量修改既有资源/路径。

- [ ] **Step 3: 运行目标测试。**

Run: `rtk cd server && uv run pytest tests/evaluation/test_guidance_strategy.py tests/resource/ tests/path/ tests/chat/ -q`

Expected: 与本重构相关的测试 PASS；记录三个已知 chat 既有失败，不能把新失败归类为既有问题。

- [ ] **Step 4: 做最终删除和回归扫描。**

Run: `rtk rg -n "WeeklyLearningDigest|weekly_digest|evaluation/summary|evaluation/time-stats|dashboard/study-stats|report_content" server src && rtk npm run build && rtk cd server && uv run pytest -q`

Expected: 第一条搜索无结果（迁移的 `DROP` 注释除外）；前端构建 PASS；后端仅可能存在已知的 `test_agent_single_module_refactor.py`、`test_onboarding_api.py`、`test_reasoning_agent.py` 失败。

- [ ] **Step 5: 提交。**

```bash
git add server/app/evaluation/guidance.py server/app/resource/api.py server/app/resource/service.py server/app/path/service.py server/app/chat/agent/nodes.py server/tests/evaluation server/tests/resource server/tests/path server/tests/chat
git commit -m "feat: apply current guidance to new learning requests"
```

## 最终交付检查

- [ ] 新建数据库与迁移数据库都存在相同的报告、策略、索引和约束。
- [ ] 生成报告只更新 `guidance_strategy` 相关字段；画像分数、时间戳和维度不变。
- [ ] 报告正文只存 Markdown，图表只读事实快照，前端禁止不安全 Markdown 内容。
- [ ] 首页未增加评估内容；个人中心没有画像或评估图表；学习路径的专属评估仍可访问。
- [ ] 全部旧周摘要和旧汇总接口/客户端已删除，且不存在兼容别名。
