"""Compile structured teaching scenes into a validated template composition."""

from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

from app.shared.cartoon.layouts import (
    layout_scene,
)
from app.shared.cartoon.schemas import (
    CompositionPlan,
    TeachingLesson,
    TeachingScene,
    TeachingStep,
    stage_visual_model,
)
from app.shared.cartoon.templates import (
    CartoonTemplate,
    CartoonTemplateCatalog,
)


COMPOSITION_ID = (
    "cartoon-teaching-video"
)

_ACTION_LABELS = {
    "reveal": "建立对象",
    "focus": "聚焦观察",
    "compare": "对比判断",
    "traverse": "顺序遍历",
    "transfer": "数据传递",
    "mutate": "状态变化",
    "insert": "结构插入",
    "remove": "结构移除",
    "connect": "建立关系",
    "highlight": "重点强调",
}

_MECHANISM_ACTION_LABELS = {
    ("state_transition", "transfer"): "状态转换",
    ("state_transition", "mutate"): "状态更新",
    ("message_exchange", "transfer"): "消息传递",
    ("data_flow", "transfer"): "数据传递",
    ("pipeline", "transfer"): "阶段流转",
    ("memory_change", "mutate"): "内存更新",
    ("container_operation", "insert"): "写入容器",
    ("container_operation", "remove"): "移出容器",
    ("tree_growth", "insert"): "节点展开",
    ("graph_traversal", "traverse"): "路径遍历",
    ("comparison", "compare"): "对比判断",
}

_MECHANISM_LABELS = {
    "structure": "结构关系",
    "sequence": "顺序过程",
    "state_transition": "状态转换",
    "data_flow": "数据流",
    "message_exchange": "消息交换",
    "container_operation": "容器操作",
    "tree_growth": "树形展开",
    "graph_traversal": "图遍历",
    "timeline": "时间线",
    "memory_change": "内存变化",
    "pipeline": "流水线",
    "comparison": "对比辨析",
}

_MODE_LABELS = {
    "concept": "概念讲解",
    "algorithm": "算法过程",
    "protocol": "协议交互",
    "state-machine": "状态机",
    "architecture": "系统结构",
    "comparison": "对比讲解",
}


