# 提示词：VideoAgent 讲解视频生成智能体 (Resource Domain)

## 1. 架构定位

VideoAgent 是位于 `standalone resource` 领域下的 **Aggregation Agent (聚合智能体)**。
它与 `PPTAgent` 处于同一架构层级，在阶段 3 并行执行。

**核心特征：**
1. **聚合型**：必须接收前置 Worker Agents（如 Content, Reading, Code）生成的 `previous_results`，基于已验证的知识内容生成视频分镜脚本。
2. **纯 JSON 产物**：当前仅负责生成结构化的 JSON 预览 Payload，供前端渲染视频卡片或后续渲染管线使用（不直接在此管线中包含渲染代码）。
3. **单文件组织**：保持高内聚，将相关的 Sub-agents（提取、大纲、分镜等）和 Schema 声明全部收敛于 `server/app/resource/agents/video.py`。
4. **共享底层**：必须使用现有的 `GeneratedResource` 和 `GeneratedResourceItem` 体系持久化结果，不允许创建新的数据表。

## 2. 核心职责

1. 接受包含用户需求、画像、蓝图和前置产物的 `ResourceInput`。
2. 通过内部微型 DAG 并发生成视频所需的分镜信息：
   - 提取素材 (VideoMaterialAgent)
   - 浓缩大纲 (VideoOutlineAgent)
   - 并发生成分镜 (SceneWriterAgent)
3. 拼装符合前端 `VideoPreviewPayload` 规范的完整 JSON。
4. 保证容错性，内部组件失败时，安全地降级或返回清晰的 AgentResult 错误。

## 3. 生成物结构 (Video Payload)

生成的产物是 `AgentResult`，其 `content` 包含如下 JSON：

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

## 4. 实现指南

- **不引入新模块**：禁止创建 `app/video/` 等新模块。所有的实现都必须位于 `app/resource/` 中。
- **并行生成**：对于多分镜场景，必须使用 `asyncio.gather` 并行调用分镜撰写智能体，以确保响应速度。
- **SSE 进度**：遵循当前的 `AgentRunTracker` 机制推送进度。
- **统一 Review**：生成的 Payload 同样会被 `video_review` Agent 独立处理。

## 5. 设计约束

1. **绝对不要引入 FFmpeg 或 S3 逻辑**：资源的媒体渲染不在当前管线范围内。
2. **避免过早抽象**：不需要为了 VideoAgent 提取过多的公共工具类，单文件或就近放置 helper 函数即可。
3. **利用统一的上下文**：善用 `instruction.reference_materials`。
