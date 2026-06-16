import { Rect, Txt } from '@motion-canvas/2d';
import { createRef, all } from '@motion-canvas/core';
import { FrameLayout } from '../components/FrameLayout';
import { theme } from '../styles/theme';
import { TeachingVideoScene } from '../schema/videoPlan';
import { getTimingConfig } from '../renderer/sceneTiming';

export function* renderConceptExplain(
  view: any,
  scene: TeachingVideoScene,
  mode: any
) {
  const { concept, definition, features, summary } = scene.visual_data;
  const timing = getTimingConfig(mode);
  
  const leftCard = createRef<Rect>();
  const rightColumn = createRef<Rect>();
  const summaryBox = createRef<Rect>();
  const featureRefs = features.map(() => createRef<Rect>());

  view.add(
    <FrameLayout
      title={scene.title}
      topic="Concept Explanation"
      courseTag="Computer Science"
      subtitle={scene.subtitle}
    >
      <Rect direction="column" gap={30} width="100%" height="100%" justifyContent="center" layout>
        {/* Main Side-by-Side Area */}
        <Rect direction="row" gap={40} width="100%" grow={1} alignItems="stretch" layout>
          {/* Left: Concept Title and Definition Card */}
          <Rect
            ref={leftCard}
            fill={theme.colors.cardBg}
            border={2}
            borderColor={theme.colors.border}
            radius={theme.radius.lg}
            padding={40}
            width="45%"
            direction="column"
            gap={20}
            justifyContent="center"
            shadow={theme.shadows.md}
            opacity={0}
            x={-100}
            layout
          >
            <Txt
              text={concept}
              fontFamily={theme.fonts.sans}
              fontSize={44}
              fontWeight={800}
              fill={theme.colors.primary}
            />
            <Rect height={4} fill={theme.colors.primary} width={80} radius={2} />
            <Txt
              text={definition}
              fontFamily={theme.fonts.sans}
              fontSize={20}
              fill={theme.colors.text}
              lineHeight={32}
            />
          </Rect>

          {/* Right: Key Features list */}
          <Rect
            ref={rightColumn}
            width="50%"
            direction="column"
            gap={16}
            justifyContent="center"
            opacity={0}
            layout
          >
            {features.slice(0, timing.maxItems).map((feat: string, idx: number) => (
              <Rect
                key={`feat-${idx}`}
                ref={featureRefs[idx]}
                fill={theme.colors.cardBg}
                border={1.5}
                borderColor={theme.colors.border}
                radius={theme.radius.md}
                padding={20}
                direction="row"
                gap={16}
                alignItems="center"
                shadow={theme.shadows.sm}
                opacity={0}
                x={50}
                layout
              >
                <Rect
                  width={36}
                  height={36}
                  radius={18}
                  fill={theme.colors.primary}
                  justifyContent="center"
                  alignItems="center"
                  layout
                >
                  <Txt
                    text={String(idx + 1)}
                    fontFamily={theme.fonts.mono}
                    fontSize={16}
                    fontWeight={700}
                    fill={theme.colors.cardBg}
                  />
                </Rect>
                <Txt
                  text={feat}
                  fontFamily={theme.fonts.sans}
                  fontSize={18}
                  fontWeight={500}
                  fill={theme.colors.text}
                  grow={1}
                />
              </Rect>
            ))}
          </Rect>
        </Rect>

        {/* Bottom Summary Box */}
        {summary && (
          <Rect
            ref={summaryBox}
            fill={theme.colors.codeBg}
            border={1}
            borderColor={theme.colors.border}
            radius={theme.radius.md}
            padding={{ x: 24, y: 16 }}
            alignItems="center"
            opacity={0}
            scale={0.95}
            layout
          >
            <Txt
              text={`💡 Summary: ${summary}`}
              fontFamily={theme.fonts.sans}
              fontSize={18}
              fontWeight={600}
              fill={theme.colors.textWeak}
            />
          </Rect>
        )}
      </Rect>
    </FrameLayout>
  );

  // Animations timeline
  yield* all(
    leftCard().opacity(1, timing.transitionDuration),
    leftCard().x(0, timing.transitionDuration)
  );

  yield* rightColumn().opacity(1, timing.transitionDuration * 0.5);

  // Sequence load features
  for (let i = 0; i < Math.min(features.length, timing.maxItems); i++) {
    yield* all(
      featureRefs[i]().opacity(1, timing.transitionDuration * 0.4),
      featureRefs[i]().x(0, timing.transitionDuration * 0.4)
    );
    yield* timing.stepDelay * 0.3;
  }

  // Summary fade in
  if (summary) {
    yield* all(
      summaryBox().opacity(1, timing.transitionDuration * 0.5),
      summaryBox().scale(1, timing.transitionDuration * 0.5)
    );
  }

  // Remaining budget sleep
  yield* scene.duration_seconds - (timing.transitionDuration * 2);
}
