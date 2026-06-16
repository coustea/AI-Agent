import React from 'react';

interface SceneHeaderProps {
  course: string;
  topic: string;
  sceneTitle: string;
  currentSceneIndex: number;
  totalScenes: number;
  progress: number; // 0 to 1 progress of current scene
}

export const SceneHeader: React.FC<SceneHeaderProps> = ({
  course,
  topic,
  sceneTitle,
  currentSceneIndex,
  totalScenes,
  progress,
}) => {
  return (
    <div className="absolute top-0 left-0 right-0 h-24 px-10 flex items-center justify-between border-b border-[var(--card-border)] bg-[var(--card-bg)] backdrop-blur-md z-20">
      {/* Top progress bar indicator */}
      <div 
        className="absolute top-0 left-0 h-1 bg-[var(--primary)] transition-all duration-75"
        style={{ width: `${progress * 100}%` }}
      />

      {/* Course & Topic info */}
      <div className="flex items-center space-x-4">
        <span className="px-3 py-1 text-xs font-bold uppercase tracking-wider rounded-md bg-[var(--primary)] text-white">
          {course}
        </span>
        <span className="text-[var(--text-muted)] font-semibold text-sm">
          {topic}
        </span>
        <span className="text-[var(--text-muted)] text-sm">/</span>
        <span className="text-[var(--text-main)] font-bold text-lg">
          {sceneTitle}
        </span>
      </div>

      {/* Page / Scene Counter */}
      <div className="flex items-center space-x-2 font-mono text-sm">
        <span className="text-[var(--primary)] font-bold">{String(currentSceneIndex).padStart(2, '0')}</span>
        <span className="text-[var(--text-muted)]">/</span>
        <span className="text-[var(--text-muted)]">{String(totalScenes).padStart(2, '0')}</span>
      </div>
    </div>
  );
};
