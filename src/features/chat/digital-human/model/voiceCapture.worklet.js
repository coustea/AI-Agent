const TARGET_SAMPLE_RATE = 16000
const FRAME_SAMPLES = 640

class DigitalHumanVoiceCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this.phase = 0
    this.sum = 0
    this.sampleCount = 0
    this.frame = new Int16Array(FRAME_SAMPLES)
    this.frameOffset = 0
  }

  process(inputs) {
    const input = inputs[0]?.[0]
    if (!input) return true

    for (let index = 0; index < input.length; index++) {
      const sample = Math.max(-1, Math.min(1, input[index] || 0))
      this.sum += sample
      this.sampleCount += 1
      this.phase += TARGET_SAMPLE_RATE

      if (this.phase < sampleRate) continue
      this.phase -= sampleRate

      const resampled = this.sum / this.sampleCount
      this.sum = 0
      this.sampleCount = 0
      this.frame[this.frameOffset++] = resampled < 0
        ? Math.round(resampled * 0x8000)
        : Math.round(resampled * 0x7fff)

      if (this.frameOffset !== FRAME_SAMPLES) continue

      let squareSum = 0
      for (let frameIndex = 0; frameIndex < FRAME_SAMPLES; frameIndex++) {
        const normalized = this.frame[frameIndex] / 0x8000
        squareSum += normalized * normalized
      }
      const pcm = this.frame.buffer
      this.port.postMessage({
        pcm,
        rms: Math.sqrt(squareSum / FRAME_SAMPLES),
        durationMs: 40,
      }, [pcm])
      this.frame = new Int16Array(FRAME_SAMPLES)
      this.frameOffset = 0
    }

    return true
  }
}

registerProcessor('digital-human-voice-capture', DigitalHumanVoiceCaptureProcessor)
