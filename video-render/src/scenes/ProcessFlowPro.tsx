import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { RichVideoScene, GlobalStyle, VideoMeta } from '../schema/types';
import { EduBackground } from '../components/EduBackground';
import { SceneHeader } from '../components/SceneHeader';
import { SubtitleBar } from '../components/SubtitleBar';
import { InfoPanel } from '../components/InfoPanel';
import { DiagramNode } from '../components/DiagramNode';
import { getSpringProgress, getSlideInterpolation } from '../utils/animation';

interface ProcessFlowProProps {
  scene: RichVideoScene;
  meta: VideoMeta;
  globalStyle: GlobalStyle;
  currentSceneIndex: number;
  totalScenes: number;
}

export const ProcessFlowPro: React.FC<ProcessFlowProProps> = ({
  scene,
  meta,
  globalStyle,
  currentSceneIndex,
  totalScenes,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Extract variables
  const processName = (scene.visual.process_name as string) || '';
  const inputs = (scene.visual.inputs as string[]) || [];
  const outputs = (scene.visual.outputs as string[]) || [];
  const steps = (scene.visual.steps as { id: string; label: string; description: string; icon?: string }[]) || [];
  const failurePoints = (scene.visual.failure_points as { step_id: string; reason: string }[]) || [];

  // Determine active step based on timeline progress
  const stepDuration = durationInFrames / (steps.length || 1);
  const activeIdx = Math.min(Math.floor(frame / stepDuration), steps.length - 1);
  const activeStep = steps[activeIdx];

  // Visual failure point for the active step (if any)
  const activeFailure = failurePoints.find(fp => fp.step_id === activeStep?.id);

  // Transitions
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
        {/* Left: Step sequence rendering */}
        <div 
          className="flex flex-col space-y-8 h-full justify-center"
          style={{
            opacity: entrance,
            transform: `translateY(${getSlideInterpolation(entrance, 0, 1, 30, 0)}px)`,
          }}
        >
          <div className="edu-card flex flex-col space-y-4">
            <h3 className="text-lg font-bold text-[var(--text-main)] flex items-center justify-between">
              <span>流程图: {processName}</span>
              <span className="text-xs font-mono font-bold text-[var(--primary)] uppercase bg-blue-50 px-2 py-0.5 rounded">
                当前步骤: Step {activeIdx + 1}
              </span>
            </h3>

            {/* Horizontal flow line of nodes - responsive layout */}
            <div className="relative flex justify-between items-center py-8 px-4 h-48 bg-slate-50/50 rounded-xl">
              {steps.map((step, idx) => {
                const isActive = idx === activeIdx;
                const isPassed = idx < activeIdx;
                const status = isActive ? 'active' : isPassed ? 'success' : 'normal';

                const itemSpring = getSpringProgress(frame, fps, 20 + idx * 8, 25);

                return (
                  <div 
                    key={step.id} 
                    className="flex-1 flex items-center justify-center relative"
                    style={{
                      opacity: itemSpring,
                      transform: `scale(${getSlideInterpolation(itemSpring, 0, 1, 0.8, 1)})`,
                    }}
                  >
                    {/* Node block */}
                    <div className="relative z-10">
                      <DiagramNode
                        id={step.id}
                        label={step.label}
                        status={status}
                        className={`w-32 py-4 h-20 text-xs shadow-md transition-all duration-300 ${
                          isActive ? 'scale-105 border-[var(--primary)] ring-2 ring-[var(--primary)]/20' : ''
                        }`}
                      />
                    </div>

                    {/* Connecting arrow if not the last node */}
                    {idx < steps.length - 1 && (
                      <div className="absolute left-[calc(50%+64px)] w-[calc(100%-128px)] h-0.5 bg-slate-300 z-0">
                        {/* Animated travel dot representing data flow */}
                        {(isActive || isPassed) && (
                          <div 
                            className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-[var(--primary)] shadow-sm shadow-[var(--primary)]/50"
                            style={{
                              left: isPassed ? '100%' : `${(frame % Math.round(stepDuration)) / stepDuration * 100}%`,
                              transition: 'left 0.1s linear',
                            }}
                          />
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Step Description */}
            {activeStep && (
              <div 
                className="p-4 rounded-xl border border-blue-100 bg-blue-50/50 transition-all duration-300"
                style={{
                  transform: `translateY(${getSlideInterpolation(frame % stepDuration, 0, 8, 10, 0)}px)`,
                  opacity: getSlideInterpolation(frame % stepDuration, 0, 8, 0, 1),
                }}
              >
                <span className="text-xs font-bold text-[var(--primary)] uppercase">当前步骤描述</span>
                <h4 className="font-bold text-[var(--text-main)] text-base mt-1">{activeStep.label}</h4>
                <p className="text-xs text-[var(--text-muted)] mt-1.5 leading-relaxed">{activeStep.description}</p>
              </div>
            )}
          </div>

          {/* Input/Output displays */}
          <div className="grid grid-cols-2 gap-4">
            <div className="edu-card">
              <span className="text-xs font-bold text-[var(--text-muted)] select-none">输入要求 (Inputs)</span>
              <div className="flex flex-wrap gap-2 mt-2">
                {inputs.map((inp, idx) => (
                  <span key={idx} className="badge-primary px-3 py-1 rounded-lg text-xs font-bold font-mono shadow-sm">
                    {inp}
                  </span>
                ))}
              </div>
            </div>
            <div className="edu-card">
              <span className="text-xs font-bold text-[var(--text-muted)] select-none">输出结果 (Outputs)</span>
              <div className="flex flex-wrap gap-2 mt-2">
                {outputs.map((out, idx) => (
                  <span key={idx} className="badge-success px-3 py-1 rounded-lg text-xs font-bold font-mono shadow-sm">
                    {out}
                  </span>
                ))}
              </div>
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
            title="流程状态监控"
            points={steps.map((s, idx) => `${idx + 1}. ${s.label}`)}
            misconception={activeFailure ? `异常警报: ${activeFailure.reason}` : undefined}
          />
        </div>
      </div>

      <SubtitleBar narration={scene.narration} durationSeconds={scene.duration_seconds} captionWords={scene.caption_words} />
    </AbsoluteFill>
  );
};
