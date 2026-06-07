import { ref, nextTick } from 'vue'
import type {
  TextMessageParams,
  DigitalHumanCapabilities,
  StreamExtend,
  DigitalHumanCallbacks,
} from '@/chat/digital-human/types/digital-human'

export type {
  TextMessageParams,
  DigitalHumanCapabilities,
  StreamExtend,
  DigitalHumanCallbacks,
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
    const wsUrl = ref<string | null>(null)
    const asrText = ref('')
    const error = ref<string | null>(null)
    const audioEnabled = ref(false)
    const speechRate = ref(1.0)

    // --- 实时生成缓存 (应对不可抗力断开) ---
    const CACHE_KEY = 'dh_current_generation_cache'
    const generationCache = ref(localStorage.getItem(CACHE_KEY) || '')
    let bufferedAssistantText = ''
    let pendingAssistantComplete = false
    let assistantFlushFallbackTimer: ReturnType<typeof setTimeout> | null = null
    let assistantRevealTimer: ReturnType<typeof setTimeout> | null = null
    let revealingAssistantText = false
    let assistantRevealBudget = 0
    let assistantRevealLastTickAt = 0
    let currentSpeechStartedAt = 0
    let currentSpeechReleasedCost = 0
    let calibratedRevealCharsPerSecond = 0
    let targetRevealCharsPerSecond = 0

    let cacheDebounceTimer: ReturnType<typeof setTimeout> | null = null
    function updateCache(text: string, append = true) {
        if (append) {
            generationCache.value += text
        } else {
            generationCache.value = text
        }

        if (cacheDebounceTimer) clearTimeout(cacheDebounceTimer)
        cacheDebounceTimer = setTimeout(() => {
            if (generationCache.value) {
                localStorage.setItem(CACHE_KEY, generationCache.value)
            } else {
                localStorage.removeItem(CACHE_KEY)
            }
        }, 300)
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
    let speechDetected = false
    let speechHangTimer: ReturnType<typeof setTimeout> | null = null
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
                callbacks?.onError?.('连接因长时间无互动自动断开')
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
        const explicitWsBase = (import.meta.env.VITE_BACKEND_WS_BASE as string | undefined)?.trim()
        const explicitHttpBase = (import.meta.env.VITE_BACKEND_HTTP_BASE as string | undefined)?.trim()

        let wsBase: string
        if (explicitWsBase) {
            wsBase = explicitWsBase.replace(/\/+$/, '')
        } else if (explicitHttpBase) {
            wsBase = explicitHttpBase
                .replace(/\/+$/, '')
                .replace(/^http:/i, 'ws:')
                .replace(/^https:/i, 'wss:')
        } else {
            const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
            wsBase = `${proto}//${location.host}`
        }
        return `${wsBase}/ws/avatar?token=${encodeURIComponent(token)}`
    }

    async function connect(): Promise<void> {
        if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
            return
        }

        const url = buildWsUrl()
        wsUrl.value = url
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
            // 注意：发生异常断开时，我们不去清空 generationCache，以便重连时能够保留并恢复显示断开前的内容
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
        bufferedAssistantText = ''
        pendingAssistantComplete = false
        clearAssistantFlushFallbackTimer()
        clearAssistantRevealTimer()
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
            bufferedAssistantText = ''
            pendingAssistantComplete = false
            clearAssistantFlushFallbackTimer()
            clearAssistantRevealTimer()
            callbacks?.onAsrResult?.(data.content || '')
        } else if (type === 'assistant_chunk') {
            updateCache(data.content || '', true) // 实时追加到缓存
            bufferedAssistantText += data.content || ''
            if (isSpeaking.value) {
                startAssistantReveal()
            }
        } else if (type === 'status') {
            callbacks?.onStatus?.(data.data || {})
        } else if (type === 'assistant_complete') {
            pendingAssistantComplete = true
            clearAssistantFlushFallbackTimer()
            assistantFlushFallbackTimer = setTimeout(() => {
                if (!isSpeaking.value) {
                    startAssistantReveal()
                }
            }, 1200)
        } else if (type === 'avatar_speaking') {
            isSpeaking.value = true
            currentSpeechStartedAt = Date.now()
            currentSpeechReleasedCost = 0
            const estimatedCost = estimateBufferedTextCost(bufferedAssistantText)
            const baselineRate = calibratedRevealCharsPerSecond > 0
                ? calibratedRevealCharsPerSecond
                : (3.1 + (Math.max(0.8, Math.min(1.5, Number(speechRate.value) || 1.0)) - 0.8) * 2.6)
            const estimatedDurationSec = Math.max(1.2, estimatedCost / Math.max(2.2, baselineRate))
            targetRevealCharsPerSecond = Math.max(2.2, Math.min(7.5, estimatedCost / estimatedDurationSec))
            startAssistantReveal()
        } else if (type === 'diagram') {
            callbacks?.onDiagram?.(data.data)
        } else if (type === 'avatar_stopped') {
            isSpeaking.value = false
            if (currentSpeechStartedAt > 0 && currentSpeechReleasedCost > 0) {
                const elapsedSec = Math.max(0.25, (Date.now() - currentSpeechStartedAt) / 1000)
                const actualRate = currentSpeechReleasedCost / elapsedSec
                const clampedActualRate = Math.max(2.2, Math.min(7.5, actualRate))
                if (calibratedRevealCharsPerSecond <= 0) {
                    calibratedRevealCharsPerSecond = clampedActualRate
                } else {
                    calibratedRevealCharsPerSecond =
                        calibratedRevealCharsPerSecond * 0.7 + clampedActualRate * 0.3
                }
            }
            currentSpeechStartedAt = 0
            currentSpeechReleasedCost = 0
            targetRevealCharsPerSecond = 0
            finalizeBufferedAssistantTurn()
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
            // Container not ready yet - save stream data and init later when container arrives
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
        if (params.session_id) msg.session_id = params.session_id
        if (params.history?.length) msg.history = params.history
        if (params.attachments?.length) msg.attachments = params.attachments
        if (typeof params.enable_search === 'boolean') msg.enable_search = params.enable_search
        if (typeof params.generate_video === 'boolean') msg.generate_video = params.generate_video
                if (typeof params.speech_rate === 'number') msg.speech_rate = params.speech_rate

        ws.send(JSON.stringify(msg))
        resetIdleTimer()

        // Auto-enable audio on first text send
        if (!audioEnabled.value && isAvatarReady.value) {
            enableAudio()
        }
    }

    // ==========================================
    // Voice Activity Detection (VAD) + mic capture
    // ==========================================

    async function startVad(needDiagram = false, capabilities: DigitalHumanCapabilities = {}): Promise<void> {
        if (vadActive) return
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            error.value = '数字人未连接，无法开启语音输入'
            callbacks?.onError?.(error.value)
            return
        }

        try {
            // Tell backend to prepare VAD/ASR queue and carry diagram preference atomically.
            backendVadReady = false
            ws.send(JSON.stringify({
                type: 'start_vad',
                need_diagram: !!needDiagram,
                ...capabilities,
            }))

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
                if (!vadActive || !backendVadReady || !ws || ws.readyState !== WebSocket.OPEN) return

                const inputData = e.inputBuffer.getChannelData(0)
                let sum = 0
                const pcmData = new Int16Array(inputData.length)
                for (let i = 0; i < inputData.length; i++) {
                    const sample = inputData[i] ?? 0
                    const s = Math.max(-1, Math.min(1, sample))
                    sum += s * s
                    pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7fff
                }
                const rms = Math.sqrt(sum / Math.max(1, inputData.length))
                const speakingNow = rms > 0.02
                if (speakingNow) {
                    if (!speechDetected) {
                        speechDetected = true
                        callbacks?.onSpeechDetectedChange?.(true)
                    }
                    if (speechHangTimer) {
                        clearTimeout(speechHangTimer)
                        speechHangTimer = null
                    }
                    speechHangTimer = setTimeout(() => {
                        speechDetected = false
                        callbacks?.onSpeechDetectedChange?.(false)
                        speechHangTimer = null
                    }, 700)
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
        backendVadReady = false
        if (speechHangTimer) {
            clearTimeout(speechHangTimer)
            speechHangTimer = null
        }
        if (speechDetected) {
            speechDetected = false
            callbacks?.onSpeechDetectedChange?.(false)
        }
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

    function setSpeechRate(rate: number): void {
        const clamped = Math.max(0.8, Math.min(1.5, Number(rate) || 1.0))
        speechRate.value = clamped
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'set_speech_rate', speech_rate: clamped }))
        }
    }

    function clearAssistantFlushFallbackTimer(): void {
        if (assistantFlushFallbackTimer) {
            clearTimeout(assistantFlushFallbackTimer)
            assistantFlushFallbackTimer = null
        }
    }

    function clearAssistantRevealTimer(): void {
        if (assistantRevealTimer) {
            clearTimeout(assistantRevealTimer)
            assistantRevealTimer = null
        }
        revealingAssistantText = false
        assistantRevealBudget = 0
        assistantRevealLastTickAt = 0
        currentSpeechReleasedCost = 0
        targetRevealCharsPerSecond = 0
    }

    function isCjkCharacter(char: string): boolean {
        return /[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]/.test(char)
    }

    function takeNextRevealUnit(text: string): string {
        if (!text) return ''
        if (text.startsWith('\r\n')) return '\r\n'
        if (text.startsWith('\n')) return '\n'

        const first = text[0] || ''
        if (isCjkCharacter(first) || /[，。！？；：、“”‘’（）《》【】]/.test(first)) {
            return first
        }

        const word = text.match(/^[A-Za-z0-9_]+(?:['-][A-Za-z0-9_]+)*/)
        if (word) {
            let unit = word[0]
            let idx = unit.length
            while (idx < text.length && /\s/.test(text[idx] || '')) {
                unit += text[idx]
                idx += 1
            }
            return unit
        }

        return first
    }

    function getRevealCharsPerSecond(): number {
        const rate = Math.max(0.8, Math.min(1.5, Number(speechRate.value) || 1.0))
        const estimated = 1.7 + (rate - 0.8) * 3.2
        if (targetRevealCharsPerSecond > 0) {
            return Math.max(1.2, Math.min(7.2, targetRevealCharsPerSecond * (0.78 + (rate - 0.8) * 0.95)))
        }
        if (calibratedRevealCharsPerSecond > 0) {
            return Math.max(1.2, Math.min(7.2, calibratedRevealCharsPerSecond * (0.78 + (rate - 0.8) * 0.95)))
        }
        return estimated
    }

    function getRevealUnitCost(unit: string): number {
        const trimmed = unit.trim()
        if (!trimmed) return 0.55
        if (/^[。！？!?]$/.test(trimmed)) return 5.4
        if (/^[，,；;：:]$/.test(trimmed)) return 5.4
        if (/^[A-Za-z0-9_]+(?:['-][A-Za-z0-9_]+)*$/.test(trimmed)) {
            return Math.max(1.5, Math.min(2.8, trimmed.length * 0.38 + 0.9))
        }
        return 1
    }

    function getRevealTickDelayMs(): number {
        return 64
    }

    function estimateBufferedTextCost(text: string): number {
        let remaining = text
        let total = 0
        while (remaining) {
            const unit = takeNextRevealUnit(remaining)
            if (!unit) break
            total += getRevealUnitCost(unit)
            remaining = remaining.slice(unit.length)
        }
        return total
    }

    function revealBufferedAssistantTextStep(): void {
        assistantRevealTimer = null

        if (!bufferedAssistantText) {
            revealingAssistantText = false
            if (pendingAssistantComplete && !isSpeaking.value) {
                pendingAssistantComplete = false
                callbacks?.onAssistantComplete?.()
                updateCache('', false)
            }
            return
        }

        const now = Date.now()
        if (!assistantRevealLastTickAt) {
            assistantRevealLastTickAt = now
        }
        const elapsedMs = Math.max(0, now - assistantRevealLastTickAt)
        assistantRevealLastTickAt = now
        assistantRevealBudget += getRevealCharsPerSecond() * (elapsedMs / 1000)

        let emitted = ''
        while (bufferedAssistantText) {
            const nextUnit = takeNextRevealUnit(bufferedAssistantText)
            const unitCost = getRevealUnitCost(nextUnit)
            if (emitted && assistantRevealBudget < unitCost) {
                break
            }
            if (!emitted && assistantRevealBudget < unitCost) {
                assistantRevealBudget += 0.45
                break
            }
            bufferedAssistantText = bufferedAssistantText.slice(nextUnit.length)
            assistantRevealBudget = Math.max(0, assistantRevealBudget - unitCost)
            currentSpeechReleasedCost += unitCost
            emitted += nextUnit
        }

        if (emitted) {
            callbacks?.onAssistantChunk?.(emitted)
        }

        if (bufferedAssistantText) {
            revealingAssistantText = true
            assistantRevealTimer = setTimeout(revealBufferedAssistantTextStep, getRevealTickDelayMs())
            return
        }

        revealingAssistantText = false
        assistantRevealBudget = 0
        assistantRevealLastTickAt = 0
        if (pendingAssistantComplete && !isSpeaking.value) {
            pendingAssistantComplete = false
            callbacks?.onAssistantComplete?.()
            updateCache('', false)
        }
    }

    function startAssistantReveal(): void {
        if (revealingAssistantText || !bufferedAssistantText) return
        revealingAssistantText = true
        assistantRevealLastTickAt = Date.now()
        assistantRevealBudget = Math.max(assistantRevealBudget, 0.2)
        assistantRevealTimer = setTimeout(revealBufferedAssistantTextStep, getRevealTickDelayMs() + 180)
    }

    function flushBufferedAssistantTextImmediately(): void {
        if (!bufferedAssistantText) return
        callbacks?.onAssistantChunk?.(bufferedAssistantText)
        bufferedAssistantText = ''
    }

    function finalizeBufferedAssistantTurn(forceImmediate = false): void {
        if (forceImmediate) {
            clearAssistantRevealTimer()
            flushBufferedAssistantTextImmediately()
        } else if (bufferedAssistantText && !revealingAssistantText) {
            startAssistantReveal()
            return
        }

        if (pendingAssistantComplete) {
            pendingAssistantComplete = false
            callbacks?.onAssistantComplete?.()
            updateCache('', false)
        }
        clearAssistantFlushFallbackTimer()
    }

    function setNeedDiagram(enabled: boolean): void {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'set_need_diagram', need_diagram: !!enabled }))
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
        wsUrl,
        asrText,
        error,
        audioEnabled,
        speechRate,
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
        setSpeechRate,
        setNeedDiagram,
        enableAudio,
        setPlayerContainer,
    }
}
