import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  spring,
} from "remotion";
import { RichVideoScene, GlobalStyle, VideoMeta } from "../schema/types";
import { EduBackground } from "../components/EduBackground";
import { SceneHeader } from "../components/SceneHeader";
import { SubtitleBar } from "../components/SubtitleBar";
import { getSpringProgress, getSlideInterpolation } from "../utils/animation";

interface StorageLevel {
  name: string;
  label: string;
  capacity: string;
  access_time: string;
  cost_per_gb: string;
  level: number;
}

interface DataTransfer {
  from: string;
  to: string;
  data_size: string;
  description: string;
}

interface StorageHierarchyProps {
  scene: RichVideoScene;
  meta: VideoMeta;
  globalStyle: GlobalStyle;
  currentSceneIndex: number;
  totalScenes: number;
}

export const StorageHierarchy: React.FC<StorageHierarchyProps> = ({
  scene,
  meta,
  globalStyle,
  currentSceneIndex,
  totalScenes,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Extract visual data
  const levels: StorageLevel[] = (scene.visual.levels as StorageLevel[]) || [
    {
      name: "register",
      label: "寄存器",
      capacity: "几KB",
      access_time: "<1ns",
      cost_per_gb: "极高",
      level: 0,
    },
    {
      name: "l1",
      label: "L1 Cache",
      capacity: "32-64KB",
      access_time: "1-2ns",
      cost_per_gb: "很高",
      level: 1,
    },
    {
      name: "l2",
      label: "L2 Cache",
      capacity: "256KB-1MB",
      access_time: "3-5ns",
      cost_per_gb: "高",
      level: 2,
    },
    {
      name: "l3",
      label: "L3 Cache",
      capacity: "4-32MB",
      access_time: "10-20ns",
      cost_per_gb: "中高",
      level: 3,
    },
    {
      name: "ram",
      label: "主存 RAM",
      capacity: "4-64GB",
      access_time: "50-100ns",
      cost_per_gb: "中",
      level: 4,
    },
    {
      name: "ssd",
      label: "SSD",
      capacity: "256GB-2TB",
      access_time: "25-100μs",
      cost_per_gb: "低",
      level: 5,
    },
    {
      name: "hdd",
      label: "HDD",
      capacity: "1-20TB",
      access_time: "5-10ms",
      cost_per_gb: "极低",
      level: 6,
    },
  ];

  const transfers: DataTransfer[] =
    (scene.visual.transfers as DataTransfer[]) || [];
  const highlightLevel = (scene.visual.highlight_level as string) || "";

  // Calculate current transfer
  const transferDuration = durationInFrames / Math.max(transfers.length, 1);
  const currentTransferIdx = Math.min(
    Math.floor(frame / transferDuration),
    transfers.length - 1,
  );
  const currentTransfer = transfers[currentTransferIdx];

  // Entrance animations
  const pyramidEntrance = getSpringProgress(frame, fps, 10, 30);
  const infoEntrance = getSpringProgress(frame, fps, 30, 25);

  // Get level position (pyramid layout)
  const getLevelPosition = (level: number) => {
    const baseY = 60;
    const yStep = 55;
    const centerX = 350;
    const baseWidth = 120;
    const widthGrowth = 50;

    const width = baseWidth + level * widthGrowth;
    const y = baseY + level * yStep;
    const x = centerX - width / 2;

    return { x, y, width, height: 45 };
  };

  // Get level color based on speed
  const getLevelColor = (level: number) => {
    const colors = [
      "var(--danger)",
      "var(--accent)",
      "var(--primary)",
      "var(--primary)",
      "var(--success)",
      "#6b7280",
      "#9ca3af",
    ];
    return colors[level] || "var(--text-main)";
  };

  // Check if level is involved in current transfer
  const isLevelActive = (name: string) => {
    if (!currentTransfer) return false;
    return currentTransfer.from === name || currentTransfer.to === name;
  };

  // Render transfer arrow animation
  const renderTransferArrow = () => {
    if (!currentTransfer) return null;

    const fromLevel = levels.find((l) => l.name === currentTransfer.from);
    const toLevel = levels.find((l) => l.name === currentTransfer.to);
    if (!fromLevel || !toLevel) return null;

    const fromPos = getLevelPosition(fromLevel.level);
    const toPos = getLevelPosition(toLevel.level);

    const fromY = fromPos.y + fromPos.height / 2;
    const toY = toPos.y + toPos.height / 2;
    const arrowX = 600;

    const arrowProgress = spring({
      frame: frame % transferDuration,
      fps,
      config: { damping: 12, stiffness: 80 },
    });

    const midY = fromY + (toY - fromY) * arrowProgress;

    return (
      <g>
        {/* Vertical line */}
        <line
          x1={arrowX}
          y1={fromY}
          x2={arrowX}
          y2={toY}
          stroke="var(--primary)"
          strokeWidth={3}
          strokeDasharray="8 4"
          opacity={0.5}
        />

        {/* Animated dot */}
        <circle
          cx={arrowX}
          cy={midY}
          r={8}
          fill="var(--primary)"
          style={{
            filter: "drop-shadow(0 0 10px var(--primary))",
          }}
        />

        {/* Data size label */}
        <text
          x={arrowX + 20}
          y={midY}
          fill="var(--primary)"
          fontSize="12"
          fontWeight="bold"
          dominantBaseline="middle"
          style={{ opacity: arrowProgress }}
        >
          {currentTransfer.data_size}
        </text>

        {/* Direction indicator */}
        <text
          x={arrowX - 15}
          y={midY}
          fill="var(--text-main)"
          fontSize="16"
          dominantBaseline="middle"
          style={{ opacity: arrowProgress }}
        >
          {fromLevel.level < toLevel.level ? "↓" : "↑"}
        </text>
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
        {/* Pyramid visualization */}
        <div
          className="col-span-7 flex flex-col items-center justify-center"
          style={{
            opacity: pyramidEntrance,
            transform: `scale(${getSlideInterpolation(pyramidEntrance, 0, 1, 0.95, 1)})`,
          }}
        >
          {/* Title */}
          <div className="mb-4">
            <span className="px-4 py-1.5 rounded-full text-sm font-bold uppercase tracking-wider bg-[var(--primary)] text-white shadow-lg">
              存储器层次结构
            </span>
          </div>

          {/* SVG pyramid */}
          <svg width="700" height="420" viewBox="0 0 700 420">
            {/* Speed arrow on left */}
            <defs>
              <marker
                id="speed-arrow"
                markerWidth="10"
                markerHeight="7"
                refX="9"
                refY="3.5"
                orient="auto"
              >
                <polygon points="0 0, 10 3.5, 0 7" fill="var(--success)" />
              </marker>
            </defs>

            <g transform="translate(30, 60)">
              <line
                x1="0"
                y1="350"
                x2="0"
                y2="0"
                stroke="var(--success)"
                strokeWidth={2}
                markerEnd="url(#speed-arrow)"
              />
              <text
                x="-15"
                y="175"
                fill="var(--success)"
                fontSize="12"
                fontWeight="bold"
                textAnchor="middle"
                transform="rotate(-90, -15, 175)"
              >
                速度 ↑
              </text>
            </g>

            {/* Capacity arrow on right */}
            <g transform="translate(670, 60)">
              <line
                x1="0"
                y1="0"
                x2="0"
                y2="350"
                stroke="var(--text-muted)"
                strokeWidth={2}
              />
              <text
                x="15"
                y="175"
                fill="var(--text-muted)"
                fontSize="12"
                fontWeight="bold"
                textAnchor="middle"
                transform="rotate(90, 15, 175)"
              >
                容量 ↑
              </text>
            </g>

            {/* Render storage levels */}
            {levels.map((level, idx) => {
              const pos = getLevelPosition(level.level);
              const isActive = isLevelActive(level.name);
              const isHighlighted = highlightLevel === level.name;
              const levelEntrance = getSpringProgress(
                frame,
                fps,
                15 + idx * 5,
                15,
              );
              const color = getLevelColor(level.level);

              return (
                <g key={level.name}>
                  {/* Storage block */}
                  <rect
                    x={pos.x}
                    y={pos.y}
                    width={pos.width}
                    height={pos.height}
                    rx={8}
                    fill={isActive || isHighlighted ? `${color}20` : "white"}
                    stroke={color}
                    strokeWidth={isActive ? 3 : 2}
                    style={{
                      opacity: levelEntrance,
                      filter:
                        isActive || isHighlighted
                          ? `drop-shadow(0 0 10px ${color})`
                          : "none",
                    }}
                  />

                  {/* Level label */}
                  <text
                    x={pos.x + pos.width / 2}
                    y={pos.y + 18}
                    textAnchor="middle"
                    fill={color}
                    fontSize="14"
                    fontWeight="bold"
                    style={{ opacity: levelEntrance }}
                  >
                    {level.label}
                  </text>

                  {/* Access time */}
                  <text
                    x={pos.x + pos.width / 2}
                    y={pos.y + 35}
                    textAnchor="middle"
                    fill="var(--text-muted)"
                    fontSize="10"
                    fontFamily="monospace"
                    style={{ opacity: levelEntrance }}
                  >
                    {level.access_time}
                  </text>

                  {/* Capacity on right side */}
                  <text
                    x={pos.x + pos.width + 10}
                    y={pos.y + pos.height / 2}
                    fill="var(--text-muted)"
                    fontSize="10"
                    dominantBaseline="middle"
                    style={{ opacity: levelEntrance * 0.8 }}
                  >
                    {level.capacity}
                  </text>
                </g>
              );
            })}

            {/* Transfer animation */}
            {renderTransferArrow()}
          </svg>
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
              层次结构原理
            </h3>

            {/* Principle explanation */}
            <div className="space-y-2 text-sm">
              <p>
                • <span className="font-bold">局部性原理</span>:
                程序倾向于访问近期访问过的数据
              </p>
              <p>
                • <span className="font-bold">时间局部性</span>:
                刚访问的数据可能很快再次访问
              </p>
              <p>
                • <span className="font-bold">空间局部性</span>:
                访问位置附近的数据可能被访问
              </p>
            </div>

            {/* Current transfer */}
            {currentTransfer && (
              <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
                <div className="text-xs font-bold text-[var(--primary)] uppercase mb-1">
                  数据传输
                </div>
                <div className="flex items-center space-x-2 mb-2">
                  <span className="px-2 py-0.5 rounded text-xs font-bold bg-[var(--primary)] text-white">
                    {levels.find((l) => l.name === currentTransfer.from)?.label}
                  </span>
                  <span className="text-[var(--text-muted)]">→</span>
                  <span className="px-2 py-0.5 rounded text-xs font-bold bg-[var(--success)] text-white">
                    {levels.find((l) => l.name === currentTransfer.to)?.label}
                  </span>
                </div>
                <p className="text-sm text-[var(--text-main)]">
                  {currentTransfer.description}
                </p>
                <div className="mt-1 text-xs text-[var(--text-muted)]">
                  数据量: {currentTransfer.data_size}
                </div>
              </div>
            )}

            {/* Cost comparison */}
            <div className="pt-2 border-t border-[var(--card-border)]">
              <h4 className="text-xs font-bold text-[var(--text-muted)] uppercase mb-2">
                成本对比
              </h4>
              <div className="space-y-1 text-xs">
                {levels.slice(0, 4).map((level) => (
                  <div key={level.name} className="flex justify-between">
                    <span>{level.label}</span>
                    <span className="font-mono text-[var(--text-muted)]">
                      {level.cost_per_gb}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Legend */}
            <div className="pt-2 border-t border-[var(--card-border)]">
              <h4 className="text-xs font-bold text-[var(--text-muted)] uppercase mb-2">
                图例
              </h4>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="flex items-center space-x-2">
                  <div
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: "var(--danger)" }}
                  />
                  <span>最快/最贵</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: "#9ca3af" }}
                  />
                  <span>最慢/最便宜</span>
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
