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

interface ProcessState {
  name: string;
  label: string;
  description: string;
}

interface ProcessTransition {
  from: string;
  to: string;
  trigger: string;
  description: string;
}

interface ProcessStateTransitionProps {
  scene: RichVideoScene;
  meta: VideoMeta;
  globalStyle: GlobalStyle;
  currentSceneIndex: number;
  totalScenes: number;
}

export const ProcessStateTransition: React.FC<ProcessStateTransitionProps> = ({
  scene,
  meta,
  globalStyle,
  currentSceneIndex,
  totalScenes,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Extract visual data
  const states: ProcessState[] = (scene.visual.states as ProcessState[]) || [
    { name: "new", label: "新建", description: "进程刚创建" },
    { name: "ready", label: "就绪", description: "等待CPU调度" },
    { name: "running", label: "运行", description: "正在执行" },
    { name: "blocked", label: "阻塞", description: "等待I/O或事件" },
    { name: "terminated", label: "终止", description: "执行完毕" },
  ];

  const transitions: ProcessTransition[] =
    (scene.visual.transitions as ProcessTransition[]) || [];

  // Calculate current transition
  const transitionDuration = durationInFrames / Math.max(transitions.length, 1);
  const currentTransitionIdx = Math.min(
    Math.floor(frame / transitionDuration),
    transitions.length - 1,
  );
  const currentTransition = transitions[currentTransitionIdx];

  // Entrance animations
  const diagramEntrance = getSpringProgress(frame, fps, 10, 25);
  const infoEntrance = getSpringProgress(frame, fps, 25, 20);

  // State positions (layout for OS process states)
  const getStatePosition = (name: string) => {
    const positions: Record<string, { x: number; y: number }> = {
      new: { x: 150, y: 80 },
      ready: { x: 350, y: 80 },
      running: { x: 550, y: 200 },
      blocked: { x: 350, y: 320 },
      terminated: { x: 550, y: 320 },
    };
    return positions[name] || { x: 350, y: 200 };
  };

  // Check if state is active in current transition
  const isStateActive = (stateName: string) => {
    if (!currentTransition) return false;
    return (
      currentTransition.from === stateName || currentTransition.to === stateName
    );
  };

  // Check if transition is the current one
  const isTransitionActive = (t: ProcessTransition) => {
    return currentTransition?.from === t.from && currentTransition.to === t.to;
  };

  // Get state color
  const getStateColor = (stateName: string) => {
    if (currentTransition?.to === stateName) return "var(--success)";
    if (currentTransition?.from === stateName) return "var(--primary)";
    return "var(--text-muted)";
  };

  const renderTransitionArrow = (t: ProcessTransition) => {
    const fromPos = getStatePosition(t.from);
    const toPos = getStatePosition(t.to);
    const isActive = isTransitionActive(t);

    // Calculate arrow path
    const dx = toPos.x - fromPos.x;
    const dy = toPos.y - fromPos.y;
    const length = Math.sqrt(dx * dx + dy * dy);
    const nx = dx / length;
    const ny = dy / length;

    // Offset for start/end points (node radius ~50)
    const startX = fromPos.x + nx * 60;
    const startY = fromPos.y + ny * 60;
    const endX = toPos.x - nx * 60;
    const endY = toPos.y - ny * 60;

    // Arrow progress animation
    const arrowProgress = isActive
      ? spring({
          frame: frame % transitionDuration,
          fps,
          config: { damping: 12, stiffness: 80 },
        })
      : 0;

    const arrowLength = interpolate(arrowProgress, [0, 1], [0, length - 120]);

    return (
      <g key={`${t.from}-${t.to}`}>
        {/* Base line (dimmed) */}
        <line
          x1={startX}
          y1={startY}
          x2={endX}
          y2={endY}
          stroke={isActive ? "var(--primary)" : "var(--card-border)"}
          strokeWidth={isActive ? 3 : 2}
          strokeDasharray={isActive ? "none" : "5 5"}
          opacity={isActive ? 1 : 0.4}
        />

        {/* Animated arrow head */}
        {isActive && arrowProgress > 0.1 && (
          <>
            <line
              x1={startX}
              y1={startY}
              x2={startX + nx * arrowLength}
              y2={startY + ny * arrowLength}
              stroke="var(--primary)"
              strokeWidth={4}
              markerEnd="url(#arrowhead)"
            />
            {/* Moving dot */}
            <circle
              cx={startX + nx * arrowLength}
              cy={startY + ny * arrowLength}
              r={6}
              fill="var(--primary)"
              style={{
                filter: "drop-shadow(0 0 8px var(--primary))",
              }}
            />
          </>
        )}

        {/* Trigger label */}
        {isActive && (
          <text
            x={(startX + endX) / 2}
            y={(startY + endY) / 2 - 10}
            fill="var(--primary)"
            fontSize="12"
            fontWeight="bold"
            textAnchor="middle"
            style={{
              opacity: arrowProgress,
            }}
          >
            {t.trigger}
          </text>
        )}
      </g>
    );
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
        {/* State diagram */}
        <div
          className="col-span-8 flex flex-col items-center justify-center"
          style={{
            opacity: diagramEntrance,
            transform: `scale(${getSlideInterpolation(diagramEntrance, 0, 1, 0.95, 1)})`,
          }}
        >
          {/* Title */}
          <div className="mb-4">
            <span className="px-4 py-1.5 rounded-full text-sm font-bold uppercase tracking-wider bg-[var(--primary)] text-white shadow-lg">
              进程状态转换图
            </span>
          </div>

          {/* SVG diagram */}
          <svg width="700" height="400" viewBox="0 0 700 400">
            {/* Arrow marker definition */}
            <defs>
              <marker
                id="arrowhead"
                markerWidth="10"
                markerHeight="7"
                refX="9"
                refY="3.5"
                orient="auto"
              >
                <polygon points="0 0, 10 3.5, 0 7" fill="var(--primary)" />
              </marker>
            </defs>

            {/* Render all transitions */}
            {transitions.map((t) => renderTransitionArrow(t))}

            {/* Render states */}
            {states.map((state, idx) => {
              const pos = getStatePosition(state.name);
              const isActive = isStateActive(state.name);
              const stateEntrance = getSpringProgress(
                frame,
                fps,
                15 + idx * 5,
                15,
              );
              const color = getStateColor(state.name);

              return (
                <g key={state.name}>
                  {/* State circle */}
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={50}
                    fill={isActive ? `${color}20` : "white"}
                    stroke={color}
                    strokeWidth={isActive ? 4 : 2}
                    style={{
                      opacity: stateEntrance,
                      filter: isActive
                        ? `drop-shadow(0 0 15px ${color})`
                        : "none",
                    }}
                  />

                  {/* State label */}
                  <text
                    x={pos.x}
                    y={pos.y - 5}
                    textAnchor="middle"
                    fill={color}
                    fontSize="16"
                    fontWeight="bold"
                    style={{ opacity: stateEntrance }}
                  >
                    {state.label}
                  </text>

                  {/* State name (English) */}
                  <text
                    x={pos.x}
                    y={pos.y + 15}
                    textAnchor="middle"
                    fill={color}
                    fontSize="11"
                    fontFamily="monospace"
                    style={{ opacity: stateEntrance }}
                  >
                    {state.name.toUpperCase()}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Info panel */}
        <div
          className="col-span-4 h-full flex flex-col justify-center"
          style={{
            opacity: infoEntrance,
            transform: `translateX(${getSlideInterpolation(infoEntrance, 0, 1, 25, 0)}px)`,
          }}
        >
          <div className="edu-card space-y-4">
            <h3 className="text-lg font-bold text-[var(--primary)] border-b border-[var(--card-border)] pb-2">
              状态转换说明
            </h3>

            {/* Current transition */}
            {currentTransition && (
              <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="px-2 py-0.5 rounded text-xs font-bold bg-[var(--primary)] text-white">
                    {
                      states.find((s) => s.name === currentTransition.from)
                        ?.label
                    }
                  </span>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M5 12H19M19 12L15 8M19 12L15 16"
                      stroke="var(--primary)"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <span className="px-2 py-0.5 rounded text-xs font-bold bg-[var(--success)] text-white">
                    {states.find((s) => s.name === currentTransition.to)?.label}
                  </span>
                </div>
                <p className="text-sm text-[var(--text-main)] font-medium">
                  {currentTransition.description}
                </p>
                <div className="mt-2 text-xs text-[var(--text-muted)]">
                  触发条件:{" "}
                  <span className="font-bold text-[var(--primary)]">
                    {currentTransition.trigger}
                  </span>
                </div>
              </div>
            )}

            {/* All transitions list */}
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-[var(--text-muted)] uppercase">
                所有转换
              </h4>
              {transitions.map((t, idx) => (
                <div
                  key={idx}
                  className={`flex items-center space-x-2 text-xs p-2 rounded ${
                    isTransitionActive(t)
                      ? "bg-blue-50 border border-blue-200"
                      : ""
                  }`}
                >
                  <span
                    className={`w-4 h-4 rounded-full ${idx < currentTransitionIdx ? "bg-[var(--success)]" : idx === currentTransitionIdx ? "bg-[var(--primary)]" : "bg-slate-200"}`}
                  />
                  <span className="font-medium">
                    {states.find((s) => s.name === t.from)?.label} →{" "}
                    {states.find((s) => s.name === t.to)?.label}
                  </span>
                  <span className="text-[var(--text-muted)]">
                    ({t.trigger})
                  </span>
                </div>
              ))}
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
