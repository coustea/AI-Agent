import { Rect, Txt, Line } from '@motion-canvas/2d';
import { createRef, all } from '@motion-canvas/core';
import { FrameLayout } from '../components/FrameLayout';
import { NodeBox } from '../components/NodeBox';
import { Arrow } from '../components/Arrow';
import { theme } from '../styles/theme';
import { TeachingVideoScene } from '../schema/videoPlan';
import { getTimingConfig } from '../renderer/sceneTiming';

interface FlowNode {
  id: string;
  label: string;
  x?: number;
  y?: number;
  value?: string;
}

interface FlowEdge {
  from: string;
  to: string;
  label?: string;
}

export function* renderProcessFlow(
  view: any,
  scene: TeachingVideoScene,
  mode: any
) {
  const { nodes = [], edges = [], steps = [] } = scene.visual_data as {
    nodes: FlowNode[];
    edges: FlowEdge[];
    steps: string[];
  };
  const timing = getTimingConfig(mode);

  const nodeRefs = nodes.map(() => createRef<Rect>());
  const arrowRefs = edges.map(() => createRef<Line>());

  // Calculate layout coordinates
  const nodePositions = new Map<string, { x: number; y: number }>();
  const boxSize = 100;

  nodes.forEach((n, idx) => {
    let px = n.x !== undefined ? n.x : (idx - (nodes.length - 1) / 2) * 260;
    let py = n.y !== undefined ? n.y : 0;
    
    // Scale standard normalized coordinates if needed
    if (Math.abs(px) <= 2 && Math.abs(py) <= 2) {
      px *= 400;
      py *= 300;
    }
    nodePositions.set(n.id, { x: px, y: py });
  });

  view.add(
    <FrameLayout
      title={scene.title}
      topic="Process flow / Mechanism"
      courseTag="Computer Science"
      subtitle={scene.subtitle}
    >
      {/* Container for absolute rendering inside Middle Area */}
      <Rect width="100%" height="100%" layout={false}>
        {/* Draw Edges/Arrows first */}
        {edges.map((edge, idx) => {
          const fromPos = nodePositions.get(edge.from);
          const toPos = nodePositions.get(edge.to);
          if (!fromPos || !toPos) return null;

          // Calculate boundary coordinates
          const dx = toPos.x - fromPos.x;
          const dy = toPos.y - fromPos.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const ux = dx / dist;
          const uy = dy / dist;

          const offset = boxSize / 2 + 15; // Offset past node radius
          const startPt = [fromPos.x + ux * offset, fromPos.y + uy * offset];
          const endPt = [toPos.x - ux * offset, toPos.y - uy * offset];

          return (
            <Arrow
              key={`edge-${idx}`}
              ref={arrowRefs[idx]}
              points={[startPt, endPt]}
              opacity={0}
            />
          );
        })}

        {/* Draw Nodes */}
        {nodes.map((node, idx) => {
          const pos = nodePositions.get(node.id)!;
          return (
            <NodeBox
              key={`node-${node.id}`}
              ref={nodeRefs[idx]}
              label={node.label}
              value={node.value}
              size={boxSize}
              x={pos.x}
              y={pos.y}
              opacity={0}
              scale={0.5}
            />
          );
        })}
      </Rect>
    </FrameLayout>
  );

  // 1. Fade in all nodes
  const nodeFadeInAnims = nodes.map((_, idx) =>
    all(nodeRefs[idx]().opacity(1, timing.transitionDuration), nodeRefs[idx]().scale(1, timing.transitionDuration))
  );
  yield* all(...nodeFadeInAnims);

  // 2. Fade in all arrows
  const arrowFadeInAnims = edges.map((_, idx) =>
    arrowRefs[idx]().opacity(1, timing.transitionDuration * 0.8)
  );
  yield* all(...arrowFadeInAnims);

  yield* timing.stepDelay * 0.5;

  // 3. Sequential steps highlighting
  let lastActiveIdx = -1;
  const activeSteps = steps.slice(0, timing.maxItems);

  for (const step of activeSteps) {
    const nodeIdx = nodes.findIndex((n) => n.id === step);
    if (nodeIdx === -1) continue;

    const anims: any[] = [];
    // Reset last active node
    if (lastActiveIdx !== -1) {
      anims.push(nodeRefs[lastActiveIdx]().borderColor(theme.colors.border, timing.transitionDuration * 0.5));
      anims.push(nodeRefs[lastActiveIdx]().fill(theme.colors.cardBg, timing.transitionDuration * 0.5));
      anims.push(nodeRefs[lastActiveIdx]().scale(1.0, timing.transitionDuration * 0.5));
    }

    // Highlight current active node
    anims.push(nodeRefs[nodeIdx]().borderColor(theme.colors.primary, timing.transitionDuration * 0.5));
    anims.push(nodeRefs[nodeIdx]().fill(theme.colors.primary + '15', timing.transitionDuration * 0.5));
    anims.push(nodeRefs[nodeIdx]().scale(1.15, timing.transitionDuration * 0.5));

    lastActiveIdx = nodeIdx;
    yield* all(...anims);
    yield* timing.stepDelay;
  }

  // Sleep remainder of duration
  const activeDuration = timing.transitionDuration * 2.5 + activeSteps.length * (timing.transitionDuration * 0.5 + timing.stepDelay);
  yield* Math.max(0.5, scene.duration_seconds - activeDuration);
}
