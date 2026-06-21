# Video Agent 多智能体资源生成完善方案

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把当前 `videoAgent` 从“基本可跑”完善到可合并状态：数据库契约稳定、资源多智能体编排正确、video 审核真实生效、前端能预览真实 `video/v1` payload，并预留智能辅导入口但不接入。

**Architecture:** `video` 与 `ppt` 同属 standalone resource 聚合型 agent，不进入 path 域，不作为基础 worker；它消费前置基础资源的 `previous_results`，内部在单文件 `server/app/resource/agents/video.py` 中用合适数量的子 agent/函数并行产出分镜 JSON。数据库仍复用 `generated_resources` / `generated_resource_items`，不新增 video 专表；智能辅导只保留 service/agent adapter 的接口边界。

**Tech Stack:** FastAPI + SQLModel + PostgreSQL JSONB；Pydantic v2；Vue 3 + TypeScript；pytest；`npm run build`。

---

## File Map

- Modify: `server/app/infra/models.py`  
  清理误加字段和重复字段，保证 SQLModel 与 `server/init_schema.sql` 完全一致。
- Modify: `server/init_schema.sql`  
  仅在确认需要新增列时同步；本方案默认不新增 standalone video DB 列。
- Modify: `server/app/resource/agents/review.py`  
  让审核 Agent 读取 `video_resource.audit_content`。
- Modify: `server/app/resource/review.py`  
  保持 `build_video_audit_envelope()` 的契约，并补测试确认 envelope 可被审核 Agent 消费。
- Modify: `server/app/resource/service.py`  
  修正 video 聚合 agent 的编排注释、进度权重、review snapshot。
- Modify: `server/app/resource/agents/video.py`  
  只做契约收口：输出字段、metadata、预留 tutor adapter，不拆多文件。
- Modify: `server/app/resource/prompts/video_material.md`
- Modify: `server/app/resource/prompts/video_outline.md`
- Modify: `server/app/resource/prompts/video_scene.md`  
  保持 prompt 与实际 `video/v1` payload 一致。
- Modify: `src/features/resource/views/ResourceGenerator.vue`
- Modify: `src/features/resource/views/ResourceDetail.vue`
- Modify: `src/features/resource/components/VideoView.vue`  
  前端预览消费真实后端结构，不要求后端产出图片 URL 或二进制 MP4。
- Test: `server/tests/resource/test_video_service_orchestration.py`
- Test: `server/tests/resource/test_video_agent.py`
- Test: `server/tests/resource/test_resource_review.py` or nearest existing review test file
- Test: `server/tests/resource/test_resource_contract.py`

---

## Task 1: 修复数据库模型与 schema 漂移

**Files:**
- Modify: `server/app/infra/models.py`
- Verify: `server/init_schema.sql`
- Test: `server/tests/resource/test_resource_contract.py`

- [ ] **Step 1: 写一个 schema smoke test，先暴露漂移**

在 `server/tests/resource/test_resource_contract.py` 添加测试，重点防止 `GeneratedResourceItem`、`LearningEvent`、`LearningSession` 再出现模型列大于 SQL 列的情况。

```python
from pathlib import Path

from app.infra.models import GeneratedResourceItem, LearningEvent, LearningSession


def _table_sql(table_name: str) -> str:
    sql = Path(__file__).resolve().parents[2].joinpath("init_schema.sql").read_text()
    marker = f"CREATE TABLE IF NOT EXISTS {table_name} ("
    start = sql.index(marker)
    end = sql.index(");", start)
    return sql[start:end]


def test_generated_resource_item_model_columns_match_init_schema():
    table_sql = _table_sql("generated_resource_items")
    model_columns = set(GeneratedResourceItem.__table__.columns.keys())

    for column_name in model_columns:
        assert column_name in table_sql


def test_learning_event_and_session_do_not_expose_missing_runtime_columns():
    event_columns = set(LearningEvent.__table__.columns.keys())
    session_columns = set(LearningSession.__table__.columns.keys())

    assert {"summary", "status", "error_message", "input_json"}.isdisjoint(event_columns)
    assert {"summary", "status", "error_message", "input_json"}.isdisjoint(session_columns)
```

- [ ] **Step 2: 运行失败测试**

Run:

```bash
cd server
rtk uv run pytest tests/resource/test_resource_contract.py -q
```

Expected: 失败，原因是 `generated_resource_items.input_json` 不在 `init_schema.sql`，且 `LearningEvent` / `LearningSession` 暴露了 SQL 中不存在的字段。

- [ ] **Step 3: 清理 `server/app/infra/models.py`**

在 `GeneratedResourceItem` 中只保留一份字段定义：

