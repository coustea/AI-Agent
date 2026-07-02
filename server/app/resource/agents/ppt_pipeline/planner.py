from __future__ import annotations

import json
from typing import Any

from app.infra.llm import get_llm
from app.resource.agents.ppt_pipeline.schemas import DeckBrief


class BriefPlanner:
    """幻灯片大纲与视觉意图策划智能体"""

    def __init__(self, llm=None):
        self.llm = llm or get_llm()

    async def plan(
        self,
        learning_need: str,
        learning_scenario: str,
        user_profile: dict[str, Any] | str,
        teaching_plan: Any | None,
    ) -> DeckBrief:
        """根据学习需求、学习场景、用户画像及教学大纲，制定幻灯片大纲与视觉意图（DeckBrief）。"""
        # Format context dicts using json.dumps instead of generic str()
        if isinstance(user_profile, dict):
            profile_str = json.dumps(user_profile, ensure_ascii=False, indent=2)
        else:
            profile_str = str(user_profile)

        tp_str = ""
        if teaching_plan is not None:
            if hasattr(teaching_plan, "model_dump"):
                tp_str = json.dumps(teaching_plan.model_dump(mode="json"), ensure_ascii=False, indent=2)
            elif isinstance(teaching_plan, dict):
                tp_str = json.dumps(teaching_plan, ensure_ascii=False, indent=2)
            else:
                tp_str = str(teaching_plan)

        prompt = (
            "你是计算机专业理论教学的课件策划导演。\n"
            "请根据以下输入，为教学课件制定一份设计大纲与视觉意图（DeckBrief）：\n\n"
            f"## 学习需求\n{learning_need}\n\n"
            f"## 学习场景\n{learning_scenario}\n\n"
            f"## 用户画像\n{profile_str}\n\n"
            f"## 教学大纲 (Teaching Plan)\n{tp_str}\n\n"
            "请为这套课件确定以下核心意图，并以 DeckBrief 结构返回：\n"
            "1. purpose (演示的目的与核心意图)\n"
            "2. audience (受众类型与背景知识水平)\n"
            "3. density (内容密度：'speaker_led'（演讲者引导，字少图多）或 'reading_first'（阅读优先，字多图少）)\n"
            "4. target_slide_count (目标幻灯片页数，必须为正整数)\n"
            "5. narrative (叙事大纲逻辑脉络描述)\n"
            "6. required_points (必须包含的关键知识点列表)\n"
            "7. language (语言代码，如 'zh-CN')\n"
            "8. mood (整体视觉和情感基调描述)\n"
        )

        brief = await self.llm.ainvoke_json(DeckBrief, prompt)
        return brief
