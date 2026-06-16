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

interface CpuModule {
  id: string;
  label: string;
  description: string;
}

interface DataPath {
  from: string;
  to: string;
  label: string;
}

interface CpuStep {
  name: string;
  active_modules: string[];
  description: string;
}

interface CpuRegister {
  name: string;
  value: string;
}

interface CpuArchitectureLabProps {
  scene: RichVideoScene;
  meta: VideoMeta;
  globalStyle: GlobalStyle;
  currentSceneIndex: number;
  totalScenes: number;
}

export const CpuArchitectureLab: React.FC<CpuArchitectureLabProps> = ({
  scene,
  meta,
  globalStyle,
  currentSceneIndex,
  totalScenes,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Extract variables
  const architectureName = (scene.visual.architecture_name as string) || '';
  const currentInstruction = (scene.visual.current_instruction as string) || '';
  const modules = (scene.visual.modules as CpuModule[]) || [];
  const dataPaths = (scene.visual.data_paths as DataPath[]) || [];
  const steps = (scene.visual.steps as CpuStep[]) || [];
  const registers = (scene.visual.registers as CpuRegister[]) || [];
  const explanation = (scene.visual.explanation as string) || '';

  // Determine current executing step
  const stepDuration = durationInFrames / (steps.length || 1);
  const activeStepIdx = Math.min(Math.floor(frame / stepDuration), steps.length - 1);
  const currentStep = steps[activeStepIdx];

  // Pre-defined layout grid coordinates for module blocks inside diagram box
  const moduleCoords: Record<string, { x: number; y: number }> = {
    pc: { x: 50, y: 50 },
    memory: { x: 340, y: 50 },
    ir: { x: 50, y: 170 },
    control: { x: 200, y: 170 },
    registers: { x: 50, y: 290 },
    alu: { x: 340, y: 290 },
  };

  const sideEntrance = getSpringProgress(frame, fps, 10, 25);

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
        {/* Left: CPU architecture diagram */}
        <div className="flex flex-col space-y-6 h-full justify-center">
          <div className="edu-card flex flex-col space-y-4 h-[440px]">
            <div className="flex justify-between items-center select-none border-b border-[var(--card-border)] pb-2">
              <h3 className="text-lg font-bold text-[var(--text-main)]">
                架构周期: {architectureName}
              </h3>
              <span className="badge-danger px-3 py-1 rounded-full text-xs font-bold font-mono">
                当前指令: {currentInstruction}
              </span>
            </div>

            {/* Microarchitecture Canvas */}
            <div className="relative flex-1 bg-slate-50/50 rounded-xl overflow-visible">
              {/* Draw Data Paths */}
              {dataPaths.map((dp, idx) => {
                const start = moduleCoords[dp.from];
                const end = moduleCoords[dp.to];
                if (!start || !end) return null;

                // Adjust nodes overlap
                const dx = end.x - start.x;
                const dy = end.y - start.y;
                const len = Math.sqrt(dx * dx + dy * dy);
                const offset = 40;

                const x1 = start.x + (dx / len) * offset + 50; // offset centering
                const y1 = start.y + (dy / len) * offset + 25;
                const x2 = end.x - (dx / len) * offset + 50;
                const y2 = end.y - (dy / len) * offset + 25;

                // Data path is active if both nodes are currently active
                const isPathActive =
                  currentStep?.active_modules.includes(dp.from) &&
                  currentStep?.active_modules.includes(dp.to);

                return (
                  <AnimatedArrow
                    key={idx}
                    startX={x1}
                    startY={y1}
                    endX={x2}
                    endY={y2}
                    label={dp.label}
                    isActive={isPathActive}
                  />
                );
              })}

              {/* Draw Modules */}
              {modules.map((m) => {
                const pos = moduleCoords[m.id] || { x: 50, y: 50 };
                const isActive = currentStep?.active_modules.includes(m.id);

                return (
                  <div
                    key={m.id}
                    className="absolute"
                    style={{
                      left: pos.x,
                      top: pos.y,
                    }}
                  >
                    <DiagramNode
                      id={m.id}
                      label={m.label}
                      status={isActive ? 'active' : 'normal'}
                      className="w-24 h-14 text-xs font-bold border-2 shadow-md flex items-center justify-center"
                    />
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right sideboard detail pane */}
        <div
          className="h-full flex flex-col justify-center space-y-4"
          style={{
            opacity: sideEntrance,
            transform: `translateX(${getSlideInterpolation(sideEntrance, 0, 1, 45, 0)}px)`,
          }}
        >
          {/* Registers Table */}
          <div className="edu-card !p-4 flex flex-col space-y-2.5">
            <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] border-b border-[var(--card-border)] pb-1 select-none">
              寄存器状态 (Registers)
            </h4>
            <div className="grid grid-cols-2 gap-2 font-mono text-xs">
              {registers.map((reg, idx) => (
                <div key={idx} className="flex justify-between p-2 rounded bg-slate-50 border border-[var(--card-border)]">
                  <span className="font-bold text-[var(--primary)]">{reg.name}</span>
                  <span className="font-extrabold text-[var(--text-main)]">{reg.value}</span>
                </div>
              ))}
            </div>
          </div>

          <InfoPanel
            title="CPU 执行解析"
            explanation={explanation}
            points={steps.map((st, idx) => `${idx + 1}. ${st.name}: ${st.description}`)}
          />
        </div>
      </div>

      <SubtitleBar narration={scene.narration} durationSeconds={scene.duration_seconds} />
    </AbsoluteFill>
  );
};
