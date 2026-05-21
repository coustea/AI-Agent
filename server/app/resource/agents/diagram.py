"""
图表 Agent — 生成 Mermaid 图表代码。

支持 18 种图表类型，包含质量检测和重试逻辑。
"""

from __future__ import annotations

import re

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.agents.base import Agent
from app.resource.schemas import WorkerResult, WorkerState

logger = get_logger(__name__)

# Mermaid 关键字集合，用于质量检测
_MERMAID_KEYWORDS = {
    "graph", "flowchart", "sequenceDiagram", "classDiagram",
    "stateDiagram", "erDiagram", "gantt", "pie", "gitGraph",
    "mindmap", "timeline", "quadrantChart", "sankey",
    "block", "packet", "architecture",
}

# 图表类型 → Mermaid 语法提示
_DIAGRAM_SYNTAX_HINTS: dict[str, str] = {
    "hierarchy": "使用 graph TD 或 flowchart TD",
    "flow": "使用 flowchart TD/LR",
    "compare": "使用 flowchart LR 或 subgraph 分组对比",
    "relation": "使用 graph TD 或 erDiagram",
    "state": "使用 stateDiagram-v2",
    "class": "使用 classDiagram",
    "er": "使用 erDiagram",
    "block": "使用 block-beta",
    "packet": "使用 packet-beta",
    "git": "使用 gitGraph",
    "sequence": "使用 sequenceDiagram",
    "activity": "使用 flowchart TD 配合特殊节点样式",
    "usecase": "使用 flowchart LR",
    "component": "使用 flowchart TD 或 architecture",
    "package": "使用 flowchart TD 配合 subgraph",
    "deployment": "使用 flowchart TD",
    "object": "使用 flowchart TD",
    "communication": "使用 sequenceDiagram",
}