_RICH_RUNTIME_JS = r"""
const RichRuntime = (() => {
  const pointInCanvas = (canvas, element) => {

    if (!canvas || !element) return null;

    const canvasRect = canvas.getBoundingClientRect();
    const rect = element.getBoundingClientRect();

    return {
      x: rect.left - canvasRect.left + rect.width / 2,
      y: rect.top - canvasRect.top + rect.height / 2,
    };
  };

  const prepare = () => {
    document.querySelectorAll("[data-motion-token]").forEach((token) => {
      gsap.set(token, {
        opacity: 0,
        scale: 0.65,
        x: 0,
        y: 0,
        transformOrigin: "50% 50%",
      });
    });
  };

  const drawEdge = (tl, edge, at, duration) => {
    if (!edge) return;

    tl.set(
      edge,
      {
        visibility: "visible",
        opacity: 0,
      },
      at
    );
    tl.to(
      edge,
      {
        opacity: 1,
        duration: Math.max(0.22, duration),
        ease: "power2.out",
      },
      at
    );
  };

  const moveToken = (tl, canvas, token, elements, at, duration) => {

    if (!token || elements.length < 2) return;

    const points = elements
      .map((element) => pointInCanvas(canvas, element))
      .filter(Boolean);

    if (points.length < 2) return;

    const tokenRect = token.getBoundingClientRect();
    const offsetX = tokenRect.width / 2;
    const offsetY = tokenRect.height / 2;

    gsap.set(token, {
      x: points[0].x - offsetX,
      y: points[0].y - offsetY,
      opacity: 0,
      scale: 0.65,
    });

    tl.to(
      token,
      {
        opacity: 1,
        scale: 1,
        duration: 0.16,
        ease: "power2.out",
      },
      at
    );

    const segmentDuration = Math.max(
      0.24,
      (duration - 0.32) / Math.max(1, points.length - 1)
    );

    points.slice(1).forEach((point, index) => {
      tl.to(
        token,
        {
          x: point.x - offsetX,
          y: point.y - offsetY,
          duration: segmentDuration,
          ease: index % 2 === 0
            ? "power2.inOut"
            : "sine.inOut",
        },
        at + 0.16 + index * segmentDuration
      );
    });

    tl.to(
      token,
      {
        opacity: 0,
        scale: 0.72,
        duration: 0.16,
        ease: "power1.in",
      },
      at + duration - 0.16
    );
  };

  const compare = (tl, allNodes, targets, at, duration) => {
    if (!targets.length) return;

    const others = allNodes.filter(
      (node) => !targets.includes(node)
    );

    if (others.length) {
      tl.to(
        others,
        {
          opacity: 0.28,
          duration: 0.22,
          ease: "power1.out",
        },
        at
      );
    }

    tl.to(
      targets,
      {
        scale: 1.055,
        duration: 0.28,
        ease: "back.out(1.8)",
      },
      at + 0.08
    );

    tl.to(
      targets,
      {
        scale: 1,
        duration: 0.24,
        ease: "power1.out",
      },
      at + Math.max(0.34, duration * 0.56)
    );

    if (others.length) {
      tl.to(
        others,
        {
          opacity: 1,
          duration: 0.24,
          ease: "power1.out",
        },
        at + Math.max(0.5, duration - 0.24)
      );
    }
  };

  const mutate = (tl, targets, at, duration) => {
    if (!targets.length) return;

    const slice = Math.max(
      0.12,
      Math.min(0.22, duration / 5)
    );

    tl.to(
      targets,
      {
        x: -7,
        duration: slice,
        ease: "power1.inOut",
      },
      at
    );

    tl.to(
      targets,
      {
        x: 7,
        duration: slice,
        ease: "power1.inOut",
      },
      at + slice
    );

    tl.to(
      targets,
      {
        x: 0,
        scale: 1.055,
        duration: slice,
        ease: "power1.out",
      },
      at + slice * 2
    );

    tl.to(
      targets,
      {
        scale: 1,
        duration: slice,
        ease: "power1.out",
      },
      at + Math.max(slice * 3, duration - slice)
    );
  };

  const badgeAnchor = (canvas, refs) => {
    const elements = [
      refs.source,
      refs.destination,
      ...(refs.targets || []),
    ].filter(Boolean);

    const canvasRect = canvas.getBoundingClientRect();
    const points = elements.map((element) => {
      const rect = element.getBoundingClientRect();
      return {
        x: rect.left - canvasRect.left + rect.width / 2,
        y: rect.top - canvasRect.top,
      };
    });

    if (!points.length) return null;

    return {
      x: points.reduce((sum, point) => sum + point.x, 0) / points.length,
      y: Math.max(
        8,
        Math.min(
          ...points.map((point) => point.y)
        ) - 40
      ),
    };
  };

  const showBadge = (tl, refs, payload, at, duration) => {
    const badge = refs.badge;
    const canvas = refs.canvas;
    if (!badge || !canvas) return;

    const point = badgeAnchor(canvas, refs);
    if (!point) return;

    const rect = badge.getBoundingClientRect();
    const label = String(payload.label || payload.note || payload.kind || "");

    tl.call(
      () => {
        if (label) badge.textContent = label;
        badge.dataset.actionKind = String(payload.kind || "");
        badge.dataset.actionMechanism = String(payload.mechanism || "");
      },
      null,
      at
    );

    tl.set(
      badge,
      {
        visibility: "visible",
        opacity: 0,
        scale: 0.84,
        x: point.x - rect.width / 2,
        y: point.y,
      },
      at
    );

    tl.to(
      badge,
      {
        opacity: 1,
        scale: 1,
        y: point.y - 6,
        duration: 0.18,
        ease: "power2.out",
      },
      at + 0.02
    );

    tl.to(
      badge,
      {
        opacity: 0,
        scale: 0.92,
        y: point.y - 16,
        duration: 0.18,
        ease: "power1.in",
      },
      at + Math.max(0.24, duration - 0.2)
    );

    tl.set(
      badge,
      {
        visibility: "hidden",
      },
      at + Math.max(0.42, duration)
    );
  };

  const action = (tl, refs, payload, at) => {
    Runtime.action(tl, refs, payload, at);

    if (!refs.scene) return;

    const duration = Math.max(
      0.24,
      Number(payload.duration) || 0.7
    );

    const targets = refs.targets;
    const source = refs.source;
    const destination = refs.destination;

    showBadge(
      tl,
      refs,
      payload,
      at,
      duration
    );

    if (payload.kind === "transfer") {
      drawEdge(
        tl,
        refs.edges[0],
        at + duration * 0.08,
        duration * 0.62
      );

      moveToken(
        tl,
        refs.canvas,
        refs.token,
        [refs.source, refs.destination].filter(Boolean),
        at,
        duration
      );

      const destinationNode = refs.destination;

      if (destinationNode) {
        tl.to(
          destinationNode,
          {
            scale: 1.06,
            duration: 0.18,
            ease: "back.out(2)",
          },
          at + duration * 0.76
        );

        tl.to(
          destinationNode,
          {
            scale: 1,
            duration: 0.2,
            ease: "power1.out",
          },
          at + duration * 0.88
        );
      }
    } else if (payload.kind === "traverse") {
      moveToken(
        tl,
        refs.canvas,
        refs.token,
        refs.targets,
        at,
        duration
      );

      refs.edges.forEach((edge, index) => {
          drawEdge(
            tl,
            edge,
            at +
              index *
                duration /
                Math.max(
                  1,
                  refs.edges.length
                ),
            duration /
              Math.max(
                1,
                refs.edges.length
              )
          );
      });
    } else if (payload.kind === "connect") {
      drawEdge(
        tl,
        refs.edges[0],
        at,
        duration * 0.85
      );
    } else if (payload.kind === "compare") {
      compare(
        tl,
        refs.allNodes,
        targets,
        at,
        duration
      );
    } else if (payload.kind === "mutate") {
      mutate(
        tl,
        targets,
        at,
        duration
      );
    }
  };

  return {
    prepare,
    action,
  };
})();
""".strip()


