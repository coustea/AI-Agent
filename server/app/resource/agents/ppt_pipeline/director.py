from __future__ import annotations

from typing import Any

from app.infra.llm import get_llm
from app.resource.agents.ppt_pipeline.schemas import DeckBrief, StyleDecision


class StyleDirector:
    """幻灯片视觉风格导演智能体"""

    def __init__(self, llm=None):
        self.llm = llm or get_llm()

    async def direct(
        self,
        brief: DeckBrief,
        learning_need: str,
        learning_scenario: str,
    ) -> StyleDecision:
        """根据 DeckBrief 和上下文，选择或定制最契合的视觉风格方案（StyleDecision）。"""
        
        prompt = (
            "你是教学课件的视觉导演。请根据以下大纲与视觉意图（DeckBrief）及学习背景，选择或定制最契合的视觉风格方案：\n\n"
            f"## 学习需求\n{learning_need}\n\n"
            f"## 学习场景\n{learning_scenario}\n\n"
            "## 幻灯片大纲意图 (DeckBrief)\n"
            f"- 目的: {brief.purpose}\n"
            f"- 受众: {brief.audience}\n"
            f"- 内容密度: {brief.density}\n"
            f"- 叙事脉络: {brief.narrative}\n"
            f"- 视觉与情感基调 (Mood): {brief.mood}\n\n"
            "## 可选风格目录 (Safe Presets & Bold Templates Catalog)\n"
            "你可以从以下 12 种预设主题中选择，或者设计自定义 (custom) 视觉风格：\n"
            "1. bold-signal (自信现代, 亮橙/深灰, Archivo Black & Space Grotesk 字体)\n"
            "2. electric-studio (高对比专业, 蓝色/黑白, Manrope 字体)\n"
            "3. creative-voltage (创意活力, 黄绿/深蓝, Syne & Space Mono 字体)\n"
            "4. dark-botanical (精致优雅, 浅黄褐/深绿, Cormorant & IBM Plex Sans 字体)\n"
            "5. notebook-tabs (精美画册, 浅黄/深灰, Bodoni Moda & DM Sans 字体)\n"
            "6. pastel-geometry (友好几何, 浅蓝/浅紫/浅灰, Plus Jakarta Sans 字体)\n"
            "7. split-pastel (活泼创意, 浅粉/浅紫/黑, Outfit 字体)\n"
            "8. vintage-editorial (复古社论, 浅褐/米黄/深灰, Fraunces & Work Sans 字体)\n"
            "9. neon-cyber (未来科技, 霓虹绿/深海蓝, Clash Display & Satoshi 字体)\n"
            "10. terminal-green (黑客极客, 绿字/黑底, JetBrains Mono 字体)\n"
            "11. swiss-modern (极简网格, 亮红/白底/黑字, Archivo & Nunito 字体)\n"
            "12. paper-ink (文学学术, 绯红/米白, Cormorant Garamond & Source Serif 4 字体)\n\n"
            "## 风格决策规范\n"
            "- 如果选择预设或 bold 模板，请将 source 设为 'preset' 或 'bold_template'，name 设为对应的主题 ID（如 'neon-cyber'），并把对应的颜色、字体放入 design_recipe 中。\n"
            "- 如果认为这 12 种主题都不适合，可以设计一套自定义 Wildcard 风格，将 source 设为 'custom'，name 设为一个有创意的自定义名字。并在 design_recipe 中提供完整的 CSS 变量配置，包括 bg_primary、bg_secondary、card_bg、text_primary、text_secondary、text_muted、accent、accent_glow、border_color、font_display、font_body、font_mono 以及 additional_css。\n"
            "- 必须在 font_urls 中列出所需的 Google Fonts 引用连接（例如 ['https://fonts.googleapis.com/css2?family=Roboto&display=swap']）。\n"
            "- 必须继承或决策最终的 density 字段 ('speaker_led' 或 'reading_first')。\n\n"
            "请返回一个 StyleDecision 结构。"
        )

        decision = await self.llm.ainvoke_json(StyleDecision, prompt)
        return decision