class DiagramAgent(Agent):
    """图表生成 Agent。"""

    AGENT_NAME = "diagram"
    ROLE_NAME = "图表生成智能体"
    STEPS = ["分析输入", "融合画像与依赖", "生成图表", "质量检测与整理"]

    def _default_template_values(self) -> dict[str, str]:
        return {
            "diagram_type": "auto",
            "visual_style": "minimal",
            "highlight_mode": "key_points",
            "detail_level": "standard",
        }

    async def _generate(self, state: WorkerState, prompt: str, input_text: str) -> WorkerResult:
        diagram_type = state.agent_config.get("diagram_type", "auto")
        visual_style = state.agent_config.get("visual_style", "minimal")
        highlight_mode = state.agent_config.get("highlight_mode", "key_points")
        detail_level = state.agent_config.get("detail_level", "standard")

        # 自动推断图表类型
        if diagram_type == "auto":
            diagram_type = self._infer_diagram_type(state)

        # 构建图表专用指令
        diagram_instruction = self._build_diagram_instruction(diagram_type, visual_style, highlight_mode, detail_level)
        full_input = f"{input_text}\n\n{diagram_instruction}"

        llm = get_llm()

        # 第一次生成
        mermaid_code = await self._generate_mermaid(llm, prompt, full_input, diagram_type)

        # 质量检测
        quality_ok, quality_detail = self._check_quality(mermaid_code, diagram_type)

        # 重试 (最多 1 次)
        if not quality_ok:
            logger.info("[DiagramAgent] 质量检测未通过 (%s)，重试生成", quality_detail)
            retry_hint = f"上一次生成的图表质量不佳: {quality_detail}。请重新生成，确保使用正确的 Mermaid 语法。"
            mermaid_code = await self._generate_mermaid(llm, prompt, full_input, diagram_type, extra_hint=retry_hint)
            quality_ok, _ = self._check_quality(mermaid_code, diagram_type)

        # 清理 mermaid 代码
        mermaid_code = self._clean_mermaid(mermaid_code)

        return WorkerResult(
            success=True,
            content=mermaid_code,
            file_type="mermaid",
            title=self._title(state, "图表"),
            summary=f"生成 {diagram_type} 类型 Mermaid 图表",
            summary_data={
                "diagram_type": diagram_type,
                "visual_style": visual_style,
                "quality_ok": quality_ok,
            },
            metadata={
                "engine": "mermaid",
                "render_at": "frontend",
                "diagram_type": diagram_type,
                "visual_style": visual_style,
                "highlight_mode": highlight_mode,
                "detail_level": detail_level,
                "agent_id": "diagram",
            },
        )

    async def _generate_mermaid(
        self,
        llm,
        prompt: str,
        input_text: str,
        diagram_type: str,
        extra_hint: str = "",
    ) -> str:
        """调用 LLM 生成 Mermaid 代码。"""
        suffix = f"\n\n请生成 {diagram_type} 类型的 Mermaid 图表代码，只输出 Mermaid 代码，不要包含其他解释。"
        if extra_hint:
            suffix = f"\n\n{extra_hint}" + suffix

        response = await llm.ainvoke(
            f"{prompt}\n\n{input_text}{suffix}",
            temperature=0.2,
        )

        content = response.content if hasattr(response, "content") else str(response)
        return self._extract_mermaid_from_output(content)

    def _extract_mermaid_from_output(self, content: str) -> str:
        """从 LLM 输出中提取 Mermaid 代码。"""
        pattern = r"```mermaid\s*\n(.*?)```"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()

        pattern = r"```\s*\n(.*?)```"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            candidate = match.group(1).strip()
            if self._looks_like_mermaid(candidate):
                return candidate

        stripped = content.strip()
        if self._looks_like_mermaid(stripped):
            return stripped

        return content.strip()

    def _looks_like_mermaid(self, text: str) -> bool:
        """判断文本是否像 Mermaid 代码。"""
        first_line = text.split("\n")[0].strip().lower()
        return any(kw in first_line for kw in _MERMAID_KEYWORDS)

    def _check_quality(self, mermaid_code: str, diagram_type: str) -> tuple[bool, str]:
        """检测 Mermaid 代码质量。"""
        if not mermaid_code or len(mermaid_code) < 20:
            return False, "输出为空或过短"

        first_line = mermaid_code.split("\n")[0].strip().lower()
        if not any(kw in first_line for kw in _MERMAID_KEYWORDS):
            return False, f"未检测到 Mermaid 语法关键字 (首行: {first_line[:50]})"

        open_count = mermaid_code.count("[") + mermaid_code.count("{") + mermaid_code.count("(")
        close_count = mermaid_code.count("]") + mermaid_code.count("}") + mermaid_code.count(")")
        if abs(open_count - close_count) > 3:
            return False, f"括号不匹配 (开:{open_count} 闭:{close_count})"

        return True, "通过"

    def _clean_mermaid(self, code: str) -> str:
        """清理 Mermaid 代码。"""
        lines = code.split("\n")
        cleaned = []
        for line in lines:
            stripped = line.strip()
            if stripped in ("```", "```mermaid"):
                continue
            cleaned.append(line)
        return "\n".join(cleaned).strip()

    def _infer_diagram_type(self, state: WorkerState) -> str:
        """根据学习需求自动推断图表类型。"""
        need = (state.task.get("learning_need", "") or "").lower()
        if any(kw in need for kw in ("流程", "步骤", "算法", "过程")):
            return "flow"
        if any(kw in need for kw in ("架构", "系统", "模块", "组件")):
            return "component"
        if any(kw in need for kw in ("类", "对象", "继承", "接口", "设计模式")):
            return "class"
        if any(kw in need for kw in ("状态", "生命周期", "转换")):
            return "state"
        if any(kw in need for kw in ("实体", "关系", "数据库", "er", "表")):
            return "er"
        if any(kw in need for kw in ("时序", "交互", "通信", "调用")):
            return "sequence"
        if any(kw in need for kw in ("对比", "比较", "区别", "异同")):
            return "compare"
        return "hierarchy"

    def _build_diagram_instruction(
        self,
        diagram_type: str,
        visual_style: str,
        highlight_mode: str,
        detail_level: str,
    ) -> str:
        """构建图表生成专用指令。"""
        syntax_hint = _DIAGRAM_SYNTAX_HINTS.get(diagram_type, "使用 flowchart TD")

        parts = [
            f"## 图表要求",
            f"- 图表类型: {diagram_type}",
            f"- 语法提示: {syntax_hint}",
            f"- 视觉风格: {visual_style}",
            f"- 高亮模式: {highlight_mode}",
            f"- 详细程度: {detail_level}",
        ]

        if highlight_mode == "weak_points":
            parts.append("- 请用粗体或特殊样式标注薄弱知识点")
        elif highlight_mode == "key_points":
            parts.append("- 请用粗体或特殊样式标注关键知识点")

        if visual_style == "minimal":
            parts.append("- 使用简洁的节点命名，避免过长文本")
        elif visual_style == "exam":
            parts.append("- 节点中包含考试要点和关键词")

        if detail_level == "concise":
            parts.append("- 节点数量控制在 10-15 个")
        elif detail_level == "detailed":
            parts.append("- 可以展开到 20-30 个节点，包含子节点")

        return "\n".join(parts)

    def _input_suffix(self) -> str:
        return "请生成 Mermaid 图表代码。"