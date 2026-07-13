export interface GreenScreenOptions {
  minGreen?: number
  greenDominance?: number
  maxRedGreenGap?: number
}

const DEFAULT_OPTIONS: Required<GreenScreenOptions> = {
  minGreen: 120,
  greenDominance: 18,
  maxRedGreenGap: 80,
}

// 判断单个像素是否为绿幕背景像素
export function isGreenScreenPixel(
  red: number,
  green: number,
  blue: number,
  options: GreenScreenOptions = {},
): boolean {
  const minGreen = options.minGreen ?? DEFAULT_OPTIONS.minGreen
  const greenDominance = options.greenDominance ?? DEFAULT_OPTIONS.greenDominance
  const maxRedGreenGap = options.maxRedGreenGap ?? DEFAULT_OPTIONS.maxRedGreenGap
  const dominance = green - Math.max(red, blue)
  const redGreenGap = Math.abs(red - green)

  return (
    green >= minGreen
    && dominance >= greenDominance
    && redGreenGap <= maxRedGreenGap
  )
}

// 将 RGBA 像素数据中绿幕像素的 alpha 通道置为 0
export function applyGreenScreenAlpha(
  pixels: Uint8ClampedArray,
  options: GreenScreenOptions = {},
): void {
  const minGreen = options.minGreen ?? DEFAULT_OPTIONS.minGreen
  const greenDominance = options.greenDominance ?? DEFAULT_OPTIONS.greenDominance
  const maxRedGreenGap = options.maxRedGreenGap ?? DEFAULT_OPTIONS.maxRedGreenGap

  for (let index = 0; index < pixels.length; index += 4) {
    const red = pixels[index] ?? 0
    const green = pixels[index + 1] ?? 0
    const blue = pixels[index + 2] ?? 0
    const dominance = green - Math.max(red, blue)
    const redGreenGap = Math.abs(red - green)

    if (
      green >= minGreen
      && dominance >= greenDominance
      && redGreenGap <= maxRedGreenGap
    ) {
      pixels[index + 3] = 0
    }
  }
}

export function computeChromaRenderSize(
  sourceWidth: number,
  sourceHeight: number,
  maxWidth = 360,
  maxHeight = 640,
): { width: number; height: number } {
  const safeWidth = Math.max(1, Math.floor(sourceWidth || maxWidth))
  const safeHeight = Math.max(1, Math.floor(sourceHeight || maxHeight))
  const scale = Math.min(1, maxWidth / safeWidth, maxHeight / safeHeight)
  return {
    width: Math.max(1, Math.round(safeWidth * scale)),
    height: Math.max(1, Math.round(safeHeight * scale)),
  }
}
