/**
 * GPU-accelerated video rendering script for Remotion.
 *
 * Usage:
 *   npx tsx scripts/render.ts --input path/to/plan.json --output path/to/output.mp4
 *   npx tsx scripts/render.ts --input path/to/plan.json --output path/to/output.mp4 --gl angle
 *   npx tsx scripts/render.ts --input path/to/plan.json --output path/to/output.mp4 --remote 192.168.1.100
 *
 * GPU options:
 *   --gl angle      Use ANGLE (default, works on Mac & Windows/Linux with GPU)
 *   --gl swiftshader Use software rendering (fallback)
 *   --gl native-egl Use native EGL (Linux with NVIDIA)
 *
 * For remote 4060 PC:
 *   --remote <host>  SSH to remote machine and render there (requires Remotion setup on remote)
 */

import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import path from "path";
import fs from "fs";

// Parse CLI args
function parseArgs(): {
  input: string;
  output: string;
  gl: "angle" | "swiftshader" | "egl";
  concurrency: number;
  remote?: string;
} {
  const args = process.argv.slice(2);
  const result = {
    input: "",
    output: "",
    gl: "angle" as "angle" | "swiftshader" | "egl",
    concurrency: 4,
    remote: undefined as string | undefined,
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case "--input":
        result.input = args[++i];
        break;
      case "--output":
        result.output = args[++i];
        break;
      case "--gl":
        result.gl = args[++i] as "angle" | "swiftshader" | "egl";
        break;
      case "--concurrency":
        result.concurrency = parseInt(args[++i], 10);
        break;
      case "--remote":
        result.remote = args[++i];
        break;
    }
  }

  if (!result.input || !result.output) {
    console.error(
      "Usage: npx tsx scripts/render.ts --input <plan.json> --output <output.mp4> [--gl angle|swiftshader|egl] [--concurrency 4] [--remote <host>]",
    );
    process.exit(1);
  }

  return result;
}

async function main() {
  const config = parseArgs();

  console.log("=== Remotion GPU Renderer ===");
  console.log(`Input:  ${config.input}`);
  console.log(`Output: ${config.output}`);
  console.log(`GPU:    ${config.gl}`);
  console.log(`Concurrency: ${config.concurrency}`);

  // Load the video plan JSON
  const planJson = JSON.parse(fs.readFileSync(config.input, "utf-8"));
  console.log(
    `Plan loaded: "${planJson.title}" with ${planJson.scenes?.length || 0} scenes`,
  );

  // Step 1: Bundle the Remotion project
  console.log("\n[1/3] Bundling Remotion project...");
  const entryPoint = path.resolve(process.cwd(), "src/index.ts");
  const bundleStart = Date.now();
  const bundleLocation = await bundle(entryPoint, () => undefined);
  console.log(
    `Bundle created in ${((Date.now() - bundleStart) / 1000).toFixed(1)}s at ${bundleLocation}`,
  );

  // Step 2: Select the composition
  console.log("\n[2/3] Selecting composition...");
  const composition = await selectComposition({
    serveUrl: bundleLocation,
    id: "MainVideo",
    inputProps: planJson,
  });
  console.log(
    `Composition: ${composition.width}x${composition.height} @ ${composition.fps}fps, ${composition.durationInFrames} frames`,
  );

  // Step 3: Render with GPU acceleration
  console.log("\n[3/3] Rendering video (GPU accelerated)...");
  const renderStart = Date.now();

  await renderMedia({
    composition,
    serveUrl: bundleLocation,
    codec: "h264",
    outputLocation: config.output,
    inputProps: planJson,
    concurrency: config.concurrency,
    chromiumOptions: {
      gl: config.gl,
    },
    hardwareAcceleration: "if-possible",
    onProgress: ({ progress }) => {
      const pct = (progress * 100).toFixed(1);
      if (Number(pct) % 5 < 0.5) {
        console.log(`  [Progress] ${pct}%`);
      }
    },
  });

  const renderDuration = ((Date.now() - renderStart) / 1000).toFixed(1);
  const fileSize = (fs.statSync(config.output).size / 1024 / 1024).toFixed(1);
  console.log(`\n=== Render Complete ===`);
  console.log(`Time:   ${renderDuration}s`);
  console.log(`Output: ${config.output} (${fileSize} MB)`);
}

main().catch((err) => {
  console.error("Render failed:", err);
  process.exit(1);
});
