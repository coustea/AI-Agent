import { Rect, Txt } from '@motion-canvas/2d';
import { createRef } from '@motion-canvas/core';
import { FrameLayout } from '../components/FrameLayout';
import { theme } from '../styles/theme';

export interface ErrorSceneProps {
  title: string;
  errorMessage: string;
  duration: number;
}

export function* renderErrorScene(
  view: any,
  { title, errorMessage, duration }: ErrorSceneProps
) {
  const containerRef = createRef<Rect>();
  const textRef = createRef<Txt>();

  view.add(
    <FrameLayout title="Renderer Exception" topic="System Error" courseTag="Core System">
      <Rect
        ref={containerRef}
        fill="#FFF1F2" // Very light red
        border={2}
        borderColor={theme.colors.error}
        radius={theme.radius.lg}
        padding={40}
        direction="column"
        gap={20}
        alignItems="center"
        justifyContent="center"
        width={1000}
        shadow={theme.shadows.md}
        scale={0.9}
        layout
      >
        <Txt
          text="⚠️ Render Error"
          fontFamily={theme.fonts.sans}
          fontSize={36}
          fontWeight={800}
          fill={theme.colors.error}
        />
        <Txt
          text={`Failed to render scene "${title}"`}
          fontFamily={theme.fonts.sans}
          fontSize={24}
          fontWeight={600}
          fill={theme.colors.text}
        />
        <Rect
          fill={theme.colors.cardBg}
          border={1}
          borderColor={theme.colors.border}
          radius={theme.radius.md}
          padding={20}
          width="100%"
          layout
        >
          <Txt
            ref={textRef}
            text={errorMessage}
            fontFamily={theme.fonts.mono}
            fontSize={18}
            fill={theme.colors.textWeak}
            textWrap // Ensure long stack traces or error texts wrap properly
          />
        </Rect>
      </Rect>
    </FrameLayout>
  );

  // Anim entry
  yield* containerRef().scale(1, 0.4);
  // Wait
  yield* duration - 0.4;
}
