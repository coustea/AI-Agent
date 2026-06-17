import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { RichVideoScene, GlobalStyle, VideoMeta } from '../schema/types';
import { EduBackground } from '../components/EduBackground';
import { SceneHeader } from '../components/SceneHeader';
import { SubtitleBar } from '../components/SubtitleBar';
import { InfoPanel } from '../components/InfoPanel';
import { DiagramNode } from '../components/DiagramNode';
import { AnimatedArrow } from '../components/AnimatedArrow';
import { getSpringProgress, getSlideInterpolation } from '../utils/animation';

interface StateMachineLabProps {
  scene: RichVideoScene;
  meta: VideoMeta;
  globalStyle: GlobalStyle;
  currentSceneIndex: number;
  totalScenes: number;
}

export const StateMachineLab: React.FC<StateMachineLabProps> = ({
  scene,
  meta,
  globalStyle,
  currentSceneIndex,
  totalScenes,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Extract variables
  const machineName = (scene.visual.machine_name as string) || '';
  const initialState = (scene.visual.initial_state as string) || '';
  const states = (scene.visual.states as { id: string; label: string; description: string }[]) || [];
  const transitions = (scene.visual.transitions as { from: string; to: string; label: string }[]) || [];
  const eventSequence = (scene.visual.event_sequence as { time: number; event: string; active_state: string }[]) || [];
  const explanationMap = (scene.visual.explanation_map as Record<string, string>) || {};

  // Compute active state and event based on timeline seconds
  const currentTime = frame / fps;
  let activeStateId = initialState;
  let currentEvent = '系统就绪 (System Ready)';

  eventSequence.forEach((ev) => {
    if (currentTime >= ev.time) {
      activeStateId = ev.active_state;
      currentEvent = ev.event;
    }
  });

  const activeState = states.find(s => s.id === activeStateId);
  const activeStateExplanation = explanationMap[activeStateId] || activeState?.description || '';

  // Circular coordinate mapping helper for visual layout
  // Center is relative to the graphical container area which is roughly 650x360
  const getCoordinates = (index: number, total: number) => {
    const angle = (index * 2 * Math.PI) / (total || 1) - Math.PI / 2;
    const r = 130; // radius
    const cx = 280; // center X
    const cy = 180; // center Y
    return {
      x: cx + Math.cos(angle) * r,
      y: cy + Math.sin(angle) * r,
    };
  };

  // Pre-calculate positions
  const statePositions = new Map<string, { x: number; y: number }>();
  states.forEach((s, idx) => {
    const coords = getCoordinates(idx, states.length);
    statePositions.set(s.id, { x: coords.x, y: coords.y });
  });

  const entrance = getSpringProgress(frame, fps, 5, 25);
  const sideEntrance = getSpringProgress(frame, fps, 15, 25);

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

      <div className="scene-layout-grid w-full h-[calc(100%-40px)] z-10">
        {/* Left: Interactive State Machine layout */}
        <div 
          className="flex flex-col space-y-6 h-full justify-center"
          style={{
            opacity: entrance,
            transform: `translateY(${getSlideInterpolation(entrance, 0, 1, 30, 0)}px)`,
          }}
        >
          <div className="edu-card flex flex-col space-y-4 h-[460px]">
            <div className="flex justify-between items-center border-b border-[var(--card-border)] pb-2">
              <h3 className="text-lg font-bold text-[var(--text-main)]">
                状态图: {machineName}
              </h3>
              <div className="flex items-center space-x-2">
                <span className="text-xs text-[var(--text-muted)] font-bold">触发事件:</span>
                <span className="badge-primary px-3 py-1 rounded-full text-xs font-bold font-mono shadow-sm">
                  {currentEvent}
                </span>
              </div>
            </div>

            {/* Graphical Area */}
            <div className="relative flex-1 bg-slate-50/40 rounded-xl overflow-visible">
              
              {/* Render Transition Arrows */}
              {transitions.map((t, idx) => {
                const start = statePositions.get(t.from);
                const end = statePositions.get(t.to);
                if (!start || !end) return null;

                const dx = end.x - start.x;
                const dy = end.y - start.y;
                const len = Math.sqrt(dx * dx + dy * dy);
                const offset = 40; // offset from center of nodes (to touch perimeter of 80px circles)

                const ax1 = start.x + (dx / len) * offset;
                const ay1 = start.y + (dy / len) * offset;
                const ax2 = end.x - (dx / len) * offset;
                const ay2 = end.y - (dy / len) * offset;

                // Transition is active if start is the active state and time matches event state changes
                const isTransitionActive = activeStateId === t.to && eventSequence.some(
                  ev => currentTime >= ev.time && ev.active_state === t.to && currentTime - ev.time < 1.2
                );

                return (
                  <AnimatedArrow
                    key={idx}
                    startX={ax1}
                    startY={ay1}
                    endX={ax2}
                    endY={ay2}
                    label={t.label}
                    isActive={isTransitionActive}
                  />
                );
              })}

              {/* Render Nodes with entrance staggered spring */}
              {states.map((s, idx) => {
                const pos = statePositions.get(s.id);
                if (!pos) return null;

                const isActive = s.id === activeStateId;
                const itemSpring = getSpringProgress(frame, fps, 20 + idx * 8, 25);

                return (
                  <div
                    key={s.id}
                    className="absolute"
                    style={{
                      left: pos.x,
                      top: pos.y,
                      transform: `translate(-50%, -50%) scale(${getSlideInterpolation(
                        itemSpring,
                        0,
                        1,
                        0.7,
                        isActive ? 1.08 : 1.0
                      )})`,
                      opacity: itemSpring,
                    }}
                  >
                    <DiagramNode
                      id={s.id}
                      label={s.label}
                      shape="circle"
                      status={isActive ? 'active' : 'normal'}
                      className={`w-20 h-20 text-xs font-extrabold flex items-center justify-center border-2 shadow-md transition-all duration-300 ${
                        isActive ? 'ring-4 ring-[var(--primary)]/20 glow-primary border-[var(--primary)]' : ''
                      }`}
                    />
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right sideboard detail pane */}
        <div
          className="h-full flex flex-col justify-center"
          style={{
            opacity: sideEntrance,
            transform: `translateX(${getSlideInterpolation(sideEntrance, 0, 1, 30, 0)}px)`,
          }}
        >
          <InfoPanel
            title="状态模型分析"
            explanation={activeStateExplanation}
            points={states.map(s => `${s.label}: ${s.description}`)}
          />
        </div>
      </div>

      <SubtitleBar narration={scene.narration} durationSeconds={scene.duration_seconds} />
    </AbsoluteFill>
  );
};
