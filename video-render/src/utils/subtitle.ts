import type { CaptionChunk } from "../schema/types";

/**
 * Find the caption chunk that corresponds to the current frame.
 * @param chunks The array of caption chunks.
 * @param currentFrame The current frame number.
 * @param fps The frame rate of the video.
 */
export const getCurrentSubtitle = (
  chunks: CaptionChunk[] | undefined,
  currentFrame: number,
  fps: number,
): string => {
  if (!chunks || chunks.length === 0) return "";
  const currentTimeMs = (currentFrame / fps) * 1000;
  const activeChunk = chunks.find(
    (chunk) => currentTimeMs >= chunk.start_ms && currentTimeMs <= chunk.end_ms,
  );
  return activeChunk ? activeChunk.text : "";
};
