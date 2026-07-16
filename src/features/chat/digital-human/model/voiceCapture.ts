import voiceCaptureWorkletUrl from './voiceCapture.worklet.js?worker&url'

export const ASR_TARGET_SAMPLE_RATE = 16_000
export const ASR_FRAME_DURATION_MS = 40
export const ASR_FRAME_SAMPLES = ASR_TARGET_SAMPLE_RATE * ASR_FRAME_DURATION_MS / 1000
export const ASR_FALLBACK_PROCESSOR_BUFFER_SIZE = 1024

export interface VoiceCaptureFrame {
  pcm: ArrayBuffer
  rms: number
  durationMs: number
}

export type VoiceCaptureFrameHandler = (frame: VoiceCaptureFrame) => void

export function calculateAudioRms(samples: ArrayLike<number>): number {
  if (samples.length === 0) return 0
  let sum = 0
  for (let index = 0; index < samples.length; index++) {
    const sample = samples[index] ?? 0
    sum += sample * sample
  }
  return Math.sqrt(sum / samples.length)
}

export function resampleAudioForAsr(
  input: Float32Array,
  inputSampleRate: number,
  outputSampleRate = ASR_TARGET_SAMPLE_RATE,
): Float32Array {
  if (input.length === 0 || inputSampleRate === outputSampleRate) return input
  if (
    !Number.isFinite(inputSampleRate)
    || !Number.isFinite(outputSampleRate)
    || inputSampleRate <= 0
    || outputSampleRate <= 0
  ) return input

  const outputLength = Math.max(1, Math.round(input.length * outputSampleRate / inputSampleRate))
  const output = new Float32Array(outputLength)
  if (inputSampleRate > outputSampleRate) {
    const ratio = input.length / outputLength
    for (let outputIndex = 0; outputIndex < outputLength; outputIndex++) {
      const start = outputIndex * ratio
      const end = Math.min(input.length, (outputIndex + 1) * ratio)
      let weightedSum = 0
      let weight = 0
      for (let inputIndex = Math.floor(start); inputIndex < Math.ceil(end); inputIndex++) {
        const overlap = Math.min(end, inputIndex + 1) - Math.max(start, inputIndex)
        if (overlap <= 0) continue
        weightedSum += (input[inputIndex] ?? 0) * overlap
        weight += overlap
      }
      output[outputIndex] = weight > 0 ? weightedSum / weight : 0
    }
    return output
  }

  if (outputLength === 1 || input.length === 1) {
    output[0] = input[0] ?? 0
    return output
  }
  const ratio = (input.length - 1) / (outputLength - 1)
  for (let outputIndex = 0; outputIndex < outputLength; outputIndex++) {
    const position = outputIndex * ratio
    const left = Math.floor(position)
    const right = Math.min(input.length - 1, left + 1)
    const fraction = position - left
    output[outputIndex] = (input[left] ?? 0) * (1 - fraction) + (input[right] ?? 0) * fraction
  }
  return output
}

function floatToPcm16(input: Float32Array): Int16Array {
  const pcm = new Int16Array(input.length)
  for (let index = 0; index < input.length; index++) {
    const sample = Math.max(-1, Math.min(1, input[index] ?? 0))
    pcm[index] = sample < 0 ? Math.round(sample * 0x8000) : Math.round(sample * 0x7fff)
  }
  return pcm
}

class PcmFrameAccumulator {
  private samples: number[] = []

  push(input: Float32Array, handler: VoiceCaptureFrameHandler): void {
    for (const sample of input) this.samples.push(sample)
    while (this.samples.length >= ASR_FRAME_SAMPLES) {
      const frame = new Float32Array(this.samples.splice(0, ASR_FRAME_SAMPLES))
      const pcm = floatToPcm16(frame)
      handler({
        pcm: pcm.buffer.slice(0) as ArrayBuffer,
        rms: calculateAudioRms(frame),
        durationMs: ASR_FRAME_DURATION_MS,
      })
    }
  }

  clear(): void {
    this.samples.length = 0
  }
}

