import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { RichVideoScene, GlobalStyle, VideoMeta } from '../schema/types';
import { EduBackground } from '../components/EduBackground';
import { SceneHeader } from '../components/SceneHeader';
import { SubtitleBar } from '../components/SubtitleBar';
import { InfoPanel } from '../components/InfoPanel';
import { getSpringProgress, getSlideInterpolation } from '../utils/animation';

interface ArchLayer {
  id: string;
  name: string;
  description: string;
  examples: string[];
}


interface LayeredArchitectureSceneProps {
  scene: RichVideoScene;
  meta: VideoMeta;
  globalStyle: GlobalStyle;
  currentSceneIndex: number;
  totalScenes: number;
}

export const LayeredArchitectureScene: React.FC<LayeredArchitectureSceneProps> = ({
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
  const layers = (scene.visual.layers as ArchLayer[]) || [];
  const currentFocusLayer = (scene.visual.current_focus_layer as string) || '';
  const examples = (scene.visual.examples as string[]) || [];

  const focusLayer = layers.find(l => l.id === currentFocusLayer);

  // Transitions
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
        {/* Left: Stack of horizontal layers */}
        <div className="flex flex-col space-y-4 h-full justify-center">
          <div className="edu-card flex flex-col space-y-3">
            <h3 className="text-lg font-bold text-[var(--text-main)] select-none border-b border-[var(--card-border)] pb-2">
              分层结构: {architectureName}
            </h3>

            {/* Vertical Stack */}
            <div className="flex flex-col space-y-3 p-4 bg-slate-50/50 rounded-xl">
              {layers.map((layer) => {
                const isFocus = layer.id === currentFocusLayer;
                const scaleAnim = isFocus ? getSlideInterpolation(Math.sin(frame / 15), -1, 1, 1, 1.02) : 1;

                return (
                  <div
                    key={layer.id}
                    className={`p-4 rounded-xl border flex justify-between items-center bg-white ${
                      isFocus
                        ? 'border-[var(--primary)] glow-primary shadow-md'
                        : 'border-[var(--card-border)] opacity-60'
                    }`}
                    style={{
                      transform: `scale(${scaleAnim})`,
                    }}
                  >
                    <div className="flex flex-col space-y-1">
                      <span className="font-extrabold text-base text-[var(--text-main)]">
                        {layer.name} ({layer.id.toUpperCase()})
                      </span>
                      <span className="text-xs text-[var(--text-muted)] font-medium leading-relaxed">
                        {layer.description}
                      </span>
                    </div>

                    {/* Example badges */}
                    <div className="flex space-x-1.5">
                      {layer.examples.map((ex, eIdx) => (
                        <span
                          key={eIdx}
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                            isFocus
                              ? 'bg-[var(--primary)] text-white'
                              : 'bg-slate-100 text-slate-500 border border-slate-200'
                          }`}
                        >
                          {ex}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Sidebar explanation panel */}
        <div
          className="h-full flex flex-col justify-center"
          style={{
            opacity: sideEntrance,
            transform: `translateX(${getSlideInterpolation(sideEntrance, 0, 1, 45, 0)}px)`,
          }}
        >
          <InfoPanel
            title="聚焦层详细解析"
            explanation={focusLayer?.description}
            points={[
              `当前焦点: ${focusLayer?.name || '无'}`,
              `主要包含协议: ${focusLayer?.examples.join(', ') || '无'}`,
              ...examples,
            ]}
          />
        </div>
      </div>

      <SubtitleBar narration={scene.narration} durationSeconds={scene.duration_seconds} captionWords={scene.caption_words} />
    </AbsoluteFill>
  );
};