```python
summary: str | None = Field(default=None, sa_column=Column(Text))
status: str = Field(default="pending", max_length=50)
error_message: str | None = Field(default=None, sa_column=Column(Text))
```

删除同一 class 内重复的第二份 `summary/status/error_message`，并删除 `input_json`。在 `LearningEvent` 和 `LearningSession` 中删除这四个误加字段：

```python
summary: str | None = Field(default=None, sa_column=Column(Text))
status: str = Field(default="completed", max_length=32)
error_message: str | None = Field(default=None, sa_column=Column(Text))
input_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
```

保留 `PathNodeResource` 的 `summary/status/error_message/input_json`，因为 `server/init_schema.sql` 已有这些列。

- [ ] **Step 4: 运行验证**

Run:

```bash
cd server
rtk uv run pytest tests/resource/test_resource_contract.py -q
```

Expected: PASS。

---

## Task 2: 让 video 审核真正读取待审内容

**Files:**
- Modify: `server/app/resource/agents/review.py`
- Modify: `server/tests/resource/test_video_service_orchestration.py`

- [ ] **Step 1: 添加失败测试**

在 `server/tests/resource/test_video_service_orchestration.py` 添加：

```python
from app.resource.agents.review import ReviewAgent


def test_review_agent_extracts_video_resource_audit_content():
    envelope = {
        "mode": "video_audit",
        "video_resource": {
            "agent_id": "video",
            "audit_content": '{"schema_version":"video/v1","scenes":[{"narration":"TCP 三次握手"}]}',
        },
    }

    content = ReviewAgent._extract_audit_content(envelope)

    assert "video/v1" in content
    assert "TCP 三次握手" in content
```

- [ ] **Step 2: 运行失败测试**

Run:

```bash
cd server
rtk uv run pytest tests/resource/test_video_service_orchestration.py::test_review_agent_extracts_video_resource_audit_content -q
```

Expected: FAIL，当前只读取 `deep_audit_resources` 和 `ppt_resource`。

- [ ] **Step 3: 修复审核内容提取**

在 `ReviewAgent._extract_audit_content()` 中将聚合资源读取改为可扩展列表：

```python
for key in ("ppt_resource", "video_resource"):
    resource = envelope.get(key)
    if isinstance(resource, dict) and resource.get("audit_content"):
        parts.append(resource["audit_content"])
```

- [ ] **Step 4: 运行相关测试**

Run:

```bash
cd server
rtk uv run pytest tests/resource/test_video_service_orchestration.py tests/resource/test_agent_integration.py -q
```

Expected: PASS。

---

## Task 3: 修正多智能体编排的进度模型

**Files:**
- Modify: `server/app/resource/service.py`
- Modify: `server/tests/resource/test_video_service_orchestration.py`

- [ ] **Step 1: 添加失败测试**

在 `server/tests/resource/test_video_service_orchestration.py` 添加：

```python
from app.resource.service import ResourceService
from app.resource.review import VIDEO_AGENT_ID, VIDEO_REVIEW_AGENT_ID


def test_overall_progress_treats_video_as_aggregation_stage_not_worker():
    progress = ResourceService._calculate_overall_progress(
        status="generating",
        selected_agents=["content", "reading", "video"],
        agent_snapshots={
            "planning": {"progress": 100},
            "content": {"progress": 100},
            "reading": {"progress": 100},
            "pre_review": {"progress": 100},
            "bundle": {"progress": 100},
            VIDEO_AGENT_ID: {"progress": 50},
            VIDEO_REVIEW_AGENT_ID: {"progress": 0},
        },
    )

    assert 80 <= progress < 100
```

- [ ] **Step 2: 运行失败测试**

Run:

```bash
cd server
rtk uv run pytest tests/resource/test_video_service_orchestration.py::test_overall_progress_treats_video_as_aggregation_stage_not_worker -q
```

Expected: 当前实现没有给 `video_review` 权重，且 worker 过滤只排除 `ppt`，结果不可信。

- [ ] **Step 3: 修改 `_calculate_overall_progress()`**

将 worker 过滤改为：

```python
worker_agents = [
    agent_id
    for agent_id in selected_agents
    if agent_id not in AGGREGATION_AGENT_IDS
]
```

将聚合阶段显式加权：

```python
if PPT_AGENT_ID in selected_agents:
    stages.extend([
        (15, progress_for(PPT_AGENT_ID)),
        (5, progress_for(PPT_REVIEW_AGENT_ID)),
    ])
if VIDEO_AGENT_ID in selected_agents:
    stages.extend([
        (15, progress_for(VIDEO_AGENT_ID)),
        (5, progress_for(VIDEO_REVIEW_AGENT_ID)),
    ])
```

