import { Rect, Txt } from '@motion-canvas/2d';
import { createRef, all } from '@motion-canvas/core';
import { FrameLayout } from '../components/FrameLayout';
import { theme } from '../styles/theme';
import { TeachingVideoScene } from '../schema/videoPlan';
import { getTimingConfig } from '../renderer/sceneTiming';

export function* renderSummaryCard(
  view: any,
  scene: TeachingVideoScene,
  mode: any
) {
  const { title = 'Summary', key_points = [], exam_focus } = scene.visual_data;
  const timing = getTimingConfig(mode);

  const leftColumnRef = createRef<Rect>();
  const rightColumnRef = createRef<Rect>();
  
  const pointRefs = key_points.map(() => createRef<Rect>());
  const focusCardRef = createRef<Rect>();

  view.add(
    <FrameLayout
      title={scene.title}
      topic="Course Summary"
      courseTag="Quick Review"
      subtitle={scene.subtitle}
    >
      <Rect direction="row" gap={40} width="100%" height="100%" alignItems="stretch" layout>
        {/* Left Side: Summary Points */}
        <Rect
          ref={leftColumnRef}
          width={exam_focus ? "55%" : "100%"}
          direction="column"
          gap={20}
          justifyContent="center"
          layout
        >
          <Txt
            text={title}
            fontFamily={theme.fonts.sans}
            fontSize={28}
            fontWeight={800}
            fill={theme.colors.text}
          />
          <Rect height={3} fill={theme.colors.primary} width={60} radius={1.5} />

          <Rect direction="column" gap={12} layout>
            {key_points.slice(0, timing.maxItems).map((pt: string, idx: number) => (
              <Rect
                key={`pt-${idx}`}
                ref={pointRefs[idx]}
                direction="row"
                gap={16}
                alignItems="center"
                opacity={0}
                x={-30}
                layout
              >
                <Txt
                  text="✔"
                  fontFamily={theme.fonts.sans}
                  fontSize={20}
                  fontWeight={800}
                  fill={theme.colors.secondary}
                />
                <Txt
                  text={pt}
                  fontFamily={theme.fonts.sans}
                  fontSize={18}
                  fill={theme.colors.text}
                  lineHeight={28}
                />
              </Rect>
            ))}
          </Rect>
        </Rect>

        {/* Right Side: Exam Focus Box */}
        {exam_focus && (
          <Rect
            ref={rightColumnRef}
            width="40%"
            justifyContent="center"
            alignItems="center"
            layout
          >
            <Rect
              ref={focusCardRef}
              fill="#FFFBEB" // Warm yellow warning color
              border={2}
              borderColor={theme.colors.warning}
              radius={theme.radius.lg}
              padding={32}
              direction="column"
              gap={16}
              shadow={theme.shadows.md}
              opacity={0}
              scale={0.9}
              layout
            >
              <Txt
                text="⚠️ Exam Focus"
                fontFamily={theme.fonts.sans}
                fontSize={22}
                fontWeight={800}
                fill={theme.colors.warning}
              />
              <Txt
                text={exam_focus}
                fontFamily={theme.fonts.sans}
                fontSize={18}
                lineHeight={30}
                fill={theme.colors.text}
              />
            </Rect>
          </Rect>
        )}
      </Rect>
    </FrameLayout>
  );

  // Animate Left column
  yield* leftColumnRef().opacity(1, timing.transitionDuration * 0.5);

  // Animate Key Points sequentially
  for (let i = 0; i < Math.min(key_points.length, timing.maxItems); i++) {
    yield* all(
      pointRefs[i]().opacity(1, timing.transitionDuration * 0.4),
      pointRefs[i]().x(0, timing.transitionDuration * 0.4)
    );
    yield* timing.stepDelay * 0.3;
  }

  // Animate Focus Card
  if (exam_focus) {
    yield* all(
      focusCardRef().opacity(1, timing.transitionDuration * 0.6),
      focusCardRef().scale(1, timing.transitionDuration * 0.6)
    );
  }

  const activeDuration = timing.transitionDuration * 1.5 + Math.min(key_points.length, timing.maxItems) * (timing.transitionDuration * 0.4 + timing.stepDelay * 0.3);
  yield* Math.max(0.5, scene.duration_seconds - activeDuration);
}
