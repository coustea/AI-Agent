export type VadSessionPhase = 'idle' | 'preparing' | 'listening' | 'speaking' | 'transcribing'

export class VadSessionMachine {
  private sessionId: string | null = null
  private currentPhase: VadSessionPhase = 'idle'
  private upstreamReady = false
  private captureStarted = false

  get id(): string | null {
    return this.sessionId
  }

  get phase(): VadSessionPhase {
    return this.currentPhase
  }

  get hasSession(): boolean {
    return this.sessionId !== null
  }

  get backendReady(): boolean {
    return this.upstreamReady
  }

  get captureActive(): boolean {
    return this.captureStarted
  }

  get captureReady(): boolean {
    return this.captureStarted
  }

  get listening(): boolean {
    return this.currentPhase === 'listening' || this.currentPhase === 'speaking'
  }

  matches(sessionId: string | null): boolean {
    return !!sessionId && sessionId === this.sessionId
  }

  start(sessionId: string): void {
    if (this.hasSession) throw new Error('VAD session already active')
    this.sessionId = sessionId
    this.currentPhase = 'preparing'
    this.upstreamReady = false
    this.captureStarted = false
  }

  setBackendReady(sessionId: string, ready: boolean): boolean {
    if (!this.matches(sessionId)) return false
    this.upstreamReady = ready
    if (!ready) {
      this.captureStarted = false
      this.currentPhase = 'transcribing'
    } else {
      this.refreshListeningPhase()
    }
    return true
  }

  beginCapture(sessionId: string): boolean {
    if (!this.matches(sessionId) || this.currentPhase === 'transcribing') return false
    this.captureStarted = true
    this.refreshListeningPhase()
    return true
  }

  beginSpeech(): void {
    if (this.currentPhase === 'listening') this.currentPhase = 'speaking'
  }

  submit(): void {
    if (!this.hasSession) return
    this.captureStarted = false
    this.currentPhase = 'transcribing'
  }

  releaseCapture(): void {
    this.captureStarted = false
    if (this.currentPhase === 'listening' || this.currentPhase === 'speaking') {
      this.currentPhase = 'preparing'
    }
  }

  complete(sessionId?: string | null): boolean {
    if (sessionId && !this.matches(sessionId)) return false
    this.sessionId = null
    this.currentPhase = 'idle'
    this.upstreamReady = false
    this.captureStarted = false
    return true
  }

  private refreshListeningPhase(): void {
    if (this.currentPhase === 'transcribing') return
    this.currentPhase = this.upstreamReady && this.captureStarted
      ? 'listening'
      : 'preparing'
  }
}