def _seconds(
    milliseconds: int,
) -> str:
    return (
        f"{milliseconds / 1000:.3f}"
        .rstrip("0")
        .rstrip(".")
    )


def _js(
    value: object,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
    ).replace(
        "</",
        "<\\/",
    )


def _action_runtime_label(
    scene: TeachingScene,
    action,
) -> str:
    if label := _MECHANISM_ACTION_LABELS.get(
        (
            scene.mechanism,
            action.kind,
        )
    ):
        return label

    return _ACTION_LABELS.get(
        action.kind,
        "过程变化",
    )


def _motion_artifacts(
    scene: TeachingScene,
    scene_index: int,
) -> str:
    result: list[str] = []

    for step_index, step in enumerate(scene.steps):
        for index, action in enumerate(
            step.actions
        ):
            if action.kind not in {
                "transfer",
                "traverse",
            }:
                continue

            token = f"cartoon-token-{scene_index}-{step_index}-{index}"

            result.append(
                '<span class="visual-motion-token" '
                f'data-motion-token="{html.escape(token, quote=True)}" '
                'aria-hidden="true" '
                'style="position:absolute;left:0;top:0;'
                'width:18px;height:18px;border-radius:999px;'
                'background:var(--accent-color,#2f7df6);'
                'box-shadow:0 0 0 6px rgba(47,125,246,.13),'
                '0 8px 22px rgba(47,125,246,.28);'
                'opacity:0;pointer-events:none;z-index:12">'
                "</span>"
            )

        for index, action in enumerate(
            step.actions
        ):
            badge = f"cartoon-badge-{scene_index}-{step_index}-{index}"
            label = _action_runtime_label(
                scene,
                action,
            )

            result.append(
                '<span '
                f'id="{html.escape(badge, quote=True)}" '
                'class="visual-action-badge" '
                f'data-action-badge="{html.escape(badge, quote=True)}" '
                f'data-action-kind="{html.escape(action.kind, quote=True)}" '
                f'data-action-mechanism="{html.escape(scene.mechanism, quote=True)}" '
                'aria-hidden="true">'
                f"{html.escape(label)}"
                "</span>"
            )

    return "".join(
        result
    )


