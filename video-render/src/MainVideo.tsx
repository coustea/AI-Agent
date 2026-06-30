import React from 'react';
import { useVideoConfig, Sequence, getInputProps, Audio, staticFile } from 'remotion';
import { richVideoPlanSchema } from './schema/videoPlanSchema';
import { SceneRouter } from './SceneRouter';
import { SceneTransition } from './components/SceneTransition';
import { normalizePlan } from './utils/normalizePlan';
import { buildSceneFrameRanges } from './utils/timeline';
import defaultPlan from '../input/rich_video_plan.json';

// Helper to resolve asset source dynamically (local vs remote)
const getAudioSrc = (src: string) => {
  if (!src) return '';
  if (src.startsWith('http://') || src.startsWith('https://')) {
    return src;
  }
  // Strip "/static/" prefix since Remotion's public folder maps to server/static
  let cleanPath = src;
  if (cleanPath.startsWith('/static/')) {
    cleanPath = cleanPath.substring(8);
  } else if (cleanPath.startsWith('static/')) {
    cleanPath = cleanPath.substring(7);
  } else if (cleanPath.startsWith('/')) {
    cleanPath = cleanPath.substring(1);
  }
  return staticFile(cleanPath);
};

export const MainVideo: React.FC = () => {
  const { fps } = useVideoConfig();
  const rawProps = getInputProps();

  // Use defaultPlan if rawProps is empty or missing scenes
  const hasProps = rawProps && Object.keys(rawProps).length > 0 && Array.isArray(rawProps.scenes);
  const propsToValidate = hasProps ? rawProps : defaultPlan;

  // Validate the incoming JSON structure using Zod
  const result = richVideoPlanSchema.safeParse(propsToValidate);

  if (!result.success) {
    console.error('JSON validation failed:', result.error.format());
    return (
      <div className="flex flex-col items-center justify-center w-full h-full bg-red-100 p-20 text-red-700 font-mono">
        <h1 className="text-3xl font-bold mb-4">Plan Validation Error</h1>
        <pre className="p-4 bg-red-50 border border-red-200 rounded text-xs overflow-auto max-w-4xl max-h-96">
          {JSON.stringify(result.error.format(), null, 2)}
        </pre>
      </div>
    );
  }

  // Normalize the plan (handles both V2 and backend JSON schemas gracefully)
  const videoPlan = normalizePlan(result.data);
  const { scenes, global_style: globalStyle, meta, audio: bgmConfig } = videoPlan;
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
      
      {/* Global Background Music */}
      {bgmConfig?.bgm_src && (
        <Audio
          src={getAudioSrc(bgmConfig.bgm_src)}
          volume={() => bgmConfig.bgm_volume}
          loop
        />
      )}

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
