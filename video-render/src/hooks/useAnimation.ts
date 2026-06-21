import { useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";

/**
 * Configuration options for entrance animations.
 */
interface EntranceAnimationConfig {
  /** Delay in frames before animation starts */
  delay?: number;
  /** Duration of spring animation in frames */
  duration?: number;
  /** Spring damping value (default: 15) */
  damping?: number;
  /** Spring stiffness value (default: 100) */
  stiffness?: number;
  /** Direction of slide animation */
  slideDirection?: "up" | "down" | "left" | "right" | "none";
  /** Initial slide distance in pixels */
  slideDistance?: number;
  /** Initial scale value (default: 0.95) */
  initialScale?: number;
}

/**
 * Hook for creating entrance animations with spring physics.
 * Returns opacity, transform values for fade + slide + scale effects.
 *
 * @example
 * ```tsx
 * const { opacity, transform } = useEntranceAnimation({ delay: 10 });
 * <div style={{ opacity, transform }}>Animated content</div>
 * ```
 */
export function useEntranceAnimation(config: EntranceAnimationConfig = {}) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const {
    delay = 0,
    duration,
    damping = 15,
    stiffness = 100,
    slideDirection = "up",
    slideDistance = 30,
    initialScale = 0.95,
  } = config;

  // Calculate spring progress
  const activeFrame = frame - delay;
  const progress =
    activeFrame < 0
      ? 0
      : spring({
          frame: activeFrame,
          fps,
          config: { damping, stiffness },
          durationInFrames: duration,
        });

  // Calculate transform values
  let translateY = 0;
  let translateX = 0;
  let scale = 1;

  if (slideDirection === "up") {
    translateY = interpolate(progress, [0, 1], [slideDistance, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  } else if (slideDirection === "down") {
    translateY = interpolate(progress, [0, 1], [-slideDistance, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  } else if (slideDirection === "left") {
    translateX = interpolate(progress, [0, 1], [slideDistance, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  } else if (slideDirection === "right") {
    translateX = interpolate(progress, [0, 1], [-slideDistance, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  }

  scale = interpolate(progress, [0, 1], [initialScale, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return {
    opacity: progress,
    progress,
    transform:
      slideDirection === "none"
        ? `scale(${scale})`
        : `translate(${translateX}px, ${translateY}px) scale(${scale})`,
    // Individual values for custom transforms
    translateY,
    translateX,
    scale,
  };
}

/**
 * Hook for creating staggered entrance animations for lists.
 * Returns an array of animation values for each item.
 *
 * @example
 * ```tsx
 * const items = useStaggeredAnimation({ count: 5, baseDelay: 20, staggerDelay: 8 });
 * {items.map((anim, i) => (
 *   <div key={i} style={{ opacity: anim.opacity, transform: anim.transform }}>
 *     Item {i}
 *   </div>
 * ))}
 * ```
 */
export function useStaggeredAnimation(config: {
  /** Number of items to animate */
  count: number;
  /** Base delay before first item starts */
  baseDelay?: number;
  /** Delay between each item */
  staggerDelay?: number;
  /** Spring duration */
  duration?: number;
  /** Spring damping */
  damping?: number;
  /** Spring stiffness */
  stiffness?: number;
  /** Slide direction */
  slideDirection?: "up" | "down" | "left" | "right" | "none";
  /** Slide distance */
  slideDistance?: number;
}) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const {
    count,
    baseDelay = 0,
    staggerDelay = 8,
    duration,
    damping = 15,
    stiffness = 100,
    slideDirection = "up",
    slideDistance = 20,
  } = config;

  return Array.from({ length: count }, (_, idx) => {
    const delay = baseDelay + idx * staggerDelay;
    const activeFrame = frame - delay;
    const progress =
      activeFrame < 0
        ? 0
        : spring({
            frame: activeFrame,
            fps,
            config: { damping, stiffness },
            durationInFrames: duration,
          });

    let translateY = 0;
    let translateX = 0;
    const scale = interpolate(progress, [0, 1], [0.9, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

    if (slideDirection === "up") {
      translateY = interpolate(progress, [0, 1], [slideDistance, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
    } else if (slideDirection === "left") {
      translateX = interpolate(progress, [0, 1], [slideDistance, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
    }

    return {
      opacity: progress,
      progress,
      transform:
        slideDirection === "none"
          ? `scale(${scale})`
          : `translate(${translateX}px, ${translateY}px) scale(${scale})`,
      translateY,
      translateX,
      scale,
    };
  });
}

/**
 * Hook for step-based animations that progress through a sequence.
 * Useful for timelines, process flows, code execution visualization.
 *
 * @example
 * ```tsx
 * const { activeStep, stepProgress, totalSteps } = useStepAnimation({ steps: 5 });
 * // activeStep is the current step index
 * // stepProgress is progress within the current step (0-1)
 * ```
 */
export function useStepAnimation(config: {
  /** Total number of steps */
  steps: number;
  /** Optional delay before animation starts */
  delay?: number;
}) {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const { steps, delay = 0 } = config;

  const stepDuration = durationInFrames / steps;
  const adjustedFrame = frame - delay;

  const activeStep = Math.min(
    Math.max(Math.floor(adjustedFrame / stepDuration), 0),
    steps - 1,
  );

  const stepProgress = Math.max(
    0,
    Math.min((adjustedFrame - activeStep * stepDuration) / stepDuration, 1),
  );

  return {
    activeStep,
    stepProgress,
    totalSteps: steps,
    stepDuration,
    isActive: adjustedFrame >= 0 && activeStep < steps,
  };
}

/**
 * Hook for pulsing/breathing animations.
 *
 * @example
 * ```tsx
 * const pulse = usePulseAnimation({ period: 60, minScale: 0.98, maxScale: 1.02 });
 * <div style={{ transform: `scale(${pulse.scale})` }}>Pulsing element</div>
 * ```
 */
export function usePulseAnimation(config: {
  /** Period in frames for one complete pulse cycle */
  period?: number;
  /** Minimum scale value */
  minScale?: number;
  /** Maximum scale value */
  maxScale?: number;
}) {
  const frame = useCurrentFrame();

  const { period = 60, minScale = 0.98, maxScale = 1.02 } = config;

  const scale = interpolate(
    Math.sin((frame * (2 * Math.PI)) / period),
    [-1, 1],
    [minScale, maxScale],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return {
    scale,
    phase: (frame % period) / period,
  };
}
