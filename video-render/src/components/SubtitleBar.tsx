import React, { useMemo } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { generateSubtitles } from "../utils/autoSubtitle";
import { getCurrentSubtitle } from "../utils/subtitle";
import type { CaptionWord } from "../schema/types";

interface SubtitleBarProps {
  narration: string;
  durationSeconds: number;
  captionWords?: CaptionWord[];
}

export const SubtitleBar: React.FC<SubtitleBarProps> = ({
  narration,
  durationSeconds,
  captionWords,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Prefer TTS-synchronized captions; fall back to text-split estimation
  const subtitleText = useMemo(() => {
    if (captionWords && captionWords.length > 0) {
      const currentMs = (frame / fps) * 1000;
      const activeWord = captionWords.find(
        (w) => currentMs >= w.start_ms && currentMs <= w.end_ms,
      );
      if (activeWord) return activeWord.text;

      // Group consecutive words into a phrase for the current time window
      const phraseWords: string[] = [];
      const phraseWindowMs = 2500; // show up to 2.5s of words
      for (const w of captionWords) {
        if (
          w.start_ms >= currentMs - 500 &&
          w.start_ms <= currentMs + phraseWindowMs
        ) {
          phraseWords.push(w.text);
        }
      }
      if (phraseWords.length > 0) return phraseWords.join("");
      return "";
    }

    // Fallback: character-ratio based splitting
    const chunks = generateSubtitles(narration, durationSeconds);
    return getCurrentSubtitle(chunks, frame, fps);
  }, [frame, fps, captionWords, narration, durationSeconds]);

  if (!subtitleText) return null;

  return (
    <div className="absolute bottom-12 left-1/2 -translate-x-1/2 w-3/4 max-w-4xl px-8 py-4 bg-slate-900/80 backdrop-blur-md rounded-xl border border-slate-700/50 flex justify-center items-center shadow-2xl z-30">
      <p className="text-white text-2xl font-semibold text-center leading-relaxed tracking-wide select-none">
        {subtitleText}
      </p>
    </div>
  );
};