同步更新 `run_multi_agent_generation()` 顶部注释，把阶段 3 描述为“前置审核、PPT、Video 聚合生成并行执行”，不要继续只写 PPT。

- [ ] **Step 4: 运行相关测试**

Run:

```bash
cd server
rtk uv run pytest tests/resource/test_video_service_orchestration.py tests/resource/test_ppt_internal_multi_agent.py tests/resource/test_ppt_agent.py -q
```

Expected: PASS。

---

## Task 4: 收口 video payload 与 prompts 契约

**Files:**
- Modify: `server/app/resource/agents/video.py`
- Modify: `server/app/resource/prompts/video_material.md`
- Modify: `server/app/resource/prompts/video_outline.md`
- Modify: `server/app/resource/prompts/video_scene.md`
- Modify: `server/docs/video_agent_backend_json_prompt.md`
- Test: `server/tests/resource/test_video_agent.py`

- [ ] **Step 1: 添加契约测试**

在 `server/tests/resource/test_video_agent.py` 添加：

```python
def test_video_payload_contract_uses_backend_video_v1_fields():
    payload = _valid_payload_dict()

    first_scene = payload["scenes"][0]

    assert "scene_id" in first_scene
    assert "duration_ms" in first_scene
    assert "narration" in first_scene
    assert "visual_prompt" in first_scene
    assert "visual_data" not in first_scene
    assert "imageUrl" not in first_scene
```

- [ ] **Step 2: 检查并修正 prompt 输出样例**

所有 video prompt 和 `server/docs/video_agent_backend_json_prompt.md` 必须统一使用后端真实字段：

```json
{
  "schema_version": "video/v1",
  "title": "TCP 三次握手讲解",
  "duration_seconds": 180,
  "aspect_ratio": "16:9",
  "style": "explainer",
  "voice": "teacher",
  "language": "zh-CN",
  "scenes": [
    {
      "scene_id": "scene-1",
      "index": 1,
      "role": "hook",
      "title": "为什么需要三次确认",
      "start_ms": 0,
      "duration_ms": 30000,
      "visual_type": "diagram",
      "narration": "客户端和服务端需要确认双方收发能力。",
      "captions": ["确认双方收发能力"],
      "on_screen_text": ["SYN", "SYN+ACK", "ACK"],
      "visual_prompt": "左右两列展示客户端和服务端，三条箭头展示报文顺序",
      "interaction_prompt": "暂停让学习者复述第三次 ACK 的意义",
      "source_agents": ["content", "mindmap"]
    }
  ],
  "assets": [],
  "metadata": {
    "source_agent_ids": ["content", "mindmap"]
  }
}
```

不要在 prompt 中要求 `visual_data`、`imageUrl`、`config.scenes` 或真实 MP4 文件。

- [ ] **Step 3: 确认 tutor 预留接口只做 adapter**

`VideoAgent.generate_from_tutor_context()` 保持为 adapter，目标行为：

```python
return await self.generate_resource(
    ResourceInput(
        resource_id=resource_id,
        learning_need=learning_need,
        learning_scenario="self_study",
        agent_name=self.agent_id,
        agent_config=agent_config,
        profile=profile,
        previous_results=normalized_previous_results,
    )
)
```

不要在本轮新增 tutor API 路由，也不要让 chat/path 域直接依赖 video 的落库模型。

- [ ] **Step 4: 运行 video agent 测试**

Run:

```bash
cd server
rtk uv run pytest tests/resource/test_video_agent.py tests/resource/test_resource_request_schema.py -q
```

Expected: PASS。

---

## Task 5: 前端预览接入真实 `video/v1` payload

**Files:**
- Modify: `src/features/resource/views/ResourceGenerator.vue`
- Modify: `src/features/resource/views/ResourceDetail.vue`
- Modify: `src/features/resource/components/VideoView.vue`

- [ ] **Step 1: 接入生成页预览**

在 `ResourceGenerator.vue` 中导入 `VideoView`，并在 preview dialog 中增加 video 分支：

```vue
<VideoView v-else-if="previewData.agentId === 'video'" :result-data="previewData.resultData" />
```

- [ ] **Step 2: 修正详情页 prop 名称**

`ResourceDetail.vue` 当前已写 video 分支，但传的是 `:result-data`。让 `VideoView.vue` 统一接收 `resultData`，避免详情页和生成页传参不一致。

- [ ] **Step 3: 改造 `VideoView.vue` 的输入归一化**

把 props 改为：

```ts
const props = defineProps<{ resultData?: any }>()
```

新增归一化逻辑，兼容资源详情页 envelope：

