"""
知识图解 Agent — Mermaid 图解生成 Agent。

支持 18 种图解类型：

基础图解类型 (6种):
- hierarchy: 层级结构，用于知识点组成、分类、结构拆解
- flow: 顺序流程，用于步骤、过程、运行机制
- compare: 对比结构，用于区别、优缺点、易混概念
- relation: 关系结构，用于依赖、因果、模块关系
- sequence: 交互时序，用于客户端/服务器、前后端、协议交互
- state: 状态变化，用于状态机、生命周期、算法过程

计算机学科专用图表 (5种):
- class: 类图，用于展示类结构、继承关系、接口实现
- er: 实体关系图，用于展示数据库表结构、字段关系
- block: 方块图，用于展示系统架构、模块布局
- packet: 网络包图，用于展示网络协议包结构、数据帧格式
- git: Git 图，用于展示 Git 分支、提交历史、合并流程

软件工程教学常用图表 (7种):
- activity: 活动图，用于展示业务流程、算法步骤、操作流程
- usecase: 用例图，用于展示系统功能、用户交互、需求分析
- component: 组件图，用于展示系统架构、模块划分、接口依赖
- package: 包图，用于展示代码组织、模块依赖、架构划分
- deployment: 部署图，用于展示运行环境、硬件节点、分布式系统架构
- object: 对象图，用于展示对象实例、运行时状态、对象关系
- communication: 通信图，用于展示对象协作、消息流向、交互关系

LLM 直接生成 Mermaid 源码，前端负责渲染。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.schemas import WorkerState, WorkerResult
from app.resource.worker_agents.utils import generate_execution_report
from app.shared.diagram_render import build_mermaid_render
from app.chat.schemas import DIAGRAM_MODEL_MAP, DiagramDecision

logger = get_logger(__name__)

SUPPORTED_DIAGRAM_TYPES = list(DIAGRAM_MODEL_MAP.keys())

DIAGRAM_TYPE_DESCRIPTIONS = {
    "hierarchy": "层级结构，用于知识点组成、分类、结构拆解",
    "flow": "顺序流程，用于步骤、过程、运行机制",
    "compare": "对比结构，用于区别、优缺点、易混概念",
    "relation": "关系结构，用于依赖、因果、模块关系",
    "sequence": "交互时序，用于客户端/服务器、前后端、协议交互",
    "state": "状态变化，用于状态机、生命周期、算法过程",
    "class": "类图，用于展示类结构、继承关系、接口实现",
    "er": "实体关系图，用于展示数据库表结构、字段关系",
    "block": "方块图，用于展示系统架构、模块布局",
    "packet": "网络包图，用于展示网络协议包结构、数据帧格式",
    "git": "Git 图，用于展示 Git 分支、提交历史、合并流程",
    "activity": "活动图，用于展示业务流程、算法步骤、操作流程",
    "usecase": "用例图，用于展示系统功能、用户交互、需求分析",
    "component": "组件图，用于展示系统架构、模块划分、接口依赖",
    "package": "包图，用于展示代码组织、模块依赖、架构划分",
    "deployment": "部署图，用于展示运行环境、硬件节点、分布式系统架构",
    "object": "对象图，用于展示对象实例、运行时状态、对象关系",
    "communication": "通信图，用于展示对象协作、消息流向、交互关系",
}

MERMAID_DIAGRAM_KEYWORDS = {
    "hierarchy": "graph TD",
    "flow": "flowchart TD",
    "compare": "flowchart LR",
    "relation": "graph TD",
    "sequence": "sequenceDiagram",
    "state": "stateDiagram-v2",
    "class": "classDiagram",
    "er": "erDiagram",
    "block": "block-beta",
    "packet": "packet-beta",
    "git": "gitGraph",
    "activity": "flowchart TD",
    "usecase": "flowchart LR",
    "component": "flowchart TB",
    "package": "flowchart TB",
    "deployment": "flowchart TB",
    "object": "flowchart TB",
    "communication": "flowchart LR",
}


class DiagramAgent:
    """知识图解 Agent。"""

    def __init__(self, user_id: int, resource_id: int, emitter=None):
        self.user_id = user_id
        self.resource_id = resource_id
        self.emitter = emitter
        self.llm_manager = get_llm_manager()
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "workers" / "diagram.md"
        self.diagram_model_kwargs = {"temperature": 0.1, "streaming": False, "max_tokens": 4000}

    async def _emit_action(self, action: str, detail: str = "") -> None:
        """发送 Agent 动作事件。"""
        if self.emitter:
            await self.emitter.emit_agent_action("diagram", action, detail)

    async def run(self, state: WorkerState) -> WorkerResult:
        """执行知识图解生成。"""
        logger.info("[DiagramAgent] 开始执行: topic=%s", state.task.get("topic", ""))

        await self._emit_action("loading_prompt", "加载知识图解生成提示词")
        prompt = self._load_prompt()

        await self._emit_action("building_input", "构建输入内容")
        input_text = await self._build_input(state)

        # 从 agent_config 获取 diagram_type
        diagram_type = state.agent_config.get("diagram_type") if state.agent_config else None
        if diagram_type == "auto":
            diagram_type = None

        try:
            if not diagram_type:
                await self._emit_action("deciding_type", "决策最适合的图解类型")
                diagram_type = await self._decide_diagram_type(prompt, input_text, state)
                if not diagram_type:
                    logger.info("[DiagramAgent] 不需要生成图解")
                    return WorkerResult(
                        success=True,
                        content="",
                        error="当前内容不适合生成图解",
                    )

            logger.info("[DiagramAgent] 选择图解类型: %s", diagram_type)

            await self._emit_action("calling_llm", f"调用 Spark X 生成 {diagram_type} 类型图解")
            mermaid_source = await self._generate_mermaid(diagram_type, prompt, input_text, state)

            if not mermaid_source:
                return WorkerResult(success=False, error="图解生成失败")

            content = {
                "diagram_type": diagram_type,
                "render_format": state.agent_config.get("render_format", "mermaid"),
                "source": mermaid_source,
                "description": "知识图解",
            }

            execution_report = generate_execution_report(
                agent_type="diagram",
                task=state.task,
                content=content,
                success=True,
            )

            return WorkerResult(
                success=True,
                content=content,
                file_type="mermaid",
                title=f"{state.task.get('topic', '')} - 知识图解",
                summary="生成 Mermaid 知识图解",
                execution_report=execution_report,
                metadata={
                    "engine": "mermaid",
                    "render_at": "frontend",
                    "diagram_type": diagram_type,
                },
            )

        except Exception as exc:
            logger.exception("[DiagramAgent] 执行失败")

            execution_report = generate_execution_report(
                agent_type="diagram",
                task=state.task,
                content=None,
                success=False,
                error=str(exc),
            )

            return WorkerResult(success=False, error=str(exc), execution_report=execution_report)

    async def _decide_diagram_type(
        self,
        prompt: str,
        input_text: str,
        state: WorkerState,
    ) -> str | None:
        """决策图解类型。"""
        decision_prompt = f"""{prompt}

