import { Rect, Txt } from '@motion-canvas/2d';
import { createRef, all } from '@motion-canvas/core';
import { FrameLayout } from '../components/FrameLayout';
import { theme } from '../styles/theme';
import { TeachingVideoScene } from '../schema/videoPlan';
import { getTimingConfig } from '../renderer/sceneTiming';

export function* renderQuestionSolution(
  view: any,
  scene: TeachingVideoScene,
  mode: any
) {
  const { question, steps = [], final_answer } = scene.visual_data;
  const timing = getTimingConfig(mode);

  const questionCardRef = createRef<Rect>();
  const stepsContainerRef = createRef<Rect>();
  const finalAnswerCardRef = createRef<Rect>();
  
  const stepRefs = steps.map(() => createRef<Rect>());

  view.add(
    <FrameLayout
      title={scene.title}
      topic="Exercise & Derivation"
      courseTag="Classroom Exercise"
      subtitle={scene.subtitle}
    >
      <Rect direction="column" gap={24} width="100%" height="100%" justifyContent="center" layout>
        {/* Question Header Card */}
        <Rect
          ref={questionCardRef}
          fill={theme.colors.codeBg}
          border={1.5}
          borderColor={theme.colors.border}
          radius={theme.radius.md}
          padding={24}
          width="100%"
          opacity={0}
          y={-30}
          layout
        >
          <Txt
            text={`❓ Question: ${question}`}
            fontFamily={theme.fonts.sans}
            fontSize={22}
            fontWeight={700}
            fill={theme.colors.text}
          />
        </Rect>

        {/* Mid Steps Container */}
        <Rect
          ref={stepsContainerRef}
          direction="column"
          gap={12}
          width="100%"
          grow={1}
          justifyContent="center"
          layout
        >
          {steps.slice(0, timing.maxItems).map((step: string, idx: number) => (
            <Rect
              key={`step-${idx}`}
              ref={stepRefs[idx]}
              fill={theme.colors.cardBg}
              border={1}
              borderColor={theme.colors.border}
              radius={theme.radius.sm}
              padding={16}
              direction="row"
              gap={16}
              alignItems="center"
              opacity={0}
              x={-20}
              layout
            >
              <Txt
                text={`Step ${idx + 1}`}
                fontFamily={theme.fonts.mono}
                fontSize={16}
                fontWeight={700}
                fill={theme.colors.primary}
              />
              <Rect width={1.5} height={20} fill={theme.colors.border} />
              <Txt
                text={step}
                fontFamily={theme.fonts.sans}
                fontSize={18}
                fill={theme.colors.text}
              />
            </Rect>
          ))}
        </Rect>

        {/* Final Answer Banner */}
        {final_answer && (
          <Rect
            ref={finalAnswerCardRef}
            fill={theme.colors.success + '12'} // Light success green
            border={2}
            borderColor={theme.colors.success}
            radius={theme.radius.md}
            padding={24}
            alignItems="center"
            opacity={0}
            scale={0.9}
            layout
          >
            <Txt
              text={`🏆 Final Answer: ${final_answer}`}
              fontFamily={theme.fonts.sans}
              fontSize={24}
              fontWeight={800}
              fill={theme.colors.success}
            />
          </Rect>
        )}
      </Rect>
    </FrameLayout>
  );

  // Animations
  yield* all(
    questionCardRef().opacity(1, timing.transitionDuration),
    questionCardRef().y(0, timing.transitionDuration)
  );

  // Steps sequential display
  for (let i = 0; i < Math.min(steps.length, timing.maxItems); i++) {
    yield* all(
      stepRefs[i]().opacity(1, timing.transitionDuration * 0.4),
      stepRefs[i]().x(0, timing.transitionDuration * 0.4)
    );
    yield* timing.stepDelay * 0.4;
  }

  // Answer card glow
  if (final_answer) {
    yield* all(
      finalAnswerCardRef().opacity(1, timing.transitionDuration * 0.6),
      finalAnswerCardRef().scale(1, timing.transitionDuration * 0.6)
    );
  }

  const animTime = timing.transitionDuration * 1.6 + Math.min(steps.length, timing.maxItems) * (timing.transitionDuration * 0.4 + timing.stepDelay * 0.4);
  yield* Math.max(0.5, scene.duration_seconds - animTime);
}
