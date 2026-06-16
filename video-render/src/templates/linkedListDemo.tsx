import { Rect, Txt, Line } from '@motion-canvas/2d';
import { createRef, all } from '@motion-canvas/core';
import { FrameLayout } from '../components/FrameLayout';
import { NodeBox } from '../components/NodeBox';
import { Arrow } from '../components/Arrow';
import { theme } from '../styles/theme';
import { TeachingVideoScene } from '../schema/videoPlan';
import { getTimingConfig } from '../renderer/sceneTiming';

interface ListNode {
  id: string;
  val: string | number;
}

interface ListLink {
  from: string;
  to: string;
  label?: string;
  active?: boolean;
}

interface ListOperationStep {
  explanation: string;
  highlightNodes?: string[];
  nodes: ListNode[];
  links: ListLink[];
}

export function* renderLinkedListDemo(
  view: any,
  scene: TeachingVideoScene,
  mode: any
) {
  const { title = 'Linked List Demo', operations = [] } = scene.visual_data as {
    title: string;
    operations: ListOperationStep[];
  };
  const timing = getTimingConfig(mode);

  const explanationCardRef = createRef<Rect>();
  const explanationTextRef = createRef<Txt>();
  const canvasRef = createRef<Rect>();

  view.add(
    <FrameLayout
      title={scene.title}
      topic="Linked List Manipulation"
      courseTag="Data Structures"
      subtitle={scene.subtitle}
    >
      <Rect direction="column" gap={30} width="100%" height="100%" justifyContent="center" layout>
        {/* Top Explanation Banner */}
        <Rect
          ref={explanationCardRef}
          fill={theme.colors.cardBg}
          border={2}
          borderColor={theme.colors.border}
          radius={theme.radius.lg}
          padding={20}
          width="100%"
          shadow={theme.shadows.sm}
          layout
        >
          <Txt
            ref={explanationTextRef}
            text="Initializing Linked List..."
            fontFamily={theme.fonts.sans}
            fontSize={18}
            fill={theme.colors.text}
          />
        </Rect>

        {/* Bottom Diagram Canvas */}
        <Rect
          ref={canvasRef}
          width="100%"
          grow={1}
          layout={false} // Absolute child rendering
        />
      </Rect>
    </FrameLayout>
  );

  const activeOps = operations.slice(0, timing.maxItems);

  for (let idx = 0; idx < activeOps.length; idx++) {
    const op = activeOps[idx];

    // Update explanation text
    explanationTextRef().text(op.explanation);

    // Calculate node coordinates horizontally
    const nodePositions = new Map<string, { x: number; y: number }>();
    const boxSize = 80;
    
    op.nodes.forEach((node, nIdx) => {
      // Linear placement
      const x = (nIdx - (op.nodes.length - 1) / 2) * 240;
      const y = 0;
      nodePositions.set(node.id, { x, y });
    });

    // Redraw canvas content
    canvasRef().removeChildren();

    // 1. Draw Links
    op.links.forEach((link, lIdx) => {
      const fromPos = nodePositions.get(link.from);
      const toPos = nodePositions.get(link.to);
      if (!fromPos || !toPos) return;

      // Draw arrow with boundaries
      const dx = toPos.x - fromPos.x;
      const dy = toPos.y - fromPos.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const ux = dx / dist;
      const uy = dy / dist;

      // Adjust offset past boundary
      const offset = boxSize / 2 + 10;
      const startPt = [fromPos.x + ux * offset, fromPos.y + uy * offset];
      const endPt = [toPos.x - ux * offset, toPos.y - uy * offset];

      canvasRef().add(
        <Arrow
          key={`link-${lIdx}`}
          points={[startPt, endPt]}
          active={link.active}
        />
      );

      // Label (like pointers or next)
      if (link.label) {
        canvasRef().add(
          <Txt
            text={link.label}
            fontFamily={theme.fonts.mono}
            fontSize={12}
            fill={link.active ? theme.colors.primary : theme.colors.textWeak}
            x={(startPt[0] + endPt[0]) / 2}
            y={(startPt[1] + endPt[1]) / 2 - 20}
          />
        );
      }
    });

    // 2. Draw Nodes
    op.nodes.forEach((node) => {
      const pos = nodePositions.get(node.id)!;
      const isHighlighted = op.highlightNodes?.includes(node.id) || false;

      canvasRef().add(
        <NodeBox
          key={`node-${node.id}`}
          label={String(node.val)}
          active={isHighlighted}
          shape="rect"
          size={boxSize}
          x={pos.x}
          y={pos.y}
        />
      );
    });

    yield* timing.stepDelay * 1.5;
  }

  const animTime = activeOps.length * timing.stepDelay * 1.5;
  yield* Math.max(0.5, scene.duration_seconds - animTime);
}
