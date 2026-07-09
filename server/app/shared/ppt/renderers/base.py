from __future__ import annotations

import html
from typing import Any

from app.shared.ppt.models import (
    PPTSlide,
    KeyPoint,
    ProcessStep,
    ComparisonSide,
    SystemNode,
    HierarchyNode,
)


class SlideBodyRenderer:
    """模板专属页面主体渲染基类。
    已重构：生成配合 CSS Grid 的组件化 HTML 结构。
    """

    def render(self, slide: PPTSlide, layout: Any) -> str:
        method_name = f"_{slide.type}"
        method = getattr(self, method_name, None)

        if method is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} does not implement renderer for slide type: {slide.type}"
            )

        return method(slide)

    @staticmethod
    def e(value: object) -> str:
        return html.escape("" if value is None else str(value), quote=True)

    @staticmethod
    def step_attr(step: int) -> str:
        return f' data-step style="--step:{step}"'

    def keyword_pills(self, keywords: list[str], *, class_name: str) -> str:
        if not keywords:
            return ""
        items = "".join(
            f'<span contenteditable="false">{self.e(keyword)}</span>'
            for keyword in keywords
        )
        return f'<div class="{class_name}">{items}</div>'

    def agenda_path(self, steps: list[ProcessStep], *, class_name: str, start_step: int = 4) -> str:
        return "".join(
            f"""<article class="{class_name}"{self.step_attr(index + start_step)}>
  <div class="ta-node-indicator">{index + 1:02d}</div>
  <h3 contenteditable="false">{self.e(step.title)}</h3>
  <p contenteditable="false">{self.e(step.detail)}</p>
</article>"""
            for index, step in enumerate(steps)
        )

    def goal_ladder(self, points: list[KeyPoint], *, class_name: str, start_step: int = 4) -> str:
        return "".join(
            f"""<div class="{class_name}"{self.step_attr(index + start_step)}>
  <span class="ta-matrix-badge" contenteditable="false">{self.e(point.label)}</span>
  <p contenteditable="false">{self.e(point.detail)}</p>
</div>"""
            for index, point in enumerate(points)
        )

    def point_lines(self, points: list[KeyPoint], *, class_name: str, start_step: int = 4) -> str:
        return "".join(
            f"""<div class="{class_name}"{self.step_attr(index + start_step)}>
  <h3 contenteditable="false">{self.e(point.label)}</h3>
  <p contenteditable="false">{self.e(point.detail)}</p>
</div>"""
            for index, point in enumerate(points)
        )

    def aspect_terms(self, points: list[KeyPoint], *, class_name: str, start_step: int = 4) -> str:
        return "".join(
            f"""<div class="{class_name}"{self.step_attr(index + start_step)}>
  <span class="ta-label" contenteditable="false">{self.e(point.label)}</span>
  <p contenteditable="false">{self.e(point.detail)}</p>
</div>"""
            for index, point in enumerate(points)
        )

    def mechanism_chain(self, nodes: list[SystemNode], *, class_name: str, start_step: int = 4) -> str:
        return "".join(
            f"""<article class="{class_name}" data-node="{self.e(node.id)}"{self.step_attr(index + start_step)}>
  <div class="ta-node-indicator">{self.e(node.id).upper()}</div>
  <h3 contenteditable="false">{self.e(node.label)}</h3>
  <p contenteditable="false">{self.e(node.detail)}</p>
</article>"""
            for index, node in enumerate(nodes)
        )

    def misconception_path(self, comparison: list[ComparisonSide], *, class_name: str, start_step: int = 4) -> str:
        if len(comparison) < 2:
            return ""
        myth_side = comparison[0]
        fix_side = comparison[1]
        rows = []
        for i in range(min(len(myth_side.points), len(fix_side.points))):
            rows.append(f"""<div class="{class_name}"{self.step_attr(i + start_step)}>
  <div class="ta-diag-segment">
    <span class="ta-diag-badge m-bug">BUG ({self.e(myth_side.title)})</span>
    <p contenteditable="false">{self.e(myth_side.points[i])}</p>
  </div>
  <div class="ta-diag-segment">
    <span class="ta-diag-badge m-trace">TRACE</span>
    <p contenteditable="false">分析与原理解析。</p>
  </div>
  <div class="ta-diag-segment">
    <span class="ta-diag-badge m-fix">FIX ({self.e(fix_side.title)})</span>
    <p contenteditable="false">{self.e(fix_side.points[i])}</p>
  </div>
</div>""")
        return "".join(rows)

    def hierarchy_nodes(self, hierarchy: list[HierarchyNode], *, class_name: str, start_step: int = 4) -> str:
        return "".join(
            f"""<div class="{class_name} level-{node.level}"{self.step_attr(index + start_step)}>
  <span class="ta-label">{self.e(node.label)}</span>
  <p>{self.e(node.detail)}</p>
</div>"""
            for index, node in enumerate(hierarchy)
        )

    def comparison_table(self, comparison: list[ComparisonSide], *, class_name: str) -> str:
        if not comparison:
            return ""
        headers = "".join(f"<th>{self.e(side.title)}</th>" for side in comparison)
        max_rows = max(len(side.points) for side in comparison)
        rows = []
        for r in range(max_rows):
            row_html = "<tr>"
            for side in comparison:
                val = side.points[r] if r < len(side.points) else ""
                row_html += f'<td contenteditable="false">{self.e(val)}</td>'
            row_html += "</tr>"
            rows.append(row_html)

        return f"""<div class="{class_name}">
  <table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
</div>"""


    def takeaway(self, slide: PPTSlide, *, class_name: str, step: int = 9) -> str:
        if not slide.takeaway:
            return ""
        return (
            f'<div class="{class_name}"{self.step_attr(step)} '
            f'contenteditable="false">{self.e(slide.takeaway)}</div>'
        )