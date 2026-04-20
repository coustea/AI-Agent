"""TutorAgent: 分层路由 + Plan-and-Execute 架构。

目标图结构:
    START -> classify
      ├─ direct_answer -> (generate_image/video?) -> END
      ├─ attachment_answer -> (generate_image/video?) -> END  # 图片+文档并行分析后直接回答
      └─ planner -> compile_plan -> execute_step
                         ├─ next_step -> execute_step
                         ├─ replan -> compile_plan
                         ├─ final_summarize -> (generate_image/video?) -> END
                         └─ end -> END

设计目标：稳定性、可控性、可调试性。
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
import traceback
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

# 对话上下文注入
from app.shared.request_context import runtime_context as chat_runtime_context
# Agent 内部状态类型：TypedDict 定义
from app.chat.schemas import PlanStep, StepResult, ToolCallDetail, BudgetState, TutorState
# 工具函数：从 agent.py 中提取的辅助函数，保持核心代码简洁
from app.chat.utils import (
    classify_route,
    extract_question,
    extract_query_from_args,
    extract_url_from_args,
    guard_route,
    is_search_fetch_tool,
    is_unusable_reply_text,
    likely_requires_lookup,
    load_prompts,
    looks_like_error_output,
    make_budget_state,
    merge_runtime_state,
    node_timer,
    normalize_message_content,
    stream_event,
    summarize_step_results,
    truncate,
    update_budget_after_call,
    build_messages,
)

from app.shared.vision import build_vision_service
from app.shared.agent_context import AgentContextService
from app.infra.llm import get_deepseek_chat_llm, get_deepseek_llm, get_glm_vision_llm, get_spark_x_llm
from app.infra.logging import get_logger
from app.tools import registry
from app.shared.sanitizers import sanitize_tool_messages
from app.skills.manager import SkillManager

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, START, END

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
AGENT_DIR = Path(__file__).resolve().parent       # 当前文件所在目录，用于定位 prompt.md

# 图递归保护上限（防止异常情况下无限循环）
GRAPH_RECURSION_LIMIT = 300

# 图中所有节点名称集合，用于 SSE 事件过滤（只处理这些节点的事件）
GRAPH_NODE_NAMES = {
    "classify",            # 入口分类：判断 direct / attachment / tool_needed
    "direct_answer",       # 直接回答：纯文本对话，不调用工具
    "attachment_answer",   # 附件回答：并行处理图片+文档后直接回答
    "planner",             # 规划器：制定工具执行计划
    "compile_plan",        # 计划编译：验证计划可执行性
    "execute_step",        # 执行步骤：调用工具或 LLM 中间步骤
    "replan",              # 单次重规划：失败兜底并重新生成计划
    "final_summarize",     # 最终总结：整合所有步骤结果生成最终回答
    "generate_image",      # 多模态占位节点：图片生成（当前仅日志）
    "generate_video",      # 多模态占位节点：视频生成（当前仅日志）
}


def _read_int_env(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))


# 工具调用稳定性参数（支持环境变量覆盖）
TOOL_CALL_TIMEOUT_SEC = _read_int_env("TUTOR_TOOL_TIMEOUT_SEC", 30, minimum=5, maximum=180)
TOOL_CALL_MAX_ATTEMPTS = _read_int_env("TUTOR_TOOL_MAX_ATTEMPTS", 2, minimum=1, maximum=3)
MAX_REPLAN_ATTEMPTS = _read_int_env("TUTOR_MAX_REPLAN_ATTEMPTS", 1, minimum=1, maximum=1)
URL_PATTERN = re.compile(r"https?://\S+")


# ---------------------------------------------------------------------------
# Prompt 加载
# ---------------------------------------------------------------------------
PROMPTS: dict[str, str] = load_prompts(AGENT_DIR)


class PlannerStepSchema(BaseModel):
    kind: str = "llm"
    name: str = ""
    goal: str = "执行当前步骤"
    args_hint: dict[str, Any] = Field(default_factory=dict)
    context_reasoning: str = Field(
        default="",
        description="该步骤的设计依据：参考了用户的哪些画像/记忆/对话上下文",
    )


class PlannerOutputSchema(BaseModel):
    context_used: str = Field(
        default="",
        description="简要说明你参考了用户的哪些上下文信息来设计此计划",
    )
    steps: list[PlannerStepSchema] = Field(default_factory=list)


class ImageGenerationPlanSchema(BaseModel):
    title: str = ""
    visual_goal: str = ""
    positive_prompt: str = ""
    negative_prompt: str = ""
    style: str = ""
    aspect_ratio: str = "16:9"
    key_elements: list[str] = Field(default_factory=list)
    safety_notes: str = ""


class VideoSceneSchema(BaseModel):
    scene_id: int = 1
    shot: str = ""
    duration_sec: int = 4
    description: str = ""


class VideoGenerationPlanSchema(BaseModel):
    title: str = ""
    visual_goal: str = ""
    positive_prompt: str = ""
    negative_prompt: str = ""
    style: str = ""
    aspect_ratio: str = "16:9"
    total_duration_sec: int = 12
    scenes: list[VideoSceneSchema] = Field(default_factory=list)
    audio_notes: str = ""
    safety_notes: str = ""


class TutorAgent:
    """导师对话智能体：分层路由 + Plan-and-Execute 架构。

    三种对话路径:
    1. direct_answer — 纯文本对话，无需工具
    2. vision_answer — 图片理解，使用 GLM-4V 视觉模型
    3. plan_execute  — 工具辅助对话，走 planner → execute → guard 循环
    """

    _shared_instance: "TutorAgent | None" = None  # 全局单例

    def __init__(self) -> None:
        # ---- LLM 实例（按用途区分温度和 token 限制） ----
        self.llm = get_spark_x_llm(temperature=1.0, streaming=True)         # 聊天模型：SparkMAX（流式输出）
        self.worker_llm = get_deepseek_llm(temperature=0.2, streaming=False) # 工作模型：DeepSeek（中间步骤分析）
        self.classifier_llm = get_deepseek_chat_llm(temperature=0.0, streaming=False, max_tokens=120)   # 决策模型：DeepSeek Chat 分类
        # 规划模型：DeepSeek Chat 结构化 JSON 输出，避免手工解析字符串 JSON
        self.planner_llm = get_deepseek_chat_llm(
            temperature=0.0,
            streaming=False,
            max_tokens=1400,
        ).with_structured_output(PlannerOutputSchema)
        # 多模态规划模型：图片与视频使用不同模型，按前端开关触发
        self.image_plan_llm = get_deepseek_chat_llm(
            temperature=0.1,
            streaming=False,
            max_tokens=900,
        ).with_structured_output(ImageGenerationPlanSchema)
        self.video_plan_llm = get_deepseek_llm(
            temperature=0.1,
            streaming=False,
            max_tokens=1200,
        ).with_structured_output(VideoGenerationPlanSchema)

        # ---- 视觉模型（图片理解） ----
        self.glm_vision_llm = get_glm_vision_llm()                 # GLM-4V 视觉模型实例
        self.vision_service = build_vision_service(self.glm_vision_llm)  # 视觉服务封装

        # ---- 上下文服务（记忆 CRUD 委托，module_name="mentor"） ----
        self.ctx_service = AgentContextService(module_name="mentor")

        # ---- 图与并发控制 ----
        self.graph = None                                            # LangGraph 编译后的图（懒初始化）
        self._init_lock = asyncio.Lock()                             # 保证图只编译一次的异步锁
        self._background_tasks: set[asyncio.Task] = set()           # 后台任务集合（画像更新等）

        # ---- 工具配置 ----
        self.tool_names = [                                          # 可用工具名称列表（plan-execute 模式使用）
            "web_fetch", "duckduckgo_search",                        # 网页抓取 + 搜索
            "read_uploaded_file", "list_uploaded_files",             # 文件读取
            "execute_shell","execute_shell_sync","safe_shell"
        ]
        self._tools: list[BaseTool] = []                             # 已加载的 LangChain 工具实例
        self._tool_map: dict[str, BaseTool] = {}                     # 工具名 → 实例的映射
        self._tool_refresh_lock = asyncio.Lock()                     # 工具/技能刷新锁
        self._available_registered_tools: set[str] = set()           # 当前已加载的注册工具集合
        self._tool_required_args: dict[str, set[str]] = {}           # 工具名 -> 必填参数
        self._planner_capabilities: list[dict[str, Any]] = []        # 规划器可见能力清单

        # ---- 技能自动触发 ----
        self._skill_manager = SkillManager()                          # 技能发现与加载管理器
        self._skill_catalog: str = ""                                 # 技能目录摘要（注入到系统提示词）
        self._available_skill_names: set[str] = set()                 # 已发现技能名集合
        self._skill_alias_map: dict[str, str] = {}                    # 归一化技能名 → 原技能名

        logger.info("[TutorAgent] 初始化完成")

    @classmethod
    def get_shared(cls) -> "TutorAgent":
        """获取全局单例，首次调用时创建。"""
        if cls._shared_instance is None:
            cls._shared_instance = cls()
        return cls._shared_instance

    # ------------------------------------------------------------------
    # 通用辅助
    # ------------------------------------------------------------------

    def _default_plan(self, state: TutorState, *, reason: str) -> list[PlanStep]:
        """Planner 失败时的兜底计划（稳定优先）。"""
        # 从对话消息中提取用户原始问题，用于构造搜索查询
        question = extract_question(state.get("messages") or [])
        # 获取用户上传的文件 URL 列表
        file_urls = state.get("file_urls") or []

        steps: list[PlanStep] = []

        read_file_tool_available = self._tool_available("read_uploaded_file")
        search_tool_available = self._tool_available("duckduckgo_search")

        # 如果有文件附件，优先安排文件读取步骤
        # 因为文件内容通常是用户问题的核心上下文，必须先读取
        if read_file_tool_available:
            for url in file_urls:
                steps.append({
                    "kind": "tool",
                    "name": "read_uploaded_file",
                    "goal": "读取用户上传文件内容",
                    "args_hint": {"file_url": url},
                })
        elif file_urls:
            steps.append({
                "kind": "llm",
                "name": "intermediate_analysis",
                "goal": "文件读取工具当前不可用，先给出可执行的补救建议",
                "args_hint": {"reason": "read_uploaded_file_unavailable", "fallback": True},
            })

        # 没有文件且问题可能需要外部信息时，安排一次搜索
        # _likely_requires_lookup 通过关键词（"最新""新闻""价格"等）判断是否需要联网
        if not file_urls and likely_requires_lookup(question) and search_tool_available:
            steps.append({
                "kind": "tool",
                "name": "duckduckgo_search",
                "goal": "检索外部信息",
                "args_hint": {"query": question or "用户问题"},
            })

        # 中间分析步骤：让 LLM 整合工具返回的结果，形成结构化中间结论
        # 这一步不直接面向用户，而是为 final_answer 提供高质量输入
        steps.append({
            "kind": "llm",
            "name": "intermediate_analysis",
            "goal": "整合已有工具结果，形成可用于最终回答的结构化结论",
            "args_hint": {"reason": reason},
        })
        # 最后一步必须是 final_answer，触发 final_summarize 节点生成最终回复
        steps.append({
            "kind": "final_answer",
            "name": "final_answer",
            "goal": "交给 final_summarize 统一收口",
            "args_hint": {},
        })

        return self._normalize_plan_steps(steps)

    def _normalize_plan_steps(self, raw_steps: list[dict[str, Any]], start_index: int = 0) -> list[PlanStep]:
        # 清洗和规范化计划步骤列表，确保每一步都有完整且合法的字段
        # LLM 输出的步骤可能缺少字段、类型不对或 kind 值不在允许范围内
        normalized: list[PlanStep] = []
        # 只允许这四种步骤类型：tool（工具调用）、skill（技能调用）、llm（LLM 中间分析）、final_answer（最终回答）
        allowed_kinds = {"tool", "skill", "llm", "final_answer"}

        for i, step in enumerate(raw_steps):
            if not isinstance(step, dict):
                # 跳过非字典类型的步骤（LLM 偶尔输出非结构化内容）
                continue
            # 清洗 kind 字段：转小写、去空格，不在允许集合内的统一降级为 "llm"
            kind = str(step.get("kind", "llm")).strip().lower()
            if kind not in allowed_kinds:
                kind = "llm"
            # 清洗 name 字段：如果 LLM 没给就按序号自动生成
            name = str(step.get("name", f"step_{start_index + i}"))
            # 清洗 goal 字段：缺省为通用描述
            goal = str(step.get("goal", "执行当前步骤"))
            # 清洗 args_hint：必须是字典类型，否则置空
            args_hint = step.get("args_hint") if isinstance(step.get("args_hint"), dict) else {}
            normalized.append(
                {
                    "step_index": start_index + i,  # 步骤序号，支持从非零开始（局部重规划时用）
                    "kind": kind,
                    "name": name,
                    "goal": goal,
                    "args_hint": args_hint,
                }
            )

        # 如果清洗后没有合法步骤，返回空列表（上游会兜底到 _default_plan）
        if not normalized:
            return []

        # 硬性约束：计划最后一步必须是 final_answer，确保流程能走到最终总结
        if normalized[-1].get("kind") != "final_answer":
            next_index = normalized[-1].get("step_index", len(normalized) - 1) + 1
            normalized.append(
                {
                    "step_index": next_index,
                    "kind": "final_answer",
                    "name": "final_answer",
                    "goal": "交给 final_summarize 统一收口",
                    "args_hint": {},
                }
            )
        return normalized

    def _resolve_step_args(self, state: TutorState, step: PlanStep) -> dict[str, Any]:
        # 补全步骤的执行参数：当 LLM 规划时没给出完整参数时，用状态中的上下文自动填充
        # 这是 plan-execute 架构的关键环节——planner 可能只给"建议参数"，执行时需要补全
        args = dict(step.get("args_hint") or {})
        name = str(step.get("name", ""))
        question = extract_question(state.get("messages") or [])
        file_urls = state.get("file_urls") or []

        # 文件读取工具：如果缺少 file_url 参数，自动取用户上传的第一个文件
        if name == "read_uploaded_file" and not args.get("file_url") and file_urls:
            args["file_url"] = file_urls[0]

        # 搜索工具：如果缺少 query 参数，用用户原始问题作为搜索词
        if name == "duckduckgo_search" and not args.get("query"):
            args["query"] = question

        # 网页抓取工具：如果缺少 url 参数，尝试从之前成功的搜索结果中提取 URL
        # 典型场景：先搜索得到结果列表，再抓取其中某个链接的详细内容
        if name == "web_fetch" and not args.get("url"):
            # 从最近的成功步骤结果中逆向查找第一个 URL
            for item in reversed(state.get("step_results") or []):
                if not item.get("success"):
                    continue
                text = str(item.get("output", ""))
                # 用正则从工具输出文本中提取 http/https 链接
                url_match = URL_PATTERN.search(text)
                if url_match:
                    args["url"] = url_match.group(0)
                    break

        return args

    def _build_planner_prompt(
        self,
        *,
        state: TutorState,
        mode: str,
        failure_reason: str = "",
        completed_steps: list[StepResult] | None = None,
        current_step: PlanStep | None = None,
    ) -> str:
        question = extract_question(state.get("messages") or [])
        file_urls = state.get("file_urls") or []
        image_urls = state.get("image_urls") or []
        profile_context = state.get("profile_context", "")
        fact_context = state.get("fact_context", "")
        recent_chat_context = state.get("recent_chat_context", "")
        file_context = state.get("file_context", "")
        attachment_analysis_context = state.get("attachment_analysis_context", "")
        request_generate_image = bool(state.get("generate_image", state.get("request_generate_image", False)))
        request_generate_video = bool(state.get("generate_video", state.get("request_generate_video", False)))

        completed_summary = summarize_step_results(completed_steps or [], max_items=8)
        current_step_text = json.dumps(current_step, ensure_ascii=False) if current_step else ""

        prompt = (
            "你是 TutorAgent 的执行规划器。只负责生成可执行计划，不直接回答用户。\n\n"

            "# 上下文感知规则（最高优先级）\n"
            "1) **画像驱动**: 根据 profile_context 中的知识基础和认知水平调整策略。\n"
            "   - 知识基础薄弱 → 搜索入门级内容，避免复杂术语\n"
            "   - 认知水平较高 → 可搜索进阶资料，鼓励深度分析\n"
            "   - 认知风格偏好（如视觉/案例/推导）→ 在 goal 中体现，指导后续执行\n\n"

            "2) **记忆联动**: 根据 fact_context 中的时效性事实调整优先级。\n"
            "   - 有近期考试/截止日期 → 优先搜索相关考点或复习资料\n"
            "   - 有明确学习目标 → 围绕目标设计步骤\n"
            "   - 有已记录的薄弱点 → 针对性安排练习或解析步骤\n\n"

            "3) **对话去重**: 根据 recent_chat_context 避免重复已讨论的内容。\n"
            "   - 如果近期对话已详细回答过类似问题 → 不要安排相同的搜索\n"
            "   - 如果用户在延续之前的话题 → 安排补充性而非重复性步骤\n\n"

            "4) **附件优先**: 如果用户上传了文件/图片，优先安排文件读取或图片分析步骤。\n\n"

            "# 结构性约束\n"
            "5) 最后一步必须是 kind=final_answer。\n"
            "6) 避免重复搜索和重复抓取。\n"
            "7) 步骤数量以解决问题为准（通常 2-5 步），避免无意义冗余。\n"
            "8) 请在 context_used 中说明你参考了哪些上下文，在每步的 context_reasoning 中说明设计依据。\n"
            "9) 不要规划图片/视频生成步骤；多模态生成由工作流固定节点处理。\n\n"

            f"mode={mode}\n"
            f"user_question={question}\n"
            f"profile_context={truncate(profile_context, 1200)}\n"
            f"fact_context={truncate(fact_context, 1200)}\n"
            f"recent_chat_context={truncate(recent_chat_context, 1200)}\n"
            f"file_context={truncate(file_context, 1200)}\n"
            f"file_urls={json.dumps(file_urls, ensure_ascii=False)}\n"
            f"image_urls={json.dumps(image_urls, ensure_ascii=False)}\n"
            f"attachment_analysis_context={truncate(attachment_analysis_context, 2000)}\n"
            f"request_generate_image={request_generate_image}\n"
            f"request_generate_video={request_generate_video}\n"
            f"failure_reason={failure_reason}\n"
            f"current_step={current_step_text}\n"
            f"completed_steps={completed_summary}\n"
            f"available_capabilities={json.dumps(self._planner_capabilities, ensure_ascii=False)}\n"
        )

        if self._skill_catalog:
            prompt += (
                f"\n可用技能目录（可通过 kind=skill 步骤调用）:\n"
                f"{self._skill_catalog}\n"
                '调用方式: {"kind":"skill","name":"技能名","goal":"...","args_hint":{}}\n'
            )

        return prompt

    async def _generate_plan(
        self,
        *,
        state: TutorState,
        mode: str,
        failure_reason: str = "",
        completed_steps: list[StepResult] | None = None,
        current_step: PlanStep | None = None,
        start_index: int = 0,
    ) -> tuple[list[PlanStep], str]:
        planner_prompt = self._build_planner_prompt(
            state=state,
            mode=mode,
            failure_reason=failure_reason,
            completed_steps=completed_steps,
            current_step=current_step,
        )

        raw_output = ""
        try:
            response = await self.planner_llm.ainvoke([HumanMessage(content=planner_prompt)])

            raw_steps: list[dict[str, Any]] = []
            if isinstance(response, PlannerOutputSchema):
                raw_steps = [
                    step.model_dump() if hasattr(step, "model_dump") else step.dict()  # pydantic v2/v1 兼容
                    for step in response.steps
                ]
                if response.context_used:
                    logger.info("[TutorAgent] planner 上下文使用: %s", truncate(response.context_used, 200))
            elif isinstance(response, dict):
                maybe_steps = response.get("steps", [])
                if isinstance(maybe_steps, list):
                    raw_steps = [item for item in maybe_steps if isinstance(item, dict)]

            raw_output = json.dumps({"steps": raw_steps}, ensure_ascii=False, default=str)
            logger.info("[TutorAgent] 规划结构化输出=%s", truncate(raw_output, 500))

            plan = self._normalize_plan_steps(raw_steps, start_index=start_index)
            if not plan:
                raise ValueError("planner returned empty plan")

            self._log_plan_summary(state, plan=plan, mode=mode)
            return plan, raw_output

        except Exception as exc:
            logger.exception(
                "[TutorAgent] 规划失败 mode=%s 回退默认计划 error=%s",
                mode,
                exc,
            )
            fallback = self._default_plan(state, reason=f"planner_error:{exc}")
            if start_index > 0:
                fallback = self._normalize_plan_steps(fallback, start_index=start_index)
            self._log_plan_summary(state, plan=fallback, mode=f"{mode}:fallback")
            return fallback, raw_output

    def _log_plan_summary(self, state: TutorState, *, plan: list[PlanStep], mode: str) -> None:
        # 记录计划摘要日志：包含每一步的类型:名称，方便排查规划问题
        # mode 参数区分 initial / replan / fallback 等不同规划来源
        steps_brief = [f"{s.get('kind')}:{s.get('name')}" for s in plan]
        logger.info(
            "[TutorAgent] 执行计划 mode=%s 步骤=%s",
            mode,
            steps_brief,
        )

    def _log_step_start(self, state: TutorState, step: PlanStep) -> None:
        # 记录步骤开始执行的 debug 日志，包含步骤序号、名称和目标描述
        # 用于调试时追踪哪一步正在执行、参数是否合理
        logger.debug(
            "[TutorAgent] 步骤开始 user=%s #%s:%s 目标=%s",
            state.get("user_id"),
            step.get("step_index"), step.get("name"),
            truncate(step.get("goal", ""), 120),
        )

    def _log_step_success(self, state: TutorState, result: StepResult) -> None:
        # 记录步骤成功完成的 info 日志，包含步骤序号、名称和执行耗时
        # 耗时数据可用于性能分析和识别慢速工具调用
        logger.info(
            "[TutorAgent] 步骤完成 user=%s #%s %s %dms",
            state.get("user_id"),
            result.get("step_index"), result.get("step_name"),
            result.get("duration_ms", 0),
        )

    def _log_step_failure(self, state: TutorState, result: StepResult) -> None:
        logger.warning(
            "[TutorAgent] 步骤失败 user=%s #%s %s 原因=%s",
            state.get("user_id"),
            result.get("step_index"), result.get("step_name"),
            truncate(result.get("failure_reason", ""), 120),
        )

    def _log_guard_decision(self, state: TutorState, *, decision: str, reason: str) -> None:
        # 记录守卫节点的决策结果和原因，debug 级别不影响生产日志量
        # decision 是下一步动作（next_step / replan / final_summarize）
        # reason 是决策依据的详细描述，用于回溯为什么走了某条恢复路径
        logger.debug(
            "[TutorAgent] 步骤守卫 user=%s 决策=%s 原因=%s",
            state.get("user_id"), decision, truncate(reason, 120),
        )

    @staticmethod
    def _normalize_skill_key(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())

    def _tool_available(self, name: str) -> bool:
        return name in self._tool_map

    def _resolve_skill_name(self, requested_name: str) -> str:
        raw = (requested_name or "").strip()
        if not raw:
            return ""
        if raw in self._available_skill_names:
            return raw
        return self._skill_alias_map.get(self._normalize_skill_key(raw), raw)

    def _build_skill_catalog(self, skills: list[dict[str, Any]] | None = None) -> None:
        """构建技能目录摘要，用于注入系统提示词让 LLM 自动触发技能。"""
        items = skills if skills is not None else self._skill_manager.list_skills()
        if not items:
            self._skill_catalog = ""
            self._available_skill_names = set()
            self._skill_alias_map = {}
            return

        lines = []
        available_names: set[str] = set()
        alias_map: dict[str, str] = {}
        for skill in items:
            name = str(skill.get("name", "")).strip()
            if not name:
                continue
            available_names.add(name)
            alias_map[self._normalize_skill_key(name)] = name

            keywords = [str(k).strip() for k in (skill.get("keywords") or []) if str(k).strip()]
            for keyword in keywords:
                alias_map.setdefault(self._normalize_skill_key(keyword), name)

            desc = str(skill.get("description", ""))[:150]
            entry = f"- **{name}**: {desc}"
            if keywords:
                entry += f" (关键词: {', '.join(keywords[:5])})"
            lines.append(entry)

        self._available_skill_names = available_names
        self._skill_alias_map = alias_map
        self._skill_catalog = "\n".join(lines)
        logger.info("[TutorAgent] 技能目录构建完成 数量=%d", len(available_names))

    @staticmethod
    def _extract_required_args_from_schema(args_schema: Any) -> set[str]:
        if args_schema is None:
            return set()
        required: set[str] = set()
        model_fields = getattr(args_schema, "model_fields", None)
        if isinstance(model_fields, dict):
            for name, field in model_fields.items():
                try:
                    if field.is_required():
                        required.add(str(name))
                except Exception:
                    continue
            return required
        legacy_fields = getattr(args_schema, "__fields__", None)
        if isinstance(legacy_fields, dict):
            for name, field in legacy_fields.items():
                if getattr(field, "required", False):
                    required.add(str(name))
        return required

    def _build_planner_capabilities(self) -> None:
        capabilities: list[dict[str, Any]] = []
        tool_required_args: dict[str, set[str]] = {}

        for tool in self._tools:
            required_args = self._extract_required_args_from_schema(getattr(tool, "args_schema", None))
            tool_required_args[tool.name] = required_args
            capabilities.append(
                {
                    "kind": "tool",
                    "name": tool.name,
                    "required_args": sorted(required_args),
                    "description": truncate(getattr(tool, "description", ""), 180),
                }
            )

        for skill_name in sorted(self._available_skill_names):
            capabilities.append(
                {
                    "kind": "skill",
                    "name": skill_name,
                    "required_args": [],
                    "description": "技能能力（由 skill 工具执行）",
                }
            )

        self._tool_required_args = tool_required_args
        self._planner_capabilities = capabilities

    @staticmethod
    def _dedupe_tools(tools: list[BaseTool]) -> list[BaseTool]:
        deduped: dict[str, BaseTool] = {}
        for tool in tools:
            deduped[tool.name] = tool
        return list(deduped.values())

    async def _refresh_tool_inventory(self, *, reason: str) -> None:
        async with self._tool_refresh_lock:
            registered_tools: list[BaseTool] = []
            available_registered: set[str] = set()

            try:
                registry.ensure_loaded()
                logger.debug("[TutorAgent] 工具模块已导入 reason=%s", reason)
            except Exception:
                logger.exception("[TutorAgent] 工具模块导入失败 reason=%s", reason)

            for tool_name in self.tool_names:
                try:
                    tool = registry.get(tool_name)
                    registered_tools.append(tool)
                    available_registered.add(tool.name)
                except Exception:
                    logger.warning("[TutorAgent] 注册工具缺失 tool=%s reason=%s", tool_name, reason)

            logger.debug(
                "[TutorAgent] 注册工具刷新完成 reason=%s 数量=%d 名称=%s",
                reason,
                len(registered_tools),
                [tool.name for tool in registered_tools],
            )

            skill_tools: list[BaseTool] = []
            skills: list[dict[str, Any]] = []
            try:
                await self._skill_manager.load_all()
                skill_tools = await self._skill_manager.get_tools()
                skills = self._skill_manager.list_skills()
                self._build_skill_catalog(skills)
                logger.debug(
                    "[TutorAgent] 技能工具刷新完成 reason=%s 数量=%d",
                    reason,
                    len(skill_tools),
                )
            except Exception:
                # 技能加载失败时不影响主流程：保留普通工具能力
                self._build_skill_catalog([])
                logger.exception("[TutorAgent] 技能工具刷新失败 reason=%s", reason)

            merged_tools = self._dedupe_tools(registered_tools + skill_tools)
            self._tools = merged_tools
            self._tool_map = {tool.name: tool for tool in merged_tools}
            self._available_registered_tools = available_registered
            self._build_planner_capabilities()

    # ------------------------------------------------------------------
    # 图构建
    # ------------------------------------------------------------------
    async def _ensure_graph(self) -> None:
        if self.graph is not None:
            return

        async with self._init_lock:
            if self.graph is not None:
                return

            logger.info("[TutorAgent] 图构建开始")

            try:
                await self._refresh_tool_inventory(reason="ensure_graph")

                graph = StateGraph(TutorState)
                graph.add_node("classify", self._classify_node)
                graph.add_node("direct_answer", self._direct_answer_node)
                graph.add_node("attachment_answer", self._attachment_answer_node)
                graph.add_node("planner", self._planner_node)
                graph.add_node("compile_plan", self._compile_plan_node)
                graph.add_node("execute_step", self._execute_step_node)
                graph.add_node("replan", self._replan_node)
                graph.add_node("final_summarize", self._final_summarize_node)
                graph.add_node("generate_image", self._generate_image_node)
                graph.add_node("generate_video", self._generate_video_node)
                logger.debug("[TutorAgent] 节点已注册")

                graph.add_edge(START, "classify")
                graph.add_conditional_edges(
                    "classify",
                    classify_route,
                    {
                        "direct": "direct_answer",
                        "attachment_needed": "attachment_answer",
                        "tool_needed": "planner",
                    },
                )
                graph.add_conditional_edges(
                    "direct_answer",
                    guard_route,
                    {
                        "generate_image": "generate_image",
                        "generate_video": "generate_video",
                        "end": END,
                    },
                )
                graph.add_conditional_edges(
                    "attachment_answer",
                    guard_route,
                    {
                        "generate_image": "generate_image",
                        "generate_video": "generate_video",
                        "end": END,
                    },
                )
                graph.add_edge("planner", "compile_plan")
                graph.add_conditional_edges(
                    "compile_plan",
                    guard_route,
                    {
                        "next_step": "execute_step",
                        "replan": "replan",
                        "final_summarize": "final_summarize",
                        "end": END,
                    },
                )
                graph.add_conditional_edges(
                    "execute_step",
                    guard_route,
                    {
                        "next_step": "execute_step",
                        "replan": "replan",
                        "final_summarize": "final_summarize",
                        "end": END,
                    },
                )
                graph.add_edge("replan", "compile_plan")
                graph.add_conditional_edges(
                    "final_summarize",
                    guard_route,
                    {
                        "generate_image": "generate_image",
                        "generate_video": "generate_video",
                        "end": END,
                    },
                )
                graph.add_edge("generate_image", END)
                graph.add_edge("generate_video", END)

                self.graph = graph.compile()
                logger.info("[TutorAgent] 图构建完成")

            except Exception:
                logger.exception("[TutorAgent] 图构建失败")
                raise

    # ------------------------------------------------------------------
    # 节点: classify
    # 入口分类节点：根据用户输入和附件类型，决定走三条路径中的哪一条。
    # 优先级：文件附件 > 图片附件 > LLM 分类判断。
    # ------------------------------------------------------------------
    async def _classify_node(self, state: TutorState) -> dict[str, Any]:
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        messages = state.get("messages") or []
        file_urls = state.get("file_urls") or []
        image_urls = state.get("image_urls") or []
        generate_image = bool(state.get("generate_image", state.get("request_generate_image", False)))
        generate_video = bool(state.get("generate_video", state.get("request_generate_video", False)))
        user_message = extract_question(messages)

        with node_timer("classify", user=user_id, session=session_id):
            # 快速路径1：用户要求生成图片或视频 → tool_needed
            if generate_image or generate_video:
                logger.info(
                    "[TutorAgent] 路由分类 route=tool_needed 原因=多模态生成请求"
                )
                return {
                    "route": "tool_needed",
                    "execution_mode": "plan_execute",
                }

            # 快速路径2：有图片或文档附件 → attachment_needed（并行分析后直接回答）
            if file_urls or image_urls:
                logger.info(
                    "[TutorAgent] 路由分类 route=attachment_needed 原因=附件(图片=%s,文档=%s)",
                    len(image_urls), len(file_urls),
                )
                return {
                    "route": "attachment_needed",
                    "execution_mode": "attachment",
                }

            # 慢速路径：无附件时使用分类 LLM 判断用户意图
            classify_prompt = PROMPTS["classifier"].format(
                user_message=user_message[:800],
                has_attachments="无附件",
            )

            try:
                response = await self.classifier_llm.ainvoke([HumanMessage(content=classify_prompt)])
                raw = normalize_message_content(response.content)
                raw_norm = raw.strip().lower()

                # 关键词匹配判断路由：只有 tool_needed 走规划路径
                if "tool" in raw_norm:
                    route = "tool_needed"
                else:
                    route = "direct"

                logger.info(
                    "[TutorAgent] 路由分类 route=%s 消息=%s",
                    route, truncate(user_message, 120),
                )

                return {
                    "route": route,
                    "execution_mode": "plan_execute" if route == "tool_needed" else route,
                }

            except Exception:
                logger.exception(
                    "[TutorAgent] 路由分类 回退=direct",
                )
                return {
                    "route": "direct",
                    "execution_mode": "direct",
                }

    # ------------------------------------------------------------------
    # 图片预分析辅助方法
    # 当文件和图片同时存在时，在 classify 阶段提前完成图片视觉分析，
    # 将分析结果作为文本上下文注入 plan-execute 流程。
    # ------------------------------------------------------------------
    async def _preanalyze_images(
        self,
        image_urls: list[str],
        user_message: str,
        state: TutorState,
    ) -> str:
        """对图片做视觉分析，返回可用于 planner 上下文的文本。"""
        # 优先复用上传阶段的并行预分析结果，避免重复调用视觉模型
        pre_analysis = state.get("attachment_analysis") or {}
        pre_image = pre_analysis.get("image") if isinstance(pre_analysis, dict) else None
        if isinstance(pre_image, dict) and str(pre_image.get("analysis_text", "")).strip():
            logger.info("[TutorAgent] 图片预分析复用上传预分析结果")
            return f"### 图片分析结果\n{pre_image['analysis_text']}"

        try:
            result = await self.vision_service.analyze_images(image_urls, user_message)
            analysis_text = str(result.get("analysis_text", "")).strip()
            if analysis_text:
                mode = result.get("mode", "unknown")
                logger.info("[TutorAgent] 图片预分析完成 mode=%s", mode)
                return f"### 图片分析结果（模式: {mode}）\n{analysis_text}"
        except Exception:
            logger.exception("[TutorAgent] 图片预分析失败，跳过图片分析")
        return ""

    @staticmethod
    def _next_multimodal_guard_decision(state: TutorState) -> tuple[str, str]:
        # 图片和视频互斥：优先图片，选了一个就直接执行并结束
        if bool(state.get("generate_image", state.get("request_generate_image", False))):
            return "generate_image", "image_requested_by_frontend"
        if bool(state.get("generate_video", state.get("request_generate_video", False))):
            return "generate_video", "video_requested_by_frontend"
        return "end", "no_multimodal_requested"

    def _build_multimodal_prompt(self, state: TutorState, *, modality: str) -> str:
        question = extract_question(state.get("messages") or [])
        profile_context = truncate(state.get("profile_context", ""), 600)
        fact_context = truncate(state.get("fact_context", ""), 600)
        recent_chat_context = truncate(state.get("recent_chat_context", ""), 600)
        file_context = truncate(state.get("file_context", ""), 500)
        attachment_analysis_context = truncate(state.get("attachment_analysis_context", ""), 900)
        step_summary = summarize_step_results(state.get("step_results") or [], max_items=10)

        latest_answer = ""
        messages = state.get("messages") or []
        if isinstance(messages, list):
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    latest_answer = truncate(normalize_message_content(msg.content), 900)
                    break

        return (
            f"你是多模态资源生成器，请基于上下文生成{modality}创作指令。\n"
            "要求：不得脱离上下文，不得凭空创作与用户问题无关内容。\n"
            "输出应覆盖：主题、关键内容点、风格、受众难度、禁忌项。\n"
            f"用户问题: {question}\n"
            f"最终回答摘要: {latest_answer}\n"
            f"用户画像: {profile_context}\n"
            f"用户记忆: {fact_context}\n"
            f"近期对话: {recent_chat_context}\n"
            f"附件信息: {file_context}\n"
            f"附件分析: {attachment_analysis_context}\n"
            f"执行结果摘要:\n{step_summary}\n"
        )

    async def _plan_image_generation(self, state: TutorState) -> dict[str, Any]:
        context_prompt = self._build_multimodal_prompt(state, modality="图片")
        plan_prompt = (
            f"{context_prompt}\n"
            "请输出图片生成计划，要求：\n"
            "1) positive_prompt 可直接用于图像模型。\n"
            "2) negative_prompt 明确避免项（低质量、错别字、畸形人物等）。\n"
            "3) key_elements 保留 3-8 个关键视觉元素。\n"
            "4) style 与用户学习场景一致，避免纯装饰化。\n"
        )
        response = await self.image_plan_llm.ainvoke([HumanMessage(content=plan_prompt)])
        if isinstance(response, ImageGenerationPlanSchema):
            return response.model_dump()
        if isinstance(response, dict):
            return response
        return {
            "title": "图片生成计划",
            "visual_goal": "基于上下文生成教学图片",
            "positive_prompt": context_prompt,
            "negative_prompt": "低清晰度、错误文字、与主题无关",
            "style": "educational",
            "aspect_ratio": "16:9",
            "key_elements": [],
            "safety_notes": "不得生成违规内容",
        }

    async def _plan_video_generation(self, state: TutorState) -> dict[str, Any]:
        context_prompt = self._build_multimodal_prompt(state, modality="视频")
        plan_prompt = (
            f"{context_prompt}\n"
            "请输出视频生成计划，要求：\n"
            "1) total_duration_sec 控制在 8-30 秒。\n"
            "2) scenes 至少 2 个，含 shot、duration_sec、description。\n"
            "3) positive_prompt 要能指导视频模型生成连贯镜头。\n"
            "4) audio_notes 说明旁白/字幕建议。\n"
        )
        response = await self.video_plan_llm.ainvoke([HumanMessage(content=plan_prompt)])
        if isinstance(response, VideoGenerationPlanSchema):
            return response.model_dump()
        if isinstance(response, dict):
            return response
        return {
            "title": "视频生成计划",
            "visual_goal": "基于上下文生成教学短视频",
            "positive_prompt": context_prompt,
            "negative_prompt": "抖动镜头、语义跳跃、错误字幕",
            "style": "educational",
            "aspect_ratio": "16:9",
            "total_duration_sec": 12,
            "scenes": [],
            "audio_notes": "普通话旁白，术语解释清晰",
            "safety_notes": "不得生成违规内容",
        }

    # ------------------------------------------------------------------
    # 节点: direct_answer
    # 纯文本对话路径：不调用任何工具，直接用主模型回答用户问题。
    # 适用于简单问答、学习方法建议、闲聊等无需外部信息的场景。
    # ------------------------------------------------------------------
    async def _direct_answer_node(self, state: TutorState) -> dict[str, Any]:
        user_id = state.get("user_id")
        session_id = state.get("session_id")

        with node_timer("direct_answer", user=user_id, session=session_id):
            try:
                logger.info("[TutorAgent] 直接回答")
                system_prompt = state.get("system_prompt", "")
                # 清洗消息列表：将 ToolMessage 转为文本格式，避免直接回答路径中出现工具消息
                messages = sanitize_tool_messages(state.get("messages") or [])
                # 拼接系统提示词和对话消息，构建完整的 LLM 输入
                full_messages = build_messages(system_prompt, messages)

                # 调用主模型（高温度、流式）生成回答
                response = await self.llm.ainvoke(full_messages)
                text = normalize_message_content(response.content)

                # 检测无效回复（空内容、元数据标签、过短等），如果无效则追加重试提示后重新调用
                if is_unusable_reply_text(text):
                    logger.warning(
                        "[TutorAgent] 直接回答重试 原因=无效回复 内容=%s",
                        truncate(text, 120),
                    )
                    # 追加一条 HumanMessage 指出回复无效，引导模型重新生成
                    retry_messages = full_messages + [
                        HumanMessage(
                            content=(
                                "你上一条回复无效或过短。请重新回答用户问题，"
                                "给出完整、可读、可执行的中文回答。"
                            )
                        )
                    ]
                    retry_resp = await self.llm.ainvoke(retry_messages)
                    # 只有重试结果有效时才替换，否则保留原始回复（避免丢失信息）
                    if not is_unusable_reply_text(normalize_message_content(retry_resp.content)):
                        response = retry_resp

                logger.info(
                    "[TutorAgent] 直接回答完成 预览=%s",
                    truncate(response.content, 220),
                )
                next_decision, next_reason = self._next_multimodal_guard_decision(state)
                return {
                    "messages": [response],
                    # 标记终止原因，用于日志追踪和后续流程判断
                    "termination_reason": "direct_answer_done",
                    "last_guard_decision": next_decision,
                    "guard_reason": next_reason,
                }

            except Exception:
                logger.exception("[TutorAgent] 直接回答异常")
                raise

    # ------------------------------------------------------------------
    # 节点: attachment_answer
    # 附件理解路径：并行处理图片和文档，分析后直接回答问题。
    # ------------------------------------------------------------------
    async def _attachment_answer_node(self, state: TutorState) -> dict[str, Any]:
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        file_urls = state.get("file_urls") or []
        image_urls = state.get("image_urls") or []

        with node_timer("attachment_answer", user=user_id, session=session_id, image_count=len(image_urls), file_count=len(file_urls)):
            try:
                messages = list(state.get("messages") or [])
                question = extract_question(messages)
                system_prompt = state.get("system_prompt", "")

                logger.info(
                    "[TutorAgent] 附件回答 question=%s images=%s files=%s",
                    truncate(question, 180),
                    len(image_urls),
                    len(file_urls),
                )

                context_parts: list[str] = []

                # 并行处理图片和文档
                async def analyze_images() -> str:
                    """分析图片，返回文本结果"""
                    if not image_urls:
                        return ""
                    # 优先复用上传阶段的预分析结果
                    pre_analysis = state.get("attachment_analysis") or {}
                    pre_image = pre_analysis.get("image") if isinstance(pre_analysis, dict) else None
                    if isinstance(pre_image, dict) and str(pre_image.get("analysis_text", "")).strip():
                        logger.info("[TutorAgent] 复用图片预分析结果")
                        return str(pre_image.get("analysis_text", ""))
                    try:
                        result = await self.vision_service.analyze_images(image_urls, question)
                        analysis = str(result.get("analysis_text", "")).strip()
                        logger.info("[TutorAgent] 图片分析完成 mode=%s", result.get("mode", "unknown"))
                        return analysis
                    except Exception:
                        logger.exception("[TutorAgent] 图片分析失败")
                        return "[图片分析失败]"

                async def read_documents() -> str:
                    """读取文档，返回文本结果"""
                    if not file_urls:
                        return ""
                    if "read_uploaded_file" not in self._tool_map:
                        return ""
                    doc_contents: list[str] = []
                    tool = self._tool_map["read_uploaded_file"]
                    for file_url in file_urls:
                        try:
                            result = await asyncio.wait_for(
                                tool.ainvoke({"file_url": file_url}),
                                timeout=TOOL_CALL_TIMEOUT_SEC,
                            )
                            content = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
                            doc_contents.append(f"### 文档: {file_url}\n{content}")
                            logger.info("[TutorAgent] 文档读取完成 url=%s 长度=%s", truncate(file_url, 80), len(content))
                        except Exception:
                            logger.exception("[TutorAgent] 文档读取失败 url=%s", truncate(file_url, 80))
                            doc_contents.append(f"### 文档: {file_url}\n[读取失败]")
                    return "\n\n".join(doc_contents)

                # 并行执行图片分析和文档读取
                image_result, doc_result = await asyncio.gather(
                    analyze_images(),
                    read_documents(),
                )

                if image_result:
                    context_parts.append(f"### 图片分析结果\n{image_result}")
                if doc_result:
                    context_parts.append(doc_result)

                full_context = "\n\n".join(context_parts)

                # 构建回答提示词
                answer_prompt = (
                    f"用户问题: {question}\n\n"
                    f"以下是与问题相关的附件内容：\n{full_context}\n\n"
                    "请根据以上内容回答用户问题。如果内容不足以回答问题，请明确说明。"
                )

                full_messages = build_messages(system_prompt, [HumanMessage(content=answer_prompt)])
                response = await self.llm.ainvoke(full_messages)
                text = normalize_message_content(response.content)

                if is_unusable_reply_text(text):
                    logger.warning(
                        "[TutorAgent] 附件回答重试 原因=无效回复 内容=%s",
                        truncate(text, 120),
                    )
                    retry_messages = full_messages + [
                        HumanMessage(
                            content=(
                                "你上一条回复无效或过短。请重新回答用户问题，"
                                "给出完整、可读、可执行的中文回答。"
                            )
                        )
                    ]
                    retry_resp = await self.llm.ainvoke(retry_messages)
                    if not is_unusable_reply_text(normalize_message_content(retry_resp.content)):
                        response = retry_resp

                logger.info(
                    "[TutorAgent] 附件回答完成 预览=%s",
                    truncate(response.content, 220),
                )
                next_decision, next_reason = self._next_multimodal_guard_decision(state)
                return {
                    "messages": [response],
                    "termination_reason": "attachment_answer_done",
                    "last_guard_decision": next_decision,
                    "guard_reason": next_reason,
                }

            except Exception:
                logger.exception("[TutorAgent] 附件回答异常")
                raise

    # ------------------------------------------------------------------
    # 节点: planner
    # 制定工具执行计划：分析用户问题，生成一系列有序步骤（搜索、读取文件、分析等）。
    # 计划由 planner LLM 生成，失败时使用 _default_plan 兜底。
    # ------------------------------------------------------------------
    async def _planner_node(self, state: TutorState) -> dict[str, Any]:
        user_id = state.get("user_id")
        session_id = state.get("session_id")

        with node_timer("planner", user=user_id, session=session_id):
            # 调用 LLM 生成初始计划，返回 (步骤列表, LLM 原始输出)
            plan, raw = await self._generate_plan(state=state, mode="initial")
            # 计划版本号递增，用于标识不同版本的计划（重规划时会变化）
            plan_version = int(state.get("plan_version", 0)) + 1

            logger.info(
                "[TutorAgent] 规划完成 版本=%s 步骤数=%s",
                plan_version,
                len(plan),
            )

            return {
                "execution_mode": "plan_execute",
                "plan": plan,                                    # 新制定的步骤列表
                "compiled_plan": [],                             # 待 compile_plan 产出
                "compile_ok": False,
                "compile_errors": [],
                "last_compile_error_code": "",
                "plan_version": plan_version,                   # 版本号
                "current_step_index": 0,                        # 从第 0 步开始执行
                "step_results": state.get("step_results") or [],  # 保留已有结果（用于重规划）
                "replan_count": state.get("replan_count", 0),
                "replan_used": bool(state.get("replan_used", False)),
                "last_failure_reason": "",                      # 清空失败原因
                "last_guard_decision": "next_step",             # 初始守卫决策
                "guard_reason": "planner_initialized",
                "budget": state.get("budget") or make_budget_state(),
                "tool_call_records": state.get("tool_call_records") or [],
                "termination_reason": "",
                "_planner_raw": raw,                            # 保存 LLM 原始输出（调试用）
            }

    def _compile_plan(self, state: TutorState, plan: list[PlanStep]) -> tuple[list[PlanStep], list[dict[str, Any]]]:
        compiled: list[PlanStep] = []
        errors: list[dict[str, Any]] = []
        final_answer_count = 0

        for idx, step in enumerate(plan):
            kind = str(step.get("kind", "")).strip().lower()
            name = str(step.get("name", "")).strip()
            goal = str(step.get("goal", "")).strip()
            args = self._resolve_step_args(state, step)

            if kind not in {"tool", "skill", "llm", "final_answer"}:
                errors.append({
                    "step_index": idx,
                    "code": "INVALID_STEP_KIND",
                    "detail": f"unsupported kind: {kind}",
                })
                continue

            if kind == "final_answer":
                final_answer_count += 1
                if idx != len(plan) - 1:
                    errors.append({
                        "step_index": idx,
                        "code": "PLAN_TERMINATION_INVALID",
                        "detail": "final_answer must be the last step",
                    })
                compiled.append(
                    {
                        "step_index": idx,
                        "kind": kind,
                        "name": "final_answer",
                        "goal": goal or "交给 final_summarize 统一收口",
                        "args_hint": {},
                    }
                )
                continue

            if kind == "llm":
                compiled.append(
                    {
                        "step_index": idx,
                        "kind": kind,
                        "name": name or f"llm_step_{idx}",
                        "goal": goal or "执行中间分析",
                        "args_hint": args if isinstance(args, dict) else {},
                    }
                )
                continue

            if kind == "skill":
                resolved_skill = self._resolve_skill_name(name)
                if "skill" not in self._tool_map or not resolved_skill or resolved_skill not in self._available_skill_names:
                    errors.append({
                        "step_index": idx,
                        "code": "UNKNOWN_CAPABILITY",
                        "detail": f"unknown skill: {name}",
                    })
                    continue
                compiled.append(
                    {
                        "step_index": idx,
                        "kind": kind,
                        "name": resolved_skill,
                        "goal": goal or "执行技能步骤",
                        "args_hint": args if isinstance(args, dict) else {},
                    }
                )
                continue

            if name not in self._tool_map:
                errors.append({
                    "step_index": idx,
                    "code": "UNKNOWN_CAPABILITY",
                    "detail": f"unknown tool: {name}",
                })
                continue

            required_args = self._tool_required_args.get(name, set())
            missing = [arg for arg in required_args if args.get(arg) in (None, "", [])]
            if missing:
                errors.append({
                    "step_index": idx,
                    "code": "MISSING_REQUIRED_ARG",
                    "detail": f"{name} missing args: {', '.join(missing)}",
                })
                continue

            compiled.append(
                {
                    "step_index": idx,
                    "kind": kind,
                    "name": name,
                    "goal": goal or "执行工具步骤",
                    "args_hint": args if isinstance(args, dict) else {},
                }
            )

        if final_answer_count != 1:
            errors.append({
                "step_index": len(plan) - 1 if plan else 0,
                "code": "PLAN_TERMINATION_INVALID",
                "detail": f"final_answer_count={final_answer_count}",
            })

        return compiled, errors

    async def _compile_plan_node(self, state: TutorState) -> dict[str, Any]:
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        plan = state.get("plan") or []
        replan_used = bool(state.get("replan_used", False))

        with node_timer("compile_plan", user=user_id, session=session_id):
            compiled_plan, errors = self._compile_plan(state, plan)
            if not errors:
                decision = "next_step"
                reason = "compile_passed"
                self._log_guard_decision(state, decision=decision, reason=reason)
                return {
                    "compiled_plan": compiled_plan,
                    "compile_ok": True,
                    "compile_errors": [],
                    "last_compile_error_code": "",
                    "current_step_index": 0,
                    "last_guard_decision": decision,
                    "guard_reason": reason,
                    "last_failure_reason": "",
                }

            first_code = str(errors[0].get("code", "COMPILE_FAILED"))
            if not replan_used and int(state.get("replan_count", 0)) < MAX_REPLAN_ATTEMPTS:
                decision = "replan"
                reason = "compile_failed_replan_once"
            else:
                decision = "final_summarize"
                reason = "compile_failed_after_replan"

            self._log_guard_decision(state, decision=decision, reason=reason)
            logger.warning(
                "[TutorAgent] 计划编译失败 user=%s decision=%s errors=%s",
                user_id,
                decision,
                truncate(errors, 800),
            )
            return {
                "compiled_plan": [],
                "compile_ok": False,
                "compile_errors": errors,
                "last_compile_error_code": first_code,
                "last_guard_decision": decision,
                "guard_reason": reason,
                "last_failure_reason": first_code,
            }

    # ------------------------------------------------------------------
    # 节点: execute_step
    # 执行计划中的当前步骤：根据步骤类型（tool/llm/final_answer）执行对应操作。
    # 每次执行一个步骤，并在本节点内完成下一跳决策。
    # ------------------------------------------------------------------
    async def _execute_step_node(self, state: TutorState) -> dict[str, Any]:
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        plan = state.get("compiled_plan") or []
        idx = int(state.get("current_step_index", 0))
        plan_version = int(state.get("plan_version", 0))
        replan_used = bool(state.get("replan_used", False))

        with node_timer("execute_step", user=user_id, session=session_id, plan_version=plan_version, step_index=idx):
            if not plan or idx >= len(plan):
                result: StepResult = {
                    "plan_version": plan_version,
                    "step_index": idx,
                    "step_kind": "none",
                    "step_name": "no_step",
                    "goal": "",
                    "args_hint": {},
                    "execution_args": {},
                    "success": True,
                    "output_summary": "没有可执行步骤",
                    "output": "",
                    "failure_reason": "",
                    "error_stack": "",
                    "duration_ms": 0,
                }
                return {
                    "last_step_result": result,
                    "last_failure_reason": "",
                    "last_guard_decision": "final_summarize",
                    "guard_reason": "compiled_plan_empty_or_out_of_range",
                }

            step = plan[idx]
            step_kind = str(step.get("kind", "llm"))
            step_name = str(step.get("name", f"step_{idx}"))
            goal = str(step.get("goal", ""))

            execution_args = self._resolve_step_args(state, step)
            self._log_step_start(state, step)

            started = time.monotonic()
            step_results = list(state.get("step_results") or [])
            tool_call_records = list(state.get("tool_call_records") or [])
            budget = dict(state.get("budget") or make_budget_state())

            def build_result(
                *,
                success: bool,
                output: str,
                failure_reason: str = "",
                error_stack: str = "",
            ) -> StepResult:
                duration = int((time.monotonic() - started) * 1000)
                return {
                    "plan_version": plan_version,
                    "step_index": idx,
                    "step_kind": step_kind,
                    "step_name": step_name,
                    "goal": goal,
                    "args_hint": step.get("args_hint") if isinstance(step.get("args_hint"), dict) else {},
                    "execution_args": execution_args,
                    "success": success,
                    "output_summary": truncate(output, 260),
                    "output": output,
                    "failure_reason": failure_reason,
                    "error_stack": error_stack,
                    "duration_ms": duration,
                }

            try:
                if step_kind == "final_answer":
                    result = build_result(success=True, output="final_answer step reached")
                    step_results.append(result)
                    self._log_step_success(state, result)
                    return {
                        "step_results": step_results,
                        "last_step_result": result,
                        "last_failure_reason": "",
                        "last_guard_decision": "final_summarize",
                        "guard_reason": "final_answer_step_reached",
                    }

                if step_kind in {"tool", "skill"}:
                    tool_name, tool_args = self._resolve_tool_call_for_step(step_kind, step_name, execution_args)
                    logical_name = step_name if step_kind == "skill" else tool_name
                    output_text, record = await self._invoke_tool_with_logging(
                        state=state,
                        tool_name=tool_name,
                        logical_tool_name=logical_name,
                        tool_args=tool_args,
                        plan_version=plan_version,
                        step_index=idx,
                        step_name=step_name,
                    )
                    tool_call_records.append(record)
                    budget = update_budget_after_call(budget, logical_name)

                    success = not self._is_failed_tool_output(output_text, record)
                    failure_reason = ""
                    if not success:
                        record_error = str(record.get("error", "")).strip()
                        failure_reason = record_error or f"tool_output_invalid: {truncate(output_text, 180)}"
                    result = build_result(
                        success=success,
                        output=output_text,
                        failure_reason=failure_reason,
                    )

                    step_results.append(result)
                    if success:
                        self._log_step_success(state, result)
                    else:
                        self._log_step_failure(state, result)

                    return {
                        "step_results": step_results,
                        "last_step_result": result,
                        "last_failure_reason": result.get("failure_reason", ""),
                        "tool_call_records": tool_call_records,
                        "budget": budget,
                        "last_guard_decision": (
                            "next_step"
                            if success and idx + 1 < len(plan)
                            else ("final_summarize" if success else ("replan" if not replan_used else "final_summarize"))
                        ),
                        "guard_reason": (
                            "current_step_success"
                            if success and idx + 1 < len(plan)
                            else ("plan_completed" if success else ("current_step_failed_then_replan_once" if not replan_used else "current_step_failed_after_replan"))
                        ),
                        "current_step_index": idx + 1 if success and idx + 1 < len(plan) else idx,
                    }

                if step_kind == "llm":
                    llm_prompt = self._build_llm_step_prompt(state=state, step=step, execution_args=execution_args)
                    response = await self.worker_llm.ainvoke([HumanMessage(content=llm_prompt)])
                    output_text = normalize_message_content(response.content)
                    success = not is_unusable_reply_text(output_text)
                    result = build_result(
                        success=success,
                        output=output_text,
                        failure_reason="" if success else "llm_step_unusable_output",
                    )
                    step_results.append(result)
                    if success:
                        self._log_step_success(state, result)
                    else:
                        self._log_step_failure(state, result)

                    return {
                        "step_results": step_results,
                        "last_step_result": result,
                        "last_failure_reason": result.get("failure_reason", ""),
                        "last_guard_decision": (
                            "next_step"
                            if success and idx + 1 < len(plan)
                            else ("final_summarize" if success else ("replan" if not replan_used else "final_summarize"))
                        ),
                        "guard_reason": (
                            "current_step_success"
                            if success and idx + 1 < len(plan)
                            else ("plan_completed" if success else ("current_step_failed_then_replan_once" if not replan_used else "current_step_failed_after_replan"))
                        ),
                        "current_step_index": idx + 1 if success and idx + 1 < len(plan) else idx,
                    }

                result = build_result(
                    success=False,
                    output="",
                    failure_reason=f"unsupported_step_kind: {step_kind}",
                )
                step_results.append(result)
                self._log_step_failure(state, result)
                return {
                    "step_results": step_results,
                    "last_step_result": result,
                    "last_failure_reason": result.get("failure_reason", ""),
                    "last_guard_decision": "replan" if not replan_used else "final_summarize",
                    "guard_reason": "unsupported_step_kind",
                }

            except Exception:
                stack = traceback.format_exc()
                result = {
                    "plan_version": plan_version,
                    "step_index": idx,
                    "step_kind": step_kind,
                    "step_name": step_name,
                    "goal": goal,
                    "args_hint": step.get("args_hint") if isinstance(step.get("args_hint"), dict) else {},
                    "execution_args": execution_args,
                    "success": False,
                    "output_summary": "",
                    "output": "",
                    "failure_reason": "step_exception",
                    "error_stack": stack,
                    "duration_ms": int((time.monotonic() - started) * 1000),
                }
                step_results.append(result)
                logger.exception(
                    "[TutorAgent] 步骤执行异常 版本=%s 步骤=%s 名称=%s",
                    plan_version,
                    idx,
                    step_name,
                )
                self._log_step_failure(state, result)
                return {
                    "step_results": step_results,
                    "last_step_result": result,
                    "last_failure_reason": "step_exception",
                    "last_guard_decision": "replan" if not replan_used else "final_summarize",
                    "guard_reason": "step_exception",
                }

    def _resolve_tool_call_for_step(self, step_kind: str, step_name: str, execution_args: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """将步骤映射为可执行工具调用。"""
        if step_kind == "skill":
            # skill 步骤：映射到统一的 skill 工具，并兼容别名/大小写/下划线差异
            raw_skill_name = str(
                execution_args.get("name")
                or execution_args.get("skill_name")
                or execution_args.get("skill")
                or step_name
            ).strip()
            resolved_name = self._resolve_skill_name(raw_skill_name)
            include_resources = execution_args.get("include_resources")
            include_flag = bool(include_resources) if isinstance(include_resources, bool) else True
            return "skill", {"name": resolved_name, "include_resources": include_flag}
        return step_name, execution_args

    @staticmethod
    def _is_failed_tool_output(output_text: str, record: ToolCallDetail) -> bool:
        if str(record.get("status", "")) == "error":
            return True
        lower = (output_text or "").lower()
        if any(marker in lower for marker in ("tool_exception", "tool_timeout", "tool_not_found", "permission denied", "not found", "error:")):
            return True
        if any(marker in output_text for marker in ("技能不存在", "脚本执行超时", "路径不在", "不支持的", "错误", "失败", "异常")):
            return True
        return looks_like_error_output(output_text)

    @staticmethod
    def _should_retry_tool_error(
        *,
        logical_tool_name: str,
        attempt: int,
        max_attempts: int,
        error_text: str,
    ) -> bool:
        if attempt >= max_attempts:
            return False
        lower = (error_text or "").lower()
        transient_markers = [
            "timeout",
            "temporarily",
            "temporary",
            "connection reset",
            "connection aborted",
            "connection refused",
            "rate limit",
            "too many requests",
            "429",
            "503",
            "service unavailable",
            "network",
        ]
        if any(marker in lower for marker in transient_markers):
            return True
        return is_search_fetch_tool(logical_tool_name)

    def _build_llm_step_prompt(self, *, state: TutorState, step: PlanStep, execution_args: dict[str, Any]) -> str:
        question = extract_question(state.get("messages") or [])
        step_results = summarize_step_results(state.get("step_results") or [], max_items=10)
        profile_context = truncate(state.get("profile_context", ""), 600)
        fact_context = truncate(state.get("fact_context", ""), 400)
        return (
            "你是执行器中的中间分析步骤。不要直接以最终口吻回答用户，只输出供后续总结使用的中间结论。\n"
            f"用户问题: {question}\n"
            f"当前步骤: {json.dumps(step, ensure_ascii=False)}\n"
            f"执行参数: {json.dumps(execution_args, ensure_ascii=False)}\n"
            f"已有步骤结果: \n{step_results}\n"
            f"用户画像: {profile_context}\n"
            f"用户记忆: {fact_context}\n"
            "请根据用户画像和记忆调整分析的深度和角度，输出结构化分析，包含：关键事实、缺失信息、不确定点。"
        )

    async def _invoke_tool_with_logging(
        self,
        *,
        state: TutorState,
        tool_name: str,
        logical_tool_name: str,
        tool_args: dict[str, Any],
        plan_version: int,
        step_index: int,
        step_name: str,
    ) -> tuple[str, ToolCallDetail]:
        user_id = state.get("user_id")

        logger.debug(
            "[TutorAgent] 工具调用 user=%s tool=%s 参数=%s",
            user_id, tool_name, truncate(tool_args, 300),
        )

        started = time.monotonic()
        is_search_fetch = is_search_fetch_tool(logical_tool_name)
        query = extract_query_from_args(tool_args)
        url = extract_url_from_args(tool_args)

        if tool_name not in self._tool_map:
            try:
                await self._refresh_tool_inventory(reason=f"tool_not_found:{tool_name}")
            except Exception:
                logger.exception("[TutorAgent] 工具刷新失败 tool=%s", tool_name)

        if tool_name not in self._tool_map:
            error = f"tool_not_found: {tool_name}"
            logger.error(
                "[TutorAgent] 工具未注册 user=%s tool=%s",
                user_id, tool_name,
            )
            record: ToolCallDetail = {
                "tool": tool_name,
                "args": tool_args,
                "result": "",
                "status": "error",
                "plan_version": plan_version,
                "step_index": step_index,
                "step_name": step_name,
                "is_search_fetch": is_search_fetch,
                "query": query,
                "url": url,
                "error": error,
                "error_stack": "",
            }
            return error, record

        tool = self._tool_map[tool_name]
        last_error = "tool_exception"
        last_stack = ""
        max_attempts = TOOL_CALL_MAX_ATTEMPTS

        for attempt in range(1, max_attempts + 1):
            try:
                result = await asyncio.wait_for(
                    tool.ainvoke(tool_args),
                    timeout=TOOL_CALL_TIMEOUT_SEC,
                )
                output = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)
                elapsed = int((time.monotonic() - started) * 1000)

                logger.info(
                    "[TutorAgent] 工具完成 user=%s tool=%s attempt=%s/%s %dms",
                    user_id,
                    tool_name,
                    attempt,
                    max_attempts,
                    elapsed,
                )

                record = {
                    "tool": tool_name,
                    "args": tool_args,
                    "result": truncate(output, 4000),
                    "status": "success",
                    "plan_version": plan_version,
                    "step_index": step_index,
                    "step_name": step_name,
                    "is_search_fetch": is_search_fetch,
                    "query": query,
                    "url": url,
                    "error": "",
                    "error_stack": "",
                }
                return output, record

            except asyncio.TimeoutError:
                last_error = f"tool_timeout:{TOOL_CALL_TIMEOUT_SEC}s"
                last_stack = traceback.format_exc()
                elapsed = int((time.monotonic() - started) * 1000)
                logger.warning(
                    "[TutorAgent] 工具调用超时 tool=%s attempt=%s/%s timeout=%ss elapsed=%sms",
                    tool_name,
                    attempt,
                    max_attempts,
                    TOOL_CALL_TIMEOUT_SEC,
                    elapsed,
                )
                if not self._should_retry_tool_error(
                    logical_tool_name=logical_tool_name,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error_text=last_error,
                ):
                    break

            except Exception as exc:
                last_stack = traceback.format_exc()
                last_error = "tool_exception"
                elapsed = int((time.monotonic() - started) * 1000)
                logger.exception(
                    "[TutorAgent] 工具调用异常 tool=%s attempt=%s/%s 耗时=%sms",
                    tool_name,
                    attempt,
                    max_attempts,
                    elapsed,
                )
                if not self._should_retry_tool_error(
                    logical_tool_name=logical_tool_name,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error_text=str(exc),
                ):
                    break

        record = {
            "tool": tool_name,
            "args": tool_args,
            "result": "",
            "status": "error",
            "plan_version": plan_version,
            "step_index": step_index,
            "step_name": step_name,
            "is_search_fetch": is_search_fetch,
            "query": query,
            "url": url,
            "error": last_error,
            "error_stack": last_stack,
        }
        return last_error, record

    # ------------------------------------------------------------------
    # 节点: replan
    # 统一重规划：失败后丢弃当前计划并重新生成，缩短恢复路径提高稳定性。
    # ------------------------------------------------------------------
    async def _replan_node(self, state: TutorState) -> dict[str, Any]:
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        if bool(state.get("replan_used", False)):
            return {
                "plan": [],
                "compiled_plan": [],
                "compile_ok": False,
                "compile_errors": [{"step_index": 0, "code": "REPLAN_BUDGET_EXHAUSTED", "detail": "replan already used"}],
                "last_compile_error_code": "REPLAN_BUDGET_EXHAUSTED",
                "last_failure_reason": "REPLAN_BUDGET_EXHAUSTED",
                "last_guard_decision": "final_summarize",
                "guard_reason": "replan_already_used",
            }

        replan_count = int(state.get("replan_count", 0)) + 1
        idx = int(state.get("current_step_index", 0))
        old_plan = state.get("compiled_plan") or state.get("plan") or []
        plan_version = int(state.get("plan_version", 0)) + 1
        current_step = old_plan[idx] if idx < len(old_plan) else None

        with node_timer("replan", user=user_id, session=session_id):
            logger.warning(
                "[TutorAgent] 触发重规划 step_index=%s 原因=%s 次数=%s",
                idx,
                truncate(state.get("last_failure_reason", ""), 220),
                replan_count,
            )

            new_plan, raw = await self._generate_plan(
                state=state,
                mode="replan_once",
                failure_reason=state.get("last_failure_reason", ""),
                completed_steps=state.get("step_results") or [],
                current_step=current_step,
                start_index=0,
            )

            logger.info(
                "[TutorAgent] replan.done new_plan_version=%s old_plan=%s new_plan=%s raw=%s",
                plan_version,
                truncate([f"{s.get('kind')}:{s.get('name')}" for s in old_plan], 700),
                truncate(new_plan, 900),
                truncate(raw, 400),
            )

            return {
                "plan": new_plan,
                "compiled_plan": [],
                "compile_ok": False,
                "compile_errors": [],
                "last_compile_error_code": "",
                "plan_version": plan_version,
                "replan_count": replan_count,
                "replan_used": True,
                "current_step_index": 0,
                "last_failure_reason": "",
            }

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # 节点: final_summarize
    # 最终总结：整合所有步骤结果，生成对用户的最终回答。
    # 由 compile_plan/execute_step 决策进入。
    # 使用主模型（高温度）生成自然、完整的回答，不暴露内部工具链路。
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    async def _final_summarize_node(self, state: TutorState) -> dict[str, Any]:
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        trigger_reason = state.get("guard_reason", "") or state.get("termination_reason", "")

        with node_timer("final_summarize", user=user_id, session=session_id):
            step_results = state.get("step_results") or []
            compile_errors = state.get("compile_errors") or []
            question = extract_question(state.get("messages") or [])
            system_prompt = state.get("system_prompt", "")

            logger.info(
                "[TutorAgent] 最终总结 触发原因=%s 步骤数=%s",
                truncate(trigger_reason, 240),
                len(step_results),
            )
            logger.info(
                "[TutorAgent] 最终总结输入 数据=%s",
                truncate(step_results[-10:], 1200),
            )

            summary_prompt = (
                "你是最终回答生成器。请基于已执行的步骤结果给用户一个稳定、完整、可读的最终答案。\n"
                "要求:\n"
                "1) 不要暴露内部计划、节点、guard、replan、工具链路。\n"
                "2) 明确不确定点和信息边界。\n"
                "3) 不要再调用任何工具。\n"
                f"用户问题: {question}\n"
                f"触发原因: {trigger_reason}\n"
                f"步骤结果摘要:\n{summarize_step_results(step_results, max_items=12)}\n"
                f"计划编译错误（如有）:\n{truncate(compile_errors, 900)}\n"
            )

            try:
                response = await self.llm.ainvoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=summary_prompt),
                ])
                text = normalize_message_content(response.content)
                if is_unusable_reply_text(text):
                    logger.warning(
                        "[TutorAgent] 最终总结重试 原因=无效输出",
                    )
                    retry = await self.llm.ainvoke([
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=summary_prompt + "\n请给出完整可读中文答案，不要空话。"),
                    ])
                    if not is_unusable_reply_text(normalize_message_content(retry.content)):
                        response = retry

                logger.info(
                    "[TutorAgent] 最终总结完成 预览=%s",
                    truncate(response.content, 280),
                )
                next_decision, next_reason = self._next_multimodal_guard_decision(state)
                return {
                    "messages": [response],
                    "termination_reason": "final_summarize_done",
                    "last_guard_decision": next_decision,
                    "guard_reason": next_reason,
                }

            except Exception:
                logger.exception("[TutorAgent] 最终总结异常")
                fallback = AIMessage(content="我已经完成了当前可执行步骤，但在生成最终总结时发生错误。请重试，或补充更具体的问题。")
                next_decision, next_reason = self._next_multimodal_guard_decision(state)
                return {
                    "messages": [fallback],
                    "termination_reason": "final_summarize_error_fallback",
                    "last_guard_decision": next_decision,
                    "guard_reason": next_reason,
                }

    async def _generate_image_node(self, state: TutorState) -> dict[str, Any]:
        user_id = state.get("user_id")
        session_id = state.get("session_id")

        with node_timer("generate_image", user=user_id, session=session_id):
            should_generate_image = bool(state.get("generate_image", state.get("request_generate_image", False)))
            if not should_generate_image:
                logger.info("[TutorAgent] 跳过图片生成节点 user=%s session=%s", user_id, session_id)
                return {
                    "image_generation_status": "skipped",
                    "image_generation_prompt": "",
                    "image_generation_model": "",
                    "image_generation_plan": {},
                    "last_guard_decision": "end",
                    "guard_reason": "image_not_requested",
                }

            prompt = self._build_multimodal_prompt(state, modality="图片")
            try:
                generation_plan = await self._plan_image_generation(state)
                model_tag = "deepseek_chat(image_plan)"
                logger.info(
                    "[TutorAgent] 图片规划完成 model=%s user=%s session=%s plan=%s",
                    model_tag,
                    user_id,
                    session_id,
                    truncate(generation_plan, 1500),
                )
                status = "done"
            except Exception:
                logger.exception("[TutorAgent] 图片规划失败，回退上下文prompt")
                generation_plan = {
                    "title": "图片生成计划(降级)",
                    "positive_prompt": prompt,
                }
                model_tag = "deepseek_chat(image_plan)-fallback"
                status = "error"
            return {
                "image_generation_status": status,
                "image_generation_prompt": prompt,
                "image_generation_model": model_tag,
                "image_generation_plan": generation_plan,
                "last_guard_decision": "end",
                "guard_reason": "image_generation_plan_ready",
            }

    async def _generate_video_node(self, state: TutorState) -> dict[str, Any]:
        user_id = state.get("user_id")
        session_id = state.get("session_id")

        with node_timer("generate_video", user=user_id, session=session_id):
            if not bool(state.get("generate_video", state.get("request_generate_video", False))):
                logger.info("[TutorAgent] 跳过视频生成节点 user=%s session=%s", user_id, session_id)
                return {
                    "video_generation_status": "skipped",
                    "video_generation_prompt": "",
                    "video_generation_model": "",
                    "video_generation_plan": {},
                    "termination_reason": "multimodal_nodes_done",
                }

            prompt = self._build_multimodal_prompt(state, modality="视频")
            try:
                generation_plan = await self._plan_video_generation(state)
                model_tag = "deepseek(video_plan)"
                logger.info(
                    "[TutorAgent] 视频规划完成 model=%s user=%s session=%s plan=%s",
                    model_tag,
                    user_id,
                    session_id,
                    truncate(generation_plan, 1800),
                )
                status = "done"
            except Exception:
                logger.exception("[TutorAgent] 视频规划失败，回退上下文prompt")
                generation_plan = {
                    "title": "视频生成计划(降级)",
                    "positive_prompt": prompt,
                }
                model_tag = "deepseek(video_plan)-fallback"
                status = "error"
            return {
                "video_generation_status": status,
                "video_generation_prompt": prompt,
                "video_generation_model": model_tag,
                "video_generation_plan": generation_plan,
                "termination_reason": "multimodal_nodes_done",
            }

    def _spawn_background(self, coro: Any, *, task_name: str) -> None:
        """安全启动后台任务，确保异常被记录且任务可回收。"""
        task = asyncio.create_task(coro, name=task_name)
        self._background_tasks.add(task)

        def _done_callback(done_task: asyncio.Task) -> None:
            self._background_tasks.discard(done_task)
            if done_task.cancelled():
                return
            try:
                done_task.result()
            except Exception:
                logger.exception("[TutorAgent] 后台任务异常 task=%s", task_name)

        task.add_done_callback(_done_callback)

    # ------------------------------------------------------------------
    # 主入口：SSE 流式对话
    # 接收用户消息，运行 StateGraph，通过 SSE 事件流返回 token 和图解结果。
    # 事件类型: token（文本片段）| done（完成）| error（错误）|
    #           illustration_generating（图解生成中）| illustration（图解结果）
    # ------------------------------------------------------------------
    async def chat_stream(
        self,
        user_id: int,
        user_message: str,
        session_id: Optional[str] = None,
        image_urls: Optional[list[str]] = None,
        file_urls: Optional[list[str]] = None,
        generate_image: bool = False,
        generate_video: bool = False,
        attachment_analysis: Optional[dict[str, Any]] = None,
    ):
        effective_session = session_id or f"user-{user_id}-default-mentor"
        image_urls = image_urls or []
        file_urls = file_urls or []

        logger.info(
            "[TutorAgent] 对话开始 消息=%s 附件(图片=%s,文件=%s) 生成请求(图片=%s,视频=%s)",
            truncate(user_message, 180),
            len(image_urls),
            len(file_urls),
            bool(generate_image),
            bool(generate_video),
        )
        
        # 开始 构建 Langgraph 图
        await self._ensure_graph()

        IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        attachment_items: list[dict[str, Any]] = []
        attachment_items.extend({"url": u, "type": "image", "name": u.split("/")[-1]} for u in image_urls)
        for u in file_urls:
            attachment_items.append(
                {
                    "url": u,
                    "type": "image" if Path(u).suffix.lower() in IMAGE_EXTS else "document",
                    "name": u.split("/")[-1],
                }
            )
        attachments_json = json.dumps(attachment_items, ensure_ascii=False) if attachment_items else None

        # A. 保存用户消息
        try:
            msg_content = user_message
            if image_urls:
                msg_content += f" [Attached Images: {', '.join(image_urls)}]"
            if file_urls:
                msg_content += f" [Attached Files: {', '.join(file_urls)}]"

            await self.ctx_service.save_message(
                user_id=user_id,
                session_id=effective_session,
                role="user",
                content=msg_content,
                attachments=attachments_json,
            )
            logger.debug("[TutorAgent] 用户消息已保存")
        except Exception as exc:
            logger.exception("[TutorAgent] 用户消息保存失败")
            yield stream_event("error", f"保存消息失败，请稍后重试 ({exc})")
            return

        # B. 上下文构建
        profile_str, fact_str = await asyncio.gather(
            self.ctx_service.build_profile_ctx(user_id),
            self.ctx_service.build_memory_ctx(user_id),
        )
        file_info_str = self.ctx_service.build_file_ctx(image_urls, file_urls)
        attachment_analysis_context = str((attachment_analysis or {}).get("analysis_context", "")).strip()
        initial_messages, recent_chat_context = await self.ctx_service.build_chat_ctx(
            user_id,
            effective_session,
            user_message,
            image_urls,
            file_urls,
        )

        if attachment_analysis_context:
            analysis_hint = (
                "\n\n### 附件并行预分析结果（上传后自动生成，可直接参考）\n"
                f"{attachment_analysis_context}\n"
            )
        else:
            analysis_hint = ""

        # 技能自动触发：将可用技能目录注入系统提示词
        skill_catalog_section = ""
        if self._skill_catalog:
            skill_catalog_section = (
                "\n\n## 【可用技能目录】\n"
                "以下是你当前可以调用的技能。当你认为某个技能与用户请求相关时"
                "（哪怕只有很小的可能性），请在规划中生成 kind=skill 的步骤来调用它。\n"
                f"{self._skill_catalog}\n"
            )

        direct_prompt = PROMPTS["direct_system"].format(
            profile_context=profile_str,
            fact_context=fact_str,
            recent_chat_context=recent_chat_context,
        ) + analysis_hint + skill_catalog_section
        tool_prompt = PROMPTS["tool_system"].format(
            profile_context=profile_str,
            fact_context=fact_str,
            recent_chat_context=recent_chat_context,
            file_info_context=file_info_str,
        ) + analysis_hint + skill_catalog_section

        initial_state: TutorState = {
            "user_id": user_id,
            "session_id": effective_session,
            "image_urls": image_urls,
            "file_urls": file_urls,
            "generate_image": bool(generate_image),
            "generate_video": bool(generate_video),
            "request_generate_image": bool(generate_image),
            "request_generate_video": bool(generate_video),
            "route": "",
            "execution_mode": "",
            "profile_context": profile_str,
            "fact_context": fact_str,
            "recent_chat_context": recent_chat_context,
            "file_context": file_info_str,
            "attachment_analysis_context": attachment_analysis_context,
            "attachment_analysis": attachment_analysis or {},
            "system_prompt": direct_prompt,
            "tool_system_prompt": tool_prompt,
            "messages": initial_messages,
            "plan": [],
            "compiled_plan": [],
            "compile_ok": False,
            "compile_errors": [],
            "last_compile_error_code": "",
            "plan_version": 0,
            "current_step_index": 0,
            "step_results": [],
            "replan_count": 0,
            "replan_used": False,
            "last_failure_reason": "",
            "last_guard_decision": "",
            "guard_reason": "",
            "termination_reason": "",
            "image_generation_status": "pending" if bool(generate_image) else "skipped",
            "video_generation_status": "pending" if bool(generate_video) else "skipped",
            "image_generation_prompt": "",
            "video_generation_prompt": "",
            "image_generation_model": "",
            "video_generation_model": "",
            "image_generation_plan": {},
            "video_generation_plan": {},
            "tool_call_records": [],
            "budget": make_budget_state(),
        }

        full_reply = ""
        runtime_state: dict[str, Any] = dict(initial_state)
        event_tool_records: list[ToolCallDetail] = []
        graph_error_text = ""
        stream_token_count = 0
        graph_event_count = 0

        logger.info("[TutorAgent] 请求开始")

        try:
            with chat_runtime_context(user_id, effective_session):
                async for event in self.graph.astream_events(
                    initial_state,
                    version="v2",
                    config={"recursion_limit": GRAPH_RECURSION_LIMIT},
                ):
                    graph_event_count += 1
                    kind = event.get("event", "")
                    name = event.get("name", "")

                    if kind == "on_chain_end" and name in GRAPH_NODE_NAMES:
                        node_output = event.get("data", {}).get("output", {})
                        if isinstance(node_output, dict):
                            runtime_state = merge_runtime_state(runtime_state, node_output)

                    if kind == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and chunk.content:
                            text = chunk.content if isinstance(chunk.content, str) else ""
                            if text:
                                stream_token_count += len(text)
                                full_reply += text
                                if stream_token_count % 400 == 0:
                                    logger.debug(
                                        "[TutorAgent] 流式进度 user=%s 字符数=%s",
                                        user_id, stream_token_count,
                                    )
                                yield stream_event("token", text)

                    if kind == "on_tool_end":
                        tool_name = event.get("name", "unknown")
                        tool_input = event.get("data", {}).get("input", {})
                        tool_output = event.get("data", {}).get("output", "")
                        logger.debug(
                            "[TutorAgent] 工具事件 tool=%s 输出=%s",
                            tool_name, truncate(tool_output, 200),
                        )
                        event_tool_records.append(
                            {
                                "tool": tool_name,
                                "args": tool_input if isinstance(tool_input, dict) else str(tool_input),
                                "result": truncate(tool_output, 2000),
                                "status": "success",
                            }
                        )

                    if kind == "on_tool_error":
                        tool_name = event.get("name", "unknown")
                        tool_input = event.get("data", {}).get("input", {})
                        tool_error = event.get("data", {}).get("error", "unknown tool error")
                        logger.error(
                            "[TutorAgent] 工具错误 tool=%s 错误=%s",
                            tool_name,
                            truncate(tool_error, 300),
                        )
                        event_tool_records.append(
                            {
                                "tool": tool_name,
                                "args": tool_input if isinstance(tool_input, dict) else str(tool_input),
                                "result": "",
                                "status": "error",
                                "error": truncate(tool_error, 500),
                            }
                        )

                    if kind == "on_chain_error":
                        logger.error(
                            "[TutorAgent] 链错误 节点=%s 错误=%s",
                            name,
                            truncate(event.get("data", {}).get("error", ""), 380),
                        )

        except Exception as exc:
            logger.exception("[TutorAgent] 请求异常")
            graph_error_text = f"服务器出错，请稍后再试: {exc}"

        logger.info(
            "[TutorAgent] 请求结束 事件数=%s 字符数=%s 终止原因=%s 守卫=%s",
            graph_event_count,
            stream_token_count,
            runtime_state.get("termination_reason", ""),
            runtime_state.get("last_guard_decision", ""),
        )

        # 工具记录持久化
        state_tool_records = runtime_state.get("tool_call_records", [])
        tool_call_records = state_tool_records if isinstance(state_tool_records, list) and state_tool_records else event_tool_records
        if tool_call_records:
            try:
                await self.ctx_service.persist_tool_messages(
                    user_id=user_id,
                    session_id=effective_session,
                    tool_call_records=tool_call_records,
                )
            except Exception:
                logger.exception("[TutorAgent] 工具记录持久化失败")

        if graph_error_text:
            yield stream_event("error", graph_error_text)
            return

        if not full_reply:
            # 尝试从最终 state 兜底取最后 AI 文本
            messages = runtime_state.get("messages", [])
            if isinstance(messages, list):
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage):
                        full_reply = normalize_message_content(msg.content)
                        break

        if is_unusable_reply_text(full_reply):
            logger.error(
                "[TutorAgent] 无效回复 route=%s",
                runtime_state.get("route", ""),
            )
            yield stream_event("error", "模型未返回有效内容，请重试。")
            return

        try:
            tool_calls_json = json.dumps(tool_call_records, ensure_ascii=False) if tool_call_records else None
            await self.ctx_service.save_message(
                user_id=user_id,
                session_id=effective_session,
                role="assistant",
                content=full_reply,
                tool_calls=tool_calls_json,
            )
            logger.info(
                "[TutorAgent] 回复已保存 工具记录=%s",
                len(tool_call_records),
            )

            self._spawn_background(
                self.ctx_service.post_chat_pipeline(
                    user_id=user_id,
                    session_id=effective_session,
                    user_message=user_message,
                    assistant_reply=full_reply,
                ),
                task_name="post_chat_pipeline",
            )
        except Exception as exc:
            logger.exception("[TutorAgent] 回复保存失败")
            yield stream_event("error", f"保存回复失败，请稍后重试 ({exc})")
            return

        yield stream_event("done", {"session_id": effective_session})
