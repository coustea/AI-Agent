import React from 'react';
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig, interpolate } from 'remotion';

interface SceneTransitionProps {
  transitionType: 'fade' | 'slide_left' | 'slide_up' | 'zoom' | 'none';
  durationInFrames: number;
  children: React.ReactNode;
}

export const SceneTransition: React.FC<SceneTransitionProps> = ({
  transitionType,
  durationInFrames,
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (transitionType === 'none') {
    return <AbsoluteFill>{children}</AbsoluteFill>;
  }

  const transitionDuration = 12; // 0.4 seconds at 30fps

  // Entrance spring progress (0 -> 1)
  const enterSpring = spring({
    frame,
    fps,
    config: { damping: 15, stiffness: 110 },
    durationInFrames: transitionDuration,
  });

  // Exit spring progress (0 -> 1)
  const exitFrame = frame - (durationInFrames - transitionDuration);
  const exitSpring = spring({
    frame: exitFrame < 0 ? 0 : exitFrame,
    fps,
    config: { damping: 15, stiffness: 110 },
    durationInFrames: transitionDuration,
  });

  // Calculate style based on transition type
  let opacity = 1;
  let transform = '';

  if (transitionType === 'fade') {
    opacity = interpolate(enterSpring, [0, 1], [0, 1]) * interpolate(exitSpring, [0, 1], [1, 0]);
  } else if (transitionType === 'slide_left') {
    // Enter from right (100% -> 0%), exit to left (0% -> -100%)
    const enterTranslate = interpolate(enterSpring, [0, 1], [100, 0]);
    const exitTranslate = interpolate(exitSpring, [0, 1], [0, -100]);
    const translateX = enterTranslate + exitTranslate;
    transform = `translateX(${translateX}%)`;
    opacity = interpolate(enterSpring, [0, 1], [0, 1]) * interpolate(exitSpring, [0, 1], [1, 0]);
  } else if (transitionType === 'slide_up') {
    // Enter from bottom (100% -> 0%), exit to top (0% -> -100%)
    const enterTranslate = interpolate(enterSpring, [0, 1], [100, 0]);
    const exitTranslate = interpolate(exitSpring, [0, 1], [0, -100]);
    const translateY = enterTranslate + exitTranslate;
    transform = `translateY(${translateY}%)`;
    opacity = interpolate(enterSpring, [0, 1], [0, 1]) * interpolate(exitSpring, [0, 1], [1, 0]);
  } else if (transitionType === 'zoom') {
    // Enter scale (0.8 -> 1), exit scale (1 -> 1.15)
    const enterScale = interpolate(enterSpring, [0, 1], [0.8, 1]);
    const exitScale = interpolate(exitSpring, [0, 1], [1, 1.15]);
    const scale = enterScale * (exitScale / 1); // multiply scales
    transform = `scale(${scale})`;
    opacity = interpolate(enterSpring, [0, 1], [0, 1]) * interpolate(exitSpring, [0, 1], [1, 0]);
  }

  return (
    <AbsoluteFill
      style={{
        opacity,
        transform,
        willChange: 'transform, opacity',
      }}
    >
      {children}
    </AbsoluteFill>
  );
};
