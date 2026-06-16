import { Rect, Txt, Line } from '@motion-canvas/2d';
import { createRef, all } from '@motion-canvas/core';
import { FrameLayout } from '../components/FrameLayout';
import { NodeBox } from '../components/NodeBox';
import { Arrow } from '../components/Arrow';
import { QueueBox } from '../components/QueueBox';
import { Badge } from '../components/Badge';
import { theme } from '../styles/theme';
import { TeachingVideoScene } from '../schema/videoPlan';
import { getTimingConfig } from '../renderer/sceneTiming';

interface TraversalNode {
  id: string;
  label: string;
  x?: number;
  y?: number;
}

interface TraversalEdge {
  from: string;
  to: string;
}

interface TraversalStep {
  node: string;
  explanation: string;
  queue?: (string | number)[];
  stack?: (string | number)[];
  visited?: string[];
}

export function* renderTreeGraphTraversal(
  view: any,
  scene: TeachingVideoScene,
  mode: any
) {
  const {
    structure_type = 'tree',
    nodes = [],
    edges = [],
    steps = [],
  } = scene.visual_data as {
    structure_type: 'tree' | 'graph';
    nodes: TraversalNode[];
    edges: TraversalEdge[];
    steps: TraversalStep[];
  };
  const timing = getTimingConfig(mode);

  const leftCardRef = createRef<Rect>();
  const rightColumnRef = createRef<Rect>();
  const explanationTextRef = createRef<Txt>();
  const dsContainerRef = createRef<Rect>();
  const visitedContainerRef = createRef<Rect>();

  // Determine tree layout levels or graph coordinates
  const nodePositions = new Map<string, { x: number; y: number }>();
  const boxSize = 70;

  if (structure_type === 'tree') {
    // Hierarchical layout
    // Level 0: root, Level 1: left/right child, Level 2: grandchildren, etc.
    nodes.forEach((n, idx) => {
      // Basic BFS layout coordinates
      let x = 0;
      let y = 150; // top-ish

      if (idx === 0) {
        // Root
        x = 0;
        y = 150;
      } else if (idx === 1) {
        x = -160;
        y = 30;
      } else if (idx === 2) {
        x = 160;
        y = 30;
      } else if (idx >= 3 && idx <= 6) {
        // Grandchildren
        const mult = idx === 3 ? -240 : idx === 4 ? -80 : idx === 5 ? 80 : 240;
        x = mult;
        y = -90;
      } else {
        // Fallback row layout
        x = (idx - 5) * 100;
        y = -210;
      }

      // Override if custom coordinates provided
      if (n.x !== undefined && n.y !== undefined) {
        x = n.x * 250;
        y = n.y * 200;
      }

      nodePositions.set(n.id, { x, y });
    });
  } else {
    // Graph circular/freeform layout
    nodes.forEach((n, idx) => {
      let x = n.x !== undefined ? n.x : Math.cos((idx / nodes.length) * Math.PI * 2) * 200;
      let y = n.y !== undefined ? n.y : Math.sin((idx / nodes.length) * Math.PI * 2) * 160;
      
      if (Math.abs(x) <= 2 && Math.abs(y) <= 2) {
        x *= 200;
        y *= 160;
      }

      nodePositions.set(n.id, { x, y });
    });
  }

  view.add(
    <FrameLayout
      title={scene.title}
      topic={`${structure_type.toUpperCase()} Traversal (BFS/DFS)`}
      courseTag="Algorithms"
      subtitle={scene.subtitle}
    >
      <Rect direction="row" gap={30} width="100%" height="100%" alignItems="center" layout>
        {/* Left Side: Graph/Tree Canvas */}
        <Rect
          ref={leftCardRef}
          width="55%"
          height={760}
          fill={theme.colors.cardBg}
          border={2}
          borderColor={theme.colors.border}
          radius={theme.radius.lg}
          shadow={theme.shadows.md}
          layout={false} // Absolute diagrams inside
        />

        {/* Right Side: Execution trace & Data structures */}
        <Rect ref={rightColumnRef} width="42%" direction="column" gap={20} layout>
          {/* Action explanation */}
          <Rect
            fill={theme.colors.cardBg}
            border={1}
            borderColor={theme.colors.border}
            radius={theme.radius.md}
            padding={24}
            direction="column"
            gap={12}
            layout
          >
            <Txt
              text="⚡ Trace explanation"
              fontFamily={theme.fonts.sans}
              fontSize={15}
              fontWeight={700}
              fill={theme.colors.primary}
            />
            <Txt
              ref={explanationTextRef}
              text="Starting traversal..."
              fontFamily={theme.fonts.sans}
              fontSize={17}
              lineHeight={26}
              fill={theme.colors.text}
            />
          </Rect>

          {/* Queue / Stack state tracker */}
          <Rect
            fill={theme.colors.codeBg}
            border={1}
            borderColor={theme.colors.border}
            radius={theme.radius.md}
            padding={20}
            direction="column"
            gap={12}
            layout
          >
            <Txt
              text={`📊 Memory Store (${steps[0]?.stack ? 'Stack - LIFO' : 'Queue - FIFO'})`}
              fontFamily={theme.fonts.sans}
              fontSize={14}
              fontWeight={700}
              fill={theme.colors.textWeak}
            />
            <Rect ref={dsContainerRef} direction="row" minHeight={80} alignItems="center" layout />
          </Rect>

          {/* Visited Output History */}
          <Rect
            fill={theme.colors.cardBg}
            border={1}
            borderColor={theme.colors.border}
            radius={theme.radius.md}
            padding={20}
            direction="column"
            gap={12}
            layout
          >
            <Txt
              text="👣 Traversal Visited Order"
              fontFamily={theme.fonts.sans}
              fontSize={14}
              fontWeight={700}
              fill={theme.colors.textWeak}
            />
            <Rect
              ref={visitedContainerRef}
              direction="row"
              gap={8}
              minHeight={50}
              alignItems="center"
              textWrap
              layout
            />
          </Rect>
        </Rect>
      </Rect>
    </FrameLayout>
  );

  const activeSteps = steps.slice(0, timing.maxItems);

  for (let idx = 0; idx < activeSteps.length; idx++) {
    const step = activeSteps[idx];

    // 1. Redraw Diagram on Left
    leftCardRef().removeChildren();

    // Draw edges first
    edges.forEach((edge, eIdx) => {
      const fromPos = nodePositions.get(edge.from);
      const toPos = nodePositions.get(edge.to);
      if (!fromPos || !toPos) return;

      const dx = toPos.x - fromPos.x;
      const dy = toPos.y - fromPos.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const ux = dx / dist;
      const uy = dy / dist;

      // Tree edges have no arrowheads, graph edges might have them
      const isTree = structure_type === 'tree';
      const offset = boxSize / 2 + 5;
      const startPt = [fromPos.x + ux * offset, fromPos.y + uy * offset];
      const endPt = [toPos.x - ux * offset, toPos.y - uy * offset];

      // Highlight edge if both nodes are visited
      const edgeVisited =
        step.visited?.includes(edge.from) && step.visited?.includes(edge.to);

      leftCardRef().add(
        <Arrow
          key={`edge-${eIdx}`}
          points={[startPt, endPt]}
          endArrow={!isTree}
          active={edgeVisited}
        />
      );
    });

    // Draw Nodes
    nodes.forEach((node) => {
      const pos = nodePositions.get(node.id)!;
      const isCurrent = node.id === step.node;
      const isVisited = step.visited?.includes(node.id) || false;

      // Highlights
      let activeColor = undefined;
      if (isCurrent) {
        activeColor = theme.colors.accent;
      } else if (isVisited) {
        activeColor = theme.colors.primary;
      }

      leftCardRef().add(
        <NodeBox
          key={`node-${node.id}`}
          label={node.label}
          active={isCurrent || isVisited}
          color={activeColor}
          size={boxSize}
          x={pos.x}
          y={pos.y}
        />
      );
    });

    // 2. Update Explanation
    explanationTextRef().text(op.explanation);

    // 3. Update Queue/Stack
    dsContainerRef().removeChildren();
    const items = step.queue || step.stack || [];
    if (items.length > 0) {
      dsContainerRef().add(
        <QueueBox items={items} boxSize={50} />
      );
    } else {
      dsContainerRef().add(
        <Txt
          text="Store is empty."
          fontFamily={theme.fonts.sans}
          fontSize={14}
          fill={theme.colors.textWeak}
        />
      );
    }

    // 4. Update Visited History
    visitedContainerRef().removeChildren();
    if (step.visited && step.visited.length > 0) {
      step.visited.forEach((nodeId) => {
        const nodeLabel = nodes.find((n) => n.id === nodeId)?.label || nodeId;
        visitedContainerRef().add(<Badge text={nodeLabel} type="success" />);
      });
    } else {
      visitedContainerRef().add(
        <Txt
          text="No nodes visited yet."
          fontFamily={theme.fonts.sans}
          fontSize={14}
          fill={theme.colors.textWeak}
        />
      );
    }

    yield* timing.stepDelay * 1.5;
  }

  const animTime = activeSteps.length * timing.stepDelay * 1.5;
  yield* Math.max(0.5, scene.duration_seconds - animTime);
}