## 输入内容
{input_text}

请根据上面的"支持的图解类型"列表，判断是否需要生成图解，并选择最合适的图解类型。如果内容不适合生成图解，请将 need_diagram 设为 false。"""

        try:
            messages = [HumanMessage(content=decision_prompt)]
            validated = await self.llm_manager.ainvoke_structured(
                "spark_x",
                DiagramDecision,
                messages,
                strict=True,
                model_kwargs=self.diagram_model_kwargs,
            )
            if validated.need_diagram and validated.diagram_type in DIAGRAM_MODEL_MAP:
                return validated.diagram_type
            return None
        except Exception as exc:
            logger.warning("[DiagramAgent] 图解类型决策失败: %s", exc)
            return "hierarchy"

    async def _generate_mermaid(
        self,
        diagram_type: str,
        prompt: str,
        input_text: str,
        state: WorkerState,
    ) -> str | None:
        """生成 Mermaid 源码。"""
        if diagram_type not in DIAGRAM_MODEL_MAP:
            logger.warning("[DiagramAgent] 不支持的图解类型: %s", diagram_type)
            return None

        type_desc = DIAGRAM_TYPE_DESCRIPTIONS.get(diagram_type, "")
        mermaid_keyword = MERMAID_DIAGRAM_KEYWORDS.get(diagram_type, "graph TD")

        generation_prompt = f"""{prompt}

