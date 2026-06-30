import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { getActiveVisualCue } from "../utils/timeline";
import { useSceneData } from "./SceneDataContext";

interface SceneHeaderProps {
  course: string;
  topic: string;
  sceneTitle: string;
  currentSceneIndex: number;
  totalScenes: number;
  progress: number;
}

export const SceneHeader: React.FC<SceneHeaderProps> = ({
  course,
  topic,
  sceneTitle,
  currentSceneIndex,
  totalScenes,
  progress,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scene = useSceneData();
  const activeCue = getActiveVisualCue(
    scene?.visual_cues ?? [],
    (frame / fps) * 1000,
  );

  return (
    <header className="absolute left-16 right-16 top-10 z-20 flex h-14 items-start justify-between">
      <div className="flex min-w-0 items-start gap-5">
        <span className="mt-1 h-9 w-[5px] shrink-0 bg-[var(--primary)]" />
        <div className="min-w-0">
          <div className="flex items-baseline gap-3 text-[18px] font-semibold text-[var(--text-muted)]">
            <span className="font-bold text-[var(--primary)]">{course}</span>
            <span>{topic}</span>
          </div>
          <div className="mt-1 flex items-baseline gap-5">
            <span className="text-[26px] font-bold leading-none text-[var(--text-main)]">
              {sceneTitle}
            </span>
            {activeCue?.summary && (
              <span className="max-w-[620px] truncate text-[19px] font-medium text-[var(--primary)]">
                {activeCue.summary}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex w-[330px] shrink-0 flex-col items-end gap-3">
        <div className="font-mono text-[17px] font-semibold text-[var(--text-muted)]">
          <span className="text-[var(--text-main)]">{currentSceneIndex}</span>
          <span className="px-2">/</span>
          <span>{totalScenes}</span>
        </div>
        <div className="h-[3px] w-full overflow-hidden bg-[var(--card-border)]">
          <div
            className="h-full bg-[var(--primary)]"
            style={{ width: `${Math.min(1, Math.max(0, progress)) * 100}%` }}
          />
        </div>
      </div>
    </header>
  );
};