def _stage_html(
    scene: TeachingScene,
    scene_index: int,
) -> str:
    positions = layout_scene(
        scene
    )

    initial_nodes = {
        node.id: node
        for node
        in scene.visual_model.nodes
    }

    initial_edge_keys = {
        (
            edge.source_id,
            edge.target_id,
            edge.kind,
            edge.label,
        )
        for edge
        in scene.visual_model.edges
    }

    initial_visibility = {
        node.id: node.initially_visible
        for node
        in scene.visual_model.nodes
    }

    staged = stage_visual_model(
        scene
    )

    nodes = {
        node.id: node
        for node
        in staged.nodes
    }

    edges = staged.edges

    items: list[str] = [
        '<svg class="visual-edges" aria-hidden="true">'
    ]

    for edge_index, edge in enumerate(edges):
        edge_key = (
            edge.source_id,
            edge.target_id,
            edge.kind,
            edge.label,
        )

        edge_hidden_initially = (
            not initial_visibility.get(
                edge.source_id,
                False,
            )
            or not initial_visibility.get(
                edge.target_id,
                False,
            )
        )

        future = (
            " is-future"
            if (
                edge_key
                not in initial_edge_keys
                or edge_hidden_initially
            )
            else ""
        )

        edge_id = (
            f"{edge.source_id}:"
            f"{edge.target_id}:"
            f"{edge.kind}:"
            f"{edge.label}"
        )

        items.append(
            f'<line id="cartoon-edge-{scene_index}-{edge_index}" '
            'class="visual-edge '
            f'visual-edge--{html.escape(edge.kind, quote=True)}'
            f'{future}" '
            f'data-edge="{html.escape(edge_id, quote=True)}" '
            f'data-source="{html.escape(edge.source_id, quote=True)}" '
            f'data-target="{html.escape(edge.target_id, quote=True)}" '
            f'data-kind="{html.escape(edge.kind, quote=True)}" '
            f'data-label="{html.escape(edge.label, quote=True)}">'
            "</line>"
        )

    items.append(
        "</svg>"
    )

    for node_index, (node_id, node) in enumerate(nodes.items()):
        position = positions[
            node_id
        ]

        initial = initial_nodes.get(
            node_id
        )

        display = (
            initial
            or node
        )

        future = (
            " is-future"
            if (
                initial is None
                or not display.initially_visible
            )
            else ""
        )

        value = (
            ""
            if display.value is None
            else (
                "<em data-node-value>"
                f"{html.escape(str(display.value))}"
                "</em>"
            )
        )

        detail = (
            "<small>"
            f"{html.escape(display.detail)}"
            "</small>"
            if display.detail
            else ""
        )

        items.append(
            f'<article id="cartoon-node-{scene_index}-{node_index}" '
            'class="visual-node '
            f'visual-node--{html.escape(display.kind, quote=True)}'
            f'{future}" '
            f'data-node="{html.escape(node_id, quote=True)}" '
            f'data-kind="{html.escape(display.kind, quote=True)}" '
            f'data-state="{html.escape(display.state, quote=True)}" '
            f'data-group="{html.escape(display.group_id or "", quote=True)}" '
            f'data-initial-visible="'
            f'{str(display.initially_visible).lower()}" '
            f'style="--node-x:{position.x:.2f}%;'
            f'--node-y:{position.y:.2f}%;'
            f'--node-w:{position.width:.2f}%;'
            f'--node-h:{position.height:.2f}%;'
            'width:var(--node-w);'
            'min-height:var(--node-h)">'
            f"<strong>{html.escape(display.label)}</strong>"
            f"{detail}"
            f"{value}"
            "</article>"
        )

    items.append(
        _motion_artifacts(
            scene,
            scene_index,
        )
    )

    return "".join(
        items
    )


def _layout_name(
    scene: TeachingScene,
) -> str:
    if scene.mechanism in {
        "data_flow",
        "message_exchange",
        "sequence",
        "pipeline",
    }:
        return "trace-board"

    if scene.mechanism in {
        "container_operation",
        "memory_change",
    }:
        return "structure-lab"

    if scene.mechanism in {
        "state_transition",
        "graph_traversal",
        "tree_growth",
        "timeline",
    }:
        return "state-map"

    if scene.mechanism == "comparison":
        return "comparison-board"

    return "concept-board"