export class VoiceCapture {
  private context: AudioContext | null = null
  private stream: MediaStream | null = null
  private source: MediaStreamAudioSourceNode | null = null
  private processor: AudioWorkletNode | ScriptProcessorNode | null = null
  private processorKind: 'worklet' | 'script' | null = null
  private sink: GainNode | null = null
  private enabled = false
  private readonly fallbackFrames = new PcmFrameAccumulator()
  private readonly onFrame: VoiceCaptureFrameHandler

  constructor(onFrame: VoiceCaptureFrameHandler) {
    this.onFrame = onFrame
  }

  get contextState(): AudioContextState | 'missing' {
    return this.context?.state ?? 'missing'
  }

  get ready(): boolean {
    const track = this.stream?.getAudioTracks?.()[0] ?? this.stream?.getTracks?.()[0]
    return !!this.context
      && (this.context.state === 'running' || this.context.state === undefined)
      && !!track
      && (!track.readyState || track.readyState === 'live')
      && track.enabled !== false
      && track.muted !== true
      && !!this.processor
  }

  async prime(): Promise<void> {
    if (!this.context || this.context.state === 'closed') {
      this.context = new AudioContext({ sampleRate: ASR_TARGET_SAMPLE_RATE })
    }
    if (this.context.state === 'suspended') await this.context.resume()
  }

  async start(): Promise<void> {
    await this.prime()
    if (this.ready) {
      this.enabled = true
      return
    }

    await this.releaseGraph(false)
    const context = this.context
    if (!context) throw new Error('Microphone AudioContext is unavailable')

    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: ASR_TARGET_SAMPLE_RATE,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    })
    this.source = context.createMediaStreamSource(this.stream)

    if (context.audioWorklet && typeof AudioWorkletNode !== 'undefined') {
      await context.audioWorklet.addModule(voiceCaptureWorkletUrl)
      const worklet = new AudioWorkletNode(context, 'digital-human-voice-capture')
      worklet.port.onmessage = (event: MessageEvent<VoiceCaptureFrame>) => {
        if (!this.enabled || !(event.data?.pcm instanceof ArrayBuffer)) return
        this.onFrame(event.data)
      }
      this.processor = worklet
      this.processorKind = 'worklet'
    } else {
      const processor = context.createScriptProcessor(ASR_FALLBACK_PROCESSOR_BUFFER_SIZE, 1, 1)
      processor.onaudioprocess = (event) => {
        if (!this.enabled) return
        const input = event.inputBuffer.getChannelData(0)
        const inputRate = event.inputBuffer.sampleRate || context.sampleRate
        this.fallbackFrames.push(resampleAudioForAsr(input, inputRate), this.onFrame)
      }
      this.processor = processor
      this.processorKind = 'script'
    }

    if (typeof context.createGain === 'function') {
      this.sink = context.createGain()
      this.sink.gain.value = 0
      this.source.connect(this.processor)
      this.processor.connect(this.sink)
      this.sink.connect(context.destination)
    } else {
      this.source.connect(this.processor)
      this.processor.connect(context.destination)
    }
    this.enabled = true
  }

  pause(): void {
    this.enabled = false
    this.fallbackFrames.clear()
  }

  resume(): boolean {
    if (!this.ready) return false
    this.enabled = true
    return true
  }

  async stop(): Promise<void> {
    this.enabled = false
    await this.releaseGraph(true)
  }

  private async releaseGraph(closeContext: boolean): Promise<void> {
    if (this.processorKind === 'script' && this.processor) {
      const scriptProcessor = this.processor as ScriptProcessorNode
      scriptProcessor.onaudioprocess = null
    }
    if (this.processorKind === 'worklet' && this.processor) {
      const workletProcessor = this.processor as AudioWorkletNode
      workletProcessor.port.onmessage = null
    }
    try { this.processor?.disconnect() } catch {}
    try { this.source?.disconnect() } catch {}
    try { this.sink?.disconnect() } catch {}
    this.processor = null
    this.processorKind = null
    this.source = null
    this.sink = null
    this.fallbackFrames.clear()
    this.stream?.getTracks().forEach((track) => track.stop())
    this.stream = null

    if (closeContext && this.context) {
      const context = this.context
      this.context = null
      if (context.state !== 'closed') await context.close().catch(() => {})
    }
  }
}
