import { ref, nextTick } from 'vue'

// ==========================================
// Types
// ==========================================

export interface TextMessageParams {
    text: string
    need_diagram?: boolean
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
    onAssistantComplete?: () => void
    onDiagram?: (diagram: unknown) => void
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

    // --- 实时生成缓存 (应对不可抗力断开) ---
    const CACHE_KEY = 'dh_current_generation_cache'
    const generationCache = ref(localStorage.getItem(CACHE_KEY) || '')

    function updateCache(text: string, append = true) {
        if (append) {
            generationCache.value += text
        } else {
            generationCache.value = text
        }

        if (generationCache.value) {
            localStorage.setItem(CACHE_KEY, generationCache.value)
        } else {
            localStorage.removeItem(CACHE_KEY)
        }
    }

    // --- Idle auto-disconnect ---
    const IDLE_TIMEOUT_MS = 180_000 // 180 seconds
    const idleCountdown = ref(0) // seconds remaining until auto-disconnect
    let idleTimer: ReturnType<typeof setInterval> | null = null

    // --- Internal state (not reactive, not exposed) ---
    let ws: WebSocket | null = null
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let player: any = null
    let audioContext: AudioContext | null = null
    let audioStream: MediaStream | null = null
    let audioMonitor: ReturnType<typeof setInterval> | null = null
    let vadActive = false
    let backendVadReady = false
    let playerContainer: HTMLElement | null = null
    // Pending stream data: saved when stream_info arrives before container is ready
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let pendingStreamData: { url: string; extend: Record<string, any> } | null = null

    // ==========================================
    // Idle auto-disconnect timer
    // ==========================================

    /** Reset the idle countdown to 60s. Call on any user interaction or server message. */
    function resetIdleTimer(): void {
        if (idleTimer) clearInterval(idleTimer)
        idleCountdown.value = Math.floor(IDLE_TIMEOUT_MS / 1000)

        idleTimer = setInterval(() => {
            // Do not auto-disconnect while actively speaking/listening.
            if (isSpeaking.value || isListening.value) {
                idleCountdown.value = Math.floor(IDLE_TIMEOUT_MS / 1000)
                return
            }
            idleCountdown.value--
            if (idleCountdown.value <= 0) {
                clearInterval(idleTimer!)
                idleTimer = null
                disconnect()
                callbacks?.onError?.('连接已因长时间无互动自动断开')
            }
        }, 1000)
    }

    function stopIdleTimer(): void {
        if (idleTimer) {
            clearInterval(idleTimer)
            idleTimer = null
        }
        idleCountdown.value = 0
    }

    // ==========================================
    // WebSocket connection
    // ==========================================

    function buildWsUrl(): string {
        const token = localStorage.getItem('token') || ''

        // 优先读取 .env.local 中的 VITE_BACKEND_WS_BASE
        const envWsBase = import.meta.env.VITE_BACKEND_WS_BASE

        let baseUrl = ''
        if (envWsBase) {
            baseUrl = envWsBase
        } else {
            // 降级方案：如果没有配置环境变量，就用当前浏览器的 host
            const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
            baseUrl = `${proto}//${location.host}`
        }

        return `${baseUrl}/ws/avatar?token=${encodeURIComponent(token)}`
    }

    async function connect(): Promise<void> {
        if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
            return
        }

        const url = buildWsUrl()
        ws = new WebSocket(url)

