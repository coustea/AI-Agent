import { useCurrentFrame, useVideoConfig } from "remotion";
import type {
  RichVideoScene,
  VisualCueKind,
} from "../schema/types";
import { getCueDrivenIndex, getCueProgress } from "../utils/timeline";

export const useSceneTiming = (scene: RichVideoScene) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentMs = (frame / fps) * 1000;
  const audioDurationMs = Math.max(
    1,
    scene.audio_duration_ms || scene.duration_ms,
  );

  return {
    currentMs,
    audioProgress: Math.min(currentMs / audioDurationMs, 1),
    getActiveIndex: (itemCount: number, kinds?: VisualCueKind[]) =>
      getCueDrivenIndex(
        scene.visual_cues ?? [],
        currentMs,
        itemCount,
        audioDurationMs,
        kinds,
      ),
    getStepProgress: (itemCount: number, kinds?: VisualCueKind[]) =>
      getCueProgress(
        scene.visual_cues ?? [],
        currentMs,
        audioDurationMs,
        kinds,
        itemCount,
      ),
  };
};
