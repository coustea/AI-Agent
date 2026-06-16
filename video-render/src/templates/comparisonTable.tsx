import { Rect, Txt } from '@motion-canvas/2d';
import { createRef, all } from '@motion-canvas/core';
import { FrameLayout } from '../components/FrameLayout';
import { theme } from '../styles/theme';
import { TeachingVideoScene } from '../schema/videoPlan';
import { getTimingConfig } from '../renderer/sceneTiming';

interface ComparisonSubject {
  name: string;
  features: string[];
}

export function* renderComparisonTable(
  view: any,
  scene: TeachingVideoScene,
  mode: any
) {
  const { title = 'Comparison', left, right, conclusion } = scene.visual_data as {
    title: string;
    left: ComparisonSubject;
    right: ComparisonSubject;
    conclusion?: string;
  };
  const timing = getTimingConfig(mode);

  const leftCardRef = createRef<Rect>();
  const rightCardRef = createRef<Rect>();
  const conclusionBoxRef = createRef<Rect>();

  const leftFeatRefs = left.features.map(() => createRef<Rect>());
  const rightFeatRefs = right.features.map(() => createRef<Rect>());

  view.add(
    <FrameLayout
      title={scene.title}
      topic="Concept Comparison"
      courseTag="Differential Analysis"
      subtitle={scene.subtitle}
    >
      <Rect direction="column" gap={30} width="100%" height="100%" justifyContent="center" layout>
        {/* Comparison Cards Area */}
        <Rect direction="row" gap={40} width="100%" grow={1} alignItems="stretch" layout>
          {/* Left card */}
          <Rect
            ref={leftCardRef}
            fill={theme.colors.cardBg}
            border={2}
            borderColor={theme.colors.primary}
            radius={theme.radius.lg}
            padding={32}
            width="47%"
            direction="column"
            gap={20}
            shadow={theme.shadows.md}
            opacity={0}
            x={-50}
            layout
          >
            <Txt
              text={left.name}
              fontFamily={theme.fonts.sans}
              fontSize={32}
              fontWeight={800}
              fill={theme.colors.primary}
              textAlign="center"
            />
            <Rect height={2} fill={theme.colors.primary + '50'} width="100%" />

            <Rect direction="column" gap={12} layout>
              {left.features.slice(0, timing.maxItems).map((feat, idx) => (
                <Rect
                  key={`l-feat-${idx}`}
                  ref={leftFeatRefs[idx]}
                  direction="row"
                  gap={12}
                  alignItems="center"
                  opacity={0}
                  layout
                >
                  <Rect width={12} height={12} radius={6} fill={theme.colors.primary} />
                  <Txt
                    text={feat}
                    fontFamily={theme.fonts.sans}
                    fontSize={16}
                    fill={theme.colors.text}
                    lineHeight={24}
                  />
                </Rect>
              ))}
            </Rect>
          </Rect>

          {/* Right card */}
          <Rect
            ref={rightCardRef}
            fill={theme.colors.cardBg}
            border={2}
            borderColor={theme.colors.secondary}
            radius={theme.radius.lg}
            padding={32}
            width="47%"
            direction="column"
            gap={20}
            shadow={theme.shadows.md}
            opacity={0}
            x={50}
            layout
          >
            <Txt
              text={right.name}
              fontFamily={theme.fonts.sans}
              fontSize={32}
              fontWeight={800}
              fill={theme.colors.secondary}
              textAlign="center"
            />
            <Rect height={2} fill={theme.colors.secondary + '50'} width="100%" />

            <Rect direction="column" gap={12} layout>
              {right.features.slice(0, timing.maxItems).map((feat, idx) => (
                <Rect
                  key={`r-feat-${idx}`}
                  ref={rightFeatRefs[idx]}
                  direction="row"
                  gap={12}
                  alignItems="center"
                  opacity={0}
                  layout
                >
                  <Rect width={12} height={12} radius={6} fill={theme.colors.secondary} />
                  <Txt
                    text={feat}
                    fontFamily={theme.fonts.sans}
                    fontSize={16}
                    fill={theme.colors.text}
                    lineHeight={24}
                  />
                </Rect>
              ))}
            </Rect>
          </Rect>
        </Rect>

        {/* Conclusion Box */}
        {conclusion && (
          <Rect
            ref={conclusionBoxRef}
            fill={theme.colors.codeBg}
            border={1}
            borderColor={theme.colors.border}
            radius={theme.radius.md}
            padding={20}
            opacity={0}
            scale={0.95}
            layout
          >
            <Txt
              text={`📝 Conclusion: ${conclusion}`}
              fontFamily={theme.fonts.sans}
              fontSize={18}
              fontWeight={600}
              fill={theme.colors.text}
            />
          </Rect>
        )}
      </Rect>
    </FrameLayout>
  );

  // Animations entry
  yield* all(
    leftCardRef().opacity(1, timing.transitionDuration),
    leftCardRef().x(0, timing.transitionDuration),
    rightCardRef().opacity(1, timing.transitionDuration),
    rightCardRef().x(0, timing.transitionDuration)
  );

  // Animate features inside cards
  const featCount = Math.max(left.features.length, right.features.length);
  const cappedCount = Math.min(featCount, timing.maxItems);
  
  for (let i = 0; i < cappedCount; i++) {
    const featureAnims = [];
    if (i < left.features.length) {
      featureAnims.push(leftFeatRefs[i]().opacity(1, timing.transitionDuration * 0.4));
    }
    if (i < right.features.length) {
      featureAnims.push(rightFeatRefs[i]().opacity(1, timing.transitionDuration * 0.4));
    }
    yield* all(...featureAnims);
    yield* timing.stepDelay * 0.3;
  }

  // Animate conclusion
  if (conclusion) {
    yield* all(
      conclusionBoxRef().opacity(1, timing.transitionDuration * 0.5),
      conclusionBoxRef().scale(1, timing.transitionDuration * 0.5)
    );
  }

  const activeDuration = timing.transitionDuration * 2.0 + cappedCount * (timing.transitionDuration * 0.4 + timing.stepDelay * 0.3);
  yield* Math.max(0.5, scene.duration_seconds - activeDuration);
}
