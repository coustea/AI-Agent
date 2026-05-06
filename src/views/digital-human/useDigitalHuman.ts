import { ref, nextTick } from 'vue'

// ==========================================
// Types
// ==========================================

export interface TextMessageParams {
  text: string
  image_urls?: string[]
  file_urls?: string[]
  attachments?: Array<{ url: string; type: string }>
}

export interface StreamExtend {
  user_sign?: string
  appid?: string
  [key: string]: unknown
}

export interface DigitalHumanCallbacks {
  onAssistantChunk?: (chunk: string) => void
  onAsrResult?: (text: string) => void
  onError?: (msg: string) => void
  onConnectionChange?: (connected: boolean) => void
  onAvatarReady?: (ready: boolean) => void
  onVadStateChange?: (listening: boolean) => void
  onHistoryCleared?: (data: { session_id: string; deleted_count: number }) => void
}

// ==========================================
// Composable
// ==========================================

export function useDigitalHuman(callbacks?: DigitalHumanCallbacks) {
  // --- Reactive state ---
  const isConnected = ref(false)
  const isAvatarReady = ref(false)
  const isSpeaking = ref(false)
  const isListening = ref(false)
  const streamUrl = ref<string | null>(null)
  const streamExtend = ref<StreamExtend | null>(null)
  const asrText = ref('')
  const error = ref<string | null>(null)
  const audioEnabled = ref(false)

  // --- Internal state (not reactive, not exposed) ---
  let ws: WebSocket | null = null
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let player: any = null
  let audioContext: AudioContext | null = null
  let audioStream: MediaStream | null = null
  let audioMonitor: ReturnType<typeof setInterval> | null = null
  let vadActive = false
  let playerContainer: HTMLElement | null = null
  // Pending stream data: saved when stream_info arrives before container is ready
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let pendingStreamData: { url: string; extend: Record<string, any> } | null = null

  // ==========================================
  // WebSocket connection
  // ==========================================

  function buildWsUrl(): string {
    const token = localStorage.getItem('token') || ''
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${proto}//${location.host}/ws/avatar?token=${encodeURIComponent(token)}`
  }

  async function connect(): Promise<void> {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      return
    }

    const url = buildWsUrl()
    console.log('[DH] connecting to', url.replace(/token=[^&]+/, 'token=***'))

    ws = new WebSocket(url)

    ws.onopen = () => {
      isConnected.value = true
      error.value = null
      callbacks?.onConnectionChange?.(true)
      console.log('[DH] connected')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleMessage(data)
      } catch (e) {
        console.error('[DH] failed to parse message:', e)
      }
    }

    ws.onclose = (event) => {
      isConnected.value = false
      callbacks?.onConnectionChange?.(false)
      if (event.code === 4001) {
        error.value = '认证失败，请重新登录'
        callbacks?.onError?.(error.value)
      }
      console.log('[DH] disconnected, code:', event.code)
    }

    ws.onerror = () => {
      error.value = 'WebSocket 连接失败'
      callbacks?.onError?.(error.value)
    }
  }

  function disconnect(): void {
    stopVad()
    destroyPlayer()

    if (audioMonitor) {
      clearInterval(audioMonitor)
      audioMonitor = null
    }

    if (ws) {
      ws.onclose = null // prevent callback on intentional close
      ws.close()
      ws = null
    }

    isConnected.value = false
    isAvatarReady.value = false
    isSpeaking.value = false
    isListening.value = false
    streamUrl.value = null
    streamExtend.value = null
    audioEnabled.value = false
    error.value = null
    pendingStreamData = null
    callbacks?.onConnectionChange?.(false)
  }

  // ==========================================
  // Server message handler
  // ==========================================

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  function handleMessage(data: Record<string, any>): void {
    const { type } = data

    if (type === 'stream_info') {
      handleStreamInfo(data)
    } else if (type === 'asr_result') {
      asrText.value = data.content || ''
      callbacks?.onAsrResult?.(data.content || '')
    } else if (type === 'assistant_chunk') {
      isSpeaking.value = true
      callbacks?.onAssistantChunk?.(data.content || '')
    } else if (type === 'assistant_complete') {
      isSpeaking.value = false
    } else if (type === 'avatar_stopped') {
      isSpeaking.value = false
    } else if (type === 'vad_state') {
      const state = data.data?.listening ?? (data.state === 'listening' || data.state === 'speaking')
      isListening.value = !!state
      callbacks?.onVadStateChange?.(!!state)
    } else if (type === 'history_cleared') {
      callbacks?.onHistoryCleared?.(data.data)
    } else if (type === 'error') {
      error.value = data.content || data.message || '未知错误'
      callbacks?.onError?.(error.value!)
    }
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  function handleStreamInfo(data: Record<string, any>): void {
    const url = data.stream_url || data.data?.stream_url
    const extend = data.stream_extend || data.data?.stream_extend || {}

    if (data.reconnected) {
      // Reconnection: destroy and reinit player
      console.log('[DH] stream reconnected, reinitializing player')
      const wasAudioEnabled = audioEnabled.value
      destroyPlayer()

      nextTick(() => {
        streamUrl.value = url || null
        streamExtend.value = extend
        isAvatarReady.value = true
        callbacks?.onAvatarReady?.(true)
        initPlayer(url, extend)
        if (wasAudioEnabled) {
          setTimeout(() => enableAudio(), 1000)
        }
      })
    } else {
      // First connection
      streamUrl.value = url || null
      streamExtend.value = extend
      isAvatarReady.value = true
      callbacks?.onAvatarReady?.(true)
      initPlayer(url, extend)
    }
  }

  // ==========================================
  // RTCPlayer
  // ==========================================

  function parseXrtcsUrl(url: string): { host: string; roomId: string } {
    const withoutScheme = url.replace('xrtcs://', '').replace('xrtc://', '')
    const firstSlash = withoutScheme.indexOf('/')
    return {
      host: firstSlash > 0 ? withoutScheme.substring(0, firstSlash) : withoutScheme,
      roomId: firstSlash > 0 ? withoutScheme.substring(firstSlash + 1) : '',
    }
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  function initPlayer(url: string, extend: Record<string, any>): void {
    if (!url) {
      console.warn('[DH] cannot init player: no stream url')
      return
    }

    if (!playerContainer) {
      // Container not ready yet — save stream data and init later when container arrives
      console.log('[DH] player container not ready, saving stream data for later')
      pendingStreamData = { url, extend }
      return
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const RTCPlayer = (window as any).Interactive?.RTCPlayer
    if (!RTCPlayer) {
      console.error('[DH] RTCPlayer SDK not loaded')
      return
    }

    const parsed = parseXrtcsUrl(url)

    try {
      player = new RTCPlayer()
      player.container = playerContainer
      player.videoSize = { width: 720, height: 1280 }
      player.stream = {
        server: `wss://${parsed.host}`,
        auth: extend.user_sign || '',
        appid: extend.appid || '',
        userId: 'user_' + Math.random().toString(36).substring(2, 10),
        roomId: parsed.roomId,
      }

      player.play().then(() => {
        console.log('[DH] player started')
      }).catch((err: unknown) => {
        console.error('[DH] player error:', err)
      })
    } catch (err) {
      console.error('[DH] player init failed:', err)
    }
  }

  function destroyPlayer(): void {
    if (player) {
      try {
        player.destroy()
      } catch {
        // ignore
      }
      player = null
    }
    // Clear all children from container
    if (playerContainer) {
      while (playerContainer.firstChild) {
        playerContainer.removeChild(playerContainer.firstChild)
      }
    }
  }

  /**
   * Set the DOM element where RTCPlayer should render.
   * Called by DigitalHumanCanvas via ref.
   */
  function setPlayerContainer(el: HTMLElement | null): void {
    playerContainer = el
    // If stream data arrived before container was ready, init player now
    if (el && pendingStreamData) {
      console.log('[DH] container now ready, initializing pending player')
      const { url, extend } = pendingStreamData
      pendingStreamData = null
      initPlayer(url, extend)
    }
  }

  // ==========================================
  // Audio enable (unmute player output)
  // ==========================================

  function enableAudio(): void {
    if (!playerContainer) return

    const mediaElements = playerContainer.querySelectorAll('video, audio')
    if (mediaElements.length === 0) {
      // Retry after a short delay (player may still be initializing)
      setTimeout(() => {
        if (!playerContainer) return
        const retry = playerContainer.querySelectorAll('video, audio')
        if (retry.length > 0) {
          unmuteElements(retry)
          startAudioMonitor()
          audioEnabled.value = true
        }
      }, 500)
      return
    }

    unmuteElements(mediaElements)
    startAudioMonitor()
    audioEnabled.value = true
  }

  function unmuteElements(elements: NodeListOf<Element>): void {
    elements.forEach((media) => {
      const el = media as HTMLMediaElement
      el.muted = false
      el.volume = 1.0
      el.play().catch(() => {})
    })
  }

  function startAudioMonitor(): void {
    if (audioMonitor) return
    audioMonitor = setInterval(() => {
      if (!playerContainer) return
      playerContainer.querySelectorAll('video, audio').forEach((media) => {
        const el = media as HTMLMediaElement
        if (el.volume !== 1.0) el.volume = 1.0
      })
    }, 2000)
  }

  // ==========================================
  // Text messaging
  // ==========================================

  function sendText(params: TextMessageParams): void {
    if (!ws || ws.readyState !== WebSocket.OPEN) return

    const msg: Record<string, unknown> = { type: 'text_input', text: params.text }
    if (params.image_urls?.length) msg.image_urls = params.image_urls
    if (params.file_urls?.length) msg.file_urls = params.file_urls
    if (params.attachments?.length) msg.attachments = params.attachments

    ws.send(JSON.stringify(msg))

    // Auto-enable audio on first text send
    if (!audioEnabled.value && isAvatarReady.value) {
      enableAudio()
    }
  }

  // ==========================================
  // Voice Activity Detection (VAD) + mic capture
  // ==========================================

  async function startVad(): Promise<void> {
    if (vadActive) return

    try {
      audioStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      })

      audioContext = new AudioContext({ sampleRate: 16000 })
      const source = audioContext.createMediaStreamSource(audioStream)
      const processor = audioContext.createScriptProcessor(4096, 1, 1)

      processor.onaudioprocess = (e) => {
        if (!vadActive || !ws || ws.readyState !== WebSocket.OPEN) return

        const inputData = e.inputBuffer.getChannelData(0)
        const pcmData = new Int16Array(inputData.length)
        for (let i = 0; i < inputData.length; i++) {
          const sample = inputData[i] ?? 0
          const s = Math.max(-1, Math.min(1, sample))
          pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7fff
        }

        const uint8Array = new Uint8Array(pcmData.buffer)
        let binary = ''
        for (let i = 0; i < uint8Array.length; i++) {
          binary += String.fromCharCode(uint8Array[i] ?? 0)
        }
        const base64 = btoa(binary)

        ws.send(JSON.stringify({ type: 'audio_chunk', audio: base64 }))
      }

      source.connect(processor)
      processor.connect(audioContext.destination)

      vadActive = true
      isListening.value = true

      // Send start_vad to backend
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'start_vad' }))
      }

      // Auto-enable audio
      if (!audioEnabled.value && isAvatarReady.value) {
        enableAudio()
      }
    } catch (err) {
      console.error('[DH] mic error:', err)
      error.value = '无法访问麦克风，请检查权限设置'
      callbacks?.onError?.(error.value)
    }
  }

  function stopVad(): void {
    if (!vadActive) return

    // Stop mic tracks
    if (audioStream) {
      audioStream.getTracks().forEach((track) => track.stop())
      audioStream = null
    }

    // Close audio context
    if (audioContext) {
      audioContext.close()
      audioContext = null
    }

    // Notify backend
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'stop_vad' }))
    }

    vadActive = false
    isListening.value = false
    asrText.value = ''
  }

  function stopSpeaking(): void {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'stop_speaking' }))
    }
    isSpeaking.value = false
  }

  function clearHistory(): void {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'clear_history' }))
    }
  }

  // ==========================================
  // Return
  // ==========================================

  return {
    // State
    isConnected,
    isAvatarReady,
    isSpeaking,
    isListening,
    streamUrl,
    streamExtend,
    asrText,
    error,
    audioEnabled,

    // Methods
    connect,
    disconnect,
    sendText,
    startVad,
    stopVad,
    stopSpeaking,
    clearHistory,
    enableAudio,
    setPlayerContainer,
  }
}
