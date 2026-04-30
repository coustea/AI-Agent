"""
知识图解 Agent — 结构化图解生成 Agent。

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

后端渲染 Mermaid 为 PNG 图片并保存。
"""

from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.schemas import WorkerState, WorkerResult
from app.resource.worker_agents.utils import (
    write_agent_artifact,
    get_workspace_dir,
    read_agent_report,
)
from app.resource.worker_agents.reporter_agent import ReporterAgent
from app.resource.mermaid_renderer import render_mermaid_to_png
from app.chat.diagram_render import build_diagram_render
from app.chat.schemas import DIAGRAM_MODEL_MAP, DiagramDecision
from app.shared.json_utils import parse_first_json_object

logger = get_logger(__name__)

# 支持的图解类型
SUPPORTED_DIAGRAM_TYPES = list(DIAGRAM_MODEL_MAP.keys())

# 图解类型描述（用于决策提示）
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


class DiagramAgent:
    """知识图解 Agent。"""

    def __init__(self, user_id: int, resource_id: int, emitter=None):
        self.user_id = user_id
        self.resource_id = resource_id
        self.emitter = emitter
        self.llm_manager = get_llm_manager()
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "workers" / "diagram.md"
        # 图解生成模型参数
        self.diagram_model_kwargs = {"temperature": 0.1, "streaming": False, "max_tokens": 2000}

    async def _emit_action(self, action: str, detail: str = "") -> None:
        """发送 Agent 动作事件。"""
        if self.emitter:
            await self.emitter.emit_agent_action("diagram", action, detail)

    async def run(self, state: WorkerState) -> WorkerResult:
        """执行知识图解生成。"""
        logger.info("[DiagramAgent] 开始执行: topic=%s", state.task.get("course", ""))

        # 发送加载提示词事件
        await self._emit_action("loading_prompt", "加载知识图解生成提示词")

        # 加载 prompt
        prompt = self._load_prompt()

        # 发送构建输入事件
        await self._emit_action("building_input", "构建输入内容")

        # 构建输入
        input_text = await self._build_input(state)

        # 获取用户指定的图解类型（可选）
        diagram_type = state.parameters.get("diagram_type") if state.parameters else None

        try:
            # 1. 决策图解类型（如果用户未指定）
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

            # 2. 生成图解数据
            await self._emit_action("calling_llm", f"调用 DeepSeek 生成 {diagram_type} 类型图解")
            diagram_data = await self._generate_diagram(diagram_type, prompt, input_text, state)

            if not diagram_data:
                return WorkerResult(success=False, error="图解生成失败")

            # 3. 构建 Mermaid 渲染
            rendered = diagram_data.copy()
            rendered["render"] = build_diagram_render(rendered)
            mermaid_source = rendered.get("render", {}).get("source", "")

            # 4. 后端渲染为精美海报 PNG
            workspace_dir = get_workspace_dir(self.user_id, self.resource_id)
            png_path = workspace_dir / "diagram.png"

            try:
                # 5. 构建包含排版样式的 HTML 内容
                html_content = self._build_html_content(rendered)

                await self._emit_action("rendering_png", "使用 Playwright 渲染精美海报 PNG")
                
                # 将这个 HTML 直接截取为 PNG（包含容器和样式）
                from app.resource.mermaid_renderer import render_html_to_png
                png_bytes, png_path = await render_html_to_png(
                    html_content,
                    output_path=png_path,
                )
                logger.info("[DiagramAgent] PNG 海报已生成: %s, 大小: %d bytes", png_path, len(png_bytes))

                # 6. 同时保存 Mermaid 源码（供前端可选渲染）
                mermaid_path = await write_agent_artifact(
                    self.user_id, self.resource_id, "diagram", mermaid_source, file_type="mermaid"
                )

                # 7. 写入 HTML 产物
                await self._emit_action("saving_artifact", f"保存知识图解产物 ({len(html_content)} 字符)")
                artifact_path = await write_agent_artifact(
                    self.user_id, self.resource_id, "diagram", html_content, file_type="html"
                )

                # 8. 后台生成执行报告
                asyncio.create_task(
                    self._generate_report_async(state.task, diagram_data)
                )

                return WorkerResult(
                    success=True,
                    content=html_content,
                    artifact_path=str(png_path),  # 返回 PNG 路径作为主要产物
                    artifact_dir=str(workspace_dir),
                    file_type="png",
                )

            except Exception as render_exc:
                logger.warning("[DiagramAgent] PNG 渲染失败，降级为 HTML: %s", render_exc)

                # 降级：直接生成 HTML（前端渲染 Mermaid）
                html_content = self._build_html_content(rendered)
                artifact_path = await write_agent_artifact(
                    self.user_id, self.resource_id, "diagram", html_content, file_type="html"
                )

                asyncio.create_task(
                    self._generate_report_async(state.task, diagram_data)
                )

                return WorkerResult(
                    success=True,
                    content=html_content,
                    artifact_path=artifact_path,
                    artifact_dir=str(workspace_dir),
                    file_type="html",
                )

        except Exception as exc:
            logger.exception("[DiagramAgent] 执行失败")

            # 后台生成失败报告
            asyncio.create_task(
                self._generate_report_async(state.task, {}, error=str(exc))
            )

            return WorkerResult(success=False, error=str(exc))

    async def _decide_diagram_type(
        self,
        prompt: str,
        input_text: str,
        state: WorkerState,
    ) -> str | None:
        """决策图解类型。"""
        # 构建图解类型列表描述
        type_list = "\n".join([f"- {k}: {v}" for k, v in DIAGRAM_TYPE_DESCRIPTIONS.items()])

        decision_prompt = f"""{prompt}

## 可选图解类型

{type_list}

## 输入内容
{input_text}

请判断是否需要生成图解，并选择最合适的图解类型。如果内容不适合生成图解，请将 need_diagram 设为 false。"""

        try:
            messages = [HumanMessage(content=decision_prompt)]
            validated = await self.llm_manager.ainvoke_structured(
                "deepseek",
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
            # 降级：默认使用 hierarchy
            return "hierarchy"

    async def _generate_diagram(
        self,
        diagram_type: str,
        prompt: str,
        input_text: str,
        state: WorkerState,
    ) -> dict[str, Any] | None:
        """生成指定类型的图解数据。"""
        model_cls = DIAGRAM_MODEL_MAP.get(diagram_type)
        if model_cls is None:
            logger.warning("[DiagramAgent] 不支持的图解类型: %s", diagram_type)
            return None

        type_desc = DIAGRAM_TYPE_DESCRIPTIONS.get(diagram_type, "")
        generation_prompt = f"""{prompt}

## 图解类型
{diagram_type} — {type_desc}

## 输入内容
{input_text}

请生成 {diagram_type} 类型的结构化图解。"""

        try:
            messages = [HumanMessage(content=generation_prompt)]
            validated = await self.llm_manager.ainvoke_structured(
                "deepseek",
                model_cls,
                messages,
                strict=True,
                model_kwargs=self.diagram_model_kwargs,
            )
            payload = validated.model_dump(by_alias=True)
            payload = self._normalize_diagram_payload(model_cls, payload)
            return payload
        except Exception as exc:
            logger.warning("[DiagramAgent] 结构化生成失败，尝试宽松解析: %s", exc)
            # 兼容宽松 JSON 解析
            try:
                response = await self.llm_manager.ainvoke(
                    "deepseek",
                    [HumanMessage(content=generation_prompt)],
                    model_kwargs={
                        **self.diagram_model_kwargs,
                        "response_format": {"type": "json_object"},
                    },
                )
                content = response.content if hasattr(response, "content") else str(response)
                payload = parse_first_json_object(content)
                if payload:
                    payload = self._normalize_diagram_payload(model_cls, payload)
                    return model_cls.model_validate(payload).model_dump(by_alias=True)
            except Exception as inner_exc:
                logger.warning("[DiagramAgent] 图解生成失败: %s", inner_exc)
                return None

    @staticmethod
    def _trim_text(value: Any, max_len: int) -> Any:
        """截断文本。"""
        if not isinstance(value, str):
            return value
        value = value.strip()
        if len(value) <= max_len:
            return value
        return value[:max_len]

    @classmethod
    def _trim_mapping_fields(cls, mapping: dict[str, Any], limits: dict[str, int]) -> dict[str, Any]:
        """截断字典字段。"""
        for key, limit in limits.items():
            if key in mapping:
                mapping[key] = cls._trim_text(mapping.get(key), limit)
        return mapping

    @classmethod
    def _normalize_diagram_payload(cls, model_cls: type[Any], payload: dict[str, Any]) -> dict[str, Any]:
        """规范化图解数据。"""
        payload = dict(payload)
        cls._trim_mapping_fields(payload, {"title": 20, "summary": 50})

        if model_cls.__name__ == "HierarchyDiagram" and "spec" not in payload:
            nodes = payload.pop("nodes", None)
            if isinstance(nodes, list) and nodes and isinstance(nodes[0], dict):
                payload["spec"] = {"root": nodes[0]}

        spec = payload.get("spec")
        if not isinstance(spec, dict):
            return payload

        # 层级图特殊处理
        if model_cls.__name__ == "HierarchyDiagram":
            def _walk(node: dict[str, Any]) -> None:
                cls._trim_mapping_fields(node, {"label": 16, "description": 40})
                children = node.get("children")
                if isinstance(children, list):
                    for child in children:
                        if isinstance(child, dict):
                            _walk(child)

            root = spec.get("root")
            if isinstance(root, dict):
                _walk(root)
            return payload

        # 通用列表字段截断
        list_field_limits = {
            "steps": {"label": 16, "description": 40},
            "nodes": {"label": 16, "description": 40},
            "states": {"label": 16, "description": 40},
            "actors": {"label": 16, "description": 40},
            "items": {"label": 16, "description": 40},
            "edges": {"label": 16, "description": 40},
            "messages": {"label": 16, "description": 40},
            "transitions": {"label": 16, "description": 40},
            "classes": {"name": 40, "annotation": 20},
            "entities": {"name": 40},
            "fields": {"name": 20, "type": 20},
            "blocks": {"label": 16},
            "commits": {"id": 40, "name": 40, "tag": 20},
            "activities": {"label": 16, "description": 40},
            "usecases": {"label": 16},
            "components": {"label": 16},
            "packages": {"label": 16},
            "objects": {"name": 20},
            "links": {"label": 16},
            "connections": {"label": 16},
            "relationships": {"label": 16},
        }
        for field_name, limits in list_field_limits.items():
            values = spec.get(field_name)
            if isinstance(values, list):
                for item in values:
                    if isinstance(item, dict):
                        cls._trim_mapping_fields(item, limits)

        return payload

    def _build_html_content(self, rendered: dict[str, Any]) -> str:
        """构建 HTML 内容，包含 Mermaid 渲染。"""
        title = rendered.get("title", "知识图解")
        summary = rendered.get("summary", "")
        mermaid_source = rendered.get("render", {}).get("source", "")
        diagram_type = rendered.get("type", "hierarchy")

        # 根据图解类型选择合适的容器高度
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

    async def _generate_report_async(
        self,
        task: dict[str, Any],
        diagram_data: dict[str, Any],
        error: str | None = None,
    ) -> None:
        """后台异步生成执行报告。"""
        try:
            reporter = ReporterAgent()
            report_path, _ = await reporter.generate_report(
                user_id=self.user_id,
                resource_id=self.resource_id,
                agent_type="diagram",
                task=task,
                content=str(diagram_data),
                error=error,
            )
            logger.info("[DiagramAgent] 报告已生成: %s", report_path)
        except Exception as exc:
            logger.warning("[DiagramAgent] 报告生成失败: %s", exc)

    def _load_prompt(self) -> str:
        """加载 prompt 模板。"""
        if self.prompt_path.exists():
            return self.prompt_path.read_text(encoding="utf-8")
        return """你是智能辅导系统中的知识图解生成器。

你的任务是根据学习内容和上下文，生成适合前端渲染的结构化图解对象。

重要要求：
- 你不能生成图片
- 你只能生成结构化图解数据
- 你必须只返回一个合法 JSON 对象
- 不要输出 Markdown 代码块
- 不要输出解释文字、前后缀、注释或任何 JSON 之外的内容
- 图解必须服务于教学理解，必须进行【原子化知识拆分】
- 绝对不要在单个节点内堆砌大段文字
- title 不超过 20 个字
- summary 不超过 50 个字
- label 极其简短，不超过 10 个字。如果有较长文字，使用 <br/> 换行或放入 description
- description 不超过 40 个字
- 节点数量控制在 8 到 25 个左右，确保图表结构丰富、连线清晰"""

    async def _build_input(self, state: WorkerState) -> str:
        """构建输入内容。"""
        task = state.task
        parts = [
            f"## 主题: {task.get('course', '')}",
            f"## 知识点: {task.get('gap', '')}",
        ]

        # 读取依赖 Agent 的报告
        if state.dependencies:
            parts.append(f"\n## 参考内容（来自前置 Agent 的执行报告）")
            for dep_name in state.dependencies:
                report = await read_agent_report(
                    self.user_id, self.resource_id, dep_name
                )
                if report:
                    parts.append(f"\n### {dep_name} 报告")
                    parts.append(report)

        parts.append("\n请生成合适的知识图解。")
        return "\n".join(parts)
