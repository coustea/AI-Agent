import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";
import { RichVideoScene, GlobalStyle, VideoMeta } from "../schema/types";
import { EduBackground } from "../components/EduBackground";
import { SceneHeader } from "../components/SceneHeader";
import { SubtitleBar } from "../components/SubtitleBar";
import { getSpringProgress, getSlideInterpolation } from "../utils/animation";

interface ArrayNode {
  value: string | number;
  index: number;
  highlight?: boolean;
  status?: "normal" | "active" | "comparing" | "swapping" | "sorted";
}

interface Operation {
  type: "access" | "compare" | "swap" | "insert" | "delete";
  indices: number[];
  description: string;
}

interface ArrayLinkedListLabProps {
  scene: RichVideoScene;
  meta: VideoMeta;
  globalStyle: GlobalStyle;
  currentSceneIndex: number;
  totalScenes: number;
}

export const ArrayLinkedListLab: React.FC<ArrayLinkedListLabProps> = ({
  scene,
  meta,
  globalStyle,
  currentSceneIndex,
  totalScenes,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Extract visual data
  const structureType = (scene.visual.structure_type as string) || "array";
  const nodes: ArrayNode[] = (scene.visual.nodes as ArrayNode[]) || [];
  const operations: Operation[] =
    (scene.visual.operations as Operation[]) || [];
  const timeComplexity = (scene.visual.time_complexity as string) || "";
  const spaceComplexity = (scene.visual.space_complexity as string) || "";

  // Calculate current operation based on time
  const operationDuration = durationInFrames / Math.max(operations.length, 1);
  const currentOpIndex = Math.min(
    Math.floor(frame / operationDuration),
    operations.length - 1,
  );
  const currentOp = operations[currentOpIndex];

  // Animation progress within current operation
  const opProgress = (frame % operationDuration) / operationDuration;

  // Entrance animations
  const arrayEntrance = getSpringProgress(frame, fps, 15, 25);
  const infoEntrance = getSpringProgress(frame, fps, 25, 20);

  // Get node status based on current operation
  const getNodeStatus = (idx: number, node: ArrayNode): ArrayNode["status"] => {
    if (!currentOp) return node.status || "normal";

    const isActive = currentOp.indices.includes(idx);
    if (currentOp.type === "compare" && isActive) return "comparing";
    if (currentOp.type === "swap" && isActive) return "swapping";
    if (currentOp.type === "access" && isActive) return "active";
    return node.status || "normal";
  };

  // Get node transform for animations
  const getNodeTransform = (idx: number, status: ArrayNode["status"]) => {
    const baseY = 0;
    let y = baseY;
    let scale = 1;

    if (status === "active" || status === "comparing") {
      // Pulse up effect
      const pulseProgress = interpolate(Math.sin(frame * 0.3), [-1, 1], [0, 1]);
      y = -10 * pulseProgress;
      scale = interpolate(pulseProgress, [0, 1], [1, 1.05]);
    }

    if (status === "swapping" && currentOp) {
      // Swap animation
      const swapProgress = spring({
        frame: frame % operationDuration,
        fps,
        config: { damping: 12, stiffness: 100 },
      });

      const isLeft = idx === Math.min(...currentOp.indices);
      const direction = isLeft ? 1 : -1;
      y = interpolate(swapProgress, [0, 0.5, 1], [0, -30, 0]);
      const xOffset = interpolate(
        swapProgress,
        [0, 0.5, 1],
        [0, direction * 60, 0],
      );
      return `translate(${xOffset}px, ${y}px) scale(${scale})`;
    }

    return `translateY(${y}px) scale(${scale})`;
  };

  // Status color mapping
  const getStatusColor = (status: ArrayNode["status"]) => {
    switch (status) {
      case "active":
        return "var(--primary)";
      case "comparing":
        return "var(--accent)";
      case "swapping":
        return "var(--danger)";
      case "sorted":
        return "var(--success)";
      default:
        return "var(--text-main)";
    }
  };

  return (
    <AbsoluteFill className="p-24 pt-32 overflow-hidden">
      <EduBackground backgroundType={globalStyle.background} />
      <SceneHeader
        course={meta.subject}
        topic={meta.topic}
        sceneTitle={scene.title}
        currentSceneIndex={currentSceneIndex}
        totalScenes={totalScenes}
        progress={frame / durationInFrames}
      />

      <div className="grid grid-cols-12 gap-6 w-full h-[calc(100%-40px)] z-10 items-center">
        {/* Main visualization area */}
        <div
          className="col-span-8 flex flex-col space-y-6"
          style={{
            opacity: arrayEntrance,
            transform: `translateY(${getSlideInterpolation(arrayEntrance, 0, 1, 20, 0)}px)`,
          }}
        >
          {/* Structure type label */}
          <div className="flex items-center space-x-3">
            <span className="px-4 py-1.5 rounded-full text-sm font-bold uppercase tracking-wider bg-[var(--primary)] text-white shadow-lg">
              {structureType === "array" ? "数组 Array" : "链表 Linked List"}
            </span>
            {timeComplexity && (
              <span className="text-xs font-mono text-[var(--text-muted)]">
                时间: {timeComplexity}
              </span>
            )}
            {spaceComplexity && (
              <span className="text-xs font-mono text-[var(--text-muted)]">
                空间: {spaceComplexity}
              </span>
            )}
          </div>

          {/* Array/LinkedList visualization */}
          <div className="edu-card !p-8 min-h-[300px] flex items-center justify-center relative">
            <div className="flex items-center space-x-2">
              {nodes.map((node, idx) => {
                const status = getNodeStatus(idx, node);
                const nodeEntrance = getSpringProgress(
                  frame,
                  fps,
                  20 + idx * 3,
                  15,
                );
                const transform = getNodeTransform(idx, status);

                return (
                  <React.Fragment key={idx}>
                    {/* Node */}
                    <div
                      className="flex flex-col items-center"
                      style={{
                        opacity: nodeEntrance,
                        transform,
                      }}
                    >
                      {/* Index label */}
                      <span className="text-xs font-mono text-[var(--text-muted)] mb-1">
                        [{idx}]
                      </span>

                      {/* Node box */}
                      <div
                        className="w-16 h-16 rounded-lg flex items-center justify-center text-lg font-bold border-2"
                        style={{
                          backgroundColor:
                            status === "normal"
                              ? "white"
                              : `${getStatusColor(status)}15`,
                          borderColor: getStatusColor(status),
                          color: getStatusColor(status),
                          boxShadow:
                            status !== "normal"
                              ? `0 0 20px ${getStatusColor(status)}40`
                              : "none",
                        }}
                      >
                        {node.value}
                      </div>

                      {/* Pointer (for linked list) */}
                      {structureType === "linked_list" &&
                        idx < nodes.length - 1 && (
                          <div className="absolute right-[-20px] top-1/2 -translate-y-1/2">
                            <svg
                              width="24"
                              height="24"
                              viewBox="0 0 24 24"
                              fill="none"
                            >
                              <path
                                d="M4 12H16M16 12L12 8M16 12L12 16"
                                stroke="var(--primary)"
                                strokeWidth="2"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                              />
                            </svg>
                          </div>
                        )}
                    </div>

                    {/* Arrow for array */}
                    {structureType === "array" && idx < nodes.length - 1 && (
                      <div className="flex items-center">
                        <div
                          className="w-8 h-0.5"
                          style={{
                            backgroundColor:
                              status === "active" || status === "comparing"
                                ? "var(--primary)"
                                : "var(--card-border)",
                          }}
                        />
                      </div>
                    )}
                  </React.Fragment>
                );
              })}
            </div>

            {/* Current pointer indicator */}
            {currentOp && (
              <div
                className="absolute bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded-lg bg-[var(--primary)] text-white text-sm font-bold shadow-lg"
                style={{
                  opacity: interpolate(
                    opProgress,
                    [0, 0.2, 0.8, 1],
                    [0, 1, 1, 0],
                  ),
                }}
              >
                {currentOp.description}
              </div>
            )}
          </div>

          {/* Operation timeline */}
          {operations.length > 0 && (
            <div className="flex items-center space-x-2 px-4">
              {operations.map((op, idx) => (
                <div
                  key={idx}
                  className={`flex-1 h-2 rounded-full ${
                    idx < currentOpIndex
                      ? "bg-[var(--success)]"
                      : idx === currentOpIndex
                        ? "bg-[var(--primary)]"
                        : "bg-slate-200"
                  }`}
                />
              ))}
            </div>
          )}
        </div>

        {/* Right info panel */}
        <div
          className="col-span-4 h-full flex flex-col justify-center"
          style={{
            opacity: infoEntrance,
            transform: `translateX(${getSlideInterpolation(infoEntrance, 0, 1, 25, 0)}px)`,
          }}
        >
          <div className="edu-card space-y-4">
            <h3 className="text-lg font-bold text-[var(--primary)] border-b border-[var(--card-border)] pb-2">
              操作说明
            </h3>

            {/* Current operation details */}
            {currentOp && (
              <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
                <div className="text-xs font-bold text-[var(--primary)] uppercase mb-1">
                  当前操作: {currentOp.type.toUpperCase()}
                </div>
                <p className="text-sm text-[var(--text-main)]">
                  {currentOp.description}
                </p>
              </div>
            )}

            {/* Legend */}
            <div className="space-y-2 text-xs">
              <div className="flex items-center space-x-2">
                <div
                  className="w-4 h-4 rounded border-2"
                  style={{
                    borderColor: "var(--primary)",
                    backgroundColor: "var(--primary)15",
                  }}
                />
                <span className="text-[var(--text-muted)]">当前访问</span>
              </div>
              <div className="flex items-center space-x-2">
                <div
                  className="w-4 h-4 rounded border-2"
                  style={{
                    borderColor: "var(--accent)",
                    backgroundColor: "var(--accent)15",
                  }}
                />
                <span className="text-[var(--text-muted)]">比较中</span>
              </div>
              <div className="flex items-center space-x-2">
                <div
                  className="w-4 h-4 rounded border-2"
                  style={{
                    borderColor: "var(--danger)",
                    backgroundColor: "var(--danger)15",
                  }}
                />
                <span className="text-[var(--text-muted)]">交换中</span>
              </div>
              <div className="flex items-center space-x-2">
                <div
                  className="w-4 h-4 rounded border-2"
                  style={{
                    borderColor: "var(--success)",
                    backgroundColor: "var(--success)15",
                  }}
                />
                <span className="text-[var(--text-muted)]">已排序</span>
              </div>
            </div>

            {/* Complexity info */}
            {(timeComplexity || spaceComplexity) && (
              <div className="pt-2 border-t border-[var(--card-border)]">
                <h4 className="text-xs font-bold text-[var(--text-muted)] uppercase mb-2">
                  复杂度分析
                </h4>
                {timeComplexity && (
                  <p className="text-sm">
                    <span className="font-bold">时间:</span> {timeComplexity}
                  </p>
                )}
                {spaceComplexity && (
                  <p className="text-sm">
                    <span className="font-bold">空间:</span> {spaceComplexity}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <SubtitleBar
        narration={scene.narration}
        durationSeconds={scene.duration_seconds}
        captionWords={scene.caption_words}
      />
    </AbsoluteFill>
  );
};
