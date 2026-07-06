import React from "react";
import { AbsoluteFill } from "remotion";
import { RichVideoScene } from "../schema/types";
import { EduBackground } from "../components/EduBackground";

interface SceneProps {
  scene: RichVideoScene;
  currentSceneIndex: number;
  totalScenes: number;
}

export const UnknownSceneFallback: React.FC<SceneProps> = ({
  scene,
  currentSceneIndex,
  totalScenes,
}) => {
  return (
    <AbsoluteFill className="flex items-center justify-center p-20 bg-slate-100">
      <EduBackground backgroundType="technical_grid" />
      <div className="edu-card max-w-xl border-red-300 bg-red-50/90 text-center space-y-4 shadow-xl">
        <h2 className="text-2xl font-bold text-red-600">
          未知场景模板 (Unknown Scene Fallback)
        </h2>
        <p className="text-slate-600 text-sm">
          场景 ID:{" "}
          <code className="font-mono bg-red-100 px-1.5 py-0.5 rounded text-red-700">
            {scene.id}
          </code>
        </p>
        <p className="text-slate-600 text-sm">
          未知的类型:{" "}
          <code className="font-mono bg-red-100 px-1.5 py-0.5 rounded text-red-700">
            {scene.type}
          </code>
        </p>
        <p className="text-slate-500 text-xs">
          请检查 video plan JSON 或补充该场景对应的 React 模板。
        </p>
        <div className="text-xs text-slate-400 font-mono">
          Scene {currentSceneIndex} / {totalScenes}
        </div>
      </div>
    </AbsoluteFill>
  );
};
