import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

interface SceneTransitionProps {
  transitionType: "fade" | "slide_left" | "slide_up" | "zoom" | "none";
  durationInFrames: number;
  children: React.ReactNode;
}

export const SceneTransition: React.FC<SceneTransitionProps> = ({
  transitionType,
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enterEnd = Math.max(1, Math.round(fps * 0.32));
  const progress = interpolate(frame, [0, enterEnd], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  const style: React.CSSProperties =
    transitionType === "slide_left"
      ? { translate: `${interpolate(progress, [0, 1], [28, 0])}px 0` }
      : transitionType === "slide_up"
        ? { translate: `0 ${interpolate(progress, [0, 1], [22, 0])}px` }
        : transitionType === "zoom"
          ? { scale: interpolate(progress, [0, 1], [0.985, 1]) }
          : {};

  return (
    <AbsoluteFill
      style={{
        ...style,
        opacity:
          transitionType === "none"
            ? 1
            : interpolate(progress, [0, 1], [0.86, 1]),
      }}
    >
      {children}
    </AbsoluteFill>
  );
};
