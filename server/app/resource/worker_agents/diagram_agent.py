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
from app.utils.mermaid import build_mermaid_render
from app.chat.schemas import DIAGRAM_MODEL_MAP

logger = get_logger(__name__)

SUPPORTED_DIAGRAM_TYPES = [
    "hierarchy",
    "flow",
    "compare",
    "relation",
    "sequence",
    "state",
    "class",
    "er",
    "block",
    "packet",
    "git",
    "activity",
    "usecase",
    "component",
    "package",
    "deployment",
    "object",
    "communication",
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
    "hierarchy": "flowchart TD",
    "flow": "flowchart TD",
    "compare": "flowchart LR",
    "relation": "flowchart LR",
    "sequence": "sequenceDiagram",
    "state": "stateDiagram-v2",
    "class": "classDiagram",
    "er": "erDiagram",
    "block": "flowchart TB",
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

FLOWCHART_COMPATIBLE_TYPES = {
    "hierarchy",
    "flow",
    "compare",
    "relation",
    "block",
    "activity",
    "usecase",
    "component",
    "package",
    "deployment",
    "object",
    "communication",
}

DIAGRAM_TYPE_GUIDANCE = {
    "hierarchy": "使用 flowchart TD 或 LR。必须有核心主题、上位分类、下位知识点、易错考点，至少 3 个 subgraph。",
    "flow": "使用 flowchart TD。按起点、关键步骤、判断分支、输出结果组织，必须体现顺序、分支和回路。",
    "compare": "使用 flowchart LR。按对比对象、对比维度、相同点、差异点、适用场景组织，至少 3 个维度模块。",
    "relation": "使用 flowchart LR。突出依赖、因果、前置、影响、约束关系，避免只画树状目录。",
    "sequence": "使用 sequenceDiagram。至少 3 个参与者、6 条消息，包含 note over 解释关键阶段，不使用 classDef。",
    "state": "使用 stateDiagram-v2。至少 6 个状态、6 条转移，包含初始、终止、异常或回退路径。",
    "class": "使用 classDiagram。至少 4 个类或接口，包含属性、方法、继承、组合或依赖关系。",
    "er": "使用 erDiagram。至少 4 个实体、3 条关系，每个核心实体至少列出 2 个字段。",
    "block": "优先使用 flowchart TB 模拟模块方块图。至少 3 层模块：入口、核心处理、存储或输出。",
    "packet": "使用 packet-beta 展示字段布局。至少 8 个字段段，覆盖固定字段、标志位、长度或校验字段。",
    "git": "使用 gitGraph。至少 6 个 commit、2 条 branch、2 次 merge 或 checkout，体现开发线与复习线演进。",
    "activity": "使用 flowchart TD 模拟活动图。必须包含开始、动作、判断、并行或回退、结束。",
    "usecase": "使用 flowchart LR 模拟用例图。至少 2 类角色、6 个用例、包含 include 或 extend 语义的连线文本。",
    "component": "使用 flowchart TB 模拟组件图。至少 4 个组件、3 个接口或依赖，分层展示前端、服务、数据或外部系统。",
    "package": "使用 flowchart TB 模拟包图。至少 4 个包、依赖方向清晰，体现公共包、领域包、基础设施包。",
    "deployment": "使用 flowchart TB 模拟部署图。至少 4 个运行节点，包含客户端、服务、数据库、缓存或外部服务。",
    "object": "使用 flowchart TB 模拟对象图。至少 5 个对象实例，体现运行时引用、集合归属或状态值。",
    "communication": "使用 flowchart LR 模拟通信图。至少 4 个对象、6 条编号消息，体现协作顺序和返回关系。",
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
        self.diagram_model_kwargs = {
            "temperature": 0.2,
            "streaming": False,
            "max_tokens": 6000,
        }

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

            quality = self._analyze_mermaid_quality(mermaid_source, diagram_type)
            description = (
                f"教学知识图解：{quality['node_count']} 个知识节点、"
                f"{quality['module_count']} 个模块、{quality['edge_count']} 条关系"
            )

            content = {
                "diagram_type": diagram_type,
                "render_format": state.agent_config.get("render_format", "mermaid"),
                "source": mermaid_source,
                "description": description,
                "quality": quality,
            }

            covered_points = self._extract_diagram_labels(mermaid_source)
            summary_data = {
                "diagram_type": diagram_type,
                "covered_points": covered_points,
                "relation_type": self._infer_relation_type(diagram_type, mermaid_source),
                "node_count": quality["node_count"],
                "edge_count": quality["edge_count"],
                "module_count": quality["module_count"],
                "module_titles": quality["module_titles"],
                "quality_level": quality["quality_level"],
                "has_visual_styles": quality["has_visual_styles"],
            }

            return WorkerResult(
                success=True,
                content=content,
                file_type="mermaid",
                title=title_from_learning_need(state.task, "知识图解"),
                summary=description,
                summary_data=summary_data,
                metadata={
                    "engine": "mermaid",
                    "render_at": "frontend",
                    "diagram_type": diagram_type,
                    "quality": quality,
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
                f"Mermaid 第一行必须是: {MERMAID_DIAGRAM_KEYWORDS.get(requested_type, 'graph TD')}\n"
                f"类型专属要求: {DIAGRAM_TYPE_GUIDANCE.get(requested_type, '')}"
            )
        else:
            type_instruction = (
                "图解类型为 auto。请先在支持的图解类型中选择最适合教学表达的一种，"
                "再直接生成对应 Mermaid 源码。"
            )
        type_quality_instruction = self._build_type_quality_instruction(requested_type)

        generation_prompt = f"""{prompt}

## Single-Shot 输出要求
本次请求必须一次完成"选择图解类型"和"生成 Mermaid 源码"，不要要求二次确认。

{type_instruction}

## 输入内容
{input_text}

## 输出格式
第一行输出: DIAGRAM_TYPE: <类型英文 id>
第二行输出: REASON: <一句话选择理由>
随后输出完整 Mermaid 源码。可以使用 ```mermaid 代码围栏，但不要输出 JSON。

## 图解质量要求
你生成的知识图解不能是简单目录树，必须是教学型知识图解。

### 类型专属要求
{type_quality_instruction}

### 内容要求
每个知识模块至少覆盖以下两类信息：
- 概念定义
- 核心性质
- 操作方法
- 易错点
- 高频考点
- 应用场景
- 复杂度或边界条件

### 排版要求
1. flowchart 兼容类型优先使用 LR 或 TB，并通过 subgraph 分组。
2. sequence、state、class、er、packet、git 必须使用对应 Mermaid 原生语法。
3. 同类知识点必须放入同一个 subgraph。
4. 节点文本不超过 14 个字。
5. 连线文本尽量简短，只说明关键关系。
6. 避免所有节点纵向堆叠。
7. 避免长链条，优先使用模块化分区布局。

### 视觉样式要求
flowchart / graph 兼容类型必须添加 Mermaid classDef 样式，并使用 class 绑定节点样式。
sequence、state、class、er、packet、git 等原生类型如果 Mermaid 语法不支持 classDef，可以不添加样式，但必须通过结构完整性弥补。
至少包含以下样式：
- core：核心主题节点
- module：模块节点或模块关键节点
- key：关键知识点
- warning：易错点、边界条件、高频考点

推荐样式如下：
classDef core fill:#EEF2FF,stroke:#4F46E5,stroke-width:2px,color:#111827;
classDef module fill:#F8FAFC,stroke:#CBD5E1,stroke-width:1px,color:#1E293B;
classDef key fill:#ECFDF5,stroke:#10B981,stroke-width:1px,color:#065F46;
classDef warning fill:#FFF7ED,stroke:#FB923C,stroke-width:1px,color:#9A3412;

### Mermaid 语法限制
1. 只能输出 Mermaid 支持的语法。
2. 节点和连线文本只能使用简短自然语言。
3. 不要输出 Markdown、HTML、竖线 `|`、尖括号 `< >`。
4. 不要使用过长节点文本。
5. 不要输出 demo、占位图或简化示例。
"""

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

            # 质量校验与自动重试。重试失败时保留已生成的可渲染版本，避免质量增强拖垮结果。
            if self._is_poor_mermaid(mermaid_source, diagram_type):
                logger.warning("[DiagramAgent] Mermaid 图解质量不足，准备重试: type=%s", diagram_type)
                retry_prompt = generation_prompt + f"""

## 质量重试要求
上一次生成的图解过于简单或排版不符合要求，请重新生成更完整的教学图解。
必须做到：
{type_quality_instruction}
输出仍然保持 DIAGRAM_TYPE、REASON 和 Mermaid 源码格式。
"""
                try:
                    retry_response = await self.llm_manager.ainvoke(
                        "spark_x",
                        [HumanMessage(content=retry_prompt)],
                        model_kwargs=self.diagram_model_kwargs,
                    )
                    retry_content = retry_response.content if hasattr(retry_response, "content") else str(retry_response)
                    retry_source = self._extract_mermaid_source(retry_content)
                    if retry_source:
                        retry_type = self._extract_diagram_type(retry_content, retry_source, requested_type)
                        if not self._is_poor_mermaid(retry_source, retry_type):
                            return retry_type, retry_source
                        logger.warning("[DiagramAgent] Mermaid 重试后仍质量不足，返回较长版本")
                        if len(retry_source) > len(mermaid_source):
                            return retry_type, retry_source
                except Exception as retry_exc:
                    logger.warning("[DiagramAgent] Mermaid 质量重试失败，保留首版图解: %s", retry_exc)

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
        text = mermaid_source or ""
        first_line = text.strip().splitlines()[0].strip().lower() if text.strip() else ""
        labels: list[str] = []
        if first_line.startswith("sequencediagram"):
            labels.extend(re.findall(r"(?im)^\s*(?:participant|actor)\s+\w+(?:\s+as\s+(.+?))?\s*$", text))
            labels.extend(re.findall(r":\s*([^:\n]{2,40})", text))
        elif first_line.startswith("statediagram"):
            for left, right in re.findall(r"(?m)^\s*([^\s\[\]:]+)\s*-->\s*([^:\n]+)", text):
                labels.extend([left, right.strip().split()[0]])
        elif first_line.startswith("classdiagram"):
            labels.extend(re.findall(r"(?im)^\s*class\s+([A-Za-z][\w-]*)", text))
            labels.extend(re.findall(r"(?m)^\s*[+-]\s*([A-Za-z_][\w_]*)", text))
        elif first_line.startswith("erdiagram"):
            labels.extend(re.findall(r"(?im)^\s*([A-Z][A-Z0-9_]*)\s+\{", text))
            labels.extend(re.findall(r"(?im)^\s+\w+\s+([A-Za-z_][\w_]*)", text))
        elif first_line.startswith("packet-beta"):
            labels.extend(re.findall(r'(?m)^\s*\d+(?:-\d+)?\s*:\s*"?([^"\n]{2,40})"?', text))
        elif first_line.startswith("gitgraph"):
            labels.extend(re.findall(r'id:\s*"([^"]{2,40})"', text))
        else:
            labels.extend(re.findall(r"[\[({]\"?([^\[\]{}()\"<>|]{2,40})\"?[\])}]", text))

        cleaned = [re.sub(r"\s+", " ", item).strip() for item in labels]
        ignored = {"[*]", "as"}
        return list(dict.fromkeys(item for item in cleaned if item and item not in ignored))[:16]

    def _infer_relation_type(self, diagram_type: str, mermaid_source: str) -> str:
        """按图类型给最终资源包提供轻量关系描述。"""
        if diagram_type in {"sequence", "activity", "flow"}:
            return "流程"
        if diagram_type == "state" or "stateDiagram" in mermaid_source:
            return "状态变化"
        if diagram_type in {"class", "er", "component", "package", "deployment", "object"}:
            return "结构依赖"
        if diagram_type in {"packet", "git"}:
            return "结构演进"
        if diagram_type in {"compare", "relation"}:
            return "对比/关系"
        return "结构"

    def _build_type_quality_instruction(self, requested_type: str | None) -> str:
        """生成按图类型区分的质量要求，避免所有图都套用 flowchart 标准。"""
        common = (
            "1. 不允许输出 demo、占位图或两三个节点的简化示例。\n"
            "2. 必须覆盖定义、关键性质、操作过程、易错边界和高频考点中的至少三类信息。\n"
            "3. 节点或字段文本必须短，避免长句和 Markdown。"
        )
        if requested_type:
            return f"{common}\n4. {DIAGRAM_TYPE_GUIDANCE.get(requested_type, '')}"

        all_types = "\n".join(
            f"- {diagram_type}: {DIAGRAM_TYPE_GUIDANCE[diagram_type]}"
            for diagram_type in SUPPORTED_DIAGRAM_TYPES
        )
        return f"{common}\n4. auto 选择类型后必须严格遵守对应规则：\n{all_types}"

    def _extract_subgraph_titles(self, mermaid_source: str) -> list[str]:
        """提取 Mermaid subgraph 标题，用于前端展示模块摘要。"""
        titles: list[str] = []
        for line in (mermaid_source or "").splitlines():
            match = re.match(r"^\s*subgraph\s+(?:[A-Za-z][\w-]*\s*)?(?:\[(.*?)\]|\"(.*?)\"|(.+?))\s*$", line)
            if not match:
                continue
            title = next((part for part in match.groups() if part), "")
            title = re.sub(r"\s+", " ", title).strip()
            if title and title.lower() != "end":
                titles.append(title)
        return list(dict.fromkeys(titles))[:8]

    def _analyze_mermaid_quality(self, source: str, diagram_type: str) -> dict[str, Any]:
        """计算图解质量指标，供后端质量门槛和前端摘要复用。"""
        text = source or ""
        first_line = text.strip().splitlines()[0].strip().lower() if text.strip() else ""
        is_sequence = diagram_type == "sequence" or first_line.startswith("sequencediagram")
        is_state = diagram_type == "state" or first_line.startswith("statediagram")
        is_class = diagram_type == "class" or first_line.startswith("classdiagram")
        is_er = diagram_type == "er" or first_line.startswith("erdiagram")
        is_packet = diagram_type == "packet" or first_line.startswith("packet-beta")
        is_git = diagram_type == "git" or first_line.startswith("gitgraph")

        flow_nodes = set(re.findall(r"\b([A-Za-z][A-Za-z0-9_]*)\s*[\[\(\{]", text))
        subgraph_titles = self._extract_subgraph_titles(text)
        class_defs = set(re.findall(r"(?im)^\s*class\s+([A-Za-z][A-Za-z0-9_,\s]*)\s+\w+\s*;?\s*$", text))

        if is_sequence:
            participants = set(re.findall(r"(?im)^\s*(?:participant|actor)\s+([A-Za-z][\w-]*)\b", text))
            messages = re.findall(r"(?:->>|-->>|-\)|--\)|->|-->)", text)
            node_count = len(participants) + len(messages)
            edge_count = len(messages)
            module_count = max(1, len(participants))
        elif is_state:
            states = set()
            for left, right in re.findall(r"(?m)^\s*([^\s\[\]:]+)\s*-->\s*([^:\n]+)", text):
                if left != "[*]":
                    states.add(left.strip())
                target = right.strip().split()[0]
                if target and target != "[*]":
                    states.add(target)
            states.update(
                state.strip()
                for state in re.findall(r"(?im)^\s*state\s+\"?.+?\"?\s+as\s+([A-Za-z][\w-]*)", text)
            )
            node_count = len(states)
            edge_count = len(re.findall(r"-->", text))
            module_count = max(1, len(re.findall(r"(?im)^\s*state\s+", text)) or len(subgraph_titles))
        elif is_class:
            classes = set(re.findall(r"(?im)^\s*class\s+([A-Za-z][\w-]*)", text))
            classes.update(re.findall(r"\b([A-Za-z][\w-]*)\s*(?:<\|--|\*--|o--|-->)", text))
            classes.update(re.findall(r"(?:<\|--|\*--|o--|-->)\s*([A-Za-z][\w-]*)", text))
            node_count = len(classes)
            edge_count = len(re.findall(r"<\|--|\*--|o--|-->", text))
            module_count = max(1, len(classes))
        elif is_er:
            entities = set()
            entities.update(re.findall(r"(?im)^\s*([A-Z][A-Z0-9_]*)\s+\{", text))
            for left, right in re.findall(r"(?im)^\s*([A-Z][A-Z0-9_]*)\s+[|o}{\w-]+--[|o}{\w-]+\s+([A-Z][A-Z0-9_]*)\s*:", text):
                entities.add(left)
                entities.add(right)
            relationships = re.findall(r"[|o}{\w-]+--[|o}{\w-]+", text)
            fields = re.findall(r"(?im)^\s+\w+\s+\w+", text)
            node_count = len(entities) + len(fields)
            edge_count = len(relationships)
            module_count = max(1, len(entities))
        elif is_packet:
            segments = re.findall(r"(?im)^\s*\d+(?:-\d+)?\s*:", text)
            node_count = len(segments)
            edge_count = max(0, len(segments) - 1)
            module_count = max(1, len({segment.split("-")[0].split(":")[0].strip() for segment in segments}) // 3)
        elif is_git:
            commits = re.findall(r"(?im)^\s*commit\b", text)
            branches = re.findall(r"(?im)^\s*branch\s+([A-Za-z][\w-]*)", text)
            transitions = re.findall(r"(?im)^\s*(?:checkout|merge)\b", text)
            merges = re.findall(r"(?im)^\s*merge\b", text)
            node_count = len(commits) + len(merges)
            edge_count = max(0, len(commits) - 1) + len(transitions)
            module_count = max(1, 1 + len(set(branches)))
        else:
            node_count = len(flow_nodes)
            edge_count = len(re.findall(r"-->|---|-.->|==>|--\s+[^-\n]+?\s+-->", text))
            module_count = len(subgraph_titles)

        has_visual_styles = "classDef" in text and bool(class_defs or re.search(r"(?im)^\s*class\s+", text))
        score = 0
        if (
            node_count >= 12
            or (is_sequence and node_count >= 8)
            or (is_state and node_count >= 6)
            or (is_class and node_count >= 4)
            or (is_er and node_count >= 10)
            or (is_packet and node_count >= 8)
            or (is_git and node_count >= 5)
        ):
            score += 1
        if (
            edge_count >= 10
            or (is_sequence and edge_count >= 5)
            or (is_state and edge_count >= 5)
            or (is_class and edge_count >= 3)
            or (is_er and edge_count >= 3)
            or (is_packet and edge_count >= 7)
            or (is_git and edge_count >= 6)
        ):
            score += 1
        if (
            module_count >= 3
            or is_sequence
            or is_state
            or is_class
            or is_er
            or is_packet
            or is_git
        ):
            score += 1
        if has_visual_styles or is_sequence or is_state or is_class or is_er or is_packet or is_git:
            score += 1

        if score >= 4:
            quality_level = "complete"
        elif score == 3:
            quality_level = "rich"
        elif score == 2:
            quality_level = "basic"
        else:
            quality_level = "thin"

        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "module_count": module_count,
            "module_titles": subgraph_titles,
            "has_visual_styles": has_visual_styles,
            "quality_level": quality_level,
        }

    def _is_poor_mermaid(self, source: str, diagram_type: str) -> bool:
        """判断 Mermaid 图解是否过于简单。"""
        metrics = self._analyze_mermaid_quality(source, diagram_type)
        # 只对 flowchart / graph 类型强制检查 subgraph 和样式。
        if diagram_type == "sequence":
            return metrics["module_count"] < 2 or metrics["edge_count"] < 3
        if diagram_type == "state":
            return metrics["node_count"] < 5 or metrics["edge_count"] < 5
        if diagram_type == "class":
            return metrics["node_count"] < 4 or metrics["edge_count"] < 2
        if diagram_type == "er":
            return metrics["node_count"] < 8 or metrics["edge_count"] < 3
        if diagram_type == "packet":
            return metrics["node_count"] < 8
        if diagram_type == "git":
            return metrics["node_count"] < 5 or metrics["edge_count"] < 5

        if metrics["node_count"] < 12:
            return True
        if metrics["edge_count"] < 10:
            return True
        if diagram_type in FLOWCHART_COMPATIBLE_TYPES and metrics["module_count"] < 3:
            return True
        if diagram_type in FLOWCHART_COMPATIBLE_TYPES and not metrics["has_visual_styles"]:
            return True
        return False

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
6. 优先生成 16 到 28 个原子知识节点。对于 flowchart 或 graph 类型，必须使用 subgraph 进行模块分组，并添加 classDef 样式。
7. 节点和连线文本使用简短自然语言，不要写 Markdown、HTML 标签、代码块、竖线、尖括号。
8. 图解内容必须与输入内容一致，不要编造输入中不存在的关键事实。
9. 图解必须体现教学价值，不允许只生成简单目录树。应该包含核心主题、知识模块、具体知识点、易错点和高频考点。

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
