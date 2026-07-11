"""Planning for replayable computer-science teaching videos."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.shared.cartoon.schemas import (
    CartoonBrief,
    TeachingAction,
    TeachingLesson,
    TeachingScene,
    TeachingStep,
    VisualEdge,
    VisualModel,
    VisualNode,
)

logger = get_logger(__name__)


class CartoonPlanningError(RuntimeError):
    """A planning failure that must not be hidden by a fake execution trace."""


class CartoonLessonPlanner:
    def __init__(self, *, attempts: int = 3, retry_delay_seconds: float = 1.5) -> None:
        self.attempts = max(1, attempts)
        self.retry_delay_seconds = max(0.1, retry_delay_seconds)

    async def plan(self, brief: CartoonBrief) -> TeachingLesson:
        last_error: Exception | None = None
        for attempt in range(1, self.attempts + 1):
            try:
                response = await get_llm().ainvoke_json(
                    self._messages(brief),
                    TeachingLesson,
                    temperature=0.2,
                    max_tokens=7000,
                )
                return response if isinstance(response, TeachingLesson) else TeachingLesson.model_validate(response)
            except Exception as exc:
                last_error = exc
                category = self._error_category(exc)
                logger.warning("Cartoon teaching plan failed (attempt %d/%d, %s): %s", attempt, self.attempts, category, exc)
                if category != "transient" or attempt == self.attempts:
                    break
                await asyncio.sleep(self.retry_delay_seconds * attempt)

        if not self._requests_execution(brief):
            logger.info("Cartoon planner using declared conceptual fallback")
            return self._concept_lesson(brief)
        raise CartoonPlanningError(f"无法生成可重放的算法讲解步骤: {last_error}") from last_error

    def _messages(self, brief: CartoonBrief) -> list[Any]:
        config = brief.configuration
        return [
            SystemMessage(
                content=(
                    "你是计算机科学教学视频导演。只输出符合 TeachingLesson JSON Schema 的结构化数据。"
                    "禁止输出 HTML、CSS、JavaScript、坐标、Markdown 或未声明的动作。"
                    "每个 scene 必须选择一种 visual_model：tree、array、graph、flow、state-machine、memory、network、comparison。"
                    "算法模式必须给出可重放的初始节点/边、逐步旁白、动作及状态补丁；"
                    "例如 BST 插入必须逐步比较、到达空孩子位置、add_node 和 add_edge。"
                    "概念模式可以解释稳定的结构，但不得冒充算法执行。"
                    "动作仅可用 reveal、focus、compare、traverse、transfer、mutate、insert、remove、connect、highlight。"
                    "每场景 2-6 步；每步旁白 12-80 个中文字符；用少量真实对象而不是泛化卡片。"
                )
            ),
            HumanMessage(
                content=(
                    f"学习需求：{brief.learning_need}\n"
                    f"目标时长：{config.target_duration_seconds} 秒；深度：{config.depth}；节奏：{config.pace}\n"
                    f"知识点：{'、'.join(brief.knowledge_points)}\n"
                    f"材料：\n{self._source(brief)[:22000]}"
                )
            ),
        ]

    @staticmethod
    def _source(brief: CartoonBrief) -> str:
        return "\n\n".join(part for part in [brief.teaching_plan, brief.tutorial_markdown, "、".join(brief.knowledge_points)] if part.strip())

    @staticmethod
    def _error_category(exc: Exception) -> str:
        message = str(exc).lower()
        return "transient" if any(token in message for token in ("connection", "timeout", "temporar", "rate limit", "429", "503")) else "invalid"

    @staticmethod
    def _requests_execution(brief: CartoonBrief) -> bool:
        source = " ".join([brief.learning_need, brief.teaching_plan, brief.tutorial_markdown]).lower()
        return any(token in source for token in ("算法", "插入", "删除", "排序", "搜索", "遍历", "执行", "步骤", "dijkstra", "bfs", "dfs", "binary search"))

    def _concept_lesson(self, brief: CartoonBrief) -> TeachingLesson:
        topic = next((item.strip() for item in [*brief.knowledge_points, brief.learning_need] if item.strip()), "核心结构")[:40]
        if "树" in topic:
            nodes = [
                VisualNode(id="root", label="根节点", detail="结构的起点"),
                VisualNode(id="left", label="左子树", detail="一条分支", parent_id="root"),
                VisualNode(id="right", label="右子树", detail="另一条分支", parent_id="root"),
            ]
            model = VisualModel(kind="tree", label=topic, nodes=nodes, edges=[VisualEdge(source_id="root", target_id="left", kind="left"), VisualEdge(source_id="root", target_id="right", kind="right")])
        elif any(token in topic for token in ("数组", "队列", "栈")):
            nodes = [VisualNode(id=f"slot-{index}", label=str(index), detail="数据槽位") for index in range(4)]
            model = VisualModel(kind="array", label=topic, nodes=nodes)
        elif "图" in topic:
            nodes = [VisualNode(id="a", label="A"), VisualNode(id="b", label="B"), VisualNode(id="c", label="C"), VisualNode(id="d", label="D")]
            model = VisualModel(kind="graph", label=topic, nodes=nodes, edges=[VisualEdge(source_id="a", target_id="b"), VisualEdge(source_id="a", target_id="c"), VisualEdge(source_id="b", target_id="d")])
        else:
            nodes = [VisualNode(id="root", label=topic, detail="核心概念"), VisualNode(id="rule", label="组成规则", detail="对象之间的约束"), VisualNode(id="effect", label="行为结果", detail="规则带来的性质")]
            model = VisualModel(kind="flow", label=topic, nodes=nodes, edges=[VisualEdge(source_id="root", target_id="rule"), VisualEdge(source_id="rule", target_id="effect")])
        primary, rule, effect = (node.id for node in nodes[:3])
        return TeachingLesson(
            title=f"{topic} 动画讲解",
            topic=topic,
            scenes=[
                TeachingScene(
                    id="structure", title=f"{topic}的结构", objective="先确认组成对象和连接关系", mode="concept", tag="结构", visual_model=model,
                    steps=[
                        TeachingStep(id="show-root", narration=f"先把{topic}看成一个由规则组织起来的结构。", focus_ids=[primary], actions=[TeachingAction(kind="reveal", target_ids=[primary])]),
                        TeachingStep(id="show-rule", narration="中间的规则决定信息如何从一个对象传到下一个对象。", focus_ids=[rule], actions=[TeachingAction(kind="connect", target_ids=[primary, rule])]),
                        TeachingStep(id="show-effect", narration="当规则成立时，结构就能稳定地产生对应的行为结果。", focus_ids=[effect], actions=[TeachingAction(kind="traverse", target_ids=[rule, effect])]),
                    ],
                ),
                TeachingScene(
                    id="recap", title="抓住三个观察点", objective="用对象、规则和结果复述概念", mode="concept", tag="总结", visual_model=model,
                    steps=[
                        TeachingStep(id="recap-object", narration="第一，辨认结构中各个对象分别保存什么信息。", focus_ids=[primary], actions=[TeachingAction(kind="focus", target_ids=[primary])]),
                        TeachingStep(id="recap-rule", narration="第二，沿着连接检查规则如何限制信息流动。", focus_ids=[rule], actions=[TeachingAction(kind="highlight", target_ids=[rule])]),
                        TeachingStep(id="recap-effect", narration="第三，从最终结果反推这条规则为什么有用。", focus_ids=[effect], actions=[TeachingAction(kind="focus", target_ids=[effect])]),
                    ],
                ),
            ],
        )
