import React from 'react';
import { useVideoConfig, Sequence, getInputProps, Audio, staticFile } from 'remotion';
import { SceneRouter } from './SceneRouter';
import { SceneTransition } from './components/SceneTransition';
import { normalizePlan } from './utils/normalizePlan';
import { buildSceneFrameRanges } from './utils/timeline';

// Helper to resolve asset source dynamically (local vs remote)
const getAudioSrc = (src: string) => {
  if (!src) return '';
  if (src.startsWith('http://') || src.startsWith('https://')) {
    return src;
  }
  const cleanPath = src.startsWith('/') ? src.substring(1) : src;
  return staticFile(cleanPath);
};

export const MainVideo: React.FC = () => {
  const { fps } = useVideoConfig();
  const rawProps = getInputProps();
  const videoPlan = normalizePlan(rawProps);
  const { scenes, global_style: globalStyle, meta } = videoPlan;
  const resolvedFontFamily = globalStyle.font_family
    .toLowerCase()
    .includes("inter")
    ? '"Outfit", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif'
    : globalStyle.font_family;

  const frameRanges = buildSceneFrameRanges(
    scenes.map((scene) => scene.duration_ms),
    fps,
  );

  return (
    <div
      className={`relative h-full w-full overflow-hidden bg-[var(--canvas)] font-sans theme-${globalStyle.theme}`}
      style={{
        "--primary": globalStyle.primary_color,
        "--accent": globalStyle.primary_color,
        "--danger": globalStyle.danger_color,
        "--success": globalStyle.success_color,
        fontFamily: resolvedFontFamily,
      } as React.CSSProperties}
    >
      
      {scenes.map((scene, idx) => {
        const {
          from: startFrame,
          durationInFrames: sceneDurationFrames,
        } = frameRanges[idx];

        const transitionType = scene.transition || 'fade';

        return (
          <Sequence
            key={scene.id}
            from={startFrame}
            durationInFrames={sceneDurationFrames}
            name={`${scene.type}: ${scene.title}`}
          >
            {/* Play Scene-Specific Voiceover / Narration Audio */}
            {scene.audio_src && (
              <Audio
                src={getAudioSrc(scene.audio_src)}
                volume={1.0}
              />
            )}

            {/* Scene Transition (Fade/Slide/Zoom) */}
            <SceneTransition
              transitionType={transitionType}
              durationInFrames={sceneDurationFrames}
            >
              <SceneRouter
                scene={scene}
                meta={meta}
                globalStyle={globalStyle}
                currentSceneIndex={idx + 1}
                totalScenes={scenes.length}
              />
            </SceneTransition>
          </Sequence>
        );
      })}
    </div>
  );
};
