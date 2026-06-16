import { Rect, Txt } from '@motion-canvas/2d';
import { createRef, all } from '@motion-canvas/core';
import { FrameLayout } from '../components/FrameLayout';
import { QueueBox } from '../components/QueueBox';
import { Badge } from '../components/Badge';
import { theme } from '../styles/theme';
import { TeachingVideoScene } from '../schema/videoPlan';
import { getTimingConfig } from '../renderer/sceneTiming';

interface OperationStep {
  type: 'push' | 'pop' | 'enqueue' | 'dequeue' | 'insert' | 'delete';
  element?: string | number;
  explanation: string;
  state: {
    items: (string | number)[];
    pointers?: Record<string, number>;
  };
}

export function* renderLinearStructureDemo(
  view: any,
  scene: TeachingVideoScene,
  mode: any
) {
  const { structure = 'queue', operations = [] } = scene.visual_data as {
    structure: 'queue' | 'stack' | 'array';
    operations: OperationStep[];
  };
  const timing = getTimingConfig(mode);

  const leftPanelRef = createRef<Rect>();
  const rightPanelRef = createRef<Rect>();
  
  const stepTextRef = createRef<Txt>();
  const opTypeRef = createRef<Txt>();
  const elementRef = createRef<Txt>();

  view.add(
    <FrameLayout
      title={scene.title}
      topic={`${structure.toUpperCase()} Operations Demo`}
      courseTag="Data Structures"
      subtitle={scene.subtitle}
    >
      <Rect direction="row" gap={40} width="100%" height="100%" alignItems="center" layout>
        {/* Left Side: Step narration / Command execution */}
        <Rect
          ref={leftPanelRef}
          width="40%"
          fill={theme.colors.cardBg}
          border={2}
          borderColor={theme.colors.border}
          radius={theme.radius.lg}
          padding={32}
          direction="column"
          gap={20}
          shadow={theme.shadows.md}
          layout
        >
          <Txt
            text="⚙ Operation Command"
            fontFamily={theme.fonts.sans}
            fontSize={18}
            fontWeight={700}
            fill={theme.colors.primary}
          />
          
          <Rect direction="row" gap={12} alignItems="center" layout>
            <Badge ref={opTypeRef} text="INIT" type="primary" />
            <Txt
              ref={elementRef}
              text=""
              fontFamily={theme.fonts.mono}
              fontSize={20}
              fontWeight={700}
              fill={theme.colors.text}
            />
          </Rect>

          <Rect height={1} fill={theme.colors.border} />

          <Txt
            ref={stepTextRef}
            text="Initializing linear structure..."
            fontFamily={theme.fonts.sans}
            fontSize={18}
            lineHeight={28}
            fill={theme.colors.text}
          />
        </Rect>

        {/* Right Side: Render actual structural container */}
        <Rect
          ref={rightPanelRef}
          width="55%"
          justifyContent="center"
          alignItems="center"
          layout
        />
      </Rect>
    </FrameLayout>
  );

  const activeOps = operations.slice(0, timing.maxItems);

  for (let idx = 0; idx < activeOps.length; idx++) {
    const op = activeOps[idx];
    
    // Update explanation panel
    opTypeRef().text(op.type.toUpperCase());
    elementRef().text(op.element !== undefined ? `Value: ${op.element}` : '');
    stepTextRef().text(op.explanation);

    // Calculate highlighted indices (e.g. index of newly added element)
    let highlightIndices: number[] = [];
    if (op.state.items.length > 0) {
      if (op.type === 'push' || op.type === 'enqueue' || op.type === 'insert') {
        highlightIndices = [op.state.items.length - 1];
      }
    }

    // Determine layout direction for stack vs queue/array
    // Stacks look better stacked vertically bottom-to-top
    const isStack = structure === 'stack';
    const queueProps: any = {};
    if (isStack) {
      queueProps.direction = 'column-reverse';
    }

    // Render structure
    rightPanelRef().removeChildren();
    rightPanelRef().add(
      <QueueBox
        items={op.state.items}
        pointers={op.state.pointers}
        highlightIndices={highlightIndices}
        maxSize={6}
        {...queueProps}
      />
    );

    yield* timing.stepDelay * 1.2;
  }

  const animTime = activeOps.length * timing.stepDelay * 1.2;
  yield* Math.max(0.5, scene.duration_seconds - animTime);
}