def _action_label(
    scene: TeachingScene,
    step: TeachingStep,
) -> str:
    if not step.actions:
        return _ACTION_LABELS["focus"]

    return _action_runtime_label(
        scene,
        step.actions[0],
    )


def _mechanism_label(
    scene: TeachingScene,
) -> str:
    return _MECHANISM_LABELS.get(
        scene.mechanism,
        "计算过程",
    )


def _mode_label(
    scene: TeachingScene,
) -> str:
    return _MODE_LABELS.get(
        scene.mode,
        scene.mode,
    )


def _focus_summary(
    scene: TeachingScene,
    step: TeachingStep,
) -> str:
    nodes = {
        node.id: node
        for node
        in stage_visual_model(scene).nodes
    }

    labels = [
        nodes[node_id].label
        for node_id
        in step.focus_ids
        if node_id in nodes
    ]

    if labels:
        return " / ".join(
            labels[:3]
        )

    if step.actions:
        targets = [
            nodes[node_id].label
            for node_id
            in step.actions[0].target_ids
            if node_id in nodes
        ]

        if targets:
            return " / ".join(
                targets[:3]
            )

    return scene.visual_model.label or scene.title


def _teaching_panel_html(
    timed_scene,
) -> str:
    scene = timed_scene.scene

    summaries = []

    for index, timed in enumerate(
        timed_scene.steps
    ):
        step = timed.step
        summaries.append(
            f'<article data-step-summary="{html.escape(timed.scene_id, quote=True)}:'
            f'{html.escape(step.id, quote=True)}" '
            f'data-step-summary-index="{index}">'
            f"<b>{html.escape(_action_label(scene, step))}</b>"
            f"<strong>{html.escape(_focus_summary(scene, step))}</strong>"
            f"<span>{html.escape(step.narration)}</span>"
            "</article>"
        )

    key_points = []

    for node in stage_visual_model(scene).nodes[:4]:
        detail = (
            f"<span>{html.escape(node.detail)}</span>"
            if node.detail
            else ""
        )

        key_points.append(
            "<li>"
            f"<b>{html.escape(node.label)}</b>"
            f"{detail}"
            "</li>"
        )

    return (
        '<aside data-slot="teaching-panel">'
        '<div class="panel-kicker">'
        f"<span>{html.escape(_mode_label(scene))}</span>"
        f"<b>{html.escape(_mechanism_label(scene))}</b>"
        "</div>"
        "<div class=\"panel-focus\">"
        f"<p>{html.escape(scene.objective)}</p>"
        "</div>"
        '<div class="panel-steps">'
        + "".join(summaries)
        + "</div>"
        '<ul class="panel-keypoints">'
        + "".join(key_points)
        + "</ul>"
        "</aside>"
    )


def _scene_html(
    timed_scene,
    total_scenes: int,
    course: str,
) -> str:
    scene = timed_scene.scene
    layout = _layout_name(
        scene
    )

    chips = "".join(
        f'<span data-step-chip="{index}">'
        f"{index + 1:02d}"
        "</span>"
        for index
        in range(
            len(scene.steps)
        )
    )

    return (
        f'<section id="cartoon-scene-{timed_scene.index}" '
        'class="teaching-scene clip" '
        f'data-scene="{html.escape(scene.id, quote=True)}" '
        f'data-scene-kind="{html.escape(scene.mode, quote=True)}" '
        f'data-mechanism="{html.escape(scene.mechanism, quote=True)}" '
        f'data-layout="{html.escape(layout, quote=True)}" '
        f'data-start="{_seconds(timed_scene.start_ms)}" '
        f'data-duration="{_seconds(timed_scene.duration_ms)}">'

        '<header data-slot="header">'
        '<div class="title-copy">'
        f"<p>{html.escape(scene.tag or scene.mode)}</p>"
        f"<h1>{html.escape(scene.title)}</h1>"
        f"<span>{html.escape(scene.objective)}</span>"
        "</div>"
        '<div class="scene-meta">'
        f"<b>{timed_scene.index + 1:02d}/{total_scenes:02d}</b>"
        f"<span>{html.escape(course)}</span>"
        "</div>"
        "</header>"

        '<div data-slot="stage" '
        f'data-visual="{html.escape(scene.visual_model.kind, quote=True)}" '
        f'data-mechanism="{html.escape(scene.mechanism, quote=True)}">'
        f'<div id="cartoon-canvas-{timed_scene.index}" class="visual-canvas">'
        f"{_stage_html(scene, timed_scene.index)}"
        "</div>"
        "</div>"

        '<aside data-slot="state-rail">'
        "<span>步骤</span>"
        f"<div data-step-track>{chips}</div>"
        "</aside>"
        f"{_teaching_panel_html(timed_scene)}"
        "</section>"
    )


