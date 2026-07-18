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
import { VadSessionMachine } from '@/features/chat/digital-human/model/vadSession'
import {
    ASR_TARGET_SAMPLE_RATE,
    VoiceCapture,
    calculateAudioRms,
    resampleAudioForAsr,
    type VoiceCaptureFrame,
} from '@/features/chat/digital-human/model/voiceCapture'

export { calculateAudioRms, resampleAudioForAsr }

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
    isBusy?: boolean
}

type AvatarTransportState = 'disconnected' | 'connecting' | 'ready' | 'error'

// Keep only a short pre-roll so stale audio cannot sit seconds ahead of live speech.
export const MAX_PENDING_AUDIO_CHUNKS = 20
export const MAX_PENDING_AUDIO_CHUNKS_WHILE_ASR_CONNECTING = 8
export const MAX_WS_AUDIO_BUFFERED_BYTES = 32 * 1024
export const CONTINUOUS_VAD_RESTART_DELAY_MS = 50
// The provider frequently omits tts_end. Its estimated stop event can precede
// the audible RTC tail, so keep the microphone closed until that tail drains.
export const FALLBACK_VAD_RESTART_DELAY_MS = 1800
export const VAD_BACKEND_READY_TIMEOUT_MS = 16_000
export const VAD_WEBSOCKET_OPEN_TIMEOUT_MS = 5_000
export { ASR_TARGET_SAMPLE_RATE }
export const ASR_SPEECH_START_RMS = 0.007
export const ASR_SPEECH_CONFIRM_MS = 240
// 520ms keeps natural intra-sentence pauses while cutting end-of-utterance latency.
export const ASR_SILENCE_END_MS = 520
export const ASR_PRE_SPEECH_CHUNKS = 8
export const ASR_EMPTY_RESTART_DELAY_MS = 600
export const AVATAR_OUTPUT_ACTIVE_RMS = 0.004
export const AVATAR_OUTPUT_SILENCE_MS = 450
export const AVATAR_OUTPUT_MAX_DRAIN_MS = 8_000

export interface AsrVoiceActivityDecision {
    speechActive: boolean
    speechStarted: boolean
    speechEnded: boolean
}

export class AsrVoiceActivityGate {
    private noiseFloorRms = 0.004
    private candidateDurationMs = 0
    private silenceDurationMs = 0
    private active = false
    private activePeakRms = 0
    private lastUtterancePeakRms = 0

    update(rms: number, durationMs: number): AsrVoiceActivityDecision {
        const safeRms = Number.isFinite(rms) ? Math.max(0, rms) : 0
        const safeDurationMs = Number.isFinite(durationMs) ? Math.max(0, durationMs) : 0

        if (!this.active) {
            const startThreshold = Math.max(ASR_SPEECH_START_RMS, this.noiseFloorRms * 3)
            if (safeRms >= startThreshold) {
                this.activePeakRms = Math.max(this.activePeakRms, safeRms)
                this.candidateDurationMs += safeDurationMs
                if (this.candidateDurationMs >= ASR_SPEECH_CONFIRM_MS) {
                    this.active = true
                    this.silenceDurationMs = 0
                    return { speechActive: true, speechStarted: true, speechEnded: false }
                }
            } else {
                this.candidateDurationMs = 0
                this.activePeakRms = 0
                // Learn steady room/microphone noise even when it is above the
                // absolute minimum. Previously 0.008~0.012 RMS noise was never
                // learned, so a short fan/keyboard spike repeatedly looked like
                // speech after every continuous-listening restart.
                this.noiseFloorRms = this.noiseFloorRms * 0.94 + safeRms * 0.06
            }
            return { speechActive: false, speechStarted: false, speechEnded: false }
        }

        this.activePeakRms = Math.max(this.activePeakRms, safeRms)
        const releaseThreshold = Math.max(0.0045, this.noiseFloorRms * 1.8)
        if (safeRms >= releaseThreshold) {
            this.silenceDurationMs = 0
        } else {
            this.silenceDurationMs += safeDurationMs
        }

        if (this.silenceDurationMs >= ASR_SILENCE_END_MS) {
            this.active = false
            this.candidateDurationMs = 0
            this.silenceDurationMs = 0
            return { speechActive: false, speechStarted: false, speechEnded: true }
        }
        return { speechActive: true, speechStarted: false, speechEnded: false }
    }

    reset(preserveNoiseFloor = false): void {
        if (this.activePeakRms > 0) {
            this.lastUtterancePeakRms = this.activePeakRms
        }
        if (!preserveNoiseFloor) {
            this.noiseFloorRms = 0.004
            this.lastUtterancePeakRms = 0
        }
        this.candidateDurationMs = 0
        this.silenceDurationMs = 0
        this.active = false
        this.activePeakRms = 0
    }

    markFalsePositive(): void {
        if (this.lastUtterancePeakRms > 0) {
            this.noiseFloorRms = Math.max(
                this.noiseFloorRms,
                Math.min(0.03, this.lastUtterancePeakRms * 0.75),
            )
        }
    }
}

export function enqueueBoundedAudioChunk<T>(queue: T[], chunk: T, maxSize = MAX_PENDING_AUDIO_CHUNKS): boolean {
    const safeMaxSize = Math.max(1, Math.floor(maxSize))
    const dropped = queue.length >= safeMaxSize
    if (dropped) queue.shift()
    queue.push(chunk)
    return dropped
}

