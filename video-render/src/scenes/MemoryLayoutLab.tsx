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

interface MemoryAction {
  type: 'push_frame' | 'pop_frame' | 'create_variable';
  label: string;
  frame?: string;
  name?: string;
  value?: string;
  region?: 'stack' | 'heap' | string;
}

interface MemoryRegion {
  name: string;
  description: string;
}

interface MemoryLayoutLabProps {
  scene: RichVideoScene;
  meta: VideoMeta;
  globalStyle: GlobalStyle;
  currentSceneIndex: number;
  totalScenes: number;
}

export const MemoryLayoutLab: React.FC<MemoryLayoutLabProps> = ({
  scene,
  meta,
  globalStyle,
  currentSceneIndex,
  totalScenes,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Extract variables
  const layoutType = (scene.visual.layout_type as string) || 'stack_heap';
  const code = (scene.visual.code as string) || '';
  const memoryRegions = (scene.visual.memory_regions as MemoryRegion[]) || [];
  const actions = (scene.visual.actions as MemoryAction[]) || [];
  const explanation = (scene.visual.explanation as string) || '';

  // Determine active action
  const actionDuration = durationInFrames / (actions.length || 1);
  const activeActionIdx = Math.min(Math.floor(frame / actionDuration), actions.length - 1);
  const currentAction = actions[activeActionIdx];

  // Dynamically compute the stack and variable tables based on timeline actions
  const derivedStack: string[] = [];
  const derivedVars: { name: string; value: string; region: string; isChanged?: boolean }[] = [];

  for (let i = 0; i <= activeActionIdx; i++) {
    const act = actions[i];
    if (!act) continue;

    if (act.type === 'push_frame' && act.frame) {
      derivedStack.push(act.frame);
    } else if (act.type === 'pop_frame') {
      derivedStack.pop();
    } else if (act.type === 'create_variable' && act.name && act.value && act.region) {
      // Add or update
      const existingIdx = derivedVars.findIndex(v => v.name === act.name);
      if (existingIdx !== -1) {
        derivedVars[existingIdx] = {
          name: act.name,
          value: act.value,
          region: act.region,
          isChanged: i === activeActionIdx, // highlight if created in this exact step
        };
      } else {
        derivedVars.push({
          name: act.name,
          value: act.value,
          region: act.region,
          isChanged: i === activeActionIdx,
        });
      }
    }
  }

  // Anim values
  const sideEntrance = getSpringProgress(frame, fps, 15, 25);
  const leftEntrance = getSpringProgress(frame, fps, 5, 20);

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
        {/* Left: Code Block */}
        <div
          className="col-span-4"
          style={{
            opacity: leftEntrance,
            transform: `translateX(${getSlideInterpolation(leftEntrance, 0, 1, -30, 0)}px)`,
          }}
        >
          {code && (
            <CodeBlock
              code={code}
              language="python"
            />
          )}
        </div>

        {/* Middle: Stack and Heap Grids */}
        <div className="col-span-5 flex flex-col space-y-4">
          <div className="edu-card flex flex-col space-y-3">
            <h3 className="text-sm font-bold text-[var(--text-muted)] select-none border-b border-[var(--card-border)] pb-1.5">
              内存分布图: {layoutType.replace('_', ' ').toUpperCase()}
            </h3>

            {/* Visual stack vs heap cells */}
            <div className="grid grid-cols-2 gap-4 h-48 bg-slate-50/50 p-4 rounded-xl border border-[var(--card-border)] overflow-y-auto">
              {/* Stack Segment */}
              <div className="flex flex-col space-y-2 border-r border-[var(--card-border)] pr-2">
                <span className="text-[10px] font-bold text-[var(--primary)] uppercase text-center border-b border-blue-100 pb-1">
                  栈区 (Stack)
                </span>
                <div className="flex flex-col-reverse space-y-1.5 flex-1 justify-start">
                  {derivedVars.filter(v => v.region === 'stack').map((v, idx) => (
                    <div
                      key={idx}
                      className={`mem-cell text-xs py-1.5 font-bold ${
                        v.isChanged ? 'active' : ''
                      }`}
                    >
                      {v.name}: {v.value}
                    </div>
                  ))}
                </div>
              </div>

              {/* Heap Segment */}
              <div className="flex flex-col space-y-2 pl-2">
                <span className="text-[10px] font-bold text-purple-600 uppercase text-center border-b border-purple-100 pb-1">
                  堆区 (Heap)
                </span>
                <div className="grid grid-cols-2 gap-1.5 flex-1 items-start content-start">
                  {derivedVars.filter(v => v.region === 'heap').map((v, idx) => (
                    <div
                      key={idx}
                      className={`mem-cell text-xs py-1.5 font-bold ${
                        v.isChanged ? 'active' : ''
                      }`}
                    >
                      {v.name} ({v.value})
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Current stack operation tip */}
            {currentAction && (
              <div className="p-3 bg-slate-100 border border-slate-200 rounded-lg flex items-center justify-between text-xs">
                <span className="font-bold text-[var(--text-main)]">{currentAction.label}</span>
                <span className="text-[9px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                  {currentAction.type}
                </span>
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <CallStackPanel stack={derivedStack} />
            <VariableTable variables={derivedVars} />
          </div>
        </div>

        {/* Right: Info panel */}
        <div
          className="col-span-3 h-full flex flex-col justify-center"
          style={{
            opacity: sideEntrance,
            transform: `translateX(${getSlideInterpolation(sideEntrance, 0, 1, 30, 0)}px)`,
          }}
        >
          <InfoPanel
            title="内存解析看板"
            explanation={explanation}
            points={memoryRegions.map(mr => `${mr.name}: ${mr.description}`)}
          />
        </div>
      </div>

      <SubtitleBar narration={scene.narration} durationSeconds={scene.duration_seconds} />
    </AbsoluteFill>
  );
};
