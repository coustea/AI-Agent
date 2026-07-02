"""HTML 幻灯片生成器核心。

将 PPTDocument 数据转换为自包含的 HTML 演示文稿文件。
基于 frontend-slides 技能规范：
- 零依赖：单个 HTML 文件，内联 CSS/JS
- 固定 16:9 舞台：1920×1080 画布，统一缩放
- 风格多样：支持 STYLE_PRESETS.md 中定义的 12 种预设风格
- 交互与在线编辑：支持键盘/手势切换，以及 Ctrl+S 实时保存至后端的编辑模式
"""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import WORKPLACE_DIR

from app.resource.html_generator.assets import (
    THEMES,
    THEME_FONTS,
    VIEWPORT_BASE_CSS,
    ANIMATION_CSS,
    BACKGROUND_CSS,
    SHARED_COMPONENTS_CSS,
    SLIDE_LAYOUTS_CSS,
    BLOCK_STYLES_CSS,
    JS_PRESENTATION_CONTROLLER,
    JS_INLINE_EDITOR,
)

def get_theme(theme_id: str) -> dict[str, Any]:
    """获取主题配置。"""
    return THEMES.get(theme_id, THEMES["neon-cyber"])
class HTMLSlideGenerator:
    """HTML 幻灯片生成器。

    将 PPTDocument 数据转换为自包含且高度美观的 HTML 演示文稿。
    """

    def __init__(self, output_dir: Optional[str] = None):
        """初始化生成器。"""
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = WORKPLACE_DIR / "html_slides"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, document: Dict[str, Any], file_id: str) -> str:
        """生成 HTML 幻灯片 file 并返回路径。"""
        theme_id = document.get("theme_id", "neon-cyber")
        self.theme_id = theme_id
        theme = get_theme(theme_id)
        slides = document.get("slides", [])
        title = document.get("title", "Untitled")

        # 渲染每页 HTML
        slides_html = []
        for i, slide in enumerate(slides):
            slide_html = self._render_slide(slide, i, len(slides), theme)
            slides_html.append(slide_html)

        # 字体链接
        font_link = THEME_FONTS.get(theme_id, THEME_FONTS["neon-cyber"])

        # 构建 CSS 变量（使用 .get() 防止键缺失）
        css_vars = f""":root {{
    --bg-primary: {theme.get('bg_primary', '#0a0f1c')};
    --bg-secondary: {theme.get('bg_secondary', theme.get('bg_primary', '#111827'))};
    --card-bg: {theme.get('card_bg', 'rgba(255,255,255,0.02)')};
    --text-primary: {theme.get('text_primary', '#ffffff')};
    --text-secondary: {theme.get('text_secondary', '#9ca3af')};
    --text-muted: {theme.get('text_muted', '#64748b')};
    --accent: {theme.get('accent', '#00ffcc')};
    --accent-glow: {theme.get('accent_glow', 'rgba(0,255,204,0.3)')};
    --border-color: {theme.get('border_color', 'rgba(255,255,255,0.1)')};
    --font-display: {theme.get('font_display', 'sans-serif')};
    --font-body: {theme.get('font_body', 'sans-serif')};
    --font-mono: {theme.get('font_mono', 'monospace')};
}}"""

        # 替换 JS 中的资源 ID
        js_editor = JS_INLINE_EDITOR.replace("{{RESOURCE_ID}}", str(file_id))

        # 拼接最终页面内容
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self._escape_html(title)}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    {font_link}
    <style>
        /* === CSS CUSTOM PROPERTIES (THEME) === */
        {css_vars}

        /* === RESET === */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        /* === VIEWPORT BASE (from frontend-slides/viewport-base.css) === */
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
        {theme.get('additional_css', '')}
    </style>
