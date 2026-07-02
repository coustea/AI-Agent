import "./index.css";
import { Composition, CalculateMetadataFunction } from "remotion";
import { loadFont as loadInterFont } from "@remotion/google-fonts/Inter";
import { loadFont as loadOutfitFont } from "@remotion/google-fonts/Outfit";
import { MainVideo } from "./MainVideo";
import { normalizePlan } from "./utils/normalizePlan";
import { buildSceneFrameRanges } from "./utils/timeline";
import defaultPlan from "../input/rich_video_plan.json";

// Load Google Fonts synchronously at module load time
// Remotion will handle font loading during the render phase
loadInterFont("normal", {
  weights: ["400", "500", "600", "700", "800"],
  subsets: ["latin"],
});

loadOutfitFont("normal", {
  weights: ["400", "500", "600", "700", "800"],
  subsets: ["latin"],
});

const calculateMetadata: CalculateMetadataFunction<Record<string, unknown>> = ({ props }) => {
  const normalized = normalizePlan(props);
  const { scenes, render_config: renderConfig } = normalized;

  const fps = renderConfig.fps;
  const width = renderConfig.width;
  const height = renderConfig.height;

  const frameRanges = buildSceneFrameRanges(
    scenes.map((scene) => scene.duration_ms),
    fps,
  );
  const lastRange = frameRanges[frameRanges.length - 1];
  const durationInFrames = lastRange
    ? lastRange.from + lastRange.durationInFrames
    : 1;

  return {
    durationInFrames,
    fps,
    width,
    height,
  }
};

export const RemotionRoot: React.FC = () => {
  const normalizedDefault = normalizePlan(defaultPlan);
  const defaultFps = normalizedDefault.render_config.fps;
  const defaultWidth = normalizedDefault.render_config.width;
  const defaultHeight = normalizedDefault.render_config.height;

  // Initial duration estimate for bootstrap
  const frameRanges = buildSceneFrameRanges(
    normalizedDefault.scenes.map((scene) => scene.duration_ms),
    defaultFps,
  );
  const lastRange = frameRanges[frameRanges.length - 1];
  const initialDurationInFrames = lastRange
    ? lastRange.from + lastRange.durationInFrames
    : 1;

  return (
    <>
      <Composition
        id="MainVideo"
        component={MainVideo}
        durationInFrames={initialDurationInFrames}
        fps={defaultFps}
        width={defaultWidth}
        height={defaultHeight}
        defaultProps={defaultPlan}
        calculateMetadata={calculateMetadata}
      />
    </>
  );
};
