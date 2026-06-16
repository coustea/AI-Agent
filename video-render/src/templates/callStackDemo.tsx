import { Rect, Txt } from '@motion-canvas/2d';
import { createRef, all } from '@motion-canvas/core';
import { FrameLayout } from '../components/FrameLayout';
import { Badge } from '../components/Badge';
import { theme } from '../styles/theme';
import { TeachingVideoScene } from '../schema/videoPlan';
import { getTimingConfig } from '../renderer/sceneTiming';

interface StackFrame {
  name: string;
  args?: Record<string, any>;
}

interface StackOperationStep {
  explanation: string;
  op_type?: 'push' | 'pop' | 'init';
  frames: StackFrame[];
}

export function* renderCallStackDemo(
  view: any,
  scene: TeachingVideoScene,
  mode: any
) {
  const { title = 'Call Stack Demo', stack_frames = [] } = scene.visual_data as {
    title: string;
    stack_frames: StackOperationStep[];
  };
  const timing = getTimingConfig(mode);

  const leftCardRef = createRef<Rect>();
  const rightCardRef = createRef<Rect>();
  const explanationTextRef = createRef<Txt>();
  const opBadgeRef = createRef<Txt>();
  const stackContainerRef = createRef<Rect>();

  view.add(
    <FrameLayout
      title={scene.title}
      topic="Memory Management - Call Stack"
      courseTag="Execution Context"
      subtitle={scene.subtitle}
    >
      <Rect direction="row" gap={40} width="100%" height="100%" alignItems="center" layout>
        {/* Left Explanation Column */}
        <Rect
          ref={leftCardRef}
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
            text="💻 Execution State"
            fontFamily={theme.fonts.sans}
            fontSize={18}
            fontWeight={700}
            fill={theme.colors.primary}
          />
          
          <Rect direction="row" gap={12} alignItems="center" layout>
            <Badge ref={opBadgeRef} text="INIT" type="accent" />
          </Rect>

          <Rect height={1} fill={theme.colors.border} />

          <Txt
            ref={explanationTextRef}
            text="Initializing runtime call stack..."
            fontFamily={theme.fonts.sans}
            fontSize={18}
            lineHeight={28}
            fill={theme.colors.text}
          />
        </Rect>

        {/* Right Stack Bucket Column */}
        <Rect
          ref={rightCardRef}
          width="55%"
          justifyContent="center"
          alignItems="center"
          layout
        >
          {/* Stack bucket frame (bottom border, left/right border, open top) */}
          <Rect
            width={340}
            height={500}
            border={{ left: 4, right: 4, bottom: 4 }}
            borderColor={theme.colors.textWeak}
            radius={{ bottomLeft: theme.radius.md, bottomRight: theme.radius.md }}
            padding={12}
            direction="column-reverse" // Stack elements bottom-up
            gap={10}
            alignItems="stretch"
            justifyContent="flex-start"
            layout
            ref={stackContainerRef}
          />
        </Rect>
      </Rect>
    </FrameLayout>
  );

  const activeSteps = stack_frames.slice(0, timing.maxItems);

  for (let idx = 0; idx < activeSteps.length; idx++) {
    const step = activeSteps[idx];

    // Update explanation
    explanationTextRef().text(step.explanation);
    opBadgeRef().text(step.op_type?.toUpperCase() || 'RUNNING');

    // Re-draw stack frames in bucket
    stackContainerRef().removeChildren();

    step.frames.forEach((frame, fIdx) => {
      const isTopFrame = fIdx === step.frames.length - 1;
      
      // Parse arguments to string
      let argsStr = '';
      if (frame.args && Object.keys(frame.args).length > 0) {
        argsStr = Object.entries(frame.args)
          .map(([k, v]) => `${k}=${v}`)
          .join(', ');
      }

      stackContainerRef().add(
        <Rect
          key={`frame-${fIdx}`}
          fill={isTopFrame ? theme.colors.accent + '15' : theme.colors.cardBg}
          border={isTopFrame ? 2.5 : 1.5}
          borderColor={isTopFrame ? theme.colors.accent : theme.colors.border}
          radius={theme.radius.md}
          padding={16}
          direction="column"
          gap={4}
          alignItems="center"
          shadow={theme.shadows.sm}
          layout
        >
          <Txt
            text={`${frame.name}()`}
            fontFamily={theme.fonts.mono}
            fontSize={17}
            fontWeight={700}
            fill={isTopFrame ? theme.colors.accent : theme.colors.text}
          />
          {argsStr && (
            <Txt
              text={argsStr}
              fontFamily={theme.fonts.mono}
              fontSize={13}
              fill={theme.colors.textWeak}
            />
          )}
        </Rect>
      );
    });

    yield* timing.stepDelay * 1.5;
  }

  const animTime = activeSteps.length * timing.stepDelay * 1.5;
  yield* Math.max(0.5, scene.duration_seconds - animTime);
}