</head>
<body>
    <div class="deck-viewport">
        <main class="deck-stage" id="deckStage" role="region" aria-label="幻灯片演示">
            {''.join(slides_html)}
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

        output_path = self.output_dir / f"{file_id}.html"
        output_path.write_text(html_content, encoding="utf-8")
        return str(output_path)

    def _get_bg_and_container(self, theme_id: str, inner_html: str, index: int, active_class: str = "") -> str:
        """根据主题生成特定的背景与结构容器包裹。"""
        # 1. Backgrounds & Overlays based on theme
        bg_html = ""
        if theme_id == "neon-cyber":
            bg_html = """
    <div class="cyber-grid"></div>
    <div class="bg-glow"></div>
    <div class="bg-noise"></div>"""
        elif theme_id == "terminal-green":
            bg_html = """
    <div class="crt-scanlines"></div>"""
        elif theme_id == "dark-botanical":
            bg_html = """
    <div class="bg-noise"></div>
    <div class="botanical-glows">
        <div class="glow-circle glow-1"></div>
        <div class="glow-circle glow-2"></div>
    </div>"""
        elif theme_id == "split-pastel":
            bg_html = """
    <div class="split-grid-overlay"></div>"""
        elif theme_id == "paper-ink":
            bg_html = """
    <div class="paper-texture"></div>"""
        elif theme_id == "notebook-tabs":
            bg_html = ""
        elif theme_id == "swiss-modern":
            bg_html = """
    <div class="swiss-grid-line h-1"></div>
    <div class="swiss-grid-line h-2"></div>"""
        else:
            bg_html = """
    <div class="bg-noise"></div>"""

        # 2. Structural Wrappers based on theme
        container_html = inner_html
        if theme_id == "notebook-tabs":
            container_html = f"""
    <div class="notebook-container">
        <div class="notebook-spine">
            <div class="ring"></div>
            <div class="ring"></div>
            <div class="ring"></div>
            <div class="ring"></div>
            <div class="ring"></div>
        </div>
        <div class="notebook-tabs">
            <div class="notebook-tab t-1">Slide {index + 1}</div>
            <div class="notebook-tab t-2">Lesson</div>
            <div class="notebook-tab t-3">Index</div>
        </div>
        <div class="slide-shell" style="height: 100%; display: flex; flex-direction: column; justify-content: space-between;">
            {inner_html}
        </div>
    </div>"""
        elif theme_id == "pastel-geometry":
            container_html = f"""
    <div class="geometry-container">
        <div class="pastel-geometry-pills">
            <div class="geom-pill p-1"></div>
            <div class="geom-pill p-2"></div>
            <div class="geom-pill p-3"></div>
        </div>
        <div class="slide-shell" style="height: 100%; display: flex; flex-direction: column; justify-content: space-between;">
            {inner_html}
        </div>
    </div>"""
        elif theme_id == "terminal-green":
            container_html = f"""
    <div style="width: 100%; height: 100%; display: flex; flex-direction: column; background: #0d1117; border: 2px solid #30363d; border-radius: 8px; overflow: hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.5);">
        <div class="terminal-header">
            <span class="terminal-dot r"></span>
            <span class="terminal-dot y"></span>
            <span class="terminal-dot g"></span>
            <span style="margin-left: 15px; font-family: monospace; font-size: 14px;">slide_{index + 1:02d}.sh</span>
        </div>
        <div class="slide-shell" style="flex: 1; display: flex; flex-direction: column; justify-content: space-between; padding: 40px 60px; position: relative; overflow: hidden; height: auto;">
            {inner_html}
        </div>
    </div>"""
        else:
            container_html = f"""
    <div class="slide-shell">
        {inner_html}
    </div>"""

        return f"""<section class="slide{active_class}">
    {bg_html}
    {container_html}
</section>"""

    def _render_slide(self, slide: dict, index: int, total: int, theme: dict) -> str:
        """渲染单个幻灯片。"""
        role = slide.get("role", "concept")
        slide_title = slide.get("title", "")
        subtitle = slide.get("subtitle", "")
        takeaway = slide.get("takeaway", "")
        layout = slide.get("layout", "DualPane")
        slots = slide.get("slots", {})

        # 构建导航圆点和页码
        dots_html = "".join([f'<div class="nav-dot{" active" if i == index else ""}"></div>' for i in range(total)])
        nav_area = f'<div class="nav-dots">{dots_html}</div>'
        slide_num = f'<div class="slide-number"><span>{index + 1:02d}</span> / {total}</div>'

        # 封面幻灯片单独处理
        if role == "cover":
            inner_html = self._render_cover_slide_inner(slide_title, subtitle, takeaway)
            active_class = " active visible" if index == 0 else ""
            return self._get_bg_and_container(self.theme_id, inner_html, index, active_class)
        
        # 章节过渡页
        if role in ("prerequisite", "roadmap", "problem_intro"):
            inner_html = self._render_section_slide_inner(slide_title, subtitle, role, slide_num, nav_area, index)
            return self._get_bg_and_container(self.theme_id, inner_html, index)

        # 总结页也做精细排版
        if role == "summary":
            inner_html = self._render_summary_slide_inner(slide_title, slots, takeaway, slide_num, nav_area)
            return self._get_bg_and_container(self.theme_id, inner_html, index)

        # 内容幻灯片通用结构
        inner_html = self._render_content_slide_inner(slide_title, subtitle, layout, slots, takeaway, slide_num, nav_area, index)
        return self._get_bg_and_container(self.theme_id, inner_html, index)

    def _render_cover_slide_inner(self, title: str, subtitle: str | None, takeaway: str) -> str:
        """渲染封面幻灯片内部 — 根据主题呈现不同的封面风格。"""
        subtitle_html = f'<p class="subtitle reveal">{self._escape_html(subtitle)}</p>' if subtitle else ''

        if self.theme_id == "bold-signal":
            # Bold Signal: 大号章节编号 + 彩色焦点卡片
            return f"""
    <div class="title-slide">
        <div class="reveal-scale">
            <span class="section-label" style="margin-bottom: 28px;">教学课件</span>
            <h1 class="main-title">{self._escape_html(title)}</h1>
            {subtitle_html}
            <div class="accent-line" style="margin: 36px auto;"></div>
        </div>
    </div>"""

        elif self.theme_id == "electric-studio":
            # Electric Studio: 分割面板 — 左侧深色内容，右侧白色
            return f"""
    <div style="display: grid; grid-template-columns: 1fr 1fr; height: 100%;">
        <div style="display: flex; flex-direction: column; justify-content: center; padding: 80px 60px 80px 100px; position: relative;">
            <div class="studio-accent-bar"></div>
            <span class="section-label reveal" style="margin-bottom: 32px;">教学课件</span>
            <h1 class="main-title reveal" style="font-size: 80px; text-align: left; max-width: 700px;">{self._escape_html(title)}</h1>
            {f'<p class="subtitle reveal" style="text-align: left; margin-bottom: 0;">{self._escape_html(subtitle)}</p>' if subtitle else ''}
        </div>
        <div style="background: #ffffff; display: flex; align-items: center; justify-content: center;">
            <div class="reveal-scale" style="color: #0a0a0a; font-family: var(--font-display); font-size: 240px; font-weight: 800; opacity: 0.06;">
                01
            </div>
        </div>
    </div>"""

        elif self.theme_id in ("notebook-tabs", "pastel-geometry"):
            # 浅色主题：居中标题 + 优雅装饰
            return f"""
    <div class="title-slide">
        <div class="reveal-scale">
            <span class="section-label" style="margin-bottom: 28px;">教学课件</span>
            <h1 class="main-title">{self._escape_html(title)}</h1>
            {subtitle_html}
            <div class="accent-line" style="margin: 36px auto;"></div>
        </div>
    </div>"""

        else:
            # 默认（Neon Cyber 等暗色主题）：居中标题 + 光晕效果
            return f"""
    <div class="title-slide">
        <div class="reveal-scale">
            <span class="section-label" style="margin-bottom: 28px;">教学课件</span>
            <h1 class="main-title">{self._escape_html(title)}</h1>
            {subtitle_html}
            <div class="accent-line" style="margin: 36px auto;"></div>
            <div class="tagline">知识详解 · 互动课件</div>
        </div>
    </div>"""

    def _render_section_slide_inner(self, title: str, subtitle: str | None, role: str, slide_num: str, nav_area: str, index: int = 0) -> str:
        """渲染章节过渡页内部 — 根据主题呈现不同的章节风格。"""
        role_labels = {
            "prerequisite": "前置知识",
            "roadmap": "学习路线图",
            "problem_intro": "问题引入",
        }
        label = role_labels.get(role, "章节")
        subtitle_html = f'<p class="subtitle reveal" style="font-size: 28px; font-weight: 300;">{self._escape_html(subtitle)}</p>' if subtitle else ''
        section_num = f'{index + 1:02d}'

        if self.theme_id == "bold-signal":
            # Bold Signal: 大号章节编号 + 彩色卡片
            return f"""
        {slide_num}
        {nav_area}
        <div style="display: flex; height: 100%; align-items: center; padding: 0 100px;">
            <div class="reveal-scale" style="flex: 1;">
                <div style="font-family: var(--font-mono); font-size: 120px; font-weight: 900; color: var(--accent); opacity: 0.15; line-height: 1; margin-bottom: -20px;">{section_num}</div>
                <span class="section-label">{label}</span>
                <h2 class="main-title" style="font-size: 72px; margin-top: 24px; margin-bottom: 20px;">{self._escape_html(title)}</h2>
                {subtitle_html}
                <div class="accent-line" style="margin: 24px 0 0;"></div>
            </div>
        </div>
        <div></div>"""

        elif self.theme_id == "electric-studio":
            # Electric Studio: 分割面板 + accent bar
            return f"""
        {slide_num}
        {nav_area}
        <div class="studio-split">
            <div class="studio-left">
                <div class="studio-accent-bar"></div>
                <span class="section-label reveal">{label}</span>
                <h2 class="main-title reveal" style="font-size: 72px; text-align: left; margin-top: 20px;">{self._escape_html(title)}</h2>
                {f'<p class="subtitle reveal" style="text-align: left; margin-bottom: 0;">{self._escape_html(subtitle)}</p>' if subtitle else ''}
            </div>
            <div class="studio-right" style="display: flex; align-items: center; justify-content: center;">
                <div class="reveal-scale" style="font-family: var(--font-display); font-size: 200px; font-weight: 800; color: var(--accent); opacity: 0.08;">{section_num}</div>
            </div>
        </div>"""

        elif self.theme_id == "swiss-modern":
            # Swiss Modern: 不对称布局 + 几何线条
            return f"""
        {slide_num}
        {nav_area}
        <div class="swiss-asymmetric">
            <div class="swiss-main reveal-scale">
                <span class="section-label">{label}</span>
                <h2 class="main-title" style="font-size: 72px; margin-top: 24px;">{self._escape_html(title)}</h2>
                {subtitle_html}
            </div>
            <div class="swiss-detail reveal">
                <div style="font-family: var(--font-mono); font-size: 180px; font-weight: 900; color: var(--accent); opacity: 0.08; line-height: 0.9;">{section_num}</div>
            </div>
        </div>"""

        else:
            # 默认：居中章节页
            return f"""
        {slide_num}
        {nav_area}
        <div class="title-slide">
            <div class="reveal-scale">
                <span class="section-label">{label}</span>
                <h2 class="main-title" style="font-size: 72px; margin-top: 30px; margin-bottom: 20px;">{self._escape_html(title)}</h2>
                {subtitle_html}
                <div class="accent-line" style="margin: 24px auto 0;"></div>
            </div>
        </div>
        <div></div>"""

    def _render_summary_slide_inner(self, title: str, slots: dict, takeaway: str, slide_num: str, nav_area: str) -> str:
        """渲染总结页内部。"""
        summary_items = []
        for slot_blocks in slots.values():
            for block in slot_blocks:
                block_type = block.get("type", "")
                if block_type == "Text":
                    content = block.get("content", "")
                    if content:
                        summary_items.append(content)
                elif block_type == "KeyPoint":
                    label = block.get("label", "")
                    content = block.get("content", "")
                    if label:
                        summary_items.append(f"{label}: {content}" if content else label)

        if not summary_items:
            summary_items = ["本章核心概念已全部拆解完毕", "请结合前后关联知识建立体系", "建议完成课后习题进行自主巩固"]

        items_html = ""
        for i, item in enumerate(summary_items[:4]):
            items_html += f"""
            <div class="summary-card reveal">
                <div class="sum-icon">✓</div>
                <div class="sum-desc">{self._escape_html(item)}</div>
            </div>"""

        takeaway_html = ""
        if takeaway:
            takeaway_html = f"""
        <div class="slide-footer-area">
            <div class="takeaway-bar">
                <span class="takeaway-tag">总结</span>
                <span class="takeaway-text">{self._escape_html(takeaway)}</span>
            </div>
        </div>"""

        return f"""
        <div>
            {slide_num}
            {nav_area}
            <div class="slide-header-area" style="margin-top: 40px; text-align: center;">
                <h2 class="slide-title reveal">{self._escape_html(title)}</h2>
                <p class="slide-subtitle reveal">本章知识提炼与复习要点</p>
            </div>
        </div>
        <div class="summary-grid">
            {items_html}
        </div>
        {takeaway_html}"""

    def _render_content_slide_inner(self, title: str, subtitle: str | None, layout: str,
                               slots: dict, takeaway: str, slide_num: str, nav_area: str, index: int = 0) -> str:
        """渲染通用内容幻灯片内部 — 根据主题选择不同的布局策略。"""
        subtitle_html = f'<p class="slide-subtitle reveal">{self._escape_html(subtitle)}</p>' if subtitle else ''
        section_num = f'{index + 1:02d}'

        # 根据主题选择布局类
        layout_class = self._get_layout_class(layout)
        slots_html = self._render_slots(layout, slots)

        takeaway_html = ""
        if takeaway:
            takeaway_html = f"""
        <div class="slide-footer-area">
            <div class="takeaway-bar">
                <span class="takeaway-tag">要点</span>
                <span class="takeaway-text">{self._escape_html(takeaway)}</span>
            </div>
        </div>"""

        # Bold Signal: 大号章节编号背景
        section_num_html = ""
        if self.theme_id == "bold-signal":
            section_num_html = f'<div class="section-num">{section_num}</div>'

        return f"""
        {section_num_html}
        <div>
            {slide_num}
            {nav_area}
            <div class="slide-header-area" style="margin-top: 40px;">
                <h2 class="slide-title reveal">{self._escape_html(title)}</h2>
                {subtitle_html}
            </div>
        </div>
        <div class="slide-content-area">
            <div class="{layout_class}">
                {slots_html}
            </div>
        </div>
        {takeaway_html}"""

    def _get_layout_class(self, layout: str) -> str:
        """获取布局 CSS 类名 — 根据主题选择最适合的布局。"""
        # 主题特定的布局映射
        theme_layout_map = {
            "electric-studio": {
                "DualPane": "studio-split",
                "TriplePane": "triple-pane",
                "CardCluster": "card-cluster",
            },
            "creative-voltage": {
                "DualPane": "voltage-split",
                "TriplePane": "triple-pane",
                "CardCluster": "card-cluster",
            },
            "swiss-modern": {
                "DualPane": "swiss-asymmetric",
                "TriplePane": "triple-pane",
                "CardCluster": "card-cluster",
            },
        }

        # 先查主题特定映射
        if self.theme_id in theme_layout_map:
            mapped = theme_layout_map[self.theme_id].get(layout)
            if mapped:
                return mapped

        # 通用布局映射
        layout_map = {
            "DualPane": "dual-pane",
            "TriplePane": "triple-pane",
            "CardCluster": "card-cluster",
            "DiagramFocus": "dual-pane",
            "FlowCanvas": "dual-pane",
            "CompareTable": "dual-pane",
            "KnowledgeMap": "dual-pane",
        }
        return layout_map.get(layout, "dual-pane")

    def _render_slots(self, layout: str, slots: dict) -> str:
        """渲染各槽位 — 根据主题布局类分配不同的 HTML 结构。"""
        if not slots:
            return ""

        slot_order = self._get_slot_order(layout, slots)
        html_parts = []

        # 根据当前布局类决定槽位容器
        layout_class = self._get_layout_class(layout)

        for i, slot_name in enumerate(slot_order):
            if slot_name not in slots:
                continue
            blocks = slots[slot_name]
            blocks_html = self._render_blocks(blocks)

            # 主题特定布局的槽位包装
            if layout_class == "studio-split":
                pane_class = "studio-left" if i == 0 else "studio-right"
                html_parts.append(f'<div class="{pane_class}">{blocks_html}</div>')
            elif layout_class == "voltage-split":
                pane_class = "voltage-accent" if i == 0 else "voltage-content"
                html_parts.append(f'<div class="{pane_class}">{blocks_html}</div>')
            elif layout_class == "swiss-asymmetric":
                pane_class = "swiss-main" if i == 0 else "swiss-detail"
                html_parts.append(f'<div class="{pane_class}">{blocks_html}</div>')
            elif layout_class == "card-cluster":
                pane_class = "featured-pane" if slot_name == "featured" else ("cards-pane" if slot_name == "cards" else "")
                html_parts.append(f'<div class="pane {pane_class}">{blocks_html}</div>')
            else:
                html_parts.append(f'<div class="pane">{blocks_html}</div>')

        return "\n".join(html_parts)

    def _get_slot_order(self, layout: str, slots: dict) -> list[str]:
        """获取槽位排序顺序。"""
        default_order = {
            "DualPane": ["left", "right"],
            "TriplePane": ["left", "center", "right"],
            "CardCluster": ["featured", "cards"],
            "DiagramFocus": ["explanation", "diagram"],
            "FlowCanvas": ["annotation", "flow"],
            "CompareTable": ["comparison", "insight"],
            "KnowledgeMap": ["map", "legend"],
        }
        order = default_order.get(layout, list(slots.keys()))
        return [s for s in order if s in slots]

    def _render_blocks(self, blocks: list) -> str:
        """渲染块列表。"""
        html_parts = []
        for block in blocks:
            block_html = self._render_block(block)
            if block_html:
                html_parts.append(f'<div class="reveal">{block_html}</div>')
        return "\n".join(html_parts)

    def _render_block(self, block: dict) -> str:
        """根据类型渲染块。"""
        block_type = block.get("type", "")

        if block_type == "Text":
            return f'<div class="block-text">{self._escape_html(block.get("content", ""))}</div>'
        elif block_type == "KeyPoint":
            return f"""<div class="block-keypoint">
    <div class="kp-label">{self._escape_html(block.get("label", ""))}</div>
    <div class="kp-content">{self._escape_html(block.get("content", ""))}</div>
</div>"""
        elif block_type == "Callout":
            intent = block.get("intent", "info")
            icon = block.get("icon", "💡")
            return f"""<div class="block-callout {self._escape_html(intent)}">
    <span class="callout-icon">{icon}</span>
    <span class="callout-content">{self._escape_html(block.get("content", ""))}</span>
</div>"""
        elif block_type == "Diagram":
            nodes = block.get("nodes", [])
            nodes_html = ""
            for i, node in enumerate(nodes[:4]):
                label = node.get("label", node.get("id", ""))
                nodes_html += f"""
                <div class="diagram-node">
                    <div style="font-size: 24px; margin-bottom: 8px; color: var(--accent); font-family: var(--font-mono); font-weight: bold;">{i + 1}</div>
                    <div style="font-family: var(--font-body); font-size: 15px; color: var(--text-primary); line-height: 1.4;">{self._escape_html(label)}</div>
                </div>"""
            return f"""<div class="block-diagram">
    <div style="font-family: var(--font-mono); font-size: 12px; color: var(--accent); margin-bottom: 12px; text-transform: uppercase; letter-spacing: 2px;">Diagram / 结构图解</div>
    <div class="diagram-grid">{nodes_html}</div>
</div>"""
        elif block_type == "FlowChart":
            steps = block.get("steps", [])
            steps_html = ""
            for i, step in enumerate(steps[:4]):
                steps_html += f"""
                <div class="flow-step">
                    <div class="step-num">{i + 1}</div>
                    <div class="step-content">
                        <div class="step-title">{self._escape_html(step.get("title", ""))}</div>
                        <div class="step-desc">{self._escape_html(step.get("description", ""))}</div>
                    </div>
                </div>"""
            return f"""<div class="block-flowchart">
    {steps_html}
</div>"""
        elif block_type == "Table":
            columns = block.get("columns", [])
            rows = block.get("rows", [])
            if not columns:
                return ""
            th_html = "".join([f'<th>{self._escape_html(col)}</th>' for col in columns])
            tr_html = ""
            for row in rows[:6]:
                cells_html = "".join([f'<td>{self._escape_html(cell)}</td>' for cell in row])
                tr_html += f"<tr>{cells_html}</tr>"
            return f"""<table class="block-table">
    <thead><tr>{th_html}</tr></thead>
    <tbody>{tr_html}</tbody>
</table>"""
        elif block_type == "CardList":
            cards_html = ""
            for card in block.get("cards", [])[:4]:
                icon = card.get("icon", "✓")
                cards_html += f"""
                <div class="block-card">
                    <div class="card-icon">{icon}</div>
                    <div class="card-title">{self._escape_html(card.get("title", ""))}</div>
                    <div class="card-content">{self._escape_html(card.get("content", ""))}</div>
                </div>"""
            return cards_html
        elif block_type == "Formula":
            return f'<div class="block-formula">{self._escape_html(block.get("formula", ""))}</div>'
        elif block_type == "CodeSnippet":
            lang = block.get("language", "python")
            return f"""<div class="block-code">
    <div class="code-header">
        <span class="dot red"></span>
        <span class="dot yellow"></span>
        <span class="dot green"></span>
        <span class="lang">{self._escape_html(lang.upper())}</span>
    </div>
    <pre><code>{self._escape_html(block.get("code", ""))}</code></pre>
</div>"""
        else:
            return f'<div class="block-text">[Block: {self._escape_html(block_type)}]</div>'

    @staticmethod
    def _escape_html(text: str) -> str:
        """HTML 转义。"""
        if not text:
            return ""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#x27;"))

PPTXGenerator = HTMLSlideGenerator
