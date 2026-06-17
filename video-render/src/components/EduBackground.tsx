import React from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';

interface EduBackgroundProps {
  backgroundType: 'soft_grid_gradient' | 'circuit_board_light' | 'minimal_blueprint';
}

export const EduBackground: React.FC<EduBackgroundProps> = ({ backgroundType }) => {
  const frame = useCurrentFrame();

  // Draw floating particles or circuit paths based on background type
  return (
    <AbsoluteFill className="overflow-hidden select-none -z-10 bg-gradient-to-br from-[var(--bg-gradient-start)] to-[var(--bg-gradient-end)]">
      {/* Grid Overlay */}
      {backgroundType === 'soft_grid_gradient' && (
        <AbsoluteFill className="tech-grid opacity-75">
          {/* Glowing background shapes */}
          <div 
            className="absolute top-1/4 left-1/4 w-[600px] h-[600px] rounded-full blur-[160px] opacity-15"
            style={{
              backgroundColor: 'var(--primary)',
              transform: `translate(${Math.sin(frame / 60) * 40}px, ${Math.cos(frame / 60) * 40}px)`,
            }}
          />
          <div 
            className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] rounded-full blur-[140px] opacity-10"
            style={{
              backgroundColor: 'var(--accent)',
              transform: `translate(${Math.cos(frame / 50) * 30}px, ${Math.sin(frame / 50) * 30}px)`,
            }}
          />
        </AbsoluteFill>
      )}

      {backgroundType === 'circuit_board_light' && (
        <AbsoluteFill className="tech-dots opacity-50">
          <svg className="w-full h-full opacity-20" xmlns="http://www.w3.org/2000/svg">
            {/* Circuit paths */}
            <path
              d="M 100,100 L 400,100 L 500,200 L 900,200"
              fill="none"
              stroke="var(--primary)"
              strokeWidth="2"
              className="circuit-line"
            />
            <path
              d="M 1500,900 L 1200,900 L 1100,800 L 700,800"
              fill="none"
              stroke="var(--accent)"
              strokeWidth="2"
              className="circuit-line"
            />
            <circle cx="100" cy="100" r="4" fill="var(--primary)" />
            <circle cx="900" cy="200" r="4" fill="var(--primary)" />
            <circle cx="1500" cy="900" r="4" fill="var(--accent)" />
            <circle cx="700" cy="800" r="4" fill="var(--accent)" />
          </svg>
        </AbsoluteFill>
      )}

      {backgroundType === 'minimal_blueprint' && (
        <AbsoluteFill className="opacity-80">
          {/* Blueprint style fine lines */}
          <div className="absolute inset-0 border-[3px] border-[var(--primary)] opacity-10 m-10" />
          <svg className="w-full h-full opacity-10" xmlns="http://www.w3.org/2000/svg">
            <line x1="0" y1="200" x2="1920" y2="200" stroke="var(--primary)" strokeWidth="1" />
            <line x1="0" y1="880" x2="1920" y2="880" stroke="var(--primary)" strokeWidth="1" />
            <line x1="300" y1="0" x2="300" y2="1080" stroke="var(--primary)" strokeWidth="1" />
            <line x1="1620" y1="0" x2="1620" y2="1080" stroke="var(--primary)" strokeWidth="1" />
            {/* Fine grids */}
            <pattern id="blueprint-grid" width="20" height="20" patternUnits="userSpaceOnUse">
              <rect width="20" height="20" fill="none" stroke="var(--primary)" strokeWidth="0.5" />
            </pattern>
            <rect width="100%" height="100%" fill="url(#blueprint-grid)" opacity="0.4" />
          </svg>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};
