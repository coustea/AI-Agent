from __future__ import annotations

from app.shared.ppt.models import PPTSlide
from app.shared.ppt.renderers.base import SlideBodyRenderer


class TechnicalAtlasRenderer(SlideBodyRenderer):
    """深色技术图谱皮肤专属渲染器：全屏网格布局，消除大面积留白。"""

    def _cover(self, slide: PPTSlide) -> str:
        keywords = [p.label for p in slide.points]
        return f"""<div class="ta-stage ta-cover-layout">
  <div class="ta-cover-left" data-step style="--step:3">
    <div class="ta-console-head">boot://knowledge-graph</div>
    <p class="ta-cover-statement" contenteditable="false">{self.e(slide.statement or slide.title)}</p>
    {self.keyword_pills(keywords, class_name="ta-keyword-line")}
  </div>
  <div class="ta-cover-right" data-step style="--step:4">
    <div class="ta-console-head">system.status</div>
    <div class="ta-grid-matrix" style="grid-template-columns: 1fr; gap: 20px;">
        <div class="ta-matrix-card"><div class="ta-matrix-badge">MODE</div><p>TECH ATLAS</p></div>
        <div class="ta-matrix-card"><div class="ta-matrix-badge">FLOW</div><p>DEFINE → TRACE → MAP</p></div>
    </div>
  </div>
</div>"""

    def _agenda(self, slide: PPTSlide) -> str:
        return f"""<div class="ta-stage">
  <div data-step style="--step:3">
    <div class="ta-console-head">route.plan()</div>
    <p style="color:var(--ink-soft); font-size:24px;">{self.e(slide.statement)}</p>
  </div>
  <div class="ta-horizontal-chain">
    {self.agenda_path(slide.steps, class_name="ta-node-card", start_step=4)}
  </div>
  {self.takeaway(slide, class_name="ta-output-panel")}
</div>"""

    def _learning_goals(self, slide: PPTSlide) -> str:
        return f"""<div class="ta-stage">
  <div data-step style="--step:3">
    <div class="ta-console-head">capability.matrix</div>
    <p style="color:var(--ink-soft); font-size:24px;">{self.e(slide.statement)}</p>
  </div>
  <div class="ta-grid-matrix">
    {self.goal_ladder(slide.points, class_name="ta-matrix-card", start_step=4)}
  </div>
  {self.takeaway(slide, class_name="ta-output-panel")}
</div>"""

    def _hook_question(self, slide: PPTSlide) -> str:
        return f"""<div class="ta-stage ta-split-layout">
  <div class="ta-split-left" data-step style="--step:3">
    <div class="ta-console-head">$ question --trace</div>
    <p class="ta-cover-statement" contenteditable="false">{self.e(slide.statement or slide.question)}</p>
  </div>
  <div class="ta-split-right">
    {self.point_lines(slide.points, class_name="ta-list-row", start_step=4)}
  </div>
</div>"""

    def _definition(self, slide: PPTSlide) -> str:
        return f"""<div class="ta-stage ta-split-layout">
  <div class="ta-split-left" data-step style="--step:3">
    <div class="ta-console-head">definition.spec</div>
    <p class="ta-cover-statement" contenteditable="false">{self.e(slide.statement or slide.title)}</p>
  </div>
  <div class="ta-split-right">
    {self.point_lines(slide.points, class_name="ta-list-row", start_step=4)}
  </div>
</div>"""

    def _concept_boundary(self, slide: PPTSlide) -> str:
        return f"""<div class="ta-stage">
  <div data-step style="--step:3">
    <div class="ta-console-head">diagnose.boundary()</div>
    <p style="color:var(--ink-soft); font-size:24px;">{self.e(slide.statement)}</p>
  </div>
  <div class="ta-split-layout" style="grid-template-columns: 1fr 1fr; margin-top: 40px;">
    {self.point_lines(slide.points[:2], class_name="ta-matrix-card", start_step=4)}
  </div>
  {self.takeaway(slide, class_name="ta-output-panel")}
</div>"""

    def _mechanism_overview(self, slide: PPTSlide) -> str:
        return f"""<div class="ta-stage">
  <div data-step style="--step:3">
    <div class="ta-console-head">core.mechanism</div>
    <p style="color:var(--ink-soft); font-size:24px;">{self.e(slide.statement)}</p>
  </div>
  <div class="ta-horizontal-chain">
    {self.mechanism_chain(slide.nodes, class_name="ta-node-card", start_step=4)}
  </div>
  {self.takeaway(slide, class_name="ta-output-panel")}
</div>"""

    def _knowledge_explain(self, slide: PPTSlide) -> str:
        return f"""<div class="ta-stage ta-split-layout">
  <div class="ta-split-left" data-step style="--step:3">
    <div class="ta-console-head">module.explain</div>
    <p class="ta-cover-statement" contenteditable="false">{self.e(slide.statement or slide.title)}</p>
  </div>
  <div class="ta-split-right">
    {self.point_lines(slide.points, class_name="ta-list-row", start_step=4)}
  </div>
</div>"""

    def _comparison(self, slide: PPTSlide) -> str:
        return f"""<div class="ta-stage">
  <div data-step style="--step:3" style="margin-bottom: 24px;">
    <div class="ta-console-head">compare.params</div>
    <p style="color:var(--ink-soft); font-size:24px;">{self.e(slide.statement)}</p>
  </div>
  <div data-step style="--step:4" style="flex-grow: 1; min-height: 0;">
    {self.comparison_table(slide.comparison, class_name="ta-table-container")}
  </div>
  {self.takeaway(slide, class_name="ta-output-panel")}
</div>"""

    def _misconception(self, slide: PPTSlide) -> str:
        return f"""<div class="ta-stage">
  <div data-step style="--step:3">
    <div class="ta-console-head">debug.knowledge()</div>
    <p style="color:var(--ink-soft); font-size:24px;">{self.e(slide.statement)}</p>
  </div>
  <div class="ta-diagnostic-stack">
    {self.misconception_path(slide.comparison, class_name="ta-diagnostic-row", start_step=4)}
  </div>
  {self.takeaway(slide, class_name="ta-output-panel")}
</div>"""

    def _knowledge_map(self, slide: PPTSlide) -> str:
        return f"""<div class="ta-stage ta-split-layout">
  <div class="ta-split-left" data-step style="--step:3">
    <div class="ta-console-head">root.knowledge</div>
    <p class="ta-cover-statement" contenteditable="false">{self.e(slide.statement)}</p>
  </div>
  <div class="ta-split-right">
    {self.hierarchy_nodes(slide.hierarchy, class_name="ta-list-row", start_step=4)}
  </div>
</div>"""

    def _closing(self, slide: PPTSlide) -> str:
        return f"""<div class="ta-stage" style="justify-content: center; align-items: center;">
  <div data-step style="--step:3" style="text-align: center;">
    <div class="ta-console-head" style="justify-content: center;">final.output</div>
    <p class="ta-cover-statement" style="border: none; font-size: 56px; padding: 0; margin-top: 32px;" contenteditable="false">{self.e(slide.takeaway or slide.statement or slide.title)}</p>
  </div>
</div>"""