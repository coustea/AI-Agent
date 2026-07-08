/**
 * GPU-accelerated video rendering script for Remotion.
 *
 * Usage:
 *   npx tsx scripts/render.ts --input path/to/plan.json --output path/to/output.mp4
 *   npx tsx scripts/render.ts --input path/to/plan.json --output path/to/output.mp4 --gl angle
 *   npx tsx scripts/render.ts --input path/to/plan.json --output path/to/output.mp4 --remote 192.168.1.100
 *
 * GPU options (Ubuntu NVIDIA 默认走 angle，由后端 GPU 探测自动选择):
 *   --gl angle       Use ANGLE — Remotion 官方推荐的 GPU 后端，Ubuntu NVIDIA 默认
 *   --gl swiftshader Use software rendering (无 GPU 时的兜底)
 *   --gl egl         Use native EGL (Linux NVIDIA 纯 headless、无 X11 显示器场景)
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
  audioManifest?: string;
  remote?: string;
} {
  const args = process.argv.slice(2);
  const result = {
    input: "",
    output: "",
    gl: "angle" as "angle" | "swiftshader" | "egl",
    concurrency: 4,
    audioManifest: undefined as string | undefined,
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
      case "--audio-manifest":
        // JSON 清单 [{src, dest}]：src=绝对路径音频文件，dest=相对 public/ 的目标路径。
        // 由 renderer.py 提供；本脚本在 bundle 就绪后复制，避免 bundle 重建时被 fs.rmSync 清除。
        result.audioManifest = args[++i];
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

function getDirectoryMaxMtime(dir: string): number {
  let maxMtime = 0;
  const files = fs.readdirSync(dir);
  for (const file of files) {
    const fullPath = path.join(dir, file);
    const stat = fs.statSync(fullPath);
    if (stat.isDirectory()) {
      maxMtime = Math.max(maxMtime, getDirectoryMaxMtime(fullPath));
    } else {
      maxMtime = Math.max(maxMtime, stat.mtimeMs);
    }
  }
  return maxMtime;
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

  const cacheBundleDir = path.resolve(process.cwd(), "build/cached_bundle");
  const cacheIndexHtml = path.join(cacheBundleDir, "index.html");

  let bundleLocation: string;
  let useCache = false;

  if (fs.existsSync(cacheIndexHtml)) {
    const srcMaxMtime = Math.max(
      getDirectoryMaxMtime(path.resolve(process.cwd(), "src")),
      fs.statSync(path.resolve(process.cwd(), "package.json")).mtimeMs,
      fs.existsSync(path.resolve(process.cwd(), "remotion.config.ts"))
        ? fs.statSync(path.resolve(process.cwd(), "remotion.config.ts")).mtimeMs
        : 0,
    );
    const bundleMtime = fs.statSync(cacheIndexHtml).mtimeMs;
    if (bundleMtime > srcMaxMtime) {
      useCache = true;
    }
  }

  if (useCache) {
    bundleLocation = cacheBundleDir;
    console.log(
      `Reused cached bundle at ${bundleLocation} (saved bundle compilation time)`,
    );
  } else {
    // Ensure clean directory
    if (fs.existsSync(cacheBundleDir)) {
      fs.rmSync(cacheBundleDir, { recursive: true, force: true });
    }

    // Bundle to temp first, then copy to cache
    const tempBundleLocation = await bundle(entryPoint, () => undefined);

    // Copy temp bundle to cached_bundle directory
    fs.mkdirSync(cacheBundleDir, { recursive: true });

    const copyDir = (src: string, dest: string) => {
      fs.mkdirSync(dest, { recursive: true });
      const entries = fs.readdirSync(src, { withFileTypes: true });
      for (const entry of entries) {
        const srcPath = path.join(src, entry.name);
        const destPath = path.join(dest, entry.name);
        if (entry.isDirectory()) {
          copyDir(srcPath, destPath);
        } else {
          fs.copyFileSync(srcPath, destPath);
        }
      }
    };

    copyDir(tempBundleLocation, cacheBundleDir);
    bundleLocation = cacheBundleDir;
    console.log(
      `Bundle created in ${((Date.now() - bundleStart) / 1000).toFixed(1)}s and cached at ${bundleLocation}`,
    );
  }

  // Step 1.5: Stage audio assets from manifest (after bundle is confirmed valid)
  // renderer.py 不再直接将音频复制到 cached_bundle/public/（会被本脚本的
  // fs.rmSync 清除），而是通过 --audio-manifest 传入 [{src, dest}] 清单。
  // 本脚本在 bundle 就绪后复制，从根本上避免竞态条件。
  if (config.audioManifest) {
    const manifestEntries: Array<{ src: string; dest: string }> = JSON.parse(
      fs.readFileSync(config.audioManifest, "utf-8"),
    );
    for (const entry of manifestEntries) {
      const destPath = path.join(bundleLocation, "public", entry.dest);
      fs.mkdirSync(path.dirname(destPath), { recursive: true });
      fs.copyFileSync(entry.src, destPath);
      console.log(`  Staged audio: ${entry.dest}`);
    }
    console.log(`Staged ${manifestEntries.length} audio asset(s) into bundle`);
  }

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
  // Remotion ≥ 4.0.484 在 Linux/Windows NVIDIA 上支持 NVENC（h264_nvenc）。
  // 硬件编码激活条件：hardwareAcceleration=if-possible 且 **不设 crf / encodingMaxRate /
  // encodingBufferSize**（这些选项与硬件编码器不兼容，设了会静默回退 libx264）。
  // NVENC 不支持 crf；如需控质量用 videoBitrate（例 "8M"），这里保留默认。
  console.log("\n[3/3] Rendering video (GPU accelerated)...");
  console.log(
    "Hardware acceleration: if-possible → NVENC h264_nvenc (NVIDIA Linux/Windows)",
  );
  const renderStart = Date.now();

  await renderMedia({
    composition,
    serveUrl: bundleLocation,
    codec: "h264",
    audioCodec: "aac",
    outputLocation: config.output,
    inputProps: planJson,
    concurrency: config.concurrency,
    chromiumOptions: {
      gl: config.gl,
    },
    hardwareAcceleration: "if-possible",
    onLog: ({ level, message }) => {
      // 显式输出编码器选择 / 硬件加速相关日志，便于确认 NVENC 是否真正生效。
      if (/encoder|nvenc|h264|hardware|codec/i.test(message)) {
        console.log(`  [Remotion:${level}] ${message}`);
      }
    },
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
