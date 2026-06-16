import { SubtitleChunk } from '../schema/types';

/**
 * Find the subtitle chunk that corresponds to the current frame.
 * @param chunks The array of subtitle chunks.
 * @param currentFrame The current frame number.
 * @param fps The frame rate of the video.
 */
export const getCurrentSubtitle = (
  chunks: SubtitleChunk[] | undefined,
  currentFrame: number,
  fps: number
): string => {
  if (!chunks || chunks.length === 0) return '';
  const currentTime = currentFrame / fps;
  const activeChunk = chunks.find(
    (chunk) => currentTime >= chunk.start && currentTime <= chunk.end
  );
  return activeChunk ? activeChunk.text : '';
};
