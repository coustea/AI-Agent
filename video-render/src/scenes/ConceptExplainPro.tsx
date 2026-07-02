import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type {
  GlobalStyle,
  RichVideoScene,
  VideoMeta,
} from "../schema/types";
import { EduBackground } from "../components/EduBackground";
import { SceneHeader } from "../components/SceneHeader";
import { SubtitleBar } from "../components/SubtitleBar";
import { useSceneTiming } from "../hooks/useSceneTiming";

interface ConceptExplainProProps {
  scene: RichVideoScene;
  meta: VideoMeta;
  globalStyle: GlobalStyle;
  currentSceneIndex: number;
  totalScenes: number;
}

const cueEntrance = (currentMs: number, startMs: number) =>
  interpolate(currentMs, [startMs, startMs + 280], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

export const ConceptExplainPro: React.FC<ConceptExplainProProps> = ({
  scene,
  meta,
  globalStyle,
  currentSceneIndex,
  totalScenes,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const timing = useSceneTiming(scene);

  const mainConcept = (scene.visual.main_concept as string) || scene.title;
  const definition = (scene.visual.definition as string) || "";
  const keywords = (scene.visual.keywords as string[]) || [];
  const whyItMatters = (scene.visual.why_it_matters as string[]) || [];
  const relatedConcepts =
    (scene.visual.related_concepts as {
      name: string;
      relation: string;
    }[]) || [];
  const commonMisconception =
    (scene.visual.common_misconception as string) || "";
  const sourceConcepts =
    relatedConcepts.length > 0
      ? relatedConcepts.slice(0, 3)
      : [{ name: "原始数据", relation: "等待组织" }];
  const effectKeywords =
    keywords.length > 0 ? keywords.slice(0, 4) : ["组织", "存储", "访问"];

  const defineCue = scene.visual_cues?.find((cue) => cue.kind === "define");
  const relationCue = scene.visual_cues?.find(
    (cue) => cue.kind === "example" || cue.kind === "compare",
  );
  const misconceptionCue = scene.visual_cues?.find(
    (cue) => cue.kind === "misconception",
  );
  const definitionEnter = cueEntrance(
    timing.currentMs,
    defineCue?.start_ms ?? 120,
  );
  const relationEnter = cueEntrance(
    timing.currentMs,
    relationCue?.start_ms ?? scene.audio_duration_ms * 0.28,
  );
  const misconceptionEnter = cueEntrance(
    timing.currentMs,
    misconceptionCue?.start_ms ?? scene.audio_duration_ms * 0.68,
  );

  return (
    <AbsoluteFill className="overflow-hidden px-16 pb-36 pt-32">
      <EduBackground backgroundType={globalStyle.background} />
      <SceneHeader
        course={meta.subject}
        topic={meta.topic}
        sceneTitle={scene.title}
        currentSceneIndex={currentSceneIndex}
        totalScenes={totalScenes}
        progress={frame / durationInFrames}
      />

      <div className="relative z-10 grid h-full grid-cols-[minmax(0,1.42fr)_minmax(430px,0.58fr)] gap-20">
        <section className="flex min-w-0 flex-col justify-center pb-5">
          <div
            style={{
              opacity: definitionEnter,
              translate: `0 ${interpolate(definitionEnter, [0, 1], [24, 0])}px`,
            }}
          >
            <div className="mb-3 text-[20px] font-bold text-[var(--primary)]">
              定义
            </div>
            <h2 className="m-0 text-[76px] font-extrabold leading-[1.08] text-[var(--text-main)]">
              {mainConcept}
            </h2>
            <p className="mb-0 mt-6 max-w-[1050px] text-[34px] font-medium leading-[1.5] text-[var(--text-muted)]">
              {definition}
            </p>
          </div>

          {(relatedConcepts.length > 0 || keywords.length > 0) && (
            <div
              className="mt-14 grid min-h-[250px] grid-cols-[0.9fr_120px_1.05fr_120px_0.9fr] items-center border-y border-[var(--card-border)] py-8"
              style={{
                opacity: relationEnter,
                translate: `0 ${interpolate(relationEnter, [0, 1], [22, 0])}px`,
              }}
            >
              <div>
                <div className="mb-5 text-[18px] font-semibold text-[var(--text-muted)]">
                  依赖概念
                </div>
                <div className="space-y-4">
                  {sourceConcepts.map((item) => (
                    <div key={item.name}>
                      <div className="text-[27px] font-bold text-[var(--text-main)]">
                        {item.name}
                      </div>
                      <div className="mt-1 text-[17px] font-medium text-[var(--text-muted)]">
                        {item.relation}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex items-center px-5">
                <div className="h-[2px] flex-1 bg-[var(--primary)]" />
                <span className="text-[28px] text-[var(--primary)]">›</span>
              </div>

              <div className="flex h-40 items-center justify-center rounded-lg bg-[var(--primary)] px-7 text-center text-[34px] font-extrabold leading-tight text-white shadow-[0_20px_50px_rgba(37,99,235,0.18)]">
                {mainConcept}
              </div>

              <div className="flex items-center px-5">
                <div className="h-[2px] flex-1 bg-[var(--primary)]" />
                <span className="text-[28px] text-[var(--primary)]">›</span>
              </div>

              <div>
                <div className="mb-5 text-[18px] font-semibold text-[var(--text-muted)]">
                  核心作用
                </div>
                <div className="flex flex-col gap-3">
                  {effectKeywords.map((keyword) => (
                    <div
                      key={keyword}
                      className="border-l-[5px] border-[var(--primary)] pl-4 text-[26px] font-bold text-[var(--text-main)]"
                    >
                      {keyword}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </section>

        <aside className="my-6 flex min-h-[690px] flex-col justify-center rounded-lg bg-[var(--ink)] px-12 py-12 text-white shadow-[0_28px_70px_rgba(23,32,51,0.16)]">
          <div className="text-[21px] font-bold text-blue-300">
            为什么重要
          </div>
          <div className="mt-8 flex flex-col">
            {whyItMatters.slice(0, 4).map((point, index) => (
              <div
                key={point}
                className="grid grid-cols-[46px_1fr] items-start border-t border-white/15 py-7"
              >
                <span className="font-mono text-[19px] font-bold text-blue-300">
                  {index + 1}
                </span>
                <span className="text-[28px] font-semibold leading-[1.35] text-white">
                  {point}
                </span>
              </div>
            ))}
          </div>

          {commonMisconception && (
            <div
              className="mt-10 rounded-lg border-l-[5px] border-[var(--danger)] bg-white/10 px-7 py-6"
              style={{
                opacity: misconceptionEnter,
                translate: `0 ${interpolate(misconceptionEnter, [0, 1], [16, 0])}px`,
              }}
            >
              <div className="text-[19px] font-bold text-red-300">
                需要纠正
              </div>
              <p className="mb-0 mt-3 text-[23px] font-semibold leading-[1.45] text-white">
                {commonMisconception}
              </p>
            </div>
          )}
        </aside>
      </div>

      <SubtitleBar
        narration={scene.narration}
        durationSeconds={scene.duration_seconds}
        captionWords={scene.caption_words}
      />
    </AbsoluteFill>
  );
};
