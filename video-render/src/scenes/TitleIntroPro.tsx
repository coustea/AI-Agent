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
import { SubtitleBar } from "../components/SubtitleBar";

interface TitleIntroProProps {
  scene: RichVideoScene;
  meta: VideoMeta;
  globalStyle: GlobalStyle;
  currentSceneIndex: number;
  totalScenes: number;
}

const enter = (frame: number, start: number, duration: number) =>
  interpolate(frame, [start, start + duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

export const TitleIntroPro: React.FC<TitleIntroProProps> = ({
  scene,
  meta,
  globalStyle,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const titleEnter = enter(frame, Math.round(fps * 0.12), Math.round(fps * 0.5));
  const detailEnter = enter(frame, Math.round(fps * 0.35), Math.round(fps * 0.5));
  const mapEnter = enter(frame, Math.round(fps * 0.55), Math.round(fps * 0.5));

  const course = (scene.visual.course as string) || meta.subject;
  const chapter = (scene.visual.chapter as string) || meta.topic;
  const subtitle = (scene.visual.subtitle as string) || meta.title;
  const tags = (scene.visual.tags as string[]) || [];
  const heroKeywords = (scene.visual.hero_keywords as string[]) || [];
  const visibleKeywords =
    heroKeywords.length > 0
      ? heroKeywords.slice(0, 4)
      : tags.slice(0, 4);
  const mapCenter =
    (scene.visual.hero_center as string) ||
    scene.title.replace(/入门|基础|概述/g, "") ||
    scene.title;

  return (
    <AbsoluteFill className="overflow-hidden px-20 pb-36 pt-16">
      <EduBackground backgroundType={globalStyle.background} />

      <div className="relative z-10 grid h-full grid-cols-[1.05fr_0.95fr] items-center gap-20">
        <section className="min-w-0 pb-8">
          <div
            className="mb-10 flex items-center gap-5 text-[23px] font-semibold text-[var(--text-muted)]"
            style={{
              opacity: detailEnter,
              translate: `${interpolate(detailEnter, [0, 1], [-24, 0])}px 0`,
            }}
          >
            <span className="h-10 w-[6px] bg-[var(--primary)]" />
            <span className="font-bold text-[var(--primary)]">{course}</span>
            <span>{chapter}</span>
          </div>

          <h1
            className="m-0 max-w-[960px] text-[112px] font-extrabold leading-[1.04] text-[var(--text-main)]"
            style={{
              opacity: titleEnter,
              translate: `0 ${interpolate(titleEnter, [0, 1], [34, 0])}px`,
            }}
          >
            {scene.title}
          </h1>

          <p
            className="mb-0 mt-9 max-w-[850px] text-[38px] font-medium leading-[1.45] text-[var(--text-muted)]"
            style={{
              opacity: detailEnter,
              translate: `0 ${interpolate(detailEnter, [0, 1], [22, 0])}px`,
            }}
          >
            {subtitle}
          </p>

          {tags.length > 0 && (
            <div
              className="mt-12 flex flex-wrap gap-x-10 gap-y-3 border-t border-[var(--card-border)] pt-7 text-[20px] font-semibold text-[var(--text-muted)]"
              style={{ opacity: detailEnter }}
            >
              {tags.map((tag) => (
                <span key={tag}>{tag}</span>
              ))}
            </div>
          )}
        </section>

        <section
          className="relative h-[720px] overflow-hidden rounded-lg bg-[var(--primary)] p-14 text-white shadow-[0_32px_80px_rgba(37,99,235,0.18)]"
          style={{
            opacity: mapEnter,
            translate: `${interpolate(mapEnter, [0, 1], [44, 0])}px 0`,
          }}
        >
          <div className="text-[21px] font-semibold text-blue-100">
            从数据到结构
          </div>

          <div className="absolute left-1/2 top-[43%] h-[2px] w-[470px] -translate-x-1/2 bg-blue-200/60" />
          <div className="absolute left-1/2 top-[43%] h-[370px] w-[2px] -translate-x-1/2 -translate-y-1/2 bg-blue-200/60" />

          <div
            className="absolute left-1/2 top-[43%] flex h-48 w-48 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-lg border-2 border-white bg-white px-4 text-center font-extrabold leading-tight text-[var(--primary)] shadow-[0_20px_50px_rgba(13,35,90,0.2)]"
            style={{ fontSize: mapCenter.length > 6 ? 27 : 38 }}
          >
            {mapCenter}
          </div>

          {visibleKeywords.map((keyword, index) => {
            const positions = [
              "left-14 top-40",
              "right-14 top-40",
              "bottom-24 left-14",
              "bottom-24 right-14",
            ];
            const glyphs = [
              ["01", "02", "03"],
              ["A", "B", "C"],
              ["TOP", "MID", "LOW"],
              ["IN", "DATA", "OUT"],
            ];

            return (
              <div
                key={keyword}
                className={`absolute ${positions[index]} w-[210px]`}
                style={{
                  opacity: enter(
                    frame,
                    Math.round(fps * (0.7 + index * 0.12)),
                    Math.round(fps * 0.35),
                  ),
                }}
              >
                <div className="mb-3 text-[27px] font-bold">{keyword}</div>
                <div className="flex gap-2">
                  {glyphs[index].map((glyph) => (
                    <span
                      key={glyph}
                      className="flex h-11 min-w-11 items-center justify-center border border-blue-200/70 px-2 font-mono text-[13px] font-bold text-blue-50"
                    >
                      {glyph}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}

          <div className="absolute bottom-8 left-14 right-14 border-t border-blue-200/40 pt-5 text-[19px] font-medium text-blue-100">
            建立概念之间的连接，形成可执行的知识结构
          </div>
        </section>
      </div>

      <SubtitleBar
        narration={scene.narration}
        durationSeconds={scene.duration_seconds}
        captionWords={scene.caption_words}
      />
    </AbsoluteFill>
  );
};
