/**
 * Convert duration in seconds to number of frames based on fps
 */
export const secondsToFrames = (seconds: number, fps: number): number => {
  return Math.round(seconds * fps);
};

/**
 * Convert number of frames to duration in seconds based on fps
 */
export const framesToSeconds = (frames: number, fps: number): number => {
  return frames / fps;
};
