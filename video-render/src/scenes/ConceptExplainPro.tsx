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

interface ConceptExplainProProps {
  scene: RichVideoScene;
  meta: VideoMeta;
  globalStyle: GlobalStyle;
  currentSceneIndex: number;
  totalScenes: number;
}

export const ConceptExplainPro: React.FC<ConceptExplainProProps> = ({
  scene,
  meta,
  globalStyle,
  currentSceneIndex,
  totalScenes,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Entrance spring animations
  const baseEntrance = getSpringProgress(frame, fps, 5, 25);
  const mapEntrance = getSpringProgress(frame, fps, 20, 25);
  const sideEntrance = getSpringProgress(frame, fps, 35, 25);

  // Extract variables from visual
  const mainConcept = (scene.visual.main_concept as string) || '';
  const definition = (scene.visual.definition as string) || '';
  const keywords = (scene.visual.keywords as string[]) || [];
  const whyItMatters = (scene.visual.why_it_matters as string[]) || [];
  const relatedConcepts = (scene.visual.related_concepts as { name: string; relation: string }[]) || [];
  const commonMisconception = (scene.visual.common_misconception as string) || '';

  // Width/height of the local diagram coordinate system
  const layoutWidth = 600;
  const layoutHeight = 280;
  const centerX = layoutWidth / 2;
  const centerY = layoutHeight / 2;

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
        {/* Left/Middle: Concept card + Map */}
        <div className="flex flex-col space-y-6 h-full justify-center">
          
          {/* Main definition card */}
          <div
            className="edu-card border-l-4 border-l-[var(--primary)] flex flex-col space-y-3"
            style={{
              opacity: baseEntrance,
              transform: `translateY(${getSlideInterpolation(baseEntrance, 0, 1, 30, 0)}px)`,
            }}
          >
            <div className="flex items-center space-x-3">
              <span className="font-extrabold text-2xl text-[var(--text-main)]">
                {mainConcept}
              </span>
              <div className="flex space-x-1.5">
                {keywords.map((kw, idx) => (
                  <span key={idx} className="badge-primary px-2.5 py-0.5 rounded text-[10px] font-extrabold tracking-wider">
                    {kw}
                  </span>
                ))}
              </div>
            </div>
            <p className="text-base text-[var(--text-muted)] leading-relaxed">
              {definition}
            </p>
          </div>

          {/* Related concept nodes map */}
          <div
            className="edu-card flex items-center justify-center bg-slate-50/40 relative h-72 overflow-hidden"
            style={{
              opacity: mapEntrance,
              transform: `scale(${getSlideInterpolation(mapEntrance, 0, 1, 0.95, 1)})`,
            }}
          >
            <div 
              className="absolute overflow-visible pointer-events-none"
              style={{ width: layoutWidth, height: layoutHeight }}
            >
              {relatedConcepts.map((item, idx) => {
                const stepDelay = 35 + idx * 10;
                const arrowSpring = getSpringProgress(frame, fps, stepDelay, 20);
                
                // Position subnodes symmetrically on a semicircle
                const angle = relatedConcepts.length > 1
                  ? -Math.PI + (idx * Math.PI) / (relatedConcepts.length - 1)
                  : -Math.PI / 2; // single node goes straight up
                
                const radius = 160;
                const x = Math.cos(angle) * radius;
                const y = Math.sin(angle) * radius;

                // Center position inside layout coordinates
                const nodeX = centerX + x;
                const nodeY = centerY + y;

                return (
                  <React.Fragment key={idx}>
                    {/* Connecting Arrow from Center Node */}
                    <AnimatedArrow
                      startX={centerX}
                      startY={centerY}
                      endX={nodeX}
                      endY={nodeY}
                      label={item.relation}
                      isActive={frame > stepDelay}
                    />

                    {/* Sub Node */}
                    <div
                      className="absolute"
                      style={{
                        left: nodeX,
                        top: nodeY,
                        transform: `translate(-50%, -50%) scale(${getSlideInterpolation(arrowSpring, 0, 1, 0.7, 1)})`,
                        opacity: arrowSpring,
                      }}
                    >
                      <DiagramNode id={`rel-${idx}`} label={item.name} className="w-32 py-2 text-xs font-bold" />
                    </div>
                  </React.Fragment>
                );
              })}

              {/* Center Main Node */}
              <div 
                className="absolute"
                style={{
                  left: centerX,
                  top: centerY,
                  transform: 'translate(-50%, -50%)',
                }}
              >
                <DiagramNode id="main" label={mainConcept} status="active" className="w-44 shadow-lg" />
              </div>
            </div>
          </div>
        </div>

        {/* Right Sidebar explanation panel */}
        <div
          className="h-full flex flex-col justify-center"
          style={{
            opacity: sideEntrance,
            transform: `translateX(${getSlideInterpolation(sideEntrance, 0, 1, 30, 0)}px)`,
          }}
        >
          <InfoPanel
            title="要点精讲 & 误区排除"
            points={whyItMatters}
            misconception={commonMisconception}
          />
        </div>
      </div>

      <SubtitleBar narration={scene.narration} durationSeconds={scene.duration_seconds} captionWords={scene.caption_words} />
    </AbsoluteFill>
  );
};
