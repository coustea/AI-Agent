import type {
  CaptionChunk,
  VisualCue,
  VisualCueKind,
} from "../schema/types";

export interface SceneFrameRange {
  from: number;
  durationInFrames: number;
}

const clamp = (value: number, min: number, max: number) =>
  Math.min(Math.max(value, min), max);

export const millisecondsToFrames = (milliseconds: number, fps: number) =>
  Math.round((milliseconds / 1000) * fps);

export const buildSceneFrameRanges = (
  durationsMs: number[],
  fps: number,
): SceneFrameRange[] => {
  let elapsedMs = 0;

  return durationsMs.map((durationMs) => {
    const startMs = elapsedMs;
    elapsedMs += Math.max(0, durationMs);
    const from = millisecondsToFrames(startMs, fps);
    const end = millisecondsToFrames(elapsedMs, fps);

    return {
      from,
      durationInFrames: Math.max(1, end - from),
    };
  });
};

export const getActiveCaptionChunk = (
  chunks: CaptionChunk[],
  currentMs: number,
) =>
  chunks.find(
    (chunk) => currentMs >= chunk.start_ms && currentMs < chunk.end_ms,
  );

export const getActiveVisualCue = (
  cues: VisualCue[],
  currentMs: number,
) => {
  let activeIndex = -1;
  for (let index = 0; index < cues.length; index += 1) {
    if (currentMs >= cues[index].start_ms) activeIndex = index;
  }
  if (activeIndex < 0) return undefined;

  const activeCue = cues[activeIndex];
  const hasUpcomingCue = activeIndex < cues.length - 1;
  if (!hasUpcomingCue && currentMs >= activeCue.end_ms) return undefined;
  return activeCue;
};

export const getCueDrivenIndex = (
  cues: VisualCue[],
  currentMs: number,
  itemCount: number,
  audioDurationMs: number,
  kinds?: VisualCueKind[],
) => {
  if (itemCount <= 1) return 0;

  const relevantCues = cues.filter(
    (cue) => !kinds || kinds.includes(cue.kind),
  );
  if (relevantCues.length > 0) {
    let activeCueIndex = 0;
    for (let index = 0; index < relevantCues.length; index += 1) {
      if (currentMs >= relevantCues[index].start_ms) {
        activeCueIndex = index;
      }
    }

    return clamp(
      Math.floor((activeCueIndex * itemCount) / relevantCues.length),
      0,
      itemCount - 1,
    );
  }

  const safeDuration = Math.max(1, audioDurationMs);
  return clamp(
    Math.floor((clamp(currentMs, 0, safeDuration - 1) / safeDuration) * itemCount),
    0,
    itemCount - 1,
  );
};

export const getCueProgress = (
  cues: VisualCue[],
  currentMs: number,
  audioDurationMs: number,
  kinds?: VisualCueKind[],
  fallbackItemCount = 1,
) => {
  const relevantCues = cues.filter(
    (cue) => !kinds || kinds.includes(cue.kind),
  );
  if (relevantCues.length > 0) {
    let activeCue = relevantCues[0];
    for (const cue of relevantCues) {
      if (currentMs >= cue.start_ms) activeCue = cue;
    }
    return clamp(
      (currentMs - activeCue.start_ms) /
        Math.max(1, activeCue.end_ms - activeCue.start_ms),
      0,
      1,
    );
  }

  const overallProgress = clamp(
    currentMs / Math.max(1, audioDurationMs),
    0,
    1,
  );
  if (overallProgress === 1) return 1;
  return (overallProgress * Math.max(1, fallbackItemCount)) % 1;
};