## 图解类型
{diagram_type} — {type_desc}

## Mermaid 声明
第一行必须是: {mermaid_keyword}

## 输入内容
{input_text}

请生成 {diagram_type} 类型对应的完整 Mermaid 源码。
只输出 Mermaid 源码，不要输出解释、代码围栏或 JSON 对象格式。
生成完整知识图解，不是 demo、占位示意或两三个节点的简化样例。
覆盖输入中的主要概念、关系、步骤、边界条件或易混点。
节点和连线文本只能使用简短自然语言，不要输出 Markdown、HTML、竖线 `|`、尖括号 `< >`。
节点文本极其简短，不超过 16 个字。
节点数量优先控制在 8 到 18 个原子知识节点，确保图表结构丰富、连线清晰。"""

        try:
            messages = [HumanMessage(content=generation_prompt)]
            response = await self.llm_manager.ainvoke(
                "spark_x",
                messages,
                model_kwargs=self.diagram_model_kwargs,
            )
            content = response.content if hasattr(response, "content") else str(response)
            return build_mermaid_render(content).get("source")
        except Exception as exc:
            logger.warning("[DiagramAgent] Mermaid 图解生成失败: %s", exc)
            return None

    def _build_html_content(self, diagram_data: dict[str, Any]) -> str:
        """构建 HTML 内容。"""
        title = diagram_data.get("title", "知识图解")
        summary = diagram_data.get("summary", "")
        mermaid_source = diagram_data.get("render", {}).get("source", "")
        diagram_type = diagram_data.get("type", "hierarchy")

        height_map = {
            "sequence": "500px",
            "git": "600px",
            "er": "600px",
            "class": "600px",
            "packet": "300px",
        }
        container_height = height_map.get(diagram_type, "500px")

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: #f8fafc;
      background-image: radial-gradient(#e2e8f0 1px, transparent 1px);
      background-size: 20px 20px;
      min-height: 100vh;
      padding: 40px;
      color: #1e293b;
      display: inline-block;
      min-width: 100%;
    }}
    .container {{
      display: inline-block;
      min-width: 600px;
      background: rgba(255, 255, 255, 0.85);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.5);
      border-radius: 24px;
      padding: 30px;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.05), 0 0 0 1px rgba(0, 0, 0, 0.02);
      margin-bottom: 40px;
      margin-right: 40px;
    }}
    .diagram-container {{
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: {container_height};
      overflow: visible;
      padding: 10px;
      background: white;
      border-radius: 16px;
      box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.02);
      border: 1px solid #f1f5f9;
    }}
    .mermaid {{
      max-width: none;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="diagram-container">
      <pre class="mermaid">
{mermaid_source}
      </pre>
    </div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script>
    mermaid.initialize({{
      startOnLoad: true,
      theme: 'base',
      themeVariables: {{
        primaryColor: '#e0e7ff',
        primaryTextColor: '#3730a3',
        primaryBorderColor: '#a5b4fc',
        lineColor: '#6366f1',
        secondaryColor: '#f3e8ff',
        tertiaryColor: '#ede9fe',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
        fontSize: '14px',
        nodeBorder: 'rgba(165, 180, 252, 0.8)'
      }},
      securityLevel: 'loose',
      flowchart: {{
        useMaxWidth: false,
        htmlLabels: true,
        curve: 'monotoneX',
        padding: 20
      }},
      sequence: {{
        useMaxWidth: false,
        wrap: true,
        actorMargin: 50
      }},
      state: {{
        useMaxWidth: false,
        nodeSpacing: 50
      }},
      er: {{
        useMaxWidth: false
      }},
      class: {{
        useMaxWidth: false
      }},
      gitGraph: {{
        useMaxWidth: false
      }}
    }});
  </script>
</body>
</html>"""

    def _load_prompt(self) -> str:
        """加载 prompt 模板。"""
        if self.prompt_path.exists():
            return self.prompt_path.read_text(encoding="utf-8")
        return """你是智能辅导系统中的知识图解生成器。

你的任务是根据学习内容和上下文，直接生成可渲染的 Mermaid 源码。

## 核心要求

1. 你不能生成图片，只能生成 Mermaid 源码。
2. 你必须只输出 Mermaid 源码本身，不要输出解释、标题、代码围栏、注释或对象格式。
3. 图解必须服务于教学理解，必须进行原子化知识拆分。
4. 生成的是完整知识图解，不是 demo、示意占位或两三个节点的简化样例。
5. 必须覆盖用户要求中的主要概念、关系、步骤、边界条件、易混点或关键字段；不要只画标题级摘要。
6. 优先生成 8 到 18 个原子知识节点；如果图类型天然节点较少，也要通过消息、字段、属性、子节点或边补足关键细节。
7. 节点和连线文本使用简短自然语言，不要写 Markdown、HTML 标签、代码块、竖线、尖括号。
8. 图解内容必须与输入内容一致，不要编造输入中不存在的关键事实。

## 支持的图解类型

### 基础图解类型
- hierarchy (层级结构): 用于知识点组成、分类、结构拆解。
- flow (顺序流程): 用于步骤、过程、运行机制。
- compare (对比结构): 用于区别、优缺点、易混概念。
- relation (关系结构): 用于依赖、因果、模块关系。
- sequence (交互时序): 用于交互时序。
- state (状态变化): 用于状态机、生命周期、算法过程。

### 计算机学科专用图表
- class (类图), er (实体关系图), block (方块图), packet (网络包图), git (Git 图)。

### 软件工程教学常用图表
- activity, usecase, component, package, deployment, object, communication。
"""

    async def _build_input(self, state: WorkerState) -> str:
        """构建输入内容。"""
        task = state.task
        personalization = state.personalization
        agent_config = state.agent_config
        profile = state.learner_profile

        parts = [
            "## 课程信息",
            f"- 课程: {task.get('course', '')}",
            f"- 章节: {task.get('chapter', '')}",
            f"- 学习主题: {task.get('topic', task.get('course', ''))}",
            f"- 知识短板: {', '.join(task.get('weak_points', []))}",
            f"- 学习目标: {task.get('learning_goal', '')}",
            "",
            "## 个性化配置",
            f"- 当前水平: {personalization.get('current_level', 'basic')}",
            f"- 目标水平: {personalization.get('target_level', 'understand')}",
            f"- 讲解风格: {personalization.get('explanation_style', 'easy')}",
            "",
            "## Agent 配置",
            f"- 图解类型: {agent_config.get('diagram_type', 'auto')}",
            f"- 视觉风格: {agent_config.get('visual_style', 'minimal')}",
            f"- 包含说明: {agent_config.get('include_explanation', True)}",
            f"- 高亮短板: {agent_config.get('highlight_weak_points', True)}",
        ]

        if profile:
            parts.append("")
            parts.append("## 学习者画像")
            profile_markdown = profile.get("profile_markdown", "")
            if profile_markdown:
                parts.append(profile_markdown)

        if state.upstream_results:
            parts.append("")
            parts.append("## 上游结果摘要")
            for agent_id, result in state.upstream_results.items():
                content_preview = str(result.get("content", ""))[:300]
                parts.append(f"- {agent_id}: {content_preview}...")

        parts.append("")
        parts.append("请生成合适的知识图解。")
        return "\n".join(parts)
