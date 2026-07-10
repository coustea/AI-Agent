import { ref, nextTick } from 'vue'
import type {
  TextMessageParams,
  DigitalHumanCapabilities,
  StreamExtend,
  DigitalHumanCallbacks,
  DigitalHumanStateType,
} from '@/features/chat/digital-human/model/digital-human'
import { getAuthToken } from '@/shared/auth/token'
import { isCjkCharacter } from '@/features/chat/views/tutorUtils'

export type {
  TextMessageParams,
  DigitalHumanCapabilities,
  StreamExtend,
  DigitalHumanCallbacks,
  DigitalHumanStateType,
}

export interface IdleDisconnectState {
    state: DigitalHumanStateType
    isSpeaking: boolean
    isListening: boolean
}

// 判断是否应暂停空闲自动断开（正在交互中不自动断开）
export function shouldPauseIdleDisconnect({ state, isSpeaking, isListening }: IdleDisconnectState): boolean {
    if (isSpeaking || isListening) return true
    return state === 'avatar_connecting'
        || state === 'recognizing'
        || state === 'thinking'
        || state === 'speaking'
        || state === 'listening'
}

export function shouldCleanupLocalVadOnBackendState(listening: boolean): boolean {
    return !listening
}

// 判断数字人状态是否应停止 VAD（thinking/speaking 期间不采集麦克风）
export function shouldStopVadForDigitalHumanState(state: DigitalHumanStateType): boolean {
    // "recognizing" 是 VAD 正常流程的一部分（识别用户语音），不应停止麦克风
    // 只有 thinking/speaking 状态才需要停止 VAD（LLM 推理和数字人播报期间不需要录音）
    return state === 'thinking' || state === 'speaking'
}

export function digitalHumanStateErrorMessage(state: DigitalHumanStateType, message?: string): string {
    if (state !== 'error') return ''
    return message?.trim() || '数字人服务连接失败'
}

export interface AvatarAudioOutputs {
    audible: HTMLMediaElement | null
    muted: HTMLMediaElement[]
}

function hasAudioTrack(media: HTMLMediaElement): boolean {
    const stream = media.srcObject
    return stream instanceof MediaStream && stream.getAudioTracks().length > 0
}

export function selectAvatarAudioOutputs(elements: Iterable<Element>): AvatarAudioOutputs {
    const mediaElements = Array.from(elements).filter(
        (element): element is HTMLMediaElement => element instanceof HTMLMediaElement,
    )
    const audible = mediaElements.find((element) => element instanceof HTMLAudioElement)
        ?? mediaElements.find(hasAudioTrack)
        ?? mediaElements[0]
        ?? null

    return {
        audible,
        muted: mediaElements.filter((element) => element !== audible),
    }
}

// ==========================================
// Composable
// ==========================================

