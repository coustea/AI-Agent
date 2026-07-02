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
import { useSceneTiming } from "../hooks/useSceneTiming";

interface StackQueueItem {
  value: string | number;
  status?: "normal" | "entering" | "leaving" | "peek";
}

interface StackQueueOperation {
  type: "push" | "pop" | "enqueue" | "dequeue" | "peek";
  value?: string | number;
  description: string;
}

interface StackQueueLabProps {
  scene: RichVideoScene;
  meta: VideoMeta;
  globalStyle: GlobalStyle;
  currentSceneIndex: number;
  totalScenes: number;
}

export const StackQueueLab: React.FC<StackQueueLabProps> = ({
  scene,
  meta,
  globalStyle,
  currentSceneIndex,
  totalScenes,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Extract visual data
  const structureType =
    (scene.visual.structure_type as "stack" | "queue") || "stack";
  const initialItems: StackQueueItem[] =
    (scene.visual.items as StackQueueItem[]) || [];
  const operations: StackQueueOperation[] =
    (scene.visual.operations as StackQueueOperation[]) || [];
  const timing = useSceneTiming(scene);


  // Build dynamic item list based on operations
  const getItemsAtFrame = () => {
    const currentOpIdx = timing.getActiveIndex(operations.length, ["trace_step"]);
    const opProgress = timing.getStepProgress(operations.length, ["trace_step"]);

    const items = [...initialItems];
    for (let i = 0; i <= currentOpIdx; i++) {
      const op = operations[i];
      if (!op) continue;

      if (op.type === "push" && op.value !== undefined) {
        items.push({
          value: op.value,
          status: i === currentOpIdx ? "entering" : "normal",
        });
      } else if (op.type === "pop" && items.length > 0) {
        if (i === currentOpIdx) {
          items[items.length - 1].status = "leaving";
        } else {
          items.pop();
        }
      } else if (op.type === "enqueue" && op.value !== undefined) {
        items.push({
          value: op.value,
          status: i === currentOpIdx ? "entering" : "normal",
        });
      } else if (op.type === "dequeue" && items.length > 0) {
        if (i === currentOpIdx) {
          items[0].status = "leaving";
        } else {
          items.shift();
        }
      } else if (op.type === "peek" && items.length > 0) {
        if (i === currentOpIdx) {
          const peekIdx = structureType === "stack" ? items.length - 1 : 0;
          items[peekIdx].status = "peek";
        }
      }
    }

    return { items, currentOpIdx, opProgress };
  };

  const { items, currentOpIdx, opProgress } = getItemsAtFrame();
  const currentOp = operations[currentOpIdx];

  // Entrance animations
  const containerEntrance = getSpringProgress(frame, fps, 10, 25);
  const infoEntrance = getSpringProgress(frame, fps, 20, 20);

  // Get item animation transform
  const getItemTransform = (idx: number, item: StackQueueItem) => {


    if (item.status === "entering") {
      const enterProgress = spring({
        frame: frame % (durationInFrames / operations.length),
        fps,
        config: { damping: 12, stiffness: 100 },
      });
      const offset = structureType === "stack" ? -150 : 150;
      return structureType === "stack"
        ? `translateY(${interpolate(enterProgress, [0, 1], [offset, 0])}px) scale(${interpolate(enterProgress, [0, 1], [0.8, 1])})`
        : `translateX(${interpolate(enterProgress, [0, 1], [offset, 0])}px) scale(${interpolate(enterProgress, [0, 1], [0.8, 1])})`;
    }

    if (item.status === "leaving") {
      const leaveProgress = spring({
        frame: frame % (durationInFrames / operations.length),
        fps,
        config: { damping: 12, stiffness: 100 },
      });
      const offset = structureType === "stack" ? -150 : -150;
      return structureType === "stack"
        ? `translateY(${interpolate(leaveProgress, [0, 1], [0, offset])}px) scale(${interpolate(leaveProgress, [0, 1], [1, 0.8])})`
        : `translateX(${interpolate(leaveProgress, [0, 1], [0, offset])}px) scale(${interpolate(leaveProgress, [0, 1], [1, 0.8])})`;
    }

    if (item.status === "peek") {
      const pulseScale = 1 + 0.05 * Math.sin(frame * 0.2);
      return `scale(${pulseScale})`;
    }

    return "translateY(0) scale(1)";
  };

  // Get status color
  const getStatusColor = (status: StackQueueItem["status"]) => {
    switch (status) {
      case "entering":
        return "var(--success)";
      case "leaving":
        return "var(--danger)";
      case "peek":
        return "var(--accent)";
      default:
        return "var(--primary)";
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
        {/* Main visualization */}
        <div
          className="col-span-7 flex flex-col items-center justify-center"
          style={{
            opacity: containerEntrance,
            transform: `translateY(${getSlideInterpolation(containerEntrance, 0, 1, 20, 0)}px)`,
          }}
        >
          {/* Title badge */}
          <div className="mb-6 flex items-center space-x-3">
            <span className="px-4 py-1.5 rounded-full text-sm font-bold uppercase tracking-wider bg-[var(--primary)] text-white shadow-lg">
              {structureType === "stack"
                ? "栈 Stack (LIFO)"
                : "队列 Queue (FIFO)"}
            </span>
          </div>

          {/* Stack/Queue container */}
          <div className="relative">
            {/* Container frame */}
            <div
              className="relative border-4 border-[var(--primary)] rounded-2xl overflow-hidden"
              style={{
                width: structureType === "stack" ? 200 : 500,
                minHeight: 350,
                backgroundColor: "rgba(255,255,255,0.9)",
              }}
            >
              {/* TOP/FRONT indicator */}
              <div
                className="absolute text-xs font-bold text-[var(--primary)] bg-blue-100 px-2 py-1 rounded"
                style={{
                  top: structureType === "stack" ? 10 : "50%",
                  right: structureType === "stack" ? -50 : "auto",
                  left: structureType === "stack" ? "auto" : 10,
                  transform:
                    structureType === "stack" ? "none" : "translateY(-50%)",
                }}
              >
                {structureType === "stack" ? "← TOP" : "FRONT →"}
              </div>

              {/* BOTTOM/REAR indicator */}
              <div
                className="absolute text-xs font-bold text-[var(--text-muted)] bg-slate-100 px-2 py-1 rounded"
                style={{
                  bottom: structureType === "stack" ? 10 : "50%",
                  left: structureType === "stack" ? "auto" : 10,
                  right: structureType === "stack" ? -60 : "auto",
                  transform:
                    structureType === "stack" ? "none" : "translateY(-50%)",
                }}
              >
                {structureType === "stack" ? "← BOTTOM" : "← REAR"}
              </div>

              {/* Items */}
              <div
                className={`p-4 ${structureType === "stack" ? "flex flex-col-reverse items-center gap-2 h-full" : "flex items-center gap-2 h-full"}`}
                style={{ minHeight: 300 }}
              >
                {items.map((item, idx) => {
                  const itemEntrance = getSpringProgress(
                    frame,
                    fps,
                    15 + idx * 5,
                    15,
                  );
                  const transform = getItemTransform(idx, item);
                  const statusColor = getStatusColor(item.status);

                  return (
                    <div
                      key={`${item.value}-${idx}`}
                      className="flex items-center justify-center font-bold text-lg rounded-lg border-2"
                      style={{
                        width: structureType === "stack" ? 160 : 80,
                        height: 60,
                        opacity:
                          item.status === "leaving"
                            ? interpolate(opProgress, [0, 0.5, 1], [1, 0.5, 0])
                            : itemEntrance,
                        transform,
                        backgroundColor: item.status
                          ? `${statusColor}15`
                          : "white",
                        borderColor: statusColor,
                        color: statusColor,
                        boxShadow: item.status
                          ? `0 0 15px ${statusColor}40`
                          : "none",
                      }}
                    >
                      {item.value}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Operation arrows */}
            {structureType === "stack" && (
              <>
                <div className="absolute -right-20 top-10 flex flex-col items-center text-[var(--success)]">
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M12 4L12 20M12 4L6 10M12 4L18 10"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <span className="text-xs font-bold">PUSH</span>
                </div>
                <div className="absolute -right-20 top-24 flex flex-col items-center text-[var(--danger)]">
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M12 20L12 4M12 20L6 14M12 20L18 14"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <span className="text-xs font-bold">POP</span>
                </div>
              </>
            )}

            {structureType === "queue" && (
              <>
                <div className="absolute -left-20 top-1/2 -translate-y-1/2 flex flex-col items-center text-[var(--success)]">
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M4 12L20 12M4 12L10 6M4 12L10 18"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <span className="text-xs font-bold">ENQ</span>
                </div>
                <div className="absolute -right-20 top-1/2 -translate-y-1/2 flex flex-col items-center text-[var(--danger)]">
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M20 12L4 12M20 12L14 6M20 12L14 18"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <span className="text-xs font-bold">DEQ</span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Info panel */}
        <div
          className="col-span-5 h-full flex flex-col justify-center"
          style={{
            opacity: infoEntrance,
            transform: `translateX(${getSlideInterpolation(infoEntrance, 0, 1, 25, 0)}px)`,
          }}
        >
          <div className="edu-card space-y-4">
            <h3 className="text-lg font-bold text-[var(--primary)] border-b border-[var(--card-border)] pb-2">
              操作说明
            </h3>

            {/* Current operation */}
            {currentOp && (
              <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
                <div className="text-xs font-bold text-[var(--primary)] uppercase mb-1">
                  当前操作
                </div>
                <p className="text-sm text-[var(--text-main)] font-medium">
                  {currentOp.description}
                </p>
                {currentOp.value !== undefined && (
                  <div className="mt-2 text-sm">
                    <span className="font-bold">值:</span>{" "}
                    <span className="px-2 py-0.5 bg-[var(--primary)] text-white rounded font-mono">
                      {currentOp.value}
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Properties */}
            <div className="space-y-2 text-sm">
              <h4 className="font-bold text-[var(--text-muted)] uppercase text-xs">
                特性
              </h4>
              {structureType === "stack" ? (
                <>
                  <p>
                    • <span className="font-bold">LIFO</span> (后进先出)
                  </p>
                  <p>• 只能在栈顶操作</p>
                  <p>• PUSH/POP 时间复杂度: O(1)</p>
                </>
              ) : (
                <>
                  <p>
                    • <span className="font-bold">FIFO</span> (先进先出)
                  </p>
                  <p>• 队头出，队尾入</p>
                  <p>• ENQUEUE/DEQUEUE 时间复杂度: O(1)</p>
                </>
              )}
            </div>

            {/* Legend */}
            <div className="pt-2 border-t border-[var(--card-border)]">
              <h4 className="text-xs font-bold text-[var(--text-muted)] uppercase mb-2">
                图例
              </h4>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="flex items-center space-x-2">
                  <div
                    className="w-4 h-4 rounded border-2"
                    style={{
                      borderColor: "var(--success)",
                      backgroundColor: "var(--success)15",
                    }}
                  />
                  <span>入栈/入队</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div
                    className="w-4 h-4 rounded border-2"
                    style={{
                      borderColor: "var(--danger)",
                      backgroundColor: "var(--danger)15",
                    }}
                  />
                  <span>出栈/出队</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div
                    className="w-4 h-4 rounded border-2"
                    style={{
                      borderColor: "var(--accent)",
                      backgroundColor: "var(--accent)15",
                    }}
                  />
                  <span>查看栈顶</span>
                </div>
              </div>
            </div>
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