```ts
const videoPayload = computed(() => {
  const raw = props.resultData
  if (!raw) return null
  if (raw.content_json?.content) return raw.content_json.content
  if (raw.content_json) return raw.content_json
  if (raw.content) {
    try {
      return typeof raw.content === 'string' ? JSON.parse(raw.content) : raw.content
    } catch {
      return null
    }
  }
  return raw
})

const activeScenes = computed(() => {
  const scenes = videoPayload.value?.scenes
  return Array.isArray(scenes)
    ? scenes.map((scene: any) => ({
        id: scene.scene_id || `scene-${scene.index}`,
        duration: scene.duration_ms || 4000,
        title: scene.title || `分镜 ${scene.index || ''}`.trim(),
        desc: scene.narration || scene.visual_prompt || '',
        visualPrompt: scene.visual_prompt || '',
        visualType: scene.visual_type || 'card',
        captions: Array.isArray(scene.captions) ? scene.captions : [],
      }))
    : []
})
```

预览渲染不依赖 `imageUrl`。如果没有图像，就用 `visual_type`、`visual_prompt`、`captions` 渲染一个可读的 canvas 场景卡片。MP4 导出可以先保留按钮，但要在无 WebCodecs 支持时禁用并给出 `ElMessage.warning`。

- [ ] **Step 4: 清理 TypeScript 风险**

如果 `mp4-muxer` 引入导致构建慢或 WebCodecs 类型缺失，先把 MP4 导出降级为 “导出 JSON 脚本”。本轮目标是 videoAgent 资源 JSON 预览可用，不是浏览器端视频编码。

- [ ] **Step 5: 运行前端构建**

Run:

```bash
rtk npm run build
```

Expected: 如果仍失败，先修本分支引入的 `VideoView.vue` / `ResourceGenerator.vue` / `ResourceDetail.vue` 类型错误。现有 `OnboardingDialog.vue`、`CodeView.vue` 的 pre-existing TS 错误可以单独记录，但不要混进 video 修复提交。

---

## Task 6: 全链路验证与合并门禁

**Files:**
- Verify only

- [ ] **Step 1: 后端 targeted tests**

Run:

```bash
cd server
rtk uv run pytest tests/resource/test_video_agent.py tests/resource/test_video_service_orchestration.py tests/resource/test_resource_request_schema.py -q
```

Expected: PASS。

- [ ] **Step 2: 资源域契约与集成测试**

Run:

```bash
cd server
rtk uv run pytest tests/resource/test_resource_contract.py tests/resource/test_agent_integration.py tests/resource/test_agent_dual_entry.py -q
```

Expected: PASS。

- [ ] **Step 3: PPT 回归测试**

Run:

```bash
cd server
rtk uv run pytest tests/resource/test_ppt_internal_multi_agent.py tests/resource/test_ppt_agent.py tests/resource/test_ppt_standalone.py -q
```

Expected: PASS，确认 video 与 ppt 同层但没有破坏 ppt。

- [ ] **Step 4: 前端构建**

Run:

```bash
rtk npm run build
```

Expected: PASS，或只剩确认过的 pre-existing 错误并在 review note 中列明。

- [ ] **Step 5: 手动 smoke**

启动后端和前端：

```bash
cd server
rtk uv run fastapi dev app/main.py --port 9999
```

```bash
rtk npm run dev
```

手动生成资源时选择 `content + mindmap + video`，确认：

- `content`、`mindmap` 先并行完成；
- `video` 等待基础资源结果，通过 `previous_results` 生成；
- 产物列表出现 `讲解视频`；
- 点击预览能显示 video 分镜；
- 状态进度不会卡在 90% 以下；
- 详情页重新打开后仍能预览 video。

---

## Commit Plan

建议拆成 4 个提交：

```bash
git commit -m "fix: align resource models with database schema"
git commit -m "fix: audit video resource content"
git commit -m "fix: model video as resource aggregation stage"
git commit -m "feat: preview video resource payload"
```

每个提交前只 stage 本任务涉及文件，避免把当前工作区大量无关改动带进去。

---

## Acceptance Criteria

- `video` 保持 standalone resource 域，与 `ppt` 同层；不进入 path 域的资源记录和详情。
- `videoAgent` 内部多智能体/函数仍集中在 `server/app/resource/agents/video.py`，不拆多个 agent 文件。
- `video` 消费上游 `previous_results`，不是和基础 worker 同时抢跑。
- `video_review` 能实际审核 `video_resource.audit_content`。
- `GeneratedResourceItem`、`LearningEvent`、`LearningSession` 不再有 SQL 中不存在的模型字段。
- 前端生成页和详情页都能预览真实 `video/v1` JSON。
- 智能辅导接口只预留 adapter，不新增 tutor 对外 API。