// 数字人引擎：WebSocket + RTCPlayer + VAD 语音活动检测
export function useDigitalHuman(callbacks?: DigitalHumanCallbacks) {
    // --- 响应式状态 ---
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
    const digitalHumanState = ref<DigitalHumanStateType>('idle')

    // --- 轮次 ID 追踪（过滤过期事件） ---
    let activeTurnId: string | null = null

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
    // 更新 localStorage 缓存（断线重连后恢复字幕）
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
    // 当数字人说话时尝试启动 VAD，会暂存参数，等播报结束后自动重启
    let _pendingVadRestart: { needDiagram: boolean; capabilities: DigitalHumanCapabilities } | null = null
    // Pending stream data: saved when stream_info arrives before container is ready
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let pendingStreamData: { url: string; extend: Record<string, any> } | null = null

    // ==========================================
    // Idle auto-disconnect timer
    // ==========================================

    // 重置空闲倒计时（用户交互或服务端消息后调用）
    function resetIdleTimer(): void {
        if (idleTimer) clearInterval(idleTimer)
        idleCountdown.value = Math.floor(IDLE_TIMEOUT_MS / 1000)

        idleTimer = setInterval(() => {
            // Do not auto-disconnect while an interaction is still active.
            if (shouldPauseIdleDisconnect({
                state: digitalHumanState.value,
                isSpeaking: isSpeaking.value,
                isListening: isListening.value,
            })) {
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

    // 构建 WebSocket URL（支持环境变量配置）
    function buildWsUrl(): string {
        const token = getAuthToken() || ''
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

    // 建立 WebSocket 连接
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

    // 断开 WebSocket + 停止 VAD + 销毁播放器
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
        _pendingVadRestart = null
        clearAssistantFlushFallbackTimer()
        clearAssistantRevealTimer()
        callbacks?.onConnectionChange?.(false)
    }

    // ==========================================
    // Server message handler
    // ==========================================

    // 服务端消息分发：按 type 路由到不同处理逻辑
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    function handleMessage(data: Record<string, any>): void {
        const { type, turn_id } = data

        // Handle turn_start - sets new active turn
        if (type === 'turn_start') {
            activeTurnId = turn_id
            // Clear previous turn's buffered text
            bufferedAssistantText = ''
            pendingAssistantComplete = false
            clearAssistantFlushFallbackTimer()
            clearAssistantRevealTimer()
            return
        }

        // 过滤过期轮次的事件（turn_id 不匹配则丢弃）
        // 在 digital_human_state 处理前过滤，防止旧轮次状态污染
        // Apply this filter BEFORE handling digital_human_state to prevent old turn pollution
        const turnDependentTypes = [
            'assistant_chunk', 'assistant_complete',
            'avatar_speaking', 'avatar_stopped', 'diagram', 'status',
            'digital_human_state', 'error'  // Add digital_human_state and error to turn-dependent types
        ]
        if (turnDependentTypes.includes(type)) {
            // Filter if turn_id doesn't match activeTurnId
            if (turn_id && activeTurnId && turn_id !== activeTurnId) {
                // Stale event from previous turn - ignore
                console.warn('[DH] Ignoring stale turn event:', type, turn_id, 'current:', activeTurnId)
                return
            }
            // Also filter if we're waiting for turn_start (activeTurnId starts with 'pending_')
            // Exception: global errors without turn_id should not be filtered
            if (!turn_id && activeTurnId && activeTurnId.startsWith('pending_')) {
                // Event from old turn without turn_id - ignore while waiting for new turn_start
                console.warn('[DH] Ignoring event without turn_id while pending:', type, 'pending:', activeTurnId)
                return
            }
        }

        // 处理数字人状态变更事件（经过过期过滤后）
        if (type === 'digital_human_state') {
            const state = data.state as DigitalHumanStateType
            digitalHumanState.value = state
            if (shouldStopVadForDigitalHumanState(state) && vadActive) {
                stopVad()
            }
            const stateError = digitalHumanStateErrorMessage(state, data.message)
            if (stateError) {
                error.value = stateError
                isAvatarReady.value = false
                callbacks?.onError?.(stateError)
            }
            callbacks?.onDigitalHumanStateChange?.(state, turn_id)
            callbacks?.onStatus?.({ stage: state, message: data.message })
            // 当后端报告 thinking 状态时，立即通知前端进入思考模式
            // 这样用户可以在 LLM 推理阶段就看到思考动画，而不是等到 token 产出
            if (state === 'thinking') {
                callbacks?.onThinkingStart?.()
            }
            return
        }

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
            // 收到文本就立即开始 reveal，不等 avatar_speaking
            // 后端是 LLM 全部输出完才发 TTS，如果等 avatar_speaking 才 reveal，
            // 字幕会比语音延迟 3-4 秒
            startAssistantReveal()
        } else if (type === 'status') {
            callbacks?.onStatus?.(data.data || {})
        } else if (type === 'assistant_complete') {
            pendingAssistantComplete = true
            // 后端回答已完成，立即通知前端结束思考动画
            callbacks?.onThinkingEnd?.()
            // 确保所有缓冲文本都开始 reveal
            startAssistantReveal()
            clearAssistantFlushFallbackTimer()
            assistantFlushFallbackTimer = setTimeout(() => {
                // avatar_stopped 一直没来，强制 finalize 避免消息卡住
                if (isSpeaking.value) {
                    console.warn('[DH] avatar_stopped not received after assistant_complete, force finalizing')
                    isSpeaking.value = false
                }
                finalizeBufferedAssistantTurn(true)
            }, 8000)
        } else if (type === 'avatar_speaking') {
            isSpeaking.value = true
            currentSpeechStartedAt = Date.now()
            currentSpeechReleasedCost = 0
            // 数字人开始说话时，立即结束思考动画
            // avatar_speaking 可能在 assistant_complete 之前到达（TTS 先于 LLM 流完成）
            callbacks?.onThinkingEnd?.()
            // 数字人开始说话，立即开始字幕 reveal
            // 不再延迟，让字幕和语音同步出现
            startAssistantReveal()
        } else if (type === 'diagram') {
            callbacks?.onDiagram?.(data.data, turn_id)
        } else if (type === 'avatar_stopped') {
            isSpeaking.value = false
            if (currentSpeechStartedAt > 0 && currentSpeechReleasedCost > 0) {
                const elapsedSec = Math.max(0.25, (Date.now() - currentSpeechStartedAt) / 1000)
                const actualRate = currentSpeechReleasedCost / elapsedSec
                const clampedActualRate = Math.max(1.5, Math.min(7.0, actualRate))
                if (calibratedRevealCharsPerSecond <= 0) {
                    // 首次校准：使用实测速率 × 0.9 补偿系数
                    calibratedRevealCharsPerSecond = clampedActualRate * 0.9
                } else {
                    // 后续校准：平滑更新
                    calibratedRevealCharsPerSecond =
                        calibratedRevealCharsPerSecond * 0.7 + clampedActualRate * 0.3
                }
            }
            currentSpeechStartedAt = 0
            currentSpeechReleasedCost = 0
            targetRevealCharsPerSecond = 0
            finalizeBufferedAssistantTurn()
            // 数字人播报结束后，通知前端可以安全重启 VAD
            // 之前在 assistant_complete 时就重启 VAD，导致麦克风拾取到 TTS 回声
            callbacks?.onAvatarStopped?.()
            // 如果在播报期间有 VAD 重启请求，现在安全地执行
            if (_pendingVadRestart) {
                const { needDiagram: pendingDiagram, capabilities: pendingCaps } = _pendingVadRestart
                _pendingVadRestart = null
                // 延迟一小段时间确保 TTS 音频完全停止播放
                setTimeout(() => {
                    if (!isSpeaking.value && !vadActive && ws && ws.readyState === WebSocket.OPEN) {
                        startVad(pendingDiagram, pendingCaps)
                    }
                }, 500)
            }
        } else if (type === 'vad_state') {
            const state = data.data?.listening ?? (data.state === 'listening' || data.state === 'speaking')
            const listening = !!state
            backendVadReady = listening
            isListening.value = listening
            if (shouldCleanupLocalVadOnBackendState(listening)) {
                vadActive = false
                cleanupAudioInput()
            }
            callbacks?.onVadStateChange?.(!!state)
        } else if (type === 'history_cleared') {
            callbacks?.onHistoryCleared?.(data.data)
        } else if (type === 'error') {
            error.value = data.content || data.message || '未知错误'
            callbacks?.onError?.(error.value!)
        }
    }

    // 处理流信息（首次连接 / 重连时播放 RTC 流）
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
            // First connection: use nextTick to ensure DigitalHumanCanvas is mounted
            // and container element is available before initializing player
            nextTick(() => {
                streamUrl.value = url || null
                streamExtend.value = extend
                isAvatarReady.value = true
                // Set container first, then init player
                callbacks?.onAvatarReady?.(true)
                initPlayer(url, extend)
            })
        }
    }

    // ==========================================
    // RTCPlayer
    // ==========================================

    // 解析 xrtcs:// 协议 URL 为 RTC 连接参数
    function parseXrtcsUrl(url: string): { host: string; roomId: string } {
        const withoutScheme = url.replace('xrtcs://', '').replace('xrtc://', '')
        const firstSlash = withoutScheme.indexOf('/')
        return {
            host: firstSlash > 0 ? withoutScheme.substring(0, firstSlash) : withoutScheme,
            roomId: firstSlash > 0 ? withoutScheme.substring(firstSlash + 1) : '',
        }
    }

    // 初始化 RTC 播放器渲染数字人画面
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

    // 销毁 RTC 播放器并清空渲染容器
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

    // 启用数字人音频输出（取消静音）
    function enableAudio(): void {
        if (!playerContainer) return

        // 立即标记为已启用，让 UI 按钮消失
        audioEnabled.value = true

        const mediaElements = playerContainer.querySelectorAll('video, audio')
        if (mediaElements.length === 0) {
            // Retry after a short delay (player may still be initializing)
            setTimeout(() => {
                if (!playerContainer) return
                const retry = playerContainer.querySelectorAll('video, audio')
                if (retry.length > 0) {
                    applyAudioOutputSelection(retry)
                    startAudioMonitor()
                }
            }, 500)
            return
        }

        applyAudioOutputSelection(mediaElements)
        startAudioMonitor()
    }

    function applyAudioOutputSelection(elements: Iterable<Element>): void {
        const { audible, muted } = selectAvatarAudioOutputs(elements)

        muted.forEach((el) => {
            el.muted = true
            el.volume = 0
        })

        if (audible) {
            const el = audible
            el.muted = false
            el.volume = 1.0
            // 只对暂停的元素调用 play()，避免对已播放的元素重复调用导致音频重叠
            if (el.paused) {
                el.play().catch(() => {})
            }
        }
    }

    function startAudioMonitor(): void {
        if (audioMonitor) return
        audioMonitor = setInterval(() => {
            if (!playerContainer) return
            applyAudioOutputSelection(playerContainer.querySelectorAll('video, audio'))
        }, 2000)
    }

    // ==========================================
    // Text messaging
    // ==========================================

    // 发送文本消息到数字人（中断当前播报，开始新轮次）
    function sendText(params: TextMessageParams): void {
        if (!ws || ws.readyState !== WebSocket.OPEN) return

        // Send stop_speaking if avatar is speaking (interrupt)
        if (isSpeaking.value) {
            ws.send(JSON.stringify({ type: 'stop_speaking' }))
        }

        // Mark turn as pending - old events will be filtered until turn_start arrives
        // Use a sentinel value to distinguish from null (no active turn)
        activeTurnId = 'pending_' + Date.now()

        // Clear all turn state
        updateCache('', false) // 开始新的提问，清空旧缓存
        bufferedAssistantText = ''
        pendingAssistantComplete = false
        clearAssistantFlushFallbackTimer()
        clearAssistantRevealTimer()

        const msg: Record<string, unknown> = { type: 'text_input', text: params.text }
        if (typeof params.need_diagram === 'boolean') msg.need_diagram = params.need_diagram
        if (params.session_id) msg.session_id = params.session_id
        if (params.attachments?.length) msg.attachments = params.attachments
        if (typeof params.enable_search === 'boolean') msg.enable_search = params.enable_search
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

    // 清理麦克风音频资源（停止轨道、关闭 AudioContext）
    function cleanupAudioInput(): void {
        // Stop mic tracks - does NOT depend on vadActive
        if (audioStream) {
            audioStream.getTracks().forEach((track) => track.stop())
            audioStream = null
        }

        // Close audio context - use void + catch to avoid unhandled promise
        if (audioContext) {
            void audioContext.close().catch(() => {})
            audioContext = null
        }

        // Clear speech detection timers
        if (speechHangTimer) {
            clearTimeout(speechHangTimer)
            speechHangTimer = null
        }
        if (speechDetected) {
            speechDetected = false
            callbacks?.onSpeechDetectedChange?.(false)
        }
    }

    // 启动语音活动检测（VAD）：采集麦克风音频 → PCM → base64 → WebSocket 发送
    async function startVad(needDiagram = false, capabilities: DigitalHumanCapabilities = {}): Promise<void> {
        if (vadActive) return
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            error.value = '数字人未连接，无法开启语音输入'
            callbacks?.onError?.(error.value)
            return
        }
        // 数字人正在说话时，不允许开启语音识别
        // 避免麦克风拾取到 TTS 回声导致错误识别
        if (isSpeaking.value) {
            console.warn('[DH] Cannot start VAD while avatar is speaking, will auto-restart after speech ends')
            _pendingVadRestart = { needDiagram, capabilities }
            return
        }
        if (shouldStopVadForDigitalHumanState(digitalHumanState.value)) {
            return
        }

        // Clear turn state
        activeTurnId = null
        bufferedAssistantText = ''
        pendingAssistantComplete = false
        clearAssistantFlushFallbackTimer()
        clearAssistantRevealTimer()

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
            // 使用 2048 buffer（128ms @ 16kHz）替代 4096（256ms）以降低采集延迟
            const processor = audioContext.createScriptProcessor(2048, 1, 1)
            // 缓存后端未就绪时的音频数据，等 backend 就绪后批量发送
            const pendingAudioChunks: string[] = []

            processor.onaudioprocess = (e) => {
                if (!vadActive || !ws || ws.readyState !== WebSocket.OPEN) return

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

                if (!backendVadReady) {
                    // 后端还没就绪，缓存音频数据
                    pendingAudioChunks.push(base64)
                    return
                }

                // 发送缓存的音频数据（如果有）
                while (pendingAudioChunks.length > 0) {
                    const chunk = pendingAudioChunks.shift()!
                    ws.send(JSON.stringify({ type: 'audio_chunk', audio: chunk }))
                }

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
            // Cleanup audio resources even when vadActive not yet set
            cleanupAudioInput()
            backendVadReady = false
            error.value = '无法访问麦克风或语音服务未就绪，请检查权限并重试'
            callbacks?.onError?.(error.value)
            // Notify backend to cleanup if start_vad was sent
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'stop_vad' }))
            }
        }
    }

    // 停止语音活动检测并通知后端
    function stopVad(): void {
        // Always cleanup audio resources, even if vadActive is false
        // (e.g., if vad failed during startup but audioStream/audioContext were created)
        cleanupAudioInput()

        // Notify backend if connected
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

    // 取下一个字幕展示单元（支持 CJK、英文单词、标点）
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
        // 基础估算速率：保守估计，字幕跟在语音后面
        const estimated = 2.0 + (rate - 0.8) * 2.5
        if (targetRevealCharsPerSecond > 0) {
            return Math.max(1.2, Math.min(7.0, targetRevealCharsPerSecond * (0.85 + (rate - 0.8) * 0.3)))
        }
        if (calibratedRevealCharsPerSecond > 0) {
            return Math.max(1.2, Math.min(7.0, calibratedRevealCharsPerSecond * (0.85 + (rate - 0.8) * 0.3)))
        }
        return estimated
    }

    function getRevealUnitCost(unit: string): number {
        const trimmed = unit.trim()
        if (!trimmed) return 0.5
        // 句末标点：较长停顿
        if (/^[。！？!?]$/.test(trimmed)) return 5.0
        // 分句标点：中等停顿
        if (/^[，,；;]$/.test(trimmed)) return 3.0
        // 冒号、引号：短停顿
        if (/^[：:""''（）()《》【】]$/.test(trimmed)) return 1.5
        // 英文单词
        if (/^[A-Za-z0-9_]+(?:['-][A-Za-z0-9_]+)*$/.test(trimmed)) {
            return Math.max(1.2, Math.min(2.5, trimmed.length * 0.35 + 0.8))
        }
        return 1
    }

    function getRevealTickDelayMs(): number {
        return 64
    }

    // 逐步 reveal 缓冲文本（按语速节流展示字幕）
    function revealBufferedAssistantTextStep(): void {
        assistantRevealTimer = null

        if (!bufferedAssistantText) {
            revealingAssistantText = false
            if (pendingAssistantComplete && !isSpeaking.value) {
                pendingAssistantComplete = false
                callbacks?.onAssistantComplete?.(activeTurnId ?? undefined)
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
            callbacks?.onAssistantChunk?.(emitted, activeTurnId ?? undefined)
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
            callbacks?.onAssistantComplete?.(activeTurnId ?? undefined)
            updateCache('', false)
        }
    }

    function startAssistantReveal(): void {
        if (revealingAssistantText || !bufferedAssistantText) return
        revealingAssistantText = true
        assistantRevealLastTickAt = Date.now()
        // 初始预算，让前几个字能快速出现
        assistantRevealBudget = Math.max(assistantRevealBudget, 0.3)
        // 首个 reveal 延迟 80ms
        assistantRevealTimer = setTimeout(revealBufferedAssistantTextStep, getRevealTickDelayMs() + 80)
    }

    function flushBufferedAssistantTextImmediately(): void {
        if (!bufferedAssistantText) return
        callbacks?.onAssistantChunk?.(bufferedAssistantText, activeTurnId ?? undefined)
        bufferedAssistantText = ''
    }

    // 结束当前轮次：强制刷出剩余文本或启动 reveal
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
            callbacks?.onAssistantComplete?.(activeTurnId ?? undefined)
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
        digitalHumanState, // 统一数字人状态

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
