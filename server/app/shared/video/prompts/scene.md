# 教学视频分镜编写

你负责把单个教学场景写成可由 Remotion 动态演示的结构化内容。

视频请求：
{request}

素材摘要：
{digest}

场景合约：
{contract}

全片视觉风格：
{style}

视觉数据约束：
{visual_contract}

要求：
1. 旁白使用自然、准确、简洁的中文口语，先说现象，再解释机制，最后给出本幕结论。
2. 屏幕只承载关键词、状态、步骤、关系和结论，不要把整段旁白搬到画面。
3. `visual_beats` 描述教学事件。每个 `text_anchor` 必须逐字出现在 `narration` 中，系统会用它对齐真实 TTS 时间。
4. 每个 beat 只触发一个明确变化，例如显示定义、移动指针、点亮节点、发送报文、切换代码行或揭示结论。
5. `visual` 只包含知识内容，禁止颜色、字体、CSS、坐标、布局、主题、时间戳和动画参数。
6. 内容必须由素材摘要支持；代码、状态、边和复杂度必须真实正确。
7. 输出严格 JSON，不要解释。

# OUTPUT EXAMPLE

```json
{
  "scene_id": "s3",
  "index": 3,
  "title": "上下文切换过程",
  "narration": "调度器选中 P2 后，先保存 P1 的寄存器和程序计数器到 PCB1，然后从 PCB2 恢复 P2 的寄存器状态，最后切换地址空间，P2 开始执行。",
  "visual_type": "process_flow",
  "visual": {
    "steps": ["保存 P1 上下文到 PCB1", "从 PCB2 恢复 P2 上下文", "切换页表地址空间", "P2 开始执行"],
    "highlight_step": 2
  },
  "visual_beats": [
    {"id": "vb1", "kind": "trace_step", "target": "step_1", "text_anchor": "保存 P1 的寄存器", "summary": "保存旧进程状态"},
    {"id": "vb2", "kind": "trace_step", "target": "step_2", "text_anchor": "从 PCB2 恢复", "summary": "恢复新进程状态"},
    {"id": "vb3", "kind": "trace_step", "target": "step_3", "text_anchor": "切换地址空间", "summary": "切换内存映射"},
    {"id": "vb4", "kind": "checkpoint", "target": "step_4", "text_anchor": "P2 开始执行", "summary": "新进程开始运行"}
  ]
}
```


# SAFETY（安全约束）

- 严禁输出任何涉及色情、赌博、毒品、暴力等违法违规或不良信息的内容
