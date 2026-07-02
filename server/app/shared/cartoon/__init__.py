"""Cartoon video generation pipeline — multi-agent HTML-based animation.

Architecture (mirrors shared/ppt pipeline):
  Planner  → 规划场景叙事与时间线
  Director → 选择视觉风格与动画策略
  Author   → 生成 HyperFrames HTML 合成文件
  Validator → 静态校验 HTML 结构与 GSAP 语法
  Repair   → 根据校验结果定向修复

HyperFrames contract:
  - Root element: data-composition-id, data-start="0", data-width, data-height, data-duration
  - Scene clips: class="clip", data-start, data-duration, data-track-index
  - Animation: GSAP timeline (paused: true), registered in window.__timelines[composition-id]
  - No external scripts except GSAP CDN
  - No external media (all inline SVG/CSS)
"""
