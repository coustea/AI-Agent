import { Rect, Txt } from '@motion-canvas/2d';
import { createRef, all } from '@motion-canvas/core';
import { FrameLayout } from '../components/FrameLayout';
import { Arrow } from '../components/Arrow';
import { theme } from '../styles/theme';
import { TeachingVideoScene } from '../schema/videoPlan';
import { getTimingConfig } from '../renderer/sceneTiming';

interface SequenceMessage {
  from: string;
  to: string;
  label: string;
  explanation: string;
}

export function* renderProtocolSequence(
  view: any,
  scene: TeachingVideoScene,
  mode: any
) {
  const { participants = [], messages = [] } = scene.visual_data as {
    participants: string[];
    messages: SequenceMessage[];
  };
  const timing = getTimingConfig(mode);

  const explanationTextRef = createRef<Txt>();
  const canvasRef = createRef<Rect>();

  // Layout calculations
  const partCount = participants.length;
  const partPositions = new Map<string, number>(); // X positions
  
  participants.forEach((pName, idx) => {
    const x = (idx - (partCount - 1) / 2) * 400; // Large spacing
    partPositions.set(pName, x);
  });

  view.add(
    <FrameLayout
      title={scene.title}
      topic="Network Protocol Interaction"
      courseTag="Computer Networks"
      subtitle={scene.subtitle}
    >
      <Rect direction="column" gap={30} width="100%" height="100%" justifyContent="center" layout>
        {/* Top Explanation Banner */}
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
            text="Initializing connection handshake..."
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
          layout={false} // Absolute diagram overlays
        />
      </Rect>
    </FrameLayout>
  );

  const activeMsgs = messages.slice(0, timing.maxItems);

  for (let idx = 0; idx < activeMsgs.length; idx++) {
    const activeMsg = activeMsgs[idx];
    
    // Update explanation
    explanationTextRef().text(activeMsg.explanation);

    // Redraw Canvas content
    canvasRef().removeChildren();

    // 1. Draw Participant columns (vertical lines with labels at the top)
    participants.forEach((pName) => {
      const x = partPositions.get(pName)!;

      // Header card for participant
      canvasRef().add(
        <Rect
          fill={theme.colors.codeBg}
          border={1.5}
          borderColor={theme.colors.border}
          radius={theme.radius.md}
          padding={{ x: 24, y: 10 }}
          x={x}
          y={200} // Top of canvas
          layout
        >
          <Txt
            text={pName}
            fontFamily={theme.fonts.sans}
            fontSize={18}
            fontWeight={700}
            fill={theme.colors.text}
          />
        </Rect>
      );

      // Vertical line representing life line
      canvasRef().add(
        <Arrow
          points={[[x, 160], [x, -220]]}
          endArrow={false} // Solid line
          lineWidth={2}
          stroke={theme.colors.border}
        />
      );
    });

    // 2. Draw all messages up to current step
    activeMsgs.slice(0, idx + 1).forEach((msg, mIdx) => {
      const fromX = partPositions.get(msg.from);
      const toX = partPositions.get(msg.to);
      if (fromX === undefined || toX === undefined) return;

      // Vertically space out arrows over timeline
      // Start top (y = 100), step down by 65px per message
      const yStart = 100 - mIdx * 60;
      // Slant arrow down by 35px to show transmission delay
      const yEnd = yStart - 35;

      const isCurrentMsg = mIdx === idx;
      const arrowColor = isCurrentMsg ? theme.colors.primary : theme.colors.textWeak + '60';

      canvasRef().add(
        <Arrow
          key={`msg-arrow-${mIdx}`}
          points={[[fromX, yStart], [toX, yEnd]]}
          active={isCurrentMsg}
          stroke={arrowColor}
        />
      );

      // Render message label text above the slanted line
      const textX = (fromX + toX) / 2;
      const textY = (yStart + yEnd) / 2 - 16;
      canvasRef().add(
        <Txt
          text={msg.label}
          fontFamily={theme.fonts.mono}
          fontSize={15}
          fontWeight={isCurrentMsg ? 700 : 500}
          fill={isCurrentMsg ? theme.colors.primary : theme.colors.textWeak}
          x={textX}
          y={textY}
          textAlign="center"
        />
      );
    });

    yield* timing.stepDelay * 1.5;
  }

  const animTime = activeMsgs.length * timing.stepDelay * 1.5;
  yield* Math.max(0.5, scene.duration_seconds - animTime);
}
