from __future__ import annotations

import re
from typing import Any

from app.infra.llm import get_llm
from app.resource.html_generator.assets import (
    VIEWPORT_BASE_CSS,
    ANIMATION_CSS,
    BACKGROUND_CSS,
    SHARED_COMPONENTS_CSS,
    SLIDE_LAYOUTS_CSS,
    BLOCK_STYLES_CSS,
    JS_PRESENTATION_CONTROLLER,
    JS_INLINE_EDITOR,
)
from app.resource.agents.ppt_pipeline.schemas import DeckBrief, StyleDecision


class HTMLAuthor:
    """HTML 幻灯片内容创作智能体"""

    def __init__(self, llm=None):
        self.llm = llm or get_llm()

    async def author(
        self,
        brief: DeckBrief,
        style: StyleDecision,
        outline: str,
        file_id: str = "presentation",
    ) -> str:
        """根据大纲意图、视觉决策和教学大纲，生成幻灯片 HTML 并封装为完整的演示文稿。"""
        
        prompt = (
            "你是资深的教学课件前端开发工程师与内容作家。你的任务是根据幻灯片大纲意图、视觉风格决策和教学内容大纲，生成精美、交互流畅的幻灯片 HTML 标记（Slide Markup）。\n\n"
            "## 1. 教学大纲意图 (DeckBrief)\n"
            f"- 目的: {brief.purpose}\n"
            f"- 受众: {brief.audience}\n"
            f"- 内容密度: {brief.density}\n"
            f"- 目标页数: {brief.target_slide_count}\n"
            f"- 叙事逻辑: {brief.narrative}\n"
            f"- 关键要点: {', '.join(brief.required_points)}\n\n"
            "## 2. 视觉风格决策 (StyleDecision)\n"
            f"- 主题名称: {style.name}\n"
            f"- 决策依据: {style.rationale}\n"
            f"- 视觉密度: {style.density}\n\n"
            "## 3. 教学大纲与内容\n"
            f"{outline}\n\n"
            "## 4. 幻灯片 HTML 编写规范\n"
            "- 你必须为每一页幻灯片生成一个 `<section class=\"slide\">` 标签。第一个幻灯片页必须带有 `active visible` 类（即 `<section class=\"slide active visible\">`），后续页面则为 `<section class=\"slide\">`。\n"
            "- 零依赖：请勿引入任何外部 CSS 或 JS 库，完全依靠内置的样式与逻辑。\n"
            "- 页面尺寸：以固定比例 16:9 (1920x1080) 设计，外部舞台 (deck-stage) 会自动通过 CSS zoom/transform 缩放。\n"
            "- 内容层次：每页应当结构丰富、图文并茂。支持双栏 (pane left & pane right) 等布局。请合理嵌套标题、内容要点、卡片、代码段、公式等元素。\n"
            "- 代码块及结构：编写代码展示时请使用 `<pre><code class=\"language-python\">` 等格式。结构图可以使用具有特定箭头的 CSS 排版。\n"
            "- 纯标记输出：仅输出 HTML 幻灯片片段列表，不要包含外部 HTML 骨架（不需要 `<!DOCTYPE html>`, `<html>`, `<head>`, `<body>` 标签），我们会在 Python 外壳中进行拼接。\n\n"
            "请直接输出 HTML 幻灯片标记（可以包裹在 ```html 块中，也可以直接输出 HTML）。"
        )

        response = await self.llm.ainvoke(prompt)
        if isinstance(response, str):
            raw_markup = response
        else:
            raw_markup = getattr(response, "content", "") or ""
        
        # 清理 markdown 标记
        slide_markup = self.clean_html_markup(raw_markup)

        # 构建最终完整的 HTML
        html_content = self.wrap_in_boilerplate(
            slide_markup=slide_markup,
            brief=brief,
            style=style,
            file_id=file_id,
        )
        
        return html_content

    @staticmethod
    def clean_html_markup(content: str) -> str:
        content = content.strip()
        m = re.search(r"```(?:html|xml)?\s*(.*?)\s*```", content, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
        
        # Fallback to extract content inside the slides wrapper
        # Let's find first slide wrapper or first tag
        start_idx = content.find("<section")
        if start_idx == -1:
            start_idx = content.find("<div")
        
        end_idx = content.rfind("</section>")
        if end_idx == -1:
            end_idx = content.rfind("</div>")
            
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            # Find tag length to enclose properly
            if content[end_idx:].startswith("</section>"):
                return content[start_idx:end_idx + len("</section>")].strip()
            else:
                return content[start_idx:end_idx + len("</div>")].strip()
        return content

    @staticmethod
    def wrap_in_boilerplate(
        slide_markup: str,
        brief: DeckBrief,
        style: StyleDecision,
        file_id: str,
    ) -> str:
        """拼接成完整的自包含 HTML 演示文稿，内联所有 CSS/JS。"""
        # Resolve themes and fonts from assets.py
        from app.resource.html_generator.assets import THEMES, THEME_FONTS

        preset_theme = {}
        theme_name = style.name
        # Check if the name exists directly or as a lower-case/slug key
        if theme_name in THEMES:
            preset_theme = THEMES[theme_name]
        elif theme_name.lower() in THEMES:
            preset_theme = THEMES[theme_name.lower()]

        # Merge preset defaults with custom overrides
        recipe = {**preset_theme, **(style.design_recipe or {})}
        bg_primary = recipe.get("bg_primary", "#0a0f1c")
        bg_secondary = recipe.get("bg_secondary", recipe.get("bg_primary", "#111827"))
        card_bg = recipe.get("card_bg", "rgba(255,255,255,0.02)")
        text_primary = recipe.get("text_primary", "#ffffff")
        text_secondary = recipe.get("text_secondary", "#9ca3af")
        text_muted = recipe.get("text_muted", "#64748b")
        accent = recipe.get("accent", "#00ffcc")
        accent_glow = recipe.get("accent_glow", "rgba(0,255,204,0.3)")
        border_color = recipe.get("border_color", "rgba(255,255,255,0.1)")
        font_display = recipe.get("font_display", "sans-serif")
        font_body = recipe.get("font_body", "sans-serif")
        font_mono = recipe.get("font_mono", "monospace")
        additional_css = recipe.get("additional_css", "")

        # 构建 CSS 变量
        css_vars = f""":root {{
    --bg-primary: {bg_primary};
    --bg-secondary: {bg_secondary};
    --card-bg: {card_bg};
    --text-primary: {text_primary};
    --text-secondary: {text_secondary};
    --text-muted: {text_muted};
    --accent: {accent};
    --accent-glow: {accent_glow};
    --border-color: {border_color};
    --font-display: {font_display};
    --font-body: {font_body};
    --font-mono: {font_mono};
}}"""

        font_links = ""
        if theme_name in THEME_FONTS:
            font_links += f'\n    {THEME_FONTS[theme_name]}'
        elif theme_name.lower() in THEME_FONTS:
            font_links += f'\n    {THEME_FONTS[theme_name.lower()]}'
        else:
            for url in style.font_urls or []:
                font_links += f'\n    <link href="{url}" rel="stylesheet">'

        # 替换 JS 中的资源 ID
        js_editor = JS_INLINE_EDITOR.replace("{{RESOURCE_ID}}", str(file_id))

        # 拼接最终页面内容
        html_content = f"""<!DOCTYPE html>
<html lang="{brief.language or 'zh-CN'}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Presentation</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    {font_links}
    <style>
        /* === CSS CUSTOM PROPERTIES (THEME) === */
        {css_vars}

        /* === RESET === */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        /* === VIEWPORT BASE === */
        {VIEWPORT_BASE_CSS}

        /* === ANIMATIONS === */
        {ANIMATION_CSS}

        /* === BACKGROUND EFFECTS === */
        {BACKGROUND_CSS}

        /* === SHARED COMPONENTS === */
        {SHARED_COMPONENTS_CSS}

        /* === SLIDE LAYOUTS === */
        {SLIDE_LAYOUTS_CSS}

        /* === BLOCK STYLES === */
        {BLOCK_STYLES_CSS}

        /* === THEME OVERRIDES === */
        {additional_css}
    </style>
</head>
<body>
    <div class="deck-viewport">
        <main class="deck-stage" id="deckStage" role="region" aria-label="幻灯片演示">
            {slide_markup}
        </main>
    </div>
    <div class="progress-bar" id="progressBar"></div>
    
    <!-- Inline Editing Controls -->
    <div class="edit-hotzone"></div>
    <button class="edit-toggle" id="editToggle" title="编辑模式 (E)">✏️</button>

    <script>
        {JS_PRESENTATION_CONTROLLER}
        {js_editor}
        
        // Initialize Presentation & Editor
        const presentation = new SlidePresentation();
        const editor = new InlineEditor();
    </script>
</body>
</html>"""
        return html_content
