import { Rect, Txt } from '@motion-canvas/2d';
import { createRef, all } from '@motion-canvas/core';
import { FrameLayout } from '../components/FrameLayout';
import { CodeBlock } from '../components/CodeBlock';
import { Badge } from '../components/Badge';
import { theme } from '../styles/theme';
import { TeachingVideoScene } from '../schema/videoPlan';
import { getTimingConfig } from '../renderer/sceneTiming';

interface WalkthroughStep {
  line: number;
  explanation: string;
  state?: Record<string, any>;
}

export function* renderCodeWalkthrough(
  view: any,
  scene: TeachingVideoScene,
  mode: any
) {
  const { code = '', language = 'python', steps = [] } = scene.visual_data as {
    code: string;
    language: string;
    steps: WalkthroughStep[];
  };
  const timing = getTimingConfig(mode);

  const codeContainerRef = createRef<Rect>();
  const rightColumnRef = createRef<Rect>();
  const explanationCardRef = createRef<Rect>();
  const explanationTextRef = createRef<Txt>();
  const stateCardRef = createRef<Rect>();
  const stateContainerRef = createRef<Rect>();

  // Add initial container skeleton
  view.add(
    <FrameLayout
      title={scene.title}
      topic="Code Execution Walkthrough"
      courseTag={`${language.toUpperCase()} Program`}
      subtitle={scene.subtitle}
    >
      <Rect direction="row" gap={30} width="100%" height={1000} alignItems="stretch" layout>
        {/* Left: CodeBlock Container */}
        <Rect ref={codeContainerRef} width="52%" direction="column" layout />

        {/* Right: Explanation & State column */}
        <Rect ref={rightColumnRef} width="45%" direction="column" gap={24} layout>
          {/* Step Explanation Card */}
          <Rect
            ref={explanationCardRef}
            fill={theme.colors.cardBg}
            border={2}
            borderColor={theme.colors.border}
            radius={theme.radius.lg}
            padding={32}
            direction="column"
            gap={16}
            shadow={theme.shadows.md}
            grow={1}
            layout
          >
            <Txt
              text="⚡ Current Action"
              fontFamily={theme.fonts.sans}
              fontSize={18}
              fontWeight={700}
              fill={theme.colors.primary}
            />
            <Txt
              ref={explanationTextRef}
              text="Initializing execution..."
              fontFamily={theme.fonts.sans}
              fontSize={20}
              lineHeight={32}
              fill={theme.colors.text}
            />
          </Rect>

          {/* State Variables Card */}
          <Rect
            ref={stateCardRef}
            fill={theme.colors.codeBg}
            border={1}
            borderColor={theme.colors.border}
            radius={theme.radius.lg}
            padding={24}
            direction="column"
            gap={16}
            height={260}
            layout
          >
            <Txt
              text="📊 Variable Tracker"
              fontFamily={theme.fonts.sans}
              fontSize={16}
              fontWeight={700}
              fill={theme.colors.textWeak}
            />
            <Rect
              ref={stateContainerRef}
              direction="row"
              gap={12}
              alignItems="flex-start"
              width="100%"
              textWrap
              layout
            />
          </Rect>
        </Rect>
      </Rect>
    </FrameLayout>
  );

  // Perform walkthrough steps
  const activeSteps = steps.slice(0, timing.maxItems);

  for (let idx = 0; idx < activeSteps.length; idx++) {
    const step = activeSteps[idx];

    // 1. Update code block with line highlight
    codeContainerRef().removeChildren();
    codeContainerRef().add(
      <CodeBlock
        code={code}
        language={language}
        highlightLines={[step.line]}
        width="100%"
      />
    );

    // 2. Update explanation text
    explanationTextRef().text(step.explanation);

    // 3. Update state badges
    stateContainerRef().removeChildren();
    if (step.state && Object.keys(step.state).length > 0) {
      Object.entries(step.state).forEach(([varName, val]) => {
        stateContainerRef().add(
          <Badge
            text={`${varName} = ${typeof val === 'object' ? JSON.stringify(val) : val}`}
            type="accent"
          />
        );
      });
    } else {
      stateContainerRef().add(
        <Txt
          text="No active variables in scope."
          fontFamily={theme.fonts.sans}
          fontSize={15}
          fill={theme.colors.textWeak}
        />
      );
    }

    // Bounce/Animate the explanation card on transition
    if (idx === 0) {
      yield* timing.stepDelay * 1.5;
    } else {
      yield* timing.stepDelay;
    }
  }

  // Calculate sleeping time
  const stepTime = activeSteps.length * timing.stepDelay;
  yield* Math.max(0.5, scene.duration_seconds - stepTime);
}
