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

import re
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.schemas import WorkerState, WorkerResult
from app.resource.worker_agents.utils import (
    AgentContextBuilder,
    append_backend_context_for_prompt,
    learning_need_from_task,
    title_from_learning_need,
)
from app.shared.diagram_render import build_mermaid_render
from app.chat.schemas import DIAGRAM_MODEL_MAP

logger = get_logger(__name__)

SUPPORTED_DIAGRAM_TYPES = [
    "hierarchy",
    "flow",
    "compare",
    "relation",
    "state",
    "class",
    "block",
    "packet",
    "sequence",
    "activity",
    "component",
]

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

    STEPS = ["分析输入", "融合画像与依赖", "生成内容", "整理输出"]
    ROLE_NAME = "原理可视化图解智能体"

    def __init__(self, user_id: int, resource_id: int, emitter=None):
        self.user_id = user_id
        self.resource_id = resource_id
        self.emitter = emitter
        self.llm_manager = get_llm_manager()
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "workers" / "diagram.md"
        self.diagram_model_kwargs = {"temperature": 0.1, "streaming": False, "max_tokens": 4000}

    async def _emit_action(
        self,
        state: WorkerState,
        action: str,
        detail: str = "",
        current_step: int = 0,
        total_steps: int = 0,
        step_label: str = "",
        current_action: str = "",
    ) -> None:
        """发送 Agent 动作事件。"""
        if self.emitter:
            await self.emitter.emit_agent_action(
                state.agent_name,
                action,
                detail,
                current_step=current_step,
                total_steps=total_steps,
                step_label=step_label,
                current_action=current_action,
                layer=state.layer_index,
                layer_name="认知建构层",
                agent_role=self.ROLE_NAME,
                resource_type=state.agent_name,
            )

    async def run(self, state: WorkerState) -> WorkerResult:
        """执行知识图解生成。"""
        logger.info("[DiagramAgent] 开始执行: learning_need=%s", learning_need_from_task(state.task)[:80])
        total = 5

        await self._emit_action(
            state,
            "analyze_input",
            "原理可视化图解智能体正在分析学习需求",
            current_step=2,
            total_steps=total,
            step_label=self.STEPS[0],
            current_action="分析图解目标",
        )
        prompt = self._load_prompt()

        await self._emit_action(
            state,
            "merge_profile_dependencies",
            "原理可视化图解智能体正在融合画像和依赖信息",
            current_step=3,
            total_steps=total,
            step_label=self.STEPS[1],
            current_action="融合画像与依赖",
        )
        input_text = await self._build_input(state)

        # 从 agent_config 获取 diagram_type
        diagram_type = state.agent_config.get("diagram_type") if state.agent_config else None
        if diagram_type == "auto":
            diagram_type = None

        try:
            requested_type = diagram_type
            action_detail = f"正在为你生成 {requested_type} 类型图解..." if requested_type else "正在自动选择图解类型并生成 Mermaid..."
            await self._emit_action(
                state,
                "generate_content",
                action_detail,
                current_step=4,
                total_steps=total,
                step_label=self.STEPS[2],
                current_action="生成 Mermaid 图解",
            )
            generation = await self._generate_mermaid_single_shot(requested_type, prompt, input_text)
            if generation is None:
                return WorkerResult(success=False, error="图解生成失败")

            diagram_type, mermaid_source = generation
            logger.info("[DiagramAgent] 选择图解类型: %s", diagram_type)

            if not mermaid_source:
                return WorkerResult(success=False, error="图解生成失败")
            logger.info("[DiagramAgent] 知识图解生成完毕!!!")
            await self._emit_action(
                state,
                "finalize_output",
                f"原理可视化图解智能体正在整理输出 ({len(mermaid_source)} 字符)",
                current_step=5,
                total_steps=total,
                step_label=self.STEPS[3],
                current_action="整理图解资源",
            )

            content = {
                "diagram_type": diagram_type,
                "render_format": state.agent_config.get("render_format", "mermaid"),
                "source": mermaid_source,
                "description": "知识图解",
            }

            covered_points = self._extract_diagram_labels(mermaid_source)
            summary_data = {
                "diagram_type": diagram_type,
                "covered_points": covered_points,
                "relation_type": self._infer_relation_type(diagram_type, mermaid_source),
            }

            return WorkerResult(
                success=True,
                content=content,
                file_type="mermaid",
                title=title_from_learning_need(state.task, "知识图解"),
                summary="生成 Mermaid 知识图解",
                summary_data=summary_data,
                metadata={
                    "engine": "mermaid",
                    "render_at": "frontend",
                    "diagram_type": diagram_type,
                },
            )

        except Exception as exc:
            logger.exception("[DiagramAgent] 执行失败")
            return WorkerResult(success=False, error=str(exc))

    async def _generate_mermaid_single_shot(
        self,
        requested_type: str | None,
        prompt: str,
        input_text: str,
    ) -> tuple[str, str] | None:
        """一次 LLM 调用内完成图解类型选择和 Mermaid 源码生成。"""
        if requested_type and requested_type not in SUPPORTED_DIAGRAM_TYPES:
            logger.warning("[DiagramAgent] 不支持的图解类型: %s", requested_type)
            requested_type = None

        if requested_type:
            type_instruction = (
                f"用户指定图解类型: {requested_type} — {DIAGRAM_TYPE_DESCRIPTIONS.get(requested_type, '')}\n"
                f"Mermaid 第一行必须是: {MERMAID_DIAGRAM_KEYWORDS.get(requested_type, 'graph TD')}"
            )
        else:
            type_instruction = (
                "图解类型为 auto。请先在支持的图解类型中选择最适合教学表达的一种，"
                "再直接生成对应 Mermaid 源码。"
            )

        generation_prompt = f"""{prompt}

## Single-Shot 输出要求
本次请求必须一次完成“选择图解类型”和“生成 Mermaid 源码”，不要要求二次确认。

{type_instruction}

## 输入内容
{input_text}

## 输出格式
第一行输出: DIAGRAM_TYPE: <类型英文 id>
第二行输出: REASON: <一句话选择理由>
随后输出完整 Mermaid 源码。可以使用 ```mermaid 代码围栏，但不要输出 JSON。

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
            mermaid_source = self._extract_mermaid_source(content)
            if not mermaid_source:
                return None
            diagram_type = self._extract_diagram_type(content, mermaid_source, requested_type)
            return diagram_type, mermaid_source
        except Exception as exc:
            logger.warning("[DiagramAgent] Mermaid 图解生成失败: %s", exc)
            return None

    def _extract_mermaid_source(self, raw_content: str) -> str:
        """从 single-shot 响应中提取 Mermaid，容忍类型说明前缀。"""
        try:
            return build_mermaid_render(raw_content).get("source", "")
        except ValueError:
            lines = str(raw_content or "").splitlines()
            for index, line in enumerate(lines):
                if re.match(
                    r"^\s*(flowchart|graph|sequenceDiagram|stateDiagram-v2|classDiagram|erDiagram|block-beta|packet-beta|gitGraph)\b",
                    line,
                    re.IGNORECASE,
                ):
                    return build_mermaid_render("\n".join(lines[index:])).get("source", "")
            raise

    def _extract_diagram_type(self, raw_content: str, mermaid_source: str, requested_type: str | None) -> str:
        """从 single-shot 响应或 Mermaid 声明中恢复图解类型。"""
        if requested_type in SUPPORTED_DIAGRAM_TYPES:
            return requested_type

        match = re.search(r"(?im)^\s*DIAGRAM_TYPE\s*[:：]\s*([a-z_][\w-]*)\s*$", raw_content or "")
        if match:
            candidate = match.group(1).strip().lower().replace("-", "_")
            if candidate in SUPPORTED_DIAGRAM_TYPES:
                return candidate

        first_line = (mermaid_source or "").strip().splitlines()[0].strip().lower()
        keyword_type_pairs = sorted(
            MERMAID_DIAGRAM_KEYWORDS.items(),
            key=lambda item: len(item[1]),
            reverse=True,
        )
        for diagram_type, keyword in keyword_type_pairs:
            if first_line.startswith(keyword.lower()):
                return diagram_type
        return "hierarchy"

    def _extract_diagram_labels(self, mermaid_source: str) -> list[str]:
        """从 Mermaid 节点标签中提取可复用知识点摘要。"""
        labels = re.findall(r"[\[({]\"?([^\[\]{}()\"<>|]{2,40})\"?[\])}]", mermaid_source or "")
        cleaned = [re.sub(r"\s+", " ", item).strip() for item in labels]
        return list(dict.fromkeys(item for item in cleaned if item))[:8]

    def _infer_relation_type(self, diagram_type: str, mermaid_source: str) -> str:
        """按图类型给最终资源包提供轻量关系描述。"""
        if diagram_type in {"sequence", "activity", "flow"}:
            return "流程"
        if diagram_type == "state" or "stateDiagram" in mermaid_source:
            return "状态变化"
        if diagram_type in {"compare", "relation"}:
            return "对比/关系"
        return "结构"

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
        agent_config = state.agent_config

        parts = [
            "## 学习需求",
            learning_need_from_task(task),
            "",
            "## 学习场景",
            f"- 场景类型: {state.learning_scenario}",
            "",
            "## Agent 配置",
            f"- 图解类型: {agent_config.get('diagram_type', 'auto')}",
            f"- 视觉风格: {agent_config.get('visual_style', 'minimal')}",
            f"- 高亮模式: {agent_config.get('highlight_mode', 'key_points')}",
            f"- 细节级别: {agent_config.get('detail_level', 'standard')}",
        ]

        # Use AgentContextBuilder for context-aware prompt building
        builder = AgentContextBuilder()
        context_text = builder.build_for_agent("diagram", state)
        if context_text:
            parts.append("")
            parts.append(context_text)
        append_backend_context_for_prompt(parts, state)

        parts.append("")
        parts.append("请生成合适的知识图解。")
        return "\n".join(parts)
