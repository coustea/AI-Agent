import { spring, interpolate } from 'remotion';

/**
 * Get a physics-based spring progress value (0 to 1) for a given frame and delay.
 */
export const getSpringProgress = (
  frame: number,
  fps: number,
  delay: number = 0,
  durationInFrames?: number,
  damping: number = 15,
  stiffness: number = 100
): number => {
  const activeFrame = frame - delay;
  if (activeFrame < 0) {
    return 0;
  }
  return spring({
    frame: activeFrame,
    fps,
    config: {
      damping,
      stiffness,
    },
    durationInFrames,
  });
};

/**
 * Slide/Fade/Linear interpolation helper that clamps output to safe ranges.
 */
export const getSlideInterpolation = (
  value: number,
  inputStart: number,
  inputEnd: number,
  outputStart: number,
  outputEnd: number
): number => {
  return interpolate(value, [inputStart, inputEnd], [outputStart, outputEnd], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
};