        ws.onopen = () => {
            isConnected.value = true
            error.value = null
            callbacks?.onConnectionChange?.(true)
            resetIdleTimer()
        }

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data)
                handleMessage(data)
                resetIdleTimer() // server activity resets idle
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
            // 发生异常断开时，我们不去清空 generationCache，以便重连时能够保留并恢复显示断开前的内容
        }

        ws.onerror = () => {
            error.value = 'WebSocket 连接失败'
            callbacks?.onError?.(error.value)
        }
    }

    function disconnect(): void {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'stop_speaking' }))
        }
        stopVad()
        stopIdleTimer()
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
        backendVadReady = false
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
            updateCache('', false) // 开始新一轮对话前清理上一轮残留
            callbacks?.onAsrResult?.(data.content || '')
        } else if (type === 'assistant_chunk') {
            isSpeaking.value = true
            updateCache(data.content || '', true) // 实时追加到缓存
            callbacks?.onAssistantChunk?.(data.content || '')
        } else if (type === 'assistant_complete') {
            isSpeaking.value = false
            try {
                callbacks?.onAssistantComplete?.()
            } finally {
                updateCache('', false) // 每一次数字人生成展示完成后删除该缓存
            }
        } else if (type === 'diagram') {
            callbacks?.onDiagram?.(data.data)
        } else if (type === 'avatar_stopped') {
            isSpeaking.value = false
        } else if (type === 'vad_state') {
            const state = data.data?.listening ?? (data.state === 'listening' || data.state === 'speaking')
            backendVadReady = !!state
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

        updateCache('', false) // 开始新的提问，清空旧缓存

        const msg: Record<string, unknown> = { type: 'text_input', text: params.text }
        if (typeof params.need_diagram === 'boolean') msg.need_diagram = params.need_diagram
        if (params.image_urls?.length) msg.image_urls = params.image_urls
        if (params.file_urls?.length) msg.file_urls = params.file_urls
        if (params.attachments?.length) msg.attachments = params.attachments

        ws.send(JSON.stringify(msg))
        resetIdleTimer()

        // Auto-enable audio on first text send
        if (!audioEnabled.value && isAvatarReady.value) {
            enableAudio()
        }
    }

    // ==========================================
    // Voice Activity Detection (VAD) + mic capture (AudioWorklet)
    // ==========================================

    async function startVad(): Promise<void> {
        if (vadActive) return
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            error.value = '数字人未连接，无法开启语音输入'
            callbacks?.onError?.(error.value)
            return
        }

        try {
            // Tell backend to prepare VAD/ASR queue before sending audio chunks.
            backendVadReady = false
            ws.send(JSON.stringify({ type: 'start_vad' }))

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

            // =========================================================
            // 使用 AudioWorklet 替代被废弃的 ScriptProcessorNode
            // =========================================================
            const workletCode = `
                class PCMProcessor extends AudioWorkletProcessor {
                    constructor() {
                        super();
                        this.bufferSize = 4096;
                        this.buffer = new Int16Array(this.bufferSize);
                        this.offset = 0;
                    }
                    process(inputs, outputs, parameters) {
                        const input = inputs[0];
                        if (input && input.length > 0) {
                            const channelData = input[0];
                            for (let i = 0; i < channelData.length; i++) {
                                const s = Math.max(-1, Math.min(1, channelData[i]));
                                // 将 Float32 (-1.0 ~ 1.0) 转为 Int16 PCM
                                this.buffer[this.offset] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                                this.offset++;
                                
                                // 当收集满 4096 帧时，向主线程抛出数据
                                if (this.offset >= this.bufferSize) {
                                    this.port.postMessage(this.buffer);
                                    this.buffer = new Int16Array(this.bufferSize); // Reset
                                    this.offset = 0;
                                }
                            }
                        }
                        return true;
                    }
                }
                registerProcessor('pcm-processor', PCMProcessor);
            `
            // 利用 Blob 创建一个本地 URL，避免引入外部静态 JS 文件
            const blob = new Blob([workletCode], { type: 'application/javascript' })
            const workletUrl = URL.createObjectURL(blob)

            await audioContext.audioWorklet.addModule(workletUrl)
            const workletNode = new AudioWorkletNode(audioContext, 'pcm-processor')

            workletNode.port.onmessage = (event: MessageEvent<Int16Array>) => {
                if (!vadActive || !backendVadReady || !ws || ws.readyState !== WebSocket.OPEN) return

                const pcmData = event.data
                const uint8Array = new Uint8Array(pcmData.buffer)

                // 将 Uint8Array 转为 Base64
                let binary = ''
                for (let i = 0; i < uint8Array.length; i++) {
                    binary += String.fromCharCode(uint8Array[i] ?? 0)
                }
                const base64 = btoa(binary)

                ws.send(JSON.stringify({ type: 'audio_chunk', audio: base64 }))
            }

            source.connect(workletNode)
            // 必须连接到 destination 以保证音频图持续处理 (worklet node 内部未操作 output，因此是静音的，不会产生回音)
            workletNode.connect(audioContext.destination)

            URL.revokeObjectURL(workletUrl) // 注册完毕后释放 URL 内存

            const waitStart = Date.now()
            while (!backendVadReady && Date.now() - waitStart < 1500) {
                await new Promise((resolve) => setTimeout(resolve, 50))
            }
            if (!backendVadReady) {
                throw new Error('VAD backend ack timeout')
            }

            vadActive = true
            isListening.value = true
            resetIdleTimer()

            // Auto-enable audio
            if (!audioEnabled.value && isAvatarReady.value) {
                enableAudio()
            }
        } catch (err) {
            console.error('[DH] mic error:', err)
            backendVadReady = false
            error.value = '无法访问麦克风或语音服务未就绪，请检查权限并重试'
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

        // Close audio context (这会自动停止释放 AudioWorkletNode)
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
        backendVadReady = false
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
        idleCountdown,
        generationCache, // 导出生成的缓存状态，UI层如果重新渲染可以获取它

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