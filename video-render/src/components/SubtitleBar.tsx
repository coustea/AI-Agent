import type { Caption } from "@remotion/captions";
import React, { useMemo } from "react";
import {
  Easing,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type {
  CaptionChunk,
  CaptionWord,
} from "../schema/types";
import { generateSubtitles } from "../utils/autoSubtitle";
import { getActiveCaptionChunk } from "../utils/timeline";
import { useSceneData } from "./SceneDataContext";

interface SubtitleBarProps {
  narration: string;
  durationSeconds: number;
  audioDurationMs?: number;
  captionWords?: CaptionWord[];
  captionChunks?: CaptionChunk[];
}

export const SubtitleBar: React.FC<SubtitleBarProps> = ({
  narration,
  durationSeconds,
  audioDurationMs,
  captionWords = [],
  captionChunks = [],
}) => {
  const scene = useSceneData();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentMs = (frame / fps) * 1000;
  const resolvedChunks =
    captionChunks.length > 0 ? captionChunks : scene?.caption_chunks ?? [];
  const spokenDurationMs =
    audioDurationMs ??
    scene?.audio_duration_ms ??
    durationSeconds * 1000;

  const captions = useMemo<Caption[]>(
    () => {
      const words =
        captionWords.length > 0 ? captionWords : scene?.caption_words ?? [];
      return words.map((word) => ({
        text: word.text,
        startMs: word.start_ms,
        endMs: word.end_ms,
        timestampMs: word.start_ms,
        confidence: null,
      }));
    },
    [captionWords, scene?.caption_words],
  );

  const fallbackChunks = useMemo<CaptionChunk[]>(
    () =>
      generateSubtitles(narration, spokenDurationMs / 1000).map((chunk) => ({
        text: chunk.text,
        start_ms: chunk.start * 1000,
        end_ms: chunk.end * 1000,
      })),
    [narration, spokenDurationMs],
  );

  if (currentMs >= spokenDurationMs) return null;

  const activeChunk = getActiveCaptionChunk(
    resolvedChunks.length > 0 ? resolvedChunks : fallbackChunks,
    currentMs,
  );
  if (!activeChunk) return null;

  const chunkTokens = captions.filter(
    (caption) =>
      caption.endMs > activeChunk.start_ms &&
      caption.startMs < activeChunk.end_ms,
  );
  const enterOpacity = interpolate(
    currentMs,
    [activeChunk.start_ms, activeChunk.start_ms + 140],
    [0, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.16, 1, 0.3, 1),
    },
  );

  return (
    <div
      className="absolute bottom-8 left-1/2 z-30 flex min-h-[74px] max-w-[1320px] -translate-x-1/2 items-center justify-center rounded-lg bg-[rgba(23,32,51,0.94)] px-10 py-4 shadow-[0_16px_42px_rgba(23,32,51,0.18)]"
      style={{ opacity: enterOpacity }}
    >
      <p className="m-0 text-center text-[36px] font-semibold leading-[1.3] text-[#f8fafc]">
        {chunkTokens.length > 0
          ? chunkTokens.map((token, index) => {
              const isActive =
                token.startMs <= currentMs && token.endMs > currentMs;
              return (
                <span
                  key={`${token.startMs}-${index}`}
                  style={{
                    color: isActive ? "var(--subtitle-active)" : "white",
                  }}
                >
                  {token.text}
                </span>
              );
            })
          : activeChunk.text}
      </p>
    </div>
  );
};
