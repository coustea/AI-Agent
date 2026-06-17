import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { RichVideoScene, GlobalStyle, VideoMeta } from '../schema/types';
import { EduBackground } from '../components/EduBackground';
import { SceneHeader } from '../components/SceneHeader';
import { SubtitleBar } from '../components/SubtitleBar';
import { InfoPanel } from '../components/InfoPanel';
import { CodeBlock } from '../components/CodeBlock';
import { VariableTable } from '../components/VariableTable';
import { getSpringProgress, getSlideInterpolation } from '../utils/animation';

interface TraceStep {
  step_index: number;
  left?: number;
  right?: number;
  mid?: number;
  compare?: string;
  decision?: string;
  active_line?: number;
}

interface AlgorithmTraceBoardProps {
  scene: RichVideoScene;
  meta: VideoMeta;
  globalStyle: GlobalStyle;
  currentSceneIndex: number;
  totalScenes: number;
}

export const AlgorithmTraceBoard: React.FC<AlgorithmTraceBoardProps> = ({
  scene,
  meta,
  globalStyle,
  currentSceneIndex,
  totalScenes,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Extract variables
  const algorithmName = (scene.visual.algorithm_name as string) || '';
  const problem = (scene.visual.problem as string) || '';
  const data = (scene.visual.data as (number | string)[]) || [];
  const pseudocode = (scene.visual.pseudocode as string[]) || [];
  const steps = (scene.visual.steps as TraceStep[]) || [];
  const complexity = (scene.visual.complexity as { time: string; space: string }) || { time: '', space: '' };
  const result = (scene.visual.result as string) || '';

  // Determine current step index
  const stepDuration = durationInFrames / (steps.length || 1);
  const activeStepIdx = Math.min(Math.floor(frame / stepDuration), steps.length - 1);
  const currentStep = steps[activeStepIdx];

  // Derive variables for VariableTable
  const variables = [
    { name: 'left', value: currentStep?.left !== undefined ? currentStep.left : '-' },
    { name: 'right', value: currentStep?.right !== undefined ? currentStep.right : '-' },
    { name: 'mid', value: currentStep?.mid !== undefined ? currentStep.mid : '-' },
    { name: 'compare', value: currentStep?.compare || '-' },
    { name: 'decision', value: currentStep?.decision || '-' },
  ];

  // Anim values
  const sideEntrance = getSpringProgress(frame, fps, 15, 25);
  const codeEntrance = getSpringProgress(frame, fps, 5, 20);

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
        {/* Left Column: Pseudocode */}
        <div
          className="col-span-4"
          style={{
            opacity: codeEntrance,
            transform: `translateX(${getSlideInterpolation(codeEntrance, 0, 1, -30, 0)}px)`,
          }}
        >
          <CodeBlock
            code={pseudocode.join('\n')}
            language="python"
            activeLine={currentStep?.active_line}
          />
        </div>

        {/* Middle Column: Array / Elements visual trace */}
        <div className="col-span-5 flex flex-col space-y-6">
          <div className="edu-card flex flex-col space-y-4">
            <h3 className="text-md font-bold text-[var(--text-main)] select-none">
              算法执行板: {algorithmName}
            </h3>
            <p className="text-xs text-[var(--text-muted)] font-medium">问题: {problem}</p>

            {/* Array Box renderer */}
            <div className="flex justify-center items-center py-6 px-3 bg-slate-50/50 border border-[var(--card-border)] rounded-xl relative">
              <div className="flex space-x-2.5 overflow-visible">
                {data.map((val, idx) => {
                  const isLeft = idx === currentStep?.left;
                  const isRight = idx === currentStep?.right;
                  const isMid = idx === currentStep?.mid;

                  // Determine color/glow status based on pointers
                  let borderStyle = 'border-[var(--card-border)]';
                  let bgStyle = 'bg-white';
                  let glowStyle = '';

                  if (isMid) {
                    borderStyle = 'border-purple-500 border-2';
                    bgStyle = 'bg-purple-50';
                    glowStyle = 'glow-accent';
                  } else if (isLeft || isRight) {
                    borderStyle = 'border-[var(--primary)] border-2';
                    bgStyle = 'bg-blue-50';
                    glowStyle = 'glow-primary';
                  }

                  // Fade elements outside [left, right]
                  const isOutRange =
                    currentStep?.left !== undefined &&
                    currentStep?.right !== undefined &&
                    (idx < currentStep.left || idx > currentStep.right);

                  return (
                    <div key={idx} className="flex flex-col items-center relative">
                      {/* Array Cell */}
                      <div
                        className={`w-12 h-12 flex items-center justify-center font-mono font-black text-sm rounded-lg border transition-all duration-300 ${borderStyle} ${bgStyle} ${glowStyle} ${
                          isOutRange ? 'opacity-35 scale-95' : 'opacity-100'
                        }`}
                      >
                        {val}
                      </div>

                      {/* Array Index label */}
                      <span className="text-[9px] font-mono font-bold text-[var(--text-muted)] mt-1.5">
                        [{idx}]
                      </span>

                      {/* Pointer marker overlays */}
                      <div className="absolute -top-6 flex flex-col space-y-0.5 items-center font-bold font-mono text-[9px]">
                        {isLeft && <span className="text-[var(--primary)]">L</span>}
                        {isRight && <span className="text-[var(--primary)]">R</span>}
                        {isMid && <span className="text-purple-600">M</span>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Result text when search is done */}
            {result && activeStepIdx === steps.length - 1 && (
              <div className="p-3 bg-emerald-50/90 border border-emerald-100 text-emerald-800 rounded-xl font-bold text-center text-xs shadow-sm">
                🎉 Trace 结束: {result}
              </div>
            )}
          </div>

          <VariableTable variables={variables} />
        </div>

        {/* Right Column: Explanation Panel */}
        <div
          className="col-span-3 h-full flex flex-col justify-center"
          style={{
            opacity: sideEntrance,
            transform: `translateX(${getSlideInterpolation(sideEntrance, 0, 1, 30, 0)}px)`,
          }}
        >
          <InfoPanel
            title="追踪指标 & 复杂度"
            points={[
              `当前步骤: 第 ${activeStepIdx + 1} 步`,
              `时间复杂度: ${complexity.time}`,
              `空间复杂度: ${complexity.space}`,
            ]}
            explanation={currentStep?.decision ? `决策行为: ${currentStep.decision}` : undefined}
          />
        </div>
      </div>

      <SubtitleBar narration={scene.narration} durationSeconds={scene.duration_seconds} captionWords={scene.caption_words} />
    </AbsoluteFill>
  );
};
