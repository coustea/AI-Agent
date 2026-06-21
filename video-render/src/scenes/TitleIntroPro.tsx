import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { RichVideoScene, GlobalStyle, VideoMeta } from '../schema/types';
import { EduBackground } from '../components/EduBackground';
import { SubtitleBar } from '../components/SubtitleBar';
import { getSpringProgress, getSlideInterpolation } from '../utils/animation';

interface TitleIntroProProps {
  scene: RichVideoScene;
  meta: VideoMeta;
  globalStyle: GlobalStyle;
  currentSceneIndex: number;
  totalScenes: number;
}

export const TitleIntroPro: React.FC<TitleIntroProProps> = ({
  scene,
  meta,
  globalStyle,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Staggered entrance spring animations
  const baseSpring = getSpringProgress(frame, fps, 5, 25);
  const titleSpring = getSpringProgress(frame, fps, 15, 25);
  const subtitleSpring = getSpringProgress(frame, fps, 28, 25);
  const tagsSpring = getSpringProgress(frame, fps, 40, 25);
  const keywordSpring = getSpringProgress(frame, fps, 20, 35);

  // Extract visual configs
  const course = (scene.visual.course as string) || meta.subject;
  const chapter = (scene.visual.chapter as string) || meta.topic;
  const subtitle = (scene.visual.subtitle as string) || meta.title;
  const tags = (scene.visual.tags as string[]) || [];
  const heroKeywords = (scene.visual.hero_keywords as string[]) || [];

  return (
    <AbsoluteFill className="flex flex-col justify-between p-16 overflow-hidden">
      <EduBackground backgroundType={globalStyle.background} />

      {/* Glow highlight orb behind title */}
      <div 
        className="absolute top-1/3 left-1/4 w-[400px] h-[400px] rounded-full blur-[140px] opacity-20 pointer-events-none -z-1"
        style={{
          backgroundColor: 'var(--primary)',
          transform: `scale(${getSlideInterpolation(baseSpring, 0, 1, 0.5, 1.2)})`,
        }}
      />

      {/* Main content grid */}
      <div className="grid grid-cols-12 gap-8 w-full my-auto z-10">
        {/* Left info column */}
        <div className="col-span-8 flex flex-col justify-center space-y-6">
          <div 
            style={{
              opacity: titleSpring,
              transform: `translateY(${getSlideInterpolation(titleSpring, 0, 1, 40, 0)}px)`
            }}
          >
            <span className="px-4 py-1.5 rounded-full text-sm font-extrabold uppercase tracking-wider bg-[var(--primary)] text-white shadow-lg shadow-[var(--primary)]/20 select-none">
              {course} • {chapter}
            </span>
            <h1 className="text-6xl font-extrabold text-[var(--text-main)] mt-5 leading-tight tracking-tight">
              {scene.title}
            </h1>
          </div>

          <p 
            className="text-2xl text-[var(--text-muted)] font-medium leading-relaxed max-w-2xl"
            style={{
              opacity: subtitleSpring,
              transform: `translateY(${getSlideInterpolation(subtitleSpring, 0, 1, 25, 0)}px)`
            }}
          >
            {subtitle}
          </p>

          {/* Tags */}
          <div 
            className="flex flex-wrap gap-2.5 pt-2"
            style={{
              opacity: tagsSpring,
              transform: `translateY(${getSlideInterpolation(tagsSpring, 0, 1, 15, 0)}px)`
            }}
          >
            {tags.map((tag, idx) => (
              <span key={idx} className="badge-primary px-3.5 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider shadow-sm">
                #{tag}
              </span>
            ))}
          </div>
        </div>

        {/* Right graphical keywords column */}
        <div className="col-span-4 flex items-center justify-center relative">
          <div 
            className="relative w-80 h-80 rounded-full flex items-center justify-center"
            style={{
              opacity: keywordSpring,
              transform: `scale(${getSlideInterpolation(keywordSpring, 0, 1, 0.7, 1)})`
            }}
          >
            {/* Pulsing circle background */}
            <div className="absolute inset-0 bg-gradient-to-br from-[var(--primary)]/10 to-[var(--accent)]/5 rounded-full border border-[var(--primary)]/15 shadow-inner" />
            <div className="absolute inset-4 bg-white/40 backdrop-blur-sm rounded-full" />

            {/* Keyword elements */}
            <div className="flex flex-col items-center space-y-4 z-10 w-full px-6">
              {heroKeywords.map((kw, idx) => {
                const staggerSpring = getSpringProgress(frame, fps, 30 + idx * 8, 25);
                return (
                  <span 
                    key={idx} 
                    className="px-5 py-2.5 rounded-2xl bg-white border border-[var(--card-border)] text-sm font-extrabold shadow-md text-[var(--primary)] glow-primary transition-all duration-300 w-4/5 text-center"
                    style={{
                      opacity: staggerSpring,
                      transform: `translateY(${getSlideInterpolation(staggerSpring, 0, 1, 20, 0)}px) scale(${getSlideInterpolation(staggerSpring, 0, 1, 0.9, 1)})`,
                    }}
                  >
                    {kw}
                  </span>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Subtitles Bar */}
      <SubtitleBar narration={scene.narration} durationSeconds={scene.duration_seconds} captionWords={scene.caption_words} />
    </AbsoluteFill>
  );
};