def _audio_html(
    plan: CompositionPlan,
) -> str:
    result: list[str] = []

    for timed_scene in plan.scenes:
        for timed in timed_scene.steps:
            result.append(
                f'<audio id="audio-{timed.scene_id}-{timed.step.id}" '
                f'data-start="{_seconds(timed.start_ms)}" '
                f'data-duration="{_seconds(timed.audio_duration_ms)}" '
                'data-track-index="10" '
                f'src="{html.escape(timed.audio_src, quote=True)}">'
                "</audio>"
            )

    return "".join(
        result
    )


def _caption_html(
    plan: CompositionPlan,
) -> str:
    result: list[str] = []

    for timed_scene in plan.scenes:
        for step_index, timed in enumerate(timed_scene.steps):
            result.append(
                f'<div id="cartoon-caption-{timed_scene.index}-{step_index}" '
                'class="caption clip" '
                f'data-caption="{timed.scene_id}:{timed.step.id}" '
                f'data-start="{_seconds(timed.start_ms)}" '
                f'data-duration="{_seconds(timed.duration_ms)}" '
                'data-track-index="20">'
                f"<span>{html.escape(timed.step.narration)}</span>"
                "</div>"
            )

    return "".join(
        result
    )


def _timeline(
    plan: CompositionPlan,
) -> str:
    def element(element_id: str) -> str:
        return f"document.getElementById({_js(element_id)})"

    def scene_nodes(timed_scene) -> dict[str, int]:
        return {
            node.id: index
            for index, node in enumerate(stage_visual_model(timed_scene.scene).nodes)
        }

    def edge_indexes(timed_scene, source_id: str | None, destination_id: str | None) -> list[int]:
        if not source_id or not destination_id:
            return []
        return [
            index
            for index, edge in enumerate(stage_visual_model(timed_scene.scene).edges)
            if {edge.source_id, edge.target_id} == {source_id, destination_id}
        ]

    def action_refs(timed_scene, timed, timed_action) -> str:
        action = timed_action.action
        node_indexes = scene_nodes(timed_scene)
        target_ids = list(action.target_ids)
        source_id = action.source_id or (target_ids[0] if target_ids else None)
        destination_id = action.destination_id or (target_ids[1] if len(target_ids) > 1 else None)
        edge_ids: list[int] = []
        if action.kind == "traverse":
            for left, right in zip(target_ids, target_ids[1:]):
                edge_ids.extend(edge_indexes(timed_scene, left, right))
        else:
            edge_ids = edge_indexes(timed_scene, source_id, destination_id)
        token = "null"
        if not timed_action.synthetic and action.kind in {"transfer", "traverse"}:
            step_index = timed_scene.steps.index(timed)
            token = element(f"cartoon-token-{timed_scene.index}-{step_index}-{timed_action.action_index}")
        badge = "null"
        if not timed_action.synthetic:
            step_index = timed_scene.steps.index(timed)
            badge = element(f"cartoon-badge-{timed_scene.index}-{step_index}-{timed_action.action_index}")
        return "{" + ", ".join(
            [
                f"scene: {element(f'cartoon-scene-{timed_scene.index}')}",
                f"canvas: {element(f'cartoon-canvas-{timed_scene.index}')}",
                "allNodes: [" + ", ".join(
                    element(f"cartoon-node-{timed_scene.index}-{index}")
                    for index in node_indexes.values()
                ) + "]",
                "targets: [" + ", ".join(
                    element(f"cartoon-node-{timed_scene.index}-{node_indexes[node_id]}")
                    for node_id in target_ids
                    if node_id in node_indexes
                ) + "]",
                f"source: {element(f'cartoon-node-{timed_scene.index}-{node_indexes[source_id]}') if source_id in node_indexes else 'null'}",
                f"destination: {element(f'cartoon-node-{timed_scene.index}-{node_indexes[destination_id]}') if destination_id in node_indexes else 'null'}",
                "edges: [" + ", ".join(
                    element(f"cartoon-edge-{timed_scene.index}-{index}")
                    for index in edge_ids
                ) + "]",
                f"token: {token}",
                f"badge: {badge}",
            ]
        ) + "}"

    def patch_refs(timed_scene, timed_patch) -> str:
        patch = timed_patch.patch
        nodes = scene_nodes(timed_scene)
        target_id = patch.target_id or (patch.node.id if patch.node is not None else None)
        edges = []
        if patch.edge is not None:
            edges = edge_indexes(timed_scene, patch.edge.source_id, patch.edge.target_id)
        return "{" + ", ".join(
            [
                f"scene: {element(f'cartoon-scene-{timed_scene.index}')}",
                f"target: {element(f'cartoon-node-{timed_scene.index}-{nodes[target_id]}') if target_id in nodes else 'null'}",
                "edges: [" + ", ".join(
                    element(f"cartoon-edge-{timed_scene.index}-{index}")
                    for index in edges
                ) + "]",
            ]
        ) + "}"

    lines = [
        _RICH_RUNTIME_JS,
        "Runtime.prepare();",
        "RichRuntime.prepare();",
        (
            "Runtime.progress("
            "tl, "
            f"{element('cartoon-progress')}, "
            "0, "
            f"{_seconds(plan.total_duration_ms)}"
            ");"
        ),
    ]

    for timed_scene in plan.scenes:
        scene_ref = element(f"cartoon-scene-{timed_scene.index}")

        lines.append(
            "Runtime.sceneIn("
            "tl, "
            f"{scene_ref}, "
            f"{_seconds(timed_scene.start_ms)}, "
            ".32"
            ");"
        )

        for index, timed in enumerate(
            timed_scene.steps
        ):
            start = _seconds(
                timed.start_ms
            )

            lines.append(
                "Runtime.step("
                "tl, "
                f"{scene_ref}, "
                f"{index}, "
                f"{start}"
                ");"
            )

            lines.append(
                "Runtime.caption("
                "tl, "
                f"{element(f'cartoon-caption-{timed_scene.index}-{index}')}, "
                f"{start}, "
                f"{_seconds(timed.duration_ms)}"
                ");"
            )

            for timed_action in timed.actions:
                action = (
                    timed_action.action
                )

                payload = {
                    "kind": action.kind,
                    "mechanism": (
                        timed_scene.scene.mechanism
                    ),
                    "label": _action_runtime_label(
                        timed_scene.scene,
                        action,
                    ),
                    "targets": (
                        action.target_ids
                    ),
                    "source": (
                        action.source_id
                    ),
                    "destination": (
                        action.destination_id
                    ),
                    "duration": (
                        timed_action.duration_ms
                        / 1000
                    ),
                    "intensity": (
                        action.intensity
                    ),
                    "note": action.note,
                    "synthetic": (
                        timed_action.synthetic
                    ),
                }

                lines.append(
                    "RichRuntime.action("
                    "tl, "
                    f"{action_refs(timed_scene, timed, timed_action)}, "
                    f"{_js(payload)}, "
                    f"{_seconds(timed_action.start_ms)}"
                    ");"
                )

            for timed_patch in timed.patches:
                lines.append(
                    "Runtime.patch("
                    "tl, "
                    f"{patch_refs(timed_scene, timed_patch)}, "
                    f"{_js(timed_patch.patch.model_dump(mode='json', exclude_none=True))}, "
                    f"{_seconds(timed_patch.start_ms)}"
                    ");"
                )

        scene_out = (
            timed_scene.start_ms
            + timed_scene.duration_ms
            - 260
        )

        lines.append(
            "Runtime.sceneOut("
            "tl, "
            f"{scene_ref}, "
            f"{_seconds(scene_out)}, "
            ".24"
            ");"
        )

    return "\n    ".join(
        lines
    )