// 判断是否应暂停空闲自动断开（正在交互中不自动断开）
export function shouldPauseIdleDisconnect({ state, isSpeaking, isListening, isBusy = false }: IdleDisconnectState): boolean {
    if (isSpeaking || isListening || isBusy) return true
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
    // "recognizing" 是 VAD 正常流程的一部分（识别用户语音），不应停止麦克风。
    // 数字人传输重连期间暂停新问题，避免回答落到尚未恢复的播报链路。
    return state === 'avatar_connecting' || state === 'thinking' || state === 'speaking'
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
    let thinkingTurnId: string | null = null
    let thinkingActive = false

    // --- 实时生成缓存 (应对不可抗力断开) ---
    const CACHE_KEY = 'dh_current_generation_cache'
    const generationCache = ref(localStorage.getItem(CACHE_KEY) || '')
    let bufferedAssistantText = ''
    let pendingAssistantComplete = false
    let assistantRevealTimer: ReturnType<typeof setTimeout> | null = null
    let revealingAssistantText = false
    let assistantRevealBudget = 0
    let assistantRevealLastTickAt = 0
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
    const externalActivityBusy = ref(false)
    let idleTimer: ReturnType<typeof setInterval> | null = null

    // --- Internal state (not reactive, not exposed) ---
    let ws: WebSocket | null = null
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let player: any = null
    let audioMonitor: ReturnType<typeof setInterval> | null = null
    let audioFlushTimer: ReturnType<typeof setTimeout> | null = null
    let avatarOutputAudioContext: AudioContext | null = null
    let avatarOutputSource: MediaStreamAudioSourceNode | null = null
    let avatarOutputAnalyser: AnalyserNode | null = null
    let avatarOutputStream: MediaStream | null = null
    let avatarStopTimer: ReturnType<typeof setTimeout> | null = null
    let avatarStopGeneration = 0
    const pendingAudioChunks: ArrayBuffer[] = []
    const preSpeechAudioChunks: ArrayBuffer[] = []
    const voiceActivityGate = new AsrVoiceActivityGate()
    const voiceCapture = new VoiceCapture(handleVoiceCaptureFrame)
    let droppedAudioChunks = 0
    let pendingAudioEnd = false
    let vadSessionSequence = 0
    const vadSession = new VadSessionMachine()
    let speechDetected = false
    let playerContainer: HTMLElement | null = null
    let playerReadyTimer: ReturnType<typeof setTimeout> | null = null
    let playerReadyPollTimer: ReturnType<typeof setTimeout> | null = null
    let playerGeneration = 0
    let avatarTransportState: AvatarTransportState = 'disconnected'
    // 当数字人说话时尝试启动 VAD，会暂存参数，等播报结束后自动重启
    let _pendingVadRestart: { needDiagram: boolean; capabilities: DigitalHumanCapabilities } | null = null
    let continuousVadOptions: { needDiagram: boolean; capabilities: DigitalHumanCapabilities } | null = null
    let vadRestartTimer: ReturnType<typeof setTimeout> | null = null
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
                isBusy: externalActivityBusy.value,
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

    // Long-running work such as video rendering is still an active avatar turn.
    // Keep the transport alive even after the LLM stream itself has completed.
    function setExternalActivityBusy(active: boolean): void {
        externalActivityBusy.value = active
        if (active && isConnected.value) {
            idleCountdown.value = Math.floor(IDLE_TIMEOUT_MS / 1000)
        }
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
        avatarTransportState = 'connecting'
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
            avatarTransportState = 'disconnected'
            isConnected.value = false
            setContinuousVoice(false)
            stopVad()
            destroyPlayer()
            stopIdleTimer()
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
        setContinuousVoice(false)
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
        vadSession.complete()
        streamUrl.value = null
        streamExtend.value = null
        audioEnabled.value = false
        error.value = null
        pendingStreamData = null
        clearPendingAudioChunks()
        bufferedAssistantText = ''
        pendingAssistantComplete = false
        _pendingVadRestart = null
        avatarTransportState = 'disconnected'
        clearAssistantRevealTimer()
        endThinking()
        callbacks?.onConnectionChange?.(false)
    }

    function beginThinking(turnId?: string): void {
        const nextTurnId = turnId || activeTurnId
        if (thinkingActive && thinkingTurnId === nextTurnId) return
        thinkingActive = true
        thinkingTurnId = nextTurnId
        callbacks?.onThinkingStart?.()
    }

    function endThinking(turnId?: string): void {
        if (!thinkingActive) return
        if (turnId && thinkingTurnId && turnId !== thinkingTurnId) return
        thinkingActive = false
        thinkingTurnId = null
        callbacks?.onThinkingEnd?.()
    }

    function isTransportLifecycleMessage(data: Record<string, any>): boolean {
        if (data.type === 'stream_info') return true
        if (data.type === 'avatar_stopped' && data.data?.connection_lost === true) return true
        return data.type === 'digital_human_state'
            && ['avatar_connecting', 'avatar_ready', 'error'].includes(data.state)
    }

    function getVadSessionId(data: Record<string, any>): string | null {
        const value = data.vad_session_id ?? data.data?.vad_session_id
        return typeof value === 'string' && value ? value : null
    }

    function isCurrentVadSessionEvent(data: Record<string, any>): boolean {
        const sessionId = getVadSessionId(data)
        if (!vadSession.matches(sessionId)) {
            console.warn('[DH] Ignoring stale VAD event:', data.type, sessionId, 'current:', vadSession.id)
            return false
        }
        return true
    }

    function handleDigitalHumanState(data: Record<string, any>): void {
        const state = data.state as DigitalHumanStateType
        const turnId = data.turn_id as string | undefined

        if (state === 'avatar_connecting') {
            avatarTransportState = 'connecting'
            if (isSpeaking.value) {
                waitForAvatarOutputSilence(() => finishAvatarStopped(turnId))
            }
        } else if (state === 'avatar_ready') {
            avatarTransportState = 'ready'
            error.value = null
            if (isSpeaking.value) return
        } else if (state === 'error') {
            avatarTransportState = 'error'
        }

        digitalHumanState.value = state
        if (shouldStopVadForDigitalHumanState(state) && vadSession.hasSession) stopVad()

        const stateError = digitalHumanStateErrorMessage(state, data.message)
        if (stateError) {
            error.value = stateError
            setAvatarReady(false)
            callbacks?.onError?.(stateError)
        }

        callbacks?.onDigitalHumanStateChange?.(state, turnId)
        callbacks?.onStatus?.({ stage: state, message: data.message })
        if (state === 'thinking') beginThinking(turnId)
        if (state === 'speaking' || state === 'error') endThinking(turnId)
        if (state === 'avatar_ready' && continuousVadOptions && !isSpeaking.value && !vadSession.hasSession) {
            scheduleVadRestart(continuousVadOptions)
        }
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
            clearAssistantRevealTimer()
            // A turn has been accepted by the backend. Enter thinking immediately
            // instead of leaving the UI in the previous ASR/preparing state while
            // the user message is persisted and the LLM stream is initialized.
            beginThinking(turn_id)
            return
        }

        // 过滤过期轮次的事件（turn_id 不匹配则丢弃）
        // 在 digital_human_state 处理前过滤，防止旧轮次状态污染
        // Apply this filter BEFORE handling digital_human_state to prevent old turn pollution
        const turnDependentTypes = [
            'assistant_chunk', 'assistant_complete',
            'avatar_speaking', 'avatar_stopped', 'diagram', 'video', 'status',
            'digital_human_state', 'error'  // Add digital_human_state and error to turn-dependent types
        ]
        if (turnDependentTypes.includes(type) && !isTransportLifecycleMessage(data)) {
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
            handleDigitalHumanState(data)
            return
        }

        if (type === 'stream_info') {
            handleStreamInfo(data)
        } else if (type === 'asr_partial') {
            if (!isCurrentVadSessionEvent(data)) return
            asrText.value = data.content || ''
            callbacks?.onAsrPartial?.(data.content || '')
        } else if (type === 'asr_result') {
            if (!isCurrentVadSessionEvent(data)) return
            vadSession.complete(getVadSessionId(data))
            syncVadListeningState()
            asrText.value = data.content || ''
            updateCache('', false) // 开始新一轮对话前清理上一轮残留
            bufferedAssistantText = ''
            pendingAssistantComplete = false
            clearAssistantRevealTimer()
            callbacks?.onAsrResult?.(data.content || '')
        } else if (type === 'assistant_chunk') {
            updateCache(data.content || '', true) // 实时追加到缓存
            bufferedAssistantText += data.content || ''
            // 数字人模式以真正开口为响应起点，不用首个 LLM 文本片段
            // 提前结束“思考”状态，避免文本显示与数字人口型脱节。
            if (isSpeaking.value) startAssistantReveal()
        } else if (type === 'status') {
            callbacks?.onStatus?.(data.data || {})
        } else if (type === 'assistant_complete') {
            // The backend has the complete sentence, but the subtitle should
            // still follow the avatar's actual playback instead of appearing
            // all at once. Speech remains a single TTS request; this only
            // controls the visual reveal cadence.
            endThinking(turn_id)
            pendingAssistantComplete = true
            if (isSpeaking.value) startAssistantReveal()
        } else if (type === 'avatar_speaking') {
            clearAvatarStopWait()
            isSpeaking.value = true
            const estimatedDuration = Number(data.data?.estimated_duration)
            targetRevealCharsPerSecond = Number.isFinite(estimatedDuration) && estimatedDuration > 0
                ? Math.max(1.5, Math.min(8, getRevealTextCost(bufferedAssistantText) / estimatedDuration))
                : 0
            // 数字人开始说话时，立即结束思考动画
            // avatar_speaking 可能在 assistant_complete 之前到达（TTS 先于 LLM 流完成）
            endThinking(turn_id)
            // 数字人开始说话，立即开始字幕 reveal
            // 不再延迟，让字幕和语音同步出现
            startAssistantReveal()
        } else if (type === 'diagram') {
            callbacks?.onDiagram?.(data.data, turn_id)
        } else if (type === 'video') {
            callbacks?.onVideo?.(data.data, turn_id)
        } else if (type === 'avatar_stopped') {
            const finish = () => finishAvatarStopped(turn_id)
            if (data.data?.fallback === true) waitForAvatarOutputSilence(finish)
            else finish()
        } else if (type === 'vad_state') {
            if (!isCurrentVadSessionEvent(data)) return
            const state = data.data?.listening ?? (data.state === 'listening' || data.state === 'speaking')
            const listening = !!state
            vadSession.setBackendReady(getVadSessionId(data)!, listening)
            if (shouldCleanupLocalVadOnBackendState(listening)) {
                cleanupAudioInput(continuousVadOptions === null)
            } else {
                clearPendingAudioChunks()
                voiceActivityGate.reset(true)
                syncVadListeningState()
            }
        } else if (type === 'asr_empty') {
            if (!isCurrentVadSessionEvent(data)) return
            vadSession.complete(getVadSessionId(data))
            syncVadListeningState()
            voiceActivityGate.markFalsePositive()
            callbacks?.onStatus?.({
                stage: 'asr_empty',
                message: '未识别到有效语音，正在重新倾听',
            })
            if (avatarTransportState === 'ready' && continuousVadOptions && !isSpeaking.value) {
                digitalHumanState.value = 'avatar_ready'
                scheduleVadRestart(continuousVadOptions, ASR_EMPTY_RESTART_DELAY_MS)
            }
        } else if (type === 'history_cleared') {
            callbacks?.onHistoryCleared?.(data.data)
        } else if (type === 'error') {
            const vadSessionId = getVadSessionId(data)
            if (vadSessionId) {
                if (!isCurrentVadSessionEvent(data)) return
                vadSession.complete(vadSessionId)
                syncVadListeningState()
            }
            endThinking(turn_id)
            callbacks?.onError?.(data.content || data.message || '未知错误')
        }
    }

    // 处理流信息（首次连接 / 重连时播放 RTC 流）
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    function handleStreamInfo(data: Record<string, any>): void {
        const url = data.stream_url || data.data?.stream_url
        const extend = data.stream_extend || data.data?.stream_extend || {}
        const isDuplicateStream = !data.reconnected && !!url && streamUrl.value === url

        // The provider/bridge may replay cached metadata during initial attach.
        // Reinitializing the same RTC room creates competing players and lets a
        // later readiness timeout destroy the player that is already rendering.
        if (isDuplicateStream) return

        streamUrl.value = url || null
        streamExtend.value = extend

        setAvatarReady(false)

        if (data.reconnected) {
            // Reconnection: destroy and reinit player
            const wasAudioEnabled = audioEnabled.value
            destroyPlayer()

            nextTick(() => {
                initPlayer(url, extend)
                if (wasAudioEnabled) waitForAvatarReadyAndEnableAudio()
            })
        } else {
            // First connection: use nextTick to ensure DigitalHumanCanvas is mounted
            // and container element is available before initializing player
            nextTick(() => {
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
            reportPlayerError('数字人视频流地址无效')
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
            reportPlayerError('数字人播放器加载失败，请刷新页面重试')
            return
        }

        const parsed = parseXrtcsUrl(url)
        if (!parsed.host || !parsed.roomId) {
            reportPlayerError('数字人视频流参数无效')
            return
        }

        try {
            const generation = ++playerGeneration
            const nextPlayer = new RTCPlayer()
            player = nextPlayer
            nextPlayer.container = playerContainer
            nextPlayer.videoSize = { width: 720, height: 1280 }
            nextPlayer.stream = {
                server: `wss://${parsed.host}`,
                auth: extend.user_sign || '',
                appid: extend.appid || '',
                userId: 'user_' + Math.random().toString(36).substring(2, 10),
                roomId: parsed.roomId,
            }

            const markReady = () => {
                if (generation !== playerGeneration || player !== nextPlayer) return
                clearPlayerReadyTimer()
                error.value = null
                setAvatarReady(true)
            }
            const markFailed = (reason?: unknown) => {
                if (generation !== playerGeneration || player !== nextPlayer) return
                console.error('[DH] player error:', reason)
                reportPlayerError('数字人视频播放失败，请重新连接')
            }
            const markReadyIfRenderable = () => {
                if (generation !== playerGeneration || player !== nextPlayer || isAvatarReady.value) return false
                const videos = playerContainer?.querySelectorAll('video') ?? []
                const hasRenderableFrame = Array.from(videos).some(
                    (video) => video.readyState >= 2 && video.videoWidth > 0 && video.videoHeight > 0,
                )
                if (!hasRenderableFrame) return false
                markReady()
                return true
            }
            const probeMediaReady = () => {
                if (generation !== playerGeneration || player !== nextPlayer || isAvatarReady.value) return
                if (markReadyIfRenderable()) return
                playerReadyPollTimer = setTimeout(probeMediaReady, 100)
            }

            if (typeof nextPlayer.on === 'function') {
                nextPlayer.on('playing', markReadyIfRenderable)
                nextPlayer.on('error', markFailed)
            }

            clearPlayerReadyTimer()
            playerReadyPollTimer = setTimeout(probeMediaReady, 0)
            playerReadyTimer = setTimeout(() => {
                if (generation === playerGeneration && !isAvatarReady.value) {
                    reportPlayerError('数字人视频连接超时，请重新连接')
                }
            }, 15_000)

            Promise.resolve(nextPlayer.play()).catch((err: unknown) => {
                console.error('[DH] player error:', err)
                markFailed(err)
            })
        } catch (err) {
            console.error('[DH] player init failed:', err)
            reportPlayerError('数字人播放器初始化失败，请重新连接')
        }
    }

    function finishAvatarStopped(turnId?: string): void {
        clearAvatarStopWait()
        endThinking(turnId)
        isSpeaking.value = false
        if (avatarTransportState === 'ready' && digitalHumanState.value !== 'avatar_ready') {
            digitalHumanState.value = 'avatar_ready'
            callbacks?.onDigitalHumanStateChange?.('avatar_ready', turnId)
            callbacks?.onStatus?.({ stage: 'avatar_ready', message: 'Avatar service ready' })
        }
        targetRevealCharsPerSecond = 0
        finalizeBufferedAssistantTurn()
        callbacks?.onAvatarStopped?.()
        const restartOptions = _pendingVadRestart ?? continuousVadOptions
        _pendingVadRestart = null
        if (restartOptions) scheduleVadRestart(restartOptions, CONTINUOUS_VAD_RESTART_DELAY_MS)
    }

    function setAvatarReady(ready: boolean): void {
        if (isAvatarReady.value === ready) return
        isAvatarReady.value = ready
        callbacks?.onAvatarReady?.(ready)
    }

    function clearPlayerReadyTimer(): void {
        if (playerReadyTimer) {
            clearTimeout(playerReadyTimer)
            playerReadyTimer = null
        }
        if (playerReadyPollTimer) {
            clearTimeout(playerReadyPollTimer)
            playerReadyPollTimer = null
        }
    }

    function reportPlayerError(message: string): void {
        destroyPlayer()
        avatarTransportState = 'error'
        error.value = message
        digitalHumanState.value = 'error'
        callbacks?.onError?.(message, { source: 'player' })
        callbacks?.onDigitalHumanStateChange?.('error')
    }

    function waitForAvatarReadyAndEnableAudio(): void {
        const generation = playerGeneration
        const check = () => {
            if (generation !== playerGeneration) return
            if (isAvatarReady.value) {
                enableAudio()
                return
            }
            setTimeout(check, 100)
        }
        setTimeout(check, 100)
    }

    // 销毁 RTC 播放器并清空渲染容器
    function destroyPlayer(): void {
        playerGeneration += 1
        clearAvatarStopWait()
        closeAvatarOutputMonitor()
        clearPlayerReadyTimer()
        setAvatarReady(false)
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
            attachAvatarOutputAnalyser(el)
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

    function clearPendingAudioChunks(): void {
        pendingAudioChunks.length = 0
        preSpeechAudioChunks.length = 0
        droppedAudioChunks = 0
        pendingAudioEnd = false
        voiceActivityGate.reset(true)
        if (audioFlushTimer) {
            clearTimeout(audioFlushTimer)
            audioFlushTimer = null
        }
    }

    function detachAvatarOutputAnalyser(): void {
        if (avatarOutputSource) {
            try {
                avatarOutputSource.disconnect()
            } catch {
                // ignore a source already detached by AudioContext shutdown
            }
        }
        avatarOutputSource = null
        avatarOutputAnalyser = null
        avatarOutputStream = null
    }

    function closeAvatarOutputMonitor(): void {
        detachAvatarOutputAnalyser()
        if (avatarOutputAudioContext) {
            void avatarOutputAudioContext.close().catch(() => {})
            avatarOutputAudioContext = null
        }
    }

    function ensureAvatarOutputAudioContext(): AudioContext | null {
        try {
            if (!avatarOutputAudioContext || avatarOutputAudioContext.state === 'closed') {
                avatarOutputAudioContext = new AudioContext()
            }
            if (avatarOutputAudioContext.state === 'suspended') {
                void avatarOutputAudioContext.resume().catch(() => {})
            }
            return avatarOutputAudioContext
        } catch (err) {
            console.warn('[DH] avatar output audio context unavailable:', err)
            return null
        }
    }

    function attachAvatarOutputAnalyser(media: HTMLMediaElement): void {
        const outputContext = ensureAvatarOutputAudioContext()
        if (
            !outputContext
            || typeof outputContext.createAnalyser !== 'function'
            || typeof MediaStream === 'undefined'
            || !(media.srcObject instanceof MediaStream)
        ) {
            return
        }
        const stream = media.srcObject
        if (avatarOutputStream === stream && avatarOutputAnalyser) return

        detachAvatarOutputAnalyser()
        try {
            const source = outputContext.createMediaStreamSource(stream)
            const analyser = outputContext.createAnalyser()
            analyser.fftSize = 1024
            analyser.smoothingTimeConstant = 0.2
            source.connect(analyser)
            avatarOutputSource = source
            avatarOutputAnalyser = analyser
            avatarOutputStream = stream
        } catch (err) {
            console.warn('[DH] avatar output analyser unavailable:', err)
            detachAvatarOutputAnalyser()
        }
    }

    function clearAvatarStopWait(): void {
        avatarStopGeneration += 1
        if (avatarStopTimer) {
            clearTimeout(avatarStopTimer)
            avatarStopTimer = null
        }
    }

    function waitForAvatarOutputSilence(onSilent: () => void): void {
        clearAvatarStopWait()
        const generation = avatarStopGeneration
        const analyser = avatarOutputAnalyser
        const canMeasureOutput = !!analyser && avatarOutputAudioContext?.state === 'running'

        if (!canMeasureOutput) {
            avatarStopTimer = setTimeout(onSilent, FALLBACK_VAD_RESTART_DELAY_MS)
            return
        }

        const samples = new Float32Array(analyser.fftSize)
        const startedAt = Date.now()
        let silentSince = 0
        const check = () => {
            if (generation !== avatarStopGeneration || !avatarOutputAnalyser) return
            avatarOutputAnalyser.getFloatTimeDomainData(samples)
            const now = Date.now()
            const outputActive = calculateAudioRms(samples) >= AVATAR_OUTPUT_ACTIVE_RMS
            if (outputActive) {
                silentSince = 0
            } else if (silentSince === 0) {
                silentSince = now
            }

            const silenceConfirmed = silentSince > 0 && now - silentSince >= AVATAR_OUTPUT_SILENCE_MS
            const drainTimedOut = now - startedAt >= AVATAR_OUTPUT_MAX_DRAIN_MS
            if (silenceConfirmed || drainTimedOut) {
                onSilent()
                return
            }
            avatarStopTimer = setTimeout(check, 50)
        }
        check()
    }

    function scheduleAudioFlush(): void {
        if (audioFlushTimer || !vadSession.backendReady) return
        audioFlushTimer = setTimeout(() => {
            audioFlushTimer = null
            flushPendingAudioChunks()
        }, 40)
    }

    function flushPendingAudioChunks(): void {
        if (!vadSession.backendReady || !ws || ws.readyState !== WebSocket.OPEN) return

        while (
            pendingAudioChunks.length > 0
            && ws.bufferedAmount <= MAX_WS_AUDIO_BUFFERED_BYTES
        ) {
            const chunk = pendingAudioChunks.shift()
            if (!chunk) continue
            ws.send(chunk)
            break
        }

        if (pendingAudioChunks.length > 0) {
            scheduleAudioFlush()
        } else if (pendingAudioEnd) {
            ws.send(JSON.stringify({ type: 'audio_end' }))
            pendingAudioEnd = false
        }
    }

    function queueAudioChunk(chunk: ArrayBuffer): void {
        const maxPendingChunks = vadSession.backendReady
            ? MAX_PENDING_AUDIO_CHUNKS
            : MAX_PENDING_AUDIO_CHUNKS_WHILE_ASR_CONNECTING
        if (enqueueBoundedAudioChunk(pendingAudioChunks, chunk, maxPendingChunks)) {
            droppedAudioChunks += 1
            if (droppedAudioChunks === 1 || droppedAudioChunks % 25 === 0) {
                console.warn('[DH] audio backpressure dropped chunks:', droppedAudioChunks)
            }
        }
        scheduleAudioFlush()
    }

    function queuePreSpeechAudioChunk(chunk: ArrayBuffer): void {
        if (preSpeechAudioChunks.length >= ASR_PRE_SPEECH_CHUNKS) {
            preSpeechAudioChunks.shift()
        }
        preSpeechAudioChunks.push(chunk)
    }

    function flushPreSpeechAudioChunks(): void {
        for (const chunk of preSpeechAudioChunks) queueAudioChunk(chunk)
        preSpeechAudioChunks.length = 0
        flushPendingAudioChunks()
    }

    function requestAudioEnd(): void {
        if (pendingAudioEnd) return
        pendingAudioEnd = true
        vadSession.submit()
        voiceCapture.pause()
        syncVadListeningState()
        flushPendingAudioChunks()
    }

    function handleVoiceCaptureFrame(frame: VoiceCaptureFrame): void {
        if (!vadSession.captureActive || !ws || ws.readyState !== WebSocket.OPEN) return

        if (!vadSession.backendReady) {
            queuePreSpeechAudioChunk(frame.pcm)
            return
        }

        const decision = voiceActivityGate.update(frame.rms, frame.durationMs)
        if (decision.speechStarted) {
            vadSession.beginSpeech()
            queuePreSpeechAudioChunk(frame.pcm)
            flushPreSpeechAudioChunks()
            setSpeechDetected(true)
        } else if (decision.speechEnded) {
            queueAudioChunk(frame.pcm)
            setSpeechDetected(false)
            requestAudioEnd()
        } else if (decision.speechActive) {
            queueAudioChunk(frame.pcm)
        } else {
            queuePreSpeechAudioChunk(frame.pcm)
        }
    }

    function setSpeechDetected(detected: boolean): void {
        if (speechDetected === detected) return
        speechDetected = detected
        callbacks?.onSpeechDetectedChange?.(detected)
    }

    function syncVadListeningState(): void {
        const listening = vadSession.listening
        if (isListening.value === listening) return
        isListening.value = listening
        callbacks?.onVadStateChange?.(listening)
    }

    async function waitForWebSocketOpen(timeoutMs = VAD_WEBSOCKET_OPEN_TIMEOUT_MS): Promise<boolean> {
        const deadline = Date.now() + timeoutMs
        while (ws?.readyState === WebSocket.CONNECTING && Date.now() < deadline) {
            await new Promise((resolve) => setTimeout(resolve, 20))
        }
        return ws?.readyState === WebSocket.OPEN
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
        clearAssistantRevealTimer()

        const msg: Record<string, unknown> = { type: 'text_input', text: params.text }
        if (typeof params.need_diagram === 'boolean') msg.need_diagram = params.need_diagram
        if (typeof params.need_video === 'boolean') msg.need_video = params.need_video
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

    function cleanupAudioInput(closeAudioContext = true): void {
        if (closeAudioContext) void voiceCapture.stop()
        else voiceCapture.pause()

        setSpeechDetected(false)
        vadSession.releaseCapture()
        syncVadListeningState()
        voiceActivityGate.reset(!closeAudioContext)
        preSpeechAudioChunks.length = 0
    }

    function primeAudioContext(): Promise<void> {
        return voiceCapture.prime()
    }

    // 连续对话期间只暂停上传，保留用户手势获取到的麦克风与 AudioContext。
    function pauseAudioInput(): void {
        voiceCapture.pause()
        vadSession.submit()
        clearPendingAudioChunks()
        setSpeechDetected(false)
        syncVadListeningState()
    }

    // 启动语音活动检测（VAD）：采集麦克风音频 → PCM → base64 → WebSocket 发送
    async function startVad(needDiagram = false, capabilities: DigitalHumanCapabilities = {}): Promise<boolean> {
        if (vadSession.listening) return true
        if (vadSession.hasSession) return false
        if (!ws || (ws.readyState !== WebSocket.OPEN && ws.readyState !== WebSocket.CONNECTING)) {
            error.value = '数字人未连接，无法开启语音输入'
            callbacks?.onError?.(error.value)
            return false
        }
        // 数字人正在说话时，不允许开启语音识别
        // 避免麦克风拾取到 TTS 回声导致错误识别
        if (isSpeaking.value) {
            console.warn('[DH] Cannot start VAD while avatar is speaking, will auto-restart after speech ends')
            _pendingVadRestart = { needDiagram, capabilities }
            return false
        }
        if (shouldStopVadForDigitalHumanState(digitalHumanState.value)) {
            return false
        }

        // Clear turn state
        activeTurnId = null
        bufferedAssistantText = ''
        pendingAssistantComplete = false
        clearAssistantRevealTimer()

        const vadSessionId = `vad-${++vadSessionSequence}`
        vadSession.start(vadSessionId)

        try {
            // Start/resume synchronously from the user's click before the first
            // await. Creating it after getUserMedia resolves can lose browser
            // activation and leave the processor permanently suspended.
            const audioContextReady = primeAudioContext()
            await audioContextReady
            if (ws.readyState === WebSocket.CONNECTING && !await waitForWebSocketOpen()) {
                throw new Error('VAD WebSocket open timeout')
            }

            clearPendingAudioChunks()
            // Tell backend to prepare VAD/ASR queue and carry diagram preference atomically.
            ws.send(JSON.stringify({
                type: 'start_vad',
                vad_session_id: vadSessionId,
                need_diagram: !!needDiagram,
                ...capabilities,
            }))

            await voiceCapture.start()
            if (playerContainer) {
                const { audible } = selectAvatarAudioOutputs(
                    playerContainer.querySelectorAll('video, audio'),
                )
                if (audible) attachAvatarOutputAnalyser(audible)
            }

            // 自动恢复时复用首次用户手势取得的音频链路，不重新请求麦克风权限。
            vadSession.beginCapture(vadSessionId)

            const waitStart = Date.now()
            while (
                vadSession.matches(vadSessionId)
                && !vadSession.backendReady
                && Date.now() - waitStart < VAD_BACKEND_READY_TIMEOUT_MS
            ) {
                await new Promise((resolve) => setTimeout(resolve, 50))
            }
            if (!vadSession.matches(vadSessionId)) {
                return false
            }
            if (!vadSession.backendReady) {
                throw new Error('VAD backend ack timeout')
            }

            if (!voiceCapture.ready) {
                throw new Error(`Microphone capture did not start (AudioContext=${voiceCapture.contextState})`)
            }

            syncVadListeningState()
            flushPendingAudioChunks()
            resetIdleTimer()

            // Auto-enable audio
            if (!audioEnabled.value && isAvatarReady.value) {
                enableAudio()
            }
            return true
        } catch (err) {
            console.error('[DH] mic error:', err)
            if (!vadSession.matches(vadSessionId)) return false
            // Cleanup audio resources even when capture setup failed midway.
            cleanupAudioInput(true)
            clearPendingAudioChunks()
            isListening.value = false
            vadSession.complete(vadSessionId)
            callbacks?.onVadStateChange?.(false)
            error.value = '无法访问麦克风或语音服务未就绪，请检查权限并重试'
            callbacks?.onError?.(error.value)
            // Notify backend to cleanup if start_vad was sent
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'stop_vad', vad_session_id: vadSessionId }))
            }
            return false
        }
    }

    function clearVadRestartTimer(): void {
        if (vadRestartTimer) {
            clearTimeout(vadRestartTimer)
            vadRestartTimer = null
        }
    }

    function scheduleVadRestart(
        options: { needDiagram: boolean; capabilities: DigitalHumanCapabilities },
        delayMs = CONTINUOUS_VAD_RESTART_DELAY_MS,
    ): void {
        clearVadRestartTimer()
        vadRestartTimer = setTimeout(async () => {
            vadRestartTimer = null
            if (isSpeaking.value || vadSession.hasSession || !ws || ws.readyState !== WebSocket.OPEN) return
            await startVad(options.needDiagram, options.capabilities)
        }, delayMs)
    }

    function setContinuousVoice(
        enabled: boolean,
        needDiagram = false,
        capabilities: DigitalHumanCapabilities = {},
    ): void {
        clearVadRestartTimer()
        if (!enabled) {
            continuousVadOptions = null
            _pendingVadRestart = null
            return
        }
        continuousVadOptions = {
            needDiagram: !!needDiagram,
            capabilities: { ...capabilities },
        }
    }

    // 停止语音活动检测并通知后端
    function stopVad(preserveAudio = continuousVadOptions !== null): void {
        const vadSessionId = vadSession.id
        if (preserveAudio) pauseAudioInput()
        else cleanupAudioInput(true)
        clearPendingAudioChunks()

        // Notify backend if connected
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'stop_vad', vad_session_id: vadSessionId }))
        }

        vadSession.complete(vadSessionId)
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

    function switchSession(sessionId?: string): void {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'switch_session',
                session_id: sessionId?.trim() || '',
            }))
        }
    }

    function setSpeechRate(rate: number): void {
        const clamped = Math.max(0.8, Math.min(1.5, Number(rate) || 1.0))
        speechRate.value = clamped
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'set_speech_rate', speech_rate: clamped }))
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
        const estimated = 4.8 * rate
        if (targetRevealCharsPerSecond > 0) {
            return targetRevealCharsPerSecond
        }
        return estimated
    }

    function getRevealUnitCost(unit: string): number {
        const trimmed = unit.trim()
        if (!trimmed) return 0.5
        // 标点保留自然停顿，但不让字幕因累计停顿落后于语音。
        if (/^[。！？!?]$/.test(trimmed)) return 2.0
        if (/^[，,；;]$/.test(trimmed)) return 1.35
        if (/^[：:""''（）()《》【】]$/.test(trimmed)) return 1.1
        // 英文单词
        if (/^[A-Za-z0-9_]+(?:['-][A-Za-z0-9_]+)*$/.test(trimmed)) {
            return Math.max(1.2, Math.min(2.5, trimmed.length * 0.35 + 0.8))
        }
        return 1
    }

    function getRevealTextCost(text: string): number {
        let remaining = text
        let cost = 0
        while (remaining) {
            const unit = takeNextRevealUnit(remaining)
            if (!unit) break
            cost += getRevealUnitCost(unit)
            remaining = remaining.slice(unit.length)
        }
        return cost
    }

    function getRevealTickDelayMs(): number {
        return 64
    }

    // 逐步 reveal 缓冲文本（按语速节流展示字幕）
    function revealBufferedAssistantTextStep(): void {
        assistantRevealTimer = null

        if (!bufferedAssistantText) {
            revealingAssistantText = false
            if (pendingAssistantComplete && !thinkingActive && !isSpeaking.value) {
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
        let remainingCost = getRevealTextCost(bufferedAssistantText)
        // Keep a short subtitle tail until the actual RTC audio becomes silent.
        // This prevents the UI from announcing completion while speech is audible.
        const tailReserve = pendingAssistantComplete && isSpeaking.value
            ? Math.max(3, getRevealCharsPerSecond() * 1.5)
            : 0
        while (bufferedAssistantText) {
            const nextUnit = takeNextRevealUnit(bufferedAssistantText)
            const unitCost = getRevealUnitCost(nextUnit)
            if (remainingCost - unitCost < tailReserve) break
            if (emitted && assistantRevealBudget < unitCost) {
                break
            }
            if (!emitted && assistantRevealBudget < unitCost) {
                break
            }
            bufferedAssistantText = bufferedAssistantText.slice(nextUnit.length)
            remainingCost = Math.max(0, remainingCost - unitCost)
            assistantRevealBudget = Math.max(0, assistantRevealBudget - unitCost)
            emitted += nextUnit
        }

        if (emitted) {
            callbacks?.onAssistantChunk?.(emitted, activeTurnId ?? undefined)
        }

        if (bufferedAssistantText && remainingCost > tailReserve) {
            revealingAssistantText = true
            assistantRevealTimer = setTimeout(revealBufferedAssistantTextStep, getRevealTickDelayMs())
            return
        }

        revealingAssistantText = false
        assistantRevealBudget = 0
        assistantRevealLastTickAt = 0
        if (pendingAssistantComplete && !thinkingActive && !isSpeaking.value) {
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

    // Avatar 停止时立即刷出剩余字幕并结束当前轮次。
    function finalizeBufferedAssistantTurn(): void {
        clearAssistantRevealTimer()
        flushBufferedAssistantTextImmediately()

        if (pendingAssistantComplete) {
            pendingAssistantComplete = false
            callbacks?.onAssistantComplete?.(activeTurnId ?? undefined)
            updateCache('', false)
        }
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
        setContinuousVoice,
        stopSpeaking,
        clearHistory,
        switchSession,
        setSpeechRate,
        setNeedDiagram,
        setExternalActivityBusy,
        enableAudio,
        setPlayerContainer,
    }
}
