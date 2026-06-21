import "./index.css";
import { Composition, CalculateMetadataFunction } from "remotion";
import { loadFont as loadInterFont } from "@remotion/google-fonts/Inter";
import { loadFont as loadOutfitFont } from "@remotion/google-fonts/Outfit";
import { MainVideo } from "./MainVideo";
import { normalizePlan } from "./utils/normalizePlan";
import defaultPlan from "../input/rich_video_plan.json";

// Load Google Fonts synchronously at module load time
// Remotion will handle font loading during the render phase
loadInterFont();

loadOutfitFont();

const calculateMetadata: CalculateMetadataFunction<any> = ({ props }) => {
  try {
    const hasProps =
      props && Object.keys(props).length > 0 && Array.isArray(props.scenes);
    const normalized = normalizePlan(hasProps ? props : defaultPlan);
    const { scenes, render_config: renderConfig } = normalized;

    const fps = renderConfig.fps;
    const width = renderConfig.width;
    const height = renderConfig.height;

    // Calculate total duration in frames
    const totalDurationSeconds = scenes.reduce(
      (acc: number, scene) => acc + (scene.duration_seconds || 0),
      0,
    );
    const durationInFrames = Math.round(totalDurationSeconds * fps);

    return {
      durationInFrames,
      fps,
      width,
      height,
    };
  } catch (error) {
    console.error("calculateMetadata failed:", error);
    return {
      durationInFrames: 300,
      fps: 30,
      width: 1920,
      height: 1080,
    };
  }
};

export const RemotionRoot: React.FC = () => {
  const normalizedDefault = normalizePlan(defaultPlan);
  const defaultFps = normalizedDefault.render_config.fps;
  const defaultWidth = normalizedDefault.render_config.width;
  const defaultHeight = normalizedDefault.render_config.height;

  // Initial duration estimate for bootstrap
  const totalDurationSeconds = normalizedDefault.scenes.reduce(
    (acc: number, scene) => acc + scene.duration_seconds,
    0,
  );
  const initialDurationInFrames = Math.round(totalDurationSeconds * defaultFps);

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
