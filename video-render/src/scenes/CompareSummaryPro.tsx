import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { RichVideoScene, GlobalStyle, VideoMeta } from '../schema/types';
import { EduBackground } from '../components/EduBackground';
import { SceneHeader } from '../components/SceneHeader';
import { SubtitleBar } from '../components/SubtitleBar';
import { InfoPanel } from '../components/InfoPanel';
import { getSpringProgress, getSlideInterpolation } from '../utils/animation';

interface SideData {
  title: string;
  points: string[];
}

interface DifferenceDimension {
  dimension: string;
  left: string;
  right: string;
}

interface CompareSummaryProProps {
  scene: RichVideoScene;
  meta: VideoMeta;
  globalStyle: GlobalStyle;
  currentSceneIndex: number;
  totalScenes: number;
}

export const CompareSummaryPro: React.FC<CompareSummaryProProps> = ({
  scene,
  meta,
  globalStyle,
  currentSceneIndex,
  totalScenes,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Extract variables
  const compareTitle = (scene.visual.compare_title as string) || '';
  const left = (scene.visual.left as SideData) || { title: '', points: [] };
  const right = (scene.visual.right as SideData) || { title: '', points: [] };
  const samePoints = (scene.visual.same_points as string[]) || [];
  const differentPoints = (scene.visual.different_points as DifferenceDimension[]) || [];
  const conclusion = (scene.visual.conclusion as string) || '';
  const examHint = (scene.visual.exam_hint as string) || '';

  // Staggered entrance spring animations
  const leftEntrance = getSpringProgress(frame, fps, 5, 20);
  const rightEntrance = getSpringProgress(frame, fps, 15, 20);
  const matrixEntrance = getSpringProgress(frame, fps, 25, 20);
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

      <div className="scene-layout-grid w-full h-[calc(100%-40px)] z-10">
        {/* Left: Two column card comparison + difference table */}
        <div className="flex flex-col space-y-6 h-full justify-center">
          {compareTitle && (
            <h3 className="text-lg font-bold text-[var(--text-main)] border-b border-[var(--card-border)] pb-2 select-none">
              对比主题: {compareTitle}
            </h3>
          )}
          <div className="compare-grid w-full">
            {/* Left Card */}
            <div
              className="edu-card border-t-4 border-t-[var(--primary)] flex flex-col space-y-3"
              style={{
                opacity: leftEntrance,
                transform: `translateX(${getSlideInterpolation(leftEntrance, 0, 1, -25, 0)}px)`,
              }}
            >
              <h3 className="text-xl font-black text-[var(--text-main)]">{left.title}</h3>
              <ul className="space-y-1.5 text-xs font-semibold text-[var(--text-muted)]">
                {left.points.map((p, idx) => (
                  <li key={idx} className="flex items-start">
                    <span className="text-[var(--primary)] mr-1.5">•</span>
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Right Card */}
            <div
              className="edu-card border-t-4 border-t-[var(--accent)] flex flex-col space-y-3"
              style={{
                opacity: rightEntrance,
                transform: `translateX(${getSlideInterpolation(rightEntrance, 0, 1, 25, 0)}px)`,
              }}
            >
              <h3 className="text-xl font-black text-[var(--text-main)]">{right.title}</h3>
              <ul className="space-y-1.5 text-xs font-semibold text-[var(--text-muted)]">
                {right.points.map((p, idx) => (
                  <li key={idx} className="flex items-start">
                    <span className="text-[var(--accent)] mr-1.5">•</span>
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Dynamic Comparison Matrix */}
          {differentPoints.length > 0 && (
            <div 
              className="edu-card !p-0 overflow-hidden"
              style={{
                opacity: matrixEntrance,
                transform: `translateY(${getSlideInterpolation(matrixEntrance, 0, 1, 20, 0)}px)`,
              }}
            >
              <table className="w-full text-xs text-left border-collapse">
                <thead className="bg-slate-50 border-b border-[var(--card-border)] select-none">
                  <tr>
                    <th className="p-3.5 font-bold text-[var(--text-muted)]">比较维度</th>
                    <th className="p-3.5 font-bold text-[var(--text-main)]">{left.title}</th>
                    <th className="p-3.5 font-bold text-[var(--text-main)]">{right.title}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {differentPoints.map((dp, idx) => {
                    const rowSpring = getSpringProgress(frame, fps, 30 + idx * 8, 15);
                    return (
                      <tr 
                        key={idx} 
                        className="hover:bg-slate-50/55"
                        style={{
                          opacity: rowSpring,
                          transform: `translateY(${getSlideInterpolation(rowSpring, 0, 1, 10, 0)}px)`,
                        }}
                      >
                        <td className="p-3.5 font-bold text-[var(--primary)]">{dp.dimension}</td>
                        <td className="p-3.5 text-[var(--text-muted)] font-medium">{dp.left}</td>
                        <td className="p-3.5 text-[var(--text-muted)] font-medium">{dp.right}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right Sidebar explanation panel */}
        <div
          className="h-full flex flex-col justify-center"
          style={{
            opacity: sideEntrance,
            transform: `translateX(${getSlideInterpolation(sideEntrance, 0, 1, 25, 0)}px)`,
          }}
        >
          <InfoPanel
            title="对比总结与考点"
            explanation={conclusion}
            points={samePoints.map((s) => `相同点: ${s}`)}
            misconception={examHint}
          />
        </div>
      </div>

      <SubtitleBar narration={scene.narration} durationSeconds={scene.duration_seconds} captionWords={scene.caption_words} />
    </AbsoluteFill>
  );
};
