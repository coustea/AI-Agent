import { RenderMode } from '../schema/videoPlan';

export interface TimingConfig {
  maxItems: number;
  durationScale: number;
  transitionDuration: number;
  stepDelay: number;
}

export function getTimingConfig(mode: RenderMode): TimingConfig {
  switch (mode) {
    case 'quick':
      return {
        maxItems: 5,
        durationScale: 0.6,
        transitionDuration: 0.3,
        stepDelay: 0.4,
      };
    case 'standard':
      return {
        maxItems: 10,
        durationScale: 1.0,
        transitionDuration: 0.6,
        stepDelay: 0.8,
      };
    case 'detailed':
      return {
        maxItems: 18,
        durationScale: 1.4,
        transitionDuration: 0.9,
        stepDelay: 1.2,
      };
    default:
      return {
        maxItems: 8,
        durationScale: 1.0,
        transitionDuration: 0.5,
        stepDelay: 0.8,
      };
  }
}
