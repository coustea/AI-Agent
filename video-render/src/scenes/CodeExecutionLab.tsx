import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { RichVideoScene, GlobalStyle, VideoMeta } from '../schema/types';
import { EduBackground } from '../components/EduBackground';
import { SceneHeader } from '../components/SceneHeader';
import { SubtitleBar } from '../components/SubtitleBar';
import { InfoPanel } from '../components/InfoPanel';
import { CodeBlock } from '../components/CodeBlock';
import { CallStackPanel } from '../components/CallStackPanel';
import { VariableTable } from '../components/VariableTable';
import { getSpringProgress, getSlideInterpolation } from '../utils/animation';

interface ExecutionStep {
  step_index: number;
  active_line: number;
  description: string;
  variables: { name: string; value: string; scope?: string }[];
  call_stack: string[];
}

interface CodeExecutionLabProps {
  scene: RichVideoScene;
  meta: VideoMeta;
  globalStyle: GlobalStyle;
  currentSceneIndex: number;
  totalScenes: number;
}

export const CodeExecutionLab: React.FC<CodeExecutionLabProps> = ({
  scene,
  meta,
  globalStyle,
  currentSceneIndex,
  totalScenes,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Extract variables
  const language = (scene.visual.language as string) || 'python';
  const code = (scene.visual.code as string) || '';
  const steps = (scene.visual.steps as ExecutionStep[]) || [];
  const output = (scene.visual.output as string) || '';
  const errorOrMisconception = (scene.visual.error_or_misconception as string) || '';

  // Determine current step index
  const stepDuration = durationInFrames / (steps.length || 1);
  const activeStepIdx = Math.min(Math.floor(frame / stepDuration), steps.length - 1);
  const currentStep = steps[activeStepIdx];

  // Staggered entrance spring animations
  const codeEntrance = getSpringProgress(frame, fps, 5, 20);
  const stackEntrance = getSpringProgress(frame, fps, 15, 20);
  const variablesEntrance = getSpringProgress(frame, fps, 25, 20);
  const sideEntrance = getSpringProgress(frame, fps, 30, 20);

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
        {/* Left Column: CodeBlock */}
        <div
          className="col-span-5 h-[480px]"
          style={{
            opacity: codeEntrance,
            transform: `translateX(${getSlideInterpolation(codeEntrance, 0, 1, -25, 0)}px)`,
          }}
        >
          <CodeBlock
            code={code}
            language={language}
            activeLine={currentStep?.active_line}
          />
        </div>

        {/* Middle Column: Call Stack + Variable Table */}
        <div className="col-span-4 flex flex-col space-y-4 justify-center">
          <div
            style={{
              opacity: stackEntrance,
              transform: `translateY(${getSlideInterpolation(stackEntrance, 0, 1, 20, 0)}px)`,
            }}
          >
            <CallStackPanel stack={currentStep?.call_stack || []} />
          </div>

          <div
            style={{
              opacity: variablesEntrance,
              transform: `translateY(${getSlideInterpolation(variablesEntrance, 0, 1, 20, 0)}px)`,
            }}
          >
            <VariableTable variables={currentStep?.variables || []} />
          </div>

          {/* Terminal / stdout display */}
          {output && (
            <div 
              className="edu-card !p-3.5 bg-slate-900 border-slate-800 text-slate-100 font-mono text-xs shadow-md"
              style={{
                opacity: variablesEntrance,
                transform: `scale(${getSlideInterpolation(variablesEntrance, 0, 1, 0.95, 1)})`,
              }}
            >
              <span className="text-[10px] font-bold text-slate-500 uppercase select-none">输出结果 (Output)</span>
              <pre className="mt-1 text-emerald-400 font-bold select-text">{output}</pre>
            </div>
          )}
        </div>

        {/* Right Column: Steps explanation sidebar */}
        <div
          className="col-span-3 h-full flex flex-col justify-center"
          style={{
            opacity: sideEntrance,
            transform: `translateX(${getSlideInterpolation(sideEntrance, 0, 1, 25, 0)}px)`,
          }}
        >
          <InfoPanel
            title="代码执行调试器"
            explanation={currentStep?.description}
            misconception={errorOrMisconception}
          />
        </div>
      </div>

      <SubtitleBar narration={scene.narration} durationSeconds={scene.duration_seconds} captionWords={scene.caption_words} />
    </AbsoluteFill>
  );
};
