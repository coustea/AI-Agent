import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

interface EduBackgroundProps {
  backgroundType:
    | "soft_grid_gradient"
    | "circuit_board_light"
    | "minimal_blueprint";
}

export const EduBackground: React.FC<EduBackgroundProps> = ({
  backgroundType,
}) => {
  const frame = useCurrentFrame();

  const dashOffset = interpolate(frame, [0, 900], [0, -1000]);

  return (
    <AbsoluteFill className="z-0 select-none overflow-hidden bg-[var(--canvas)]">
      {backgroundType === "soft_grid_gradient" && (
        <>
          <AbsoluteFill className="paper-dots opacity-60" />
          <div className="absolute left-0 top-0 h-2 w-full bg-[var(--primary)]" />
          <div className="absolute bottom-0 left-0 h-2 w-full bg-[var(--ink)]" />
        </>
      )}

      {backgroundType === "circuit_board_light" && (
        <AbsoluteFill className="paper-dots opacity-70">
          <svg
            className="h-full w-full opacity-15"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M 0,210 L 420,210 L 520,310 L 1050,310"
              fill="none"
              stroke="var(--primary)"
              strokeWidth="3"
              strokeDasharray="12 8"
              strokeDashoffset={dashOffset}
            />
            <path
              d="M 1920,810 L 1500,810 L 1400,710 L 930,710"
              fill="none"
              stroke="var(--primary)"
              strokeWidth="3"
              strokeDasharray="12 8"
              strokeDashoffset={dashOffset}
            />
          </svg>
        </AbsoluteFill>
      )}

      {backgroundType === "minimal_blueprint" && (
        <>
          <AbsoluteFill className="blueprint-grid opacity-55" />
          <div className="absolute inset-x-16 top-14 h-px bg-[var(--primary)] opacity-20" />
          <div className="absolute inset-x-16 bottom-14 h-px bg-[var(--primary)] opacity-20" />
        </>
      )}
    </AbsoluteFill>
  );
};
