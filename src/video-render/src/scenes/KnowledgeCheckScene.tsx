import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { RichVideoScene, GlobalStyle, VideoMeta } from '../schema/types';
import { EduBackground } from '../components/EduBackground';
import { SceneHeader } from '../components/SceneHeader';
import { SubtitleBar } from '../components/SubtitleBar';
import { InfoPanel } from '../components/InfoPanel';
import { getSpringProgress, getSlideInterpolation } from '../utils/animation';

interface QuizOption {
  id: string;
  text: string;
}

interface KnowledgeCheckSceneProps {
  scene: RichVideoScene;
  meta: VideoMeta;
  globalStyle: GlobalStyle;
  currentSceneIndex: number;
  totalScenes: number;
}

export const KnowledgeCheckScene: React.FC<KnowledgeCheckSceneProps> = ({
  scene,
  meta,
  globalStyle,
  currentSceneIndex,
  totalScenes,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Extract variables
  const question = (scene.visual.question as string) || '';
  const options = (scene.visual.options as QuizOption[]) || [];
  const correctAnswer = (scene.visual.correct_answer as string) || '';
  const explanation = (scene.visual.explanation as string) || '';
  const relatedConcept = (scene.visual.related_concept as string) || '';
  const reviewPoints = (scene.visual.review_points as string[]) || [];

  // Timing triggers (reveal answer 1.5s before the end of the scene)
  const optionsStartFrame = 15;
  const optionsGap = 8;
  const revealFrame = Math.max(
    optionsStartFrame + options.length * optionsGap + 10,
    durationInFrames - Math.round(1.8 * fps)
  );

  const showAnswer = frame >= revealFrame;

  // Transitions
  const sideEntrance = getSpringProgress(frame, fps, revealFrame + 5, 20);
  const qEntrance = getSpringProgress(frame, fps, 5, 20);

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
        {/* Left: Question + Multiple Choice cards */}
        <div className="flex flex-col space-y-6 h-full justify-center">
          <div
            className="edu-card border-l-4 border-l-orange-500 flex flex-col space-y-4"
            style={{
              opacity: qEntrance,
              transform: `translateY(${getSlideInterpolation(qEntrance, 0, 1, 25, 0)}px)`,
            }}
          >
            <div className="flex items-center space-x-2 select-none">
              <span className="px-2.5 py-0.5 rounded text-[10px] font-extrabold text-white bg-orange-500 uppercase tracking-wider">
                Quiz
              </span>
              <span className="text-xs text-[var(--text-muted)] font-extrabold">知识随堂课测</span>
            </div>
            <h3 className="text-xl font-bold text-[var(--text-main)] leading-relaxed">
              {question}
            </h3>
          </div>

          {/* Options List */}
          <div className="flex flex-col space-y-3">
            {options.map((opt, idx) => {
              const entranceFrame = optionsStartFrame + idx * optionsGap;
              const optionEntrance = getSpringProgress(frame, fps, entranceFrame, 15);

              const isCorrect = opt.id === correctAnswer;
              const isSelected = showAnswer && isCorrect;
              const isDimmed = showAnswer && !isCorrect;

              let cardStyle = 'border-[var(--card-border)] bg-white';
              let glowStyle = '';

              if (isSelected) {
                cardStyle = 'border-[var(--success)] bg-emerald-50/90 text-[var(--success)] font-extrabold';
                glowStyle = 'glow-success scale-[1.01]';
              } else if (isDimmed) {
                cardStyle = 'border-[var(--card-border)] bg-white opacity-40 scale-95';
              }

              return (
                <div
                  key={opt.id}
                  className={`p-4 rounded-xl border flex items-center space-x-4 transition-all duration-300 ${cardStyle} ${glowStyle}`}
                  style={{
                    opacity: optionEntrance * (isDimmed ? 0.4 : 1),
                    transform: `translateX(${getSlideInterpolation(optionEntrance, 0, 1, 25, 0)}px)`,
                  }}
                >
                  {/* Option letter bubble */}
                  <span
                    className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs font-mono border-2 transition-all ${
                      isSelected
                        ? 'bg-[var(--success)] text-white border-[var(--success)] border-transparent'
                        : 'bg-slate-100 text-[var(--text-muted)] border-[var(--card-border)]'
                    }`}
                  >
                    {opt.id}
                  </span>

                  <span className="text-sm font-semibold flex-1 leading-snug">{opt.text}</span>

                  {/* Reveal Checkmark icon */}
                  {isSelected && (
                    <span className="text-[var(--success)] font-black text-lg mr-2">✓ 正确答案</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Sidebar explanation panel */}
        <div
          className="h-full flex flex-col justify-center"
          style={{
            opacity: sideEntrance,
            transform: `translateX(${getSlideInterpolation(sideEntrance, 0, 1, 25, 0)}px)`,
          }}
        >
          {showAnswer && (
            <InfoPanel
              title="考点精析"
              explanation={explanation}
              points={reviewPoints.map((rp) => `回顾要点: ${rp}`)}
              misconception={relatedConcept ? `关联考点: ${relatedConcept}` : undefined}
            />
          )}
        </div>
      </div>

      <SubtitleBar narration={scene.narration} durationSeconds={scene.duration_seconds} />
    </AbsoluteFill>
  );
};
