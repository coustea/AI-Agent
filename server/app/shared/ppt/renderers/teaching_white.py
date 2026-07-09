from __future__ import annotations

from app.shared.ppt.models import PPTSlide
from app.shared.ppt.renderers.base import SlideBodyRenderer


class TeachingWhiteRenderer(SlideBodyRenderer):
    """极简教育白皮肤专属渲染器：配合 tw- 样式，通过优雅的边框线与留白呈现内容。"""

    def _cover(self, slide: PPTSlide) -> str:
        keywords = [p.label for p in slide.points]
        seq_items = "".join(
            f'<span data-step style="--step:{i+4}">{self.e(step.title)}</span>'
            for i, step in enumerate(slide.steps[:3])
        )
        return f"""<div class="tw-cover tw-stage">
  <div class="tw-cover-hero" data-step style="--step:3">
    <p class="tw-cover-question" contenteditable="false">{self.e(slide.statement or slide.title)}</p>
    {self.keyword_pills(keywords, class_name="tw-keyword-line")}
  </div>
  <div class="tw-cover-outline" data-step style="--step:4">
    <div class="tw-outline-label">LEARNING PATH</div>
    <div class="tw-outline-seq">
      {seq_items}
    </div>
  </div>
</div>"""

    def _agenda(self, slide: PPTSlide) -> str:
        agenda_steps = "".join(
            f"""<div class="tw-route-step" data-step style="--step:{i+4}">
  <div class="tw-route-step__index">{i+1:02d}</div>
  <div class="tw-route-step__body">
    <h3 contenteditable="false">{self.e(step.title)}</h3>
    <p contenteditable="false">{self.e(step.detail)}</p>
  </div>
</div>"""
            for i, step in enumerate(slide.steps[:3])
        )
        return f"""<div class="tw-agenda tw-stage">
  <div class="tw-route-thesis" data-step style="--step:3">
    <div class="tw-board-label">ROUTE</div>
    <p contenteditable="false">{self.e(slide.statement)}</p>
  </div>
  <div class="tw-route-track">
    {agenda_steps}
  </div>
</div>"""

    def _learning_goals(self, slide: PPTSlide) -> str:
        goals_ladder = "".join(
            f"""<div class="tw-goal-step" data-step style="--step:{i+4}">
  <div class="tw-goal-step__verb" contenteditable="false">{self.e(point.label)}</div>
  <div class="tw-goal-step__text" contenteditable="false">{self.e(point.detail)}</div>
</div>"""
            for i, point in enumerate(slide.points[:4])
        )
        return f"""<div class="tw-goals tw-stage">
  <div class="tw-goal-thesis" data-step style="--step:3">
    <div class="tw-board-label">GOALS</div>
    <p contenteditable="false">{self.e(slide.statement)}</p>
  </div>
  <div class="tw-goal-ladder">
    {goals_ladder}
  </div>
</div>"""

    def _hook_question(self, slide: PPTSlide) -> str:
        question_lines = "".join(
            f"""<div class="tw-question-line" data-step style="--step:{i+4}">
  <h3 contenteditable="false">{self.e(point.label)}</h3>
  <p contenteditable="false">{self.e(point.detail)}</p>
</div>"""
            for i, point in enumerate(slide.points[:3])
        )
        return f"""<div class="tw-question tw-stage">
  <div class="tw-question-focus" data-step style="--step:3">
    <span class="tw-board-label">QUESTION</span>
    <p contenteditable="false">{self.e(slide.statement or slide.question)}</p>
  </div>
  <div class="tw-question-lines">
    {question_lines}
  </div>
</div>"""

    def _definition(self, slide: PPTSlide) -> str:
        definition_breakdown = "".join(
            f"""<div class="tw-term-row" data-step style="--step:{i+4}">
  <div class="tw-term-row__label" contenteditable="false">{self.e(point.label)}</div>
  <div class="tw-term-row__detail" contenteditable="false">{self.e(point.detail)}</div>
</div>"""
            for i, point in enumerate(slide.points[:4])
        )
        return f"""<div class="tw-definition tw-stage">
  <div class="tw-definition-statement" data-step style="--step:3">
    <span class="tw-board-label">DEFINITION</span>
    <p contenteditable="false">{self.e(slide.statement or slide.title)}</p>
  </div>
  <div class="tw-term-breakdown">
    {definition_breakdown}
  </div>
</div>"""

    def _concept_boundary(self, slide: PPTSlide) -> str:
        boundary_cards = "".join(
            f"""<div class="tw-term-row" data-step style="--step:{i+4}">
  <div class="tw-term-row__label" contenteditable="false">{self.e(point.label)}</div>
  <div class="tw-term-row__detail" contenteditable="false">{self.e(point.detail)}</div>
</div>"""
            for i, point in enumerate(slide.points[:3])
        )
        return f"""<div class="tw-definition tw-stage">
  <div class="tw-definition-statement" data-step style="--step:3">
    <span class="tw-board-label">BOUNDARY</span>
    <p contenteditable="false">{self.e(slide.statement)}</p>
  </div>
  <div class="tw-term-breakdown">
    {boundary_cards}
  </div>
</div>"""

    def _mechanism_overview(self, slide: PPTSlide) -> str:
        mechanism_steps = "".join(
            f"""<div class="tw-route-step" data-step style="--step:{i+4}">
  <div class="tw-route-step__index">{i+1:02d}</div>
  <div class="tw-route-step__body">
    <h3 contenteditable="false">{self.e(node.label)}</h3>
    <p contenteditable="false">{self.e(node.detail)}</p>
  </div>
</div>"""
            for i, node in enumerate(slide.nodes[:3])
        )
        return f"""<div class="tw-agenda tw-stage">
  <div class="tw-route-thesis" data-step style="--step:3">
    <div class="tw-board-label">MECHANISM</div>
    <p contenteditable="false">{self.e(slide.statement)}</p>
  </div>
  <div class="tw-route-track">
    {mechanism_steps}
  </div>
</div>"""

    def _knowledge_explain(self, slide: PPTSlide) -> str:
        explanation_breakdown = "".join(
            f"""<div class="tw-term-row" data-step style="--step:{i+4}">
  <div class="tw-term-row__label" contenteditable="false">{self.e(point.label)}</div>
  <div class="tw-term-row__detail" contenteditable="false">{self.e(point.detail)}</div>
</div>"""
            for i, point in enumerate(slide.points[:4])
        )
        return f"""<div class="tw-definition tw-stage">
  <div class="tw-definition-statement" data-step style="--step:3">
    <span class="tw-board-label">EXPLAIN</span>
    <p contenteditable="false">{self.e(slide.statement or slide.title)}</p>
  </div>
  <div class="tw-term-breakdown">
    {explanation_breakdown}
  </div>
</div>"""

    def _comparison(self, slide: PPTSlide) -> str:
        return f"""<div class="tw-comparison tw-stage">
  <div class="tw-comparison-thesis" data-step style="--step:3">
    <span class="tw-board-label">COMPARISON</span>
    <p contenteditable="false">{self.e(slide.statement)}</p>
  </div>
  <div class="tw-comparison-matrix" data-step style="--step:4">
    {self.comparison_table(slide.comparison, class_name="tw-table")}
  </div>
</div>"""

    def _misconception(self, slide: PPTSlide) -> str:
        if len(slide.comparison) < 2:
            return ""
        myth_side = slide.comparison[0]
        fix_side = slide.comparison[1]
        rows = []
        for i in range(min(len(myth_side.points), len(fix_side.points))):
            rows.append(f"""<div class="tw-mis-step" data-step style="--step:{i+4}">
  <div class="tw-mis-step__myth">
    <span>BUG ({self.e(myth_side.title)})</span>
    <p contenteditable="false">{self.e(myth_side.points[i])}</p>
  </div>
  <div class="tw-mis-step__reason">
    <span>TRACE</span>
    <p contenteditable="false">分析与原理解析。</p>
  </div>
  <div class="tw-mis-step__truth">
    <span>FIX ({self.e(fix_side.title)})</span>
    <p contenteditable="false">{self.e(fix_side.points[i])}</p>
  </div>
</div>""")
        return f"""<div class="tw-mis tw-stage">
  <div class="tw-mis-thesis" data-step style="--step:3">
    <span class="tw-board-label">DIAGNOSIS</span>
    <p contenteditable="false">{self.e(slide.statement)}</p>
  </div>
  <div class="tw-mis-path">
    {"".join(rows)}
  </div>
</div>"""

    def _knowledge_map(self, slide: PPTSlide) -> str:
        branches = "".join(
            f"""<div class="tw-map-branch" data-step style="--step:{i+4}">
  <h3 contenteditable="false">{self.e(node.label)}</h3>
  <div class="tw-map-branch__items">
    <span contenteditable="false">{self.e(node.detail)}</span>
  </div>
</div>"""
            for i, node in enumerate(slide.hierarchy[:4])
        )
        return f"""<div class="tw-map tw-stage">
  <div class="tw-map-rootline" data-step style="--step:3">
    <span class="tw-board-label">KNOWLEDGE NETWORK</span>
    <p contenteditable="false">{self.e(slide.statement)}</p>
  </div>
  <div class="tw-map-branches">
    {branches}
  </div>
</div>"""

    def _closing(self, slide: PPTSlide) -> str:
        return f"""<div class="tw-closing tw-stage">
  <div class="tw-closing-statement" data-step style="--step:3">
    <span>OUTRO</span>
    <p contenteditable="false">{self.e(slide.takeaway or slide.statement or slide.title)}</p>
  </div>
</div>"""