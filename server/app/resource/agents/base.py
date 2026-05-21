"""
Agent 基类 — 所有资源生成 Agent 的公共骨架。

提供 4 步 run() 流程、SSE 事件发送、Prompt 加载等通用能力。
子类只需实现 _generate() 即可。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.schemas import WorkerResult, WorkerState
from app.resource.utils import (
    AgentContextBuilder,
    append_backend_context_for_prompt,
    extract_markdown_from_llm_output,
    learning_need_from_task,
    title_from_learning_need,
)

logger = get_logger(__name__)

# prompts 目录
_PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "workers"


class Agent:
    """
    资源生成 Agent 基类。

    子类需设置:
        AGENT_NAME: str   — agent 标识 (content / mindmap / diagram / quiz / code / reading)
        ROLE_NAME: str    — 中文角色名，用于 SSE 事件展示
        STEPS: list[str]  — 步骤标签，用于进度展示

    子类需实现:
        _generate(state, prompt, input_text) -> WorkerResult
    """

    AGENT_NAME: str = ""
    ROLE_NAME: str = ""
    STEPS: list[str] = ["分析输入", "融合画像与依赖", "生成内容", "整理输出"]

    def __init__(self, user_id: int, resource_id: int, emitter=None):
        self.user_id = user_id
        self.resource_id = resource_id
        self.emitter = emitter
        self.llm = get_llm()
        self._prompt_path = _PROMPTS_DIR / f"{self.AGENT_NAME}.md"

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    async def run(self, state: WorkerState) -> WorkerResult:
        """4 步执行骨架: 分析 → 融合 → 生成 → 整理。"""
        total = len(self.STEPS) + 1  # +1 给初始化步骤
        logger.info("[%s] 开始执行: %s", self.AGENT_NAME.upper(), learning_need_from_task(state.task)[:80])

        # Step 0: 分析输入
        await self._emit(
            state, "analyze_input", f"{self.ROLE_NAME}正在分析学习需求",
            step=1, total=total, step_label=self.STEPS[0],
        )
        prompt = self._load_prompt(state)

        # Step 1: 融合画像与依赖
        await self._emit(
            state, "merge_profile_dependencies", f"{self.ROLE_NAME}正在融合画像和依赖信息",
            step=2, total=total, step_label=self.STEPS[1],
        )
        input_text = await self._build_input(state)

        try:
            # Step 2: 生成内容 (子类核心逻辑)
            await self._emit(
                state, "generate_content", f"{self.ROLE_NAME}正在生成内容",
                step=3, total=total, step_label=self.STEPS[2],
            )
            result = await self._generate(state, prompt, input_text)

            # Step 3: 整理输出
            await self._emit(
                state, "finalize_output",
                f"{self.ROLE_NAME}正在整理输出 ({len(result.content or '')} 字符)",
                step=4, total=total, step_label=self.STEPS[3],
            )

            return result

        except Exception as exc:
            logger.exception("[%s] 执行失败", self.AGENT_NAME.upper())
            return WorkerResult(success=False, error=str(exc))

    # ------------------------------------------------------------------
    # 子类必须实现
    # ------------------------------------------------------------------

    async def _generate(self, state: WorkerState, prompt: str, input_text: str) -> WorkerResult:
        """核心生成逻辑，子类必须实现。"""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # SSE 事件发送
    # ------------------------------------------------------------------

    async def _emit(
        self,
        state: WorkerState,
        action: str,
        detail: str = "",
        *,
        step: int = 0,
        total: int = 0,
        step_label: str = "",
        current_action: str = "",
    ) -> None:
        """发送 Agent 动作事件。"""
        if not self.emitter:
            return
        await self.emitter.emit_agent_action(
            state.agent_name,
            action,
            detail,
            current_step=step,
            total_steps=total,
            step_label=step_label,
            current_action=current_action or detail,
            layer=state.layer_index,
            layer_name="认知建构层",
            agent_role=self.ROLE_NAME,
            resource_type=state.agent_name,
        )

    # ------------------------------------------------------------------
    # Prompt 加载 (LangChain ChatPromptTemplate 混合模式)
    # ------------------------------------------------------------------

    def _load_prompt(self, state: WorkerState) -> str:
        """
        加载 prompt 模板文件并用 agent_config 填充变量。

        模板文件格式:
          system 部分 (可含 {variable} 占位符)
          ---
          human 部分 (可含 {input} 占位符)

        {variable} 从 state.agent_config 和默认值中解析。
        """
        if not self._prompt_path.exists():
            return self._default_prompt()

        raw = self._prompt_path.read_text(encoding="utf-8")

        # 分离 system / human 部分 (以 --- 分隔)
        if "---" in raw:
            parts = raw.split("---", 1)
            system_part = parts[0].strip()
            human_part = parts[1].strip()
        else:
            system_part = raw.strip()
            human_part = ""

        # 收集模板中的变量名
        variables = self._extract_template_variables(system_part)
        if human_part:
            variables.update(self._extract_template_variables(human_part))

        # 构建 variable → value 映射
        var_values = self._resolve_template_variables(variables, state)

        # 用 ChatPromptTemplate 渲染
        messages = [("system", system_part)]
        if human_part:
            messages.append(("human", human_part))
        else:
            messages.append(("human", "{input}"))

        template = ChatPromptTemplate.from_messages(messages)

        # 合并 input 和其他变量
        format_kwargs = {"input": "", **var_values}

        try:
            rendered = template.format_messages(**format_kwargs)
            return "\n\n".join(m.content for m in rendered if m.content)
        except Exception as exc:
            logger.warning("[%s] Prompt 模板渲染失败: %s，使用原始文本", self.AGENT_NAME.upper(), exc)
            # 回退: 简单替换
            result = system_part
            for key, value in var_values.items():
                result = result.replace(f"{{{key}}}", str(value))
            return result

    def _extract_template_variables(self, text: str) -> set[str]:
        """提取模板中的 {variable} 变量名。"""
        return set(re.findall(r"\{(\w+)\}", text))

    def _resolve_template_variables(self, variables: set[str], state: WorkerState) -> dict[str, str]:
        """
        解析模板变量值。

        优先级: state.agent_config > _default_template_values() > 空字符串
        """
        defaults = self._default_template_values()
        config = state.agent_config or {}

        result = {}
        for var in variables:
            if var == "input":
                continue  # input 由 _build_input 提供
            if var in config:
                result[var] = str(config[var])
            elif var in defaults:
                result[var] = str(defaults[var])
            else:
                result[var] = ""

        return result

    def _default_template_values(self) -> dict[str, str]:
        """模板变量默认值，子类可覆盖。"""
        return {}

    def _default_prompt(self) -> str:
        """默认 prompt，子类可覆盖。"""
        return "你是一位专业的学习资源生成助手。请根据给定的要求生成内容。"

    # ------------------------------------------------------------------
    # 输入构建
    # ------------------------------------------------------------------

    async def _build_input(self, state: WorkerState) -> str:
        """构建 LLM 输入文本。子类可覆盖以自定义输入格式。"""
        task = state.task
        agent_config = state.agent_config

        parts = [
            "## 学习需求",
            learning_need_from_task(task),
            "",
            "## 学习场景",
            f"- 场景类型: {state.learning_scenario}",
            "",
            "## 全局生成参数",
            f"- 启用智能体: {', '.join(task.get('selected_agents', [])) if task.get('selected_agents') else state.agent_name}",
            f"- 输出选项: {task.get('output_options', {})}",
            "",
            "## Agent 配置",
        ]

        # 将 agent_config 中的所有参数列出
        for key, value in agent_config.items():
            parts.append(f"- {key}: {value}")

        # 使用 AgentContextBuilder 注入画像/依赖上下文
        builder = AgentContextBuilder()
        context_text = builder.build_for_agent(self.AGENT_NAME, state)
        if context_text:
            parts.append("")
            parts.append(context_text)

        append_backend_context_for_prompt(parts, state)

        parts.append("")
        parts.append(self._input_suffix())
        return "\n".join(parts)

    def _input_suffix(self) -> str:
        """输入末尾的指令，子类可覆盖。"""
        return "请生成内容。"

    # ------------------------------------------------------------------
    # 通用工具方法
    # ------------------------------------------------------------------

    def _title(self, state: WorkerState, suffix: str = "") -> str:
        """生成资源标题。"""
        return title_from_learning_need(state.task, suffix or self.ROLE_NAME)

    def _extract_markdown(self, content: str) -> str:
        """从 LLM 输出中提取 Markdown 内容。"""
        return extract_markdown_from_llm_output(content)
