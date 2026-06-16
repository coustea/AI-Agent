import { Rect, Txt } from '@motion-canvas/2d';
import { createRef, all } from '@motion-canvas/core';
import { FrameLayout } from '../components/FrameLayout';
import { NodeBox } from '../components/NodeBox';
import { Arrow } from '../components/Arrow';
import { theme } from '../styles/theme';
import { TeachingVideoScene } from '../schema/videoPlan';
import { getTimingConfig } from '../renderer/sceneTiming';

interface StateTransition {
  from: string;
  to: string;
  label?: string;
}

interface TransitionStep {
  state: string;
  explanation: string;
}

export function* renderProcessStateTransition(
  view: any,
  scene: TeachingVideoScene,
  mode: any
) {
  const {
    states = [],
    transitions = [],
    steps = [],
  } = scene.visual_data as {
    states: string[];
    transitions: StateTransition[];
    steps: TransitionStep[];
  };
  const timing = getTimingConfig(mode);

  const canvasRef = createRef<Rect>();
  const explanationTextRef = createRef<Txt>();

  // Standard 5-State model positioning
  const standardStateCoords: Record<string, { x: number; y: number }> = {
    new: { x: -380, y: 100 },
    ready: { x: -140, y: 180 },
    running: { x: 140, y: 180 },
    waiting: { x: 0, y: -60 },
    blocked: { x: 0, y: -60 },
    terminated: { x: 380, y: 100 },
    exit: { x: 380, y: 100 },
  };

  const nodePositions = new Map<string, { x: number; y: number }>();
  const boxWidth = 120;
  const boxHeight = 70;

  states.forEach((stateName, idx) => {
    const key = stateName.toLowerCase();
    if (standardStateCoords[key]) {
      nodePositions.set(stateName, standardStateCoords[key]);
    } else {
      // Circle fallback
      const x = Math.cos((idx / states.length) * Math.PI * 2) * 280;
      const y = Math.sin((idx / states.length) * Math.PI * 2) * 180;
      nodePositions.set(stateName, { x, y });
    }
  });

  view.add(
    <FrameLayout
      title={scene.title}
      topic="Operating Systems - Process States"
      courseTag="Process Management"
      subtitle={scene.subtitle}
    >
      <Rect direction="column" gap={30} width="100%" height="100%" justifyContent="center" layout>
        {/* Top: Narration */}
        <Rect
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
            text="Initializing State Diagram..."
            fontFamily={theme.fonts.sans}
            fontSize={18}
            fill={theme.colors.text}
          />
        </Rect>

        {/* State Transition Canvas */}
        <Rect
          ref={canvasRef}
          width="100%"
          grow={1}
          layout={false} // Absolute diagrams
        />
      </Rect>
    </FrameLayout>
  );

  const activeSteps = steps.slice(0, timing.maxItems);

  for (let idx = 0; idx < activeSteps.length; idx++) {
    const step = activeSteps[idx];

    // Redraw Canvas content
    canvasRef().removeChildren();

    // 1. Draw Transitions
    transitions.forEach((trans, tIdx) => {
      const fromPos = nodePositions.get(trans.from);
      const toPos = nodePositions.get(trans.to);
      if (!fromPos || !toPos) return;

      const dx = toPos.x - fromPos.x;
      const dy = toPos.y - fromPos.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const ux = dx / dist;
      const uy = dy / dist;

      // Box radius offset along direction
      const xOffset = ux * (boxWidth / 2 + 10);
      const yOffset = uy * (boxHeight / 2 + 10);
      const startPt = [fromPos.x + xOffset, fromPos.y + yOffset];
      const endPt = [toPos.x - xOffset, toPos.y - yOffset];

      const transActive = trans.from === step.state || trans.to === step.state;

      canvasRef().add(
        <Arrow
          key={`trans-${tIdx}`}
          points={[startPt, endPt]}
          active={transActive}
        />
      );

      // Transition labels
      if (trans.label) {
        canvasRef().add(
          <Txt
            text={trans.label}
            fontFamily={theme.fonts.sans}
            fontSize={12}
            fill={transActive ? theme.colors.primary : theme.colors.textWeak}
            fontWeight={transActive ? 700 : 400}
            x={(startPt[0] + endPt[0]) / 2}
            y={(startPt[1] + endPt[1]) / 2 - 14}
            textAlign="center"
          />
        );
      }
    });

    // 2. Draw States
    states.forEach((stateName) => {
      const pos = nodePositions.get(stateName)!;
      const isActive = stateName.toLowerCase() === step.state.toLowerCase();

      canvasRef().add(
        <NodeBox
          key={`state-${stateName}`}
          label={stateName}
          active={isActive}
          shape="rect"
          size={100}
          width={boxWidth}
          height={boxHeight}
          x={pos.x}
          y={pos.y}
        />
      );
    });

    // 3. Update Text
    explanationTextRef().text(step.explanation);

    yield* timing.stepDelay * 1.5;
  }

  const animTime = activeSteps.length * timing.stepDelay * 1.5;
  yield* Math.max(0.5, scene.duration_seconds - animTime);
}
