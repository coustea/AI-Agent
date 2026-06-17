import React, { useMemo } from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import { getCurrentSubtitle } from '../utils/subtitle';
import { generateSubtitles } from '../utils/autoSubtitle';

interface SubtitleBarProps {
  narration: string;
  durationSeconds: number;
}

export const SubtitleBar: React.FC<SubtitleBarProps> = ({ narration, durationSeconds }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const subtitleChunks = useMemo(() => {
    return generateSubtitles(narration, durationSeconds);
  }, [narration, durationSeconds]);

  const text = getCurrentSubtitle(subtitleChunks, frame, fps);

  if (!text) return null;

  return (
    <div className="absolute bottom-12 left-1/2 -translate-x-1/2 w-3/4 max-w-4xl px-8 py-4 bg-slate-900/80 backdrop-blur-md rounded-xl border border-slate-700/50 flex justify-center items-center shadow-2xl z-30">
      <p className="text-white text-2xl font-semibold text-center leading-relaxed tracking-wide select-none">
        {text}
      </p>
    </div>
  );
};
