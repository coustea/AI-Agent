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

export function isGreenScreenPixel(
  red: number,
  green: number,
  blue: number,
  options: GreenScreenOptions = {},
): boolean {
  const opts = { ...DEFAULT_OPTIONS, ...options }
  const dominance = green - Math.max(red, blue)
  const redGreenGap = Math.abs(red - green)

  return (
    green >= opts.minGreen
    && dominance >= opts.greenDominance
    && redGreenGap <= opts.maxRedGreenGap
  )
}

export function applyGreenScreenAlpha(
  pixels: Uint8ClampedArray,
  options: GreenScreenOptions = {},
): void {
  for (let index = 0; index < pixels.length; index += 4) {
    const red = pixels[index] ?? 0
    const green = pixels[index + 1] ?? 0
    const blue = pixels[index + 2] ?? 0

    if (isGreenScreenPixel(red, green, blue, options)) {
      pixels[index + 3] = 0
    }
  }
}