class CartoonCompiler:
    def __init__(
        self,
        *,
        catalog: CartoonTemplateCatalog
        | None = None,
    ) -> None:
        self.catalog = (
            catalog
            or CartoonTemplateCatalog()
        )

    def compile(
        self,
        lesson: TeachingLesson,
        plan: CompositionPlan,
        template: CartoonTemplate,
    ) -> str:
        self.catalog.validate_lesson(
            template,
            lesson,
        )

        self._validate_plan_alignment(
            lesson,
            plan,
        )

        content = (
            template.composition.read_text(
                encoding="utf-8"
            )
        )

        replacements = {
            "{{ composition_id }}": (
                COMPOSITION_ID
            ),
            "{{ title }}": html.escape(
                lesson.title,
                quote=True,
            ),
            "{{ duration }}": _seconds(
                plan.total_duration_ms
            ),
            "{{ scenes_html }}": "".join(
                _scene_html(
                    scene,
                    len(plan.scenes),
                    lesson.course,
                )
                for scene
                in plan.scenes
            ),
            "{{ audio_html }}": (
                _audio_html(
                    plan
                )
            ),
            "{{ captions_html }}": (
                _caption_html(
                    plan
                )
            ),
            "{{ timeline_js }}": (
                _timeline(
                    plan
                )
            ),
        }

        for marker, value in replacements.items():
            content = content.replace(
                marker,
                value,
            )

        if re.search(
            r"\{\{\s*[a-z_]+\s*\}\}",
            content,
        ):
            raise ValueError(
                "template contains "
                "unresolved markers"
            )

        return content

    @staticmethod
    def _validate_plan_alignment(
        lesson: TeachingLesson,
        plan: CompositionPlan,
    ) -> None:
        if (
            len(lesson.scenes)
            != len(plan.scenes)
        ):
            raise ValueError(
                "lesson and composition "
                "scene counts differ"
            )

        if plan.total_duration_ms <= 0:
            raise ValueError(
                "composition duration "
                "must be positive"
            )

        previous_end = 0

        for index, (
            lesson_scene,
            timed_scene,
        ) in enumerate(
            zip(
                lesson.scenes,
                plan.scenes,
                strict=True,
            )
        ):
            if (
                timed_scene.index
                != index
            ):
                raise ValueError(
                    "composition scene index "
                    f"mismatch at {index}"
                )

            if (
                timed_scene.scene.id
                != lesson_scene.id
            ):
                raise ValueError(
                    "composition scene id mismatch: "
                    f"{timed_scene.scene.id} != "
                    f"{lesson_scene.id}"
                )

            if (
                timed_scene.start_ms
                < previous_end
            ):
                raise ValueError(
                    f"composition scene "
                    f"{lesson_scene.id} overlaps "
                    "the previous scene"
                )

            previous_end = (
                timed_scene.start_ms
                + timed_scene.duration_ms
            )

        if (
            previous_end
            > plan.total_duration_ms
        ):
            raise ValueError(
                "composition scenes exceed "
                "total duration"
            )

    def write(
        self,
        lesson: TeachingLesson,
        plan: CompositionPlan,
        output_dir: Path,
        template_id: str,
    ) -> tuple[
        Path,
        CartoonTemplate,
    ]:
        template = self.catalog.get(
            template_id
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        html_path = (
            output_dir
            / "index.html"
        )

        html_path.write_text(
            self.compile(
                lesson,
                plan,
                template,
            ),
            encoding="utf-8",
        )

        for source in (
            template.tokens,
            template.layout,
            template.motion,
        ):
            shutil.copy2(
                source,
                output_dir
                / source.name,
            )

        self._copy_vendor_assets(
            output_dir
        )

        return (
            html_path,
            template,
        )

    @staticmethod
    def _copy_vendor_assets(
        output_dir: Path,
    ) -> None:
        project_root = (
            Path(__file__)
            .resolve()
            .parents[4]
        )

        gsap_source = (
            project_root
            / "node_modules"
            / "gsap"
            / "dist"
            / "gsap.min.js"
        )

        if not gsap_source.is_file():
            return

        vendor_dir = (
            output_dir
            / "assets"
            / "vendor"
        )

        vendor_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            gsap_source,
            vendor_dir
            / "gsap.min.js",
        )
