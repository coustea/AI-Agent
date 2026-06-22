<template>
  <div v-if="visible" ref="layerRef" class="global-note-layer">
    <div
      ref="fabRef"
      class="global-note-fab"
      :class="{ 'is-dragging': isDragging, 'stick-right': isStickRight }"
      :style="{ left: `${fabPos.x}px`, top: `${fabPos.y}px` }"
      @mousedown="startDrag"
      @touchstart="startDrag"
    >
      <button class="note-fab-button" type="button" aria-label="打开笔记">
        <el-icon><EditPen /></el-icon>
      </button>
    </div>

    <transition name="note-panel-fade">
      <section
        v-if="isOpen"
        ref="panelRef"
        class="note-panel"
        :style="panelStyle"
        @mousedown.stop
        @touchstart.stop
      >
        <header class="note-panel-header" @click="collapsePanel">
          <div class="note-panel-title-wrap">
            <div class="note-panel-icon">
              <el-icon><Document /></el-icon>
            </div>
            <div>
              <h3>笔记</h3>
              <p>{{ panelSubtitle }}</p>
            </div>
          </div>
          <button class="collapse-btn" type="button" aria-label="收起笔记" @click.stop="collapsePanel">
            <el-icon><Minus /></el-icon>
          </button>
        </header>

        <div class="note-panel-body">
          <div class="note-meta-row">
            <span class="meta-chip">{{ draftStatusLabel }}</span>
            <span v-if="lastSavedLabel" class="meta-chip subtle">{{ lastSavedLabel }}</span>
          </div>

          <textarea
            v-model="editorText"
            class="note-textarea"
            placeholder="记录临时想法、待办、学习重点。未保存时会自动保留草稿，保存后下次打开会是新的空白页"
          />

          <div class="note-panel-footer">
            <div class="footer-hint">
              <span class="saved-count">{{ savedNotes.length }} 条已保存</span>
            </div>
            <button class="save-btn" type="button" @click="saveNote">
              <el-icon><Check /></el-icon>
              <span>保存</span>
            </button>
          </div>
        </div>
      </section>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Check, Document, EditPen, Minus } from '@element-plus/icons-vue'
import { useCurrentUser } from '@/features/auth/model/currentUser'
import { GLOBAL_NOTE_STORAGE_LIMIT, readGlobalNotesState, writeGlobalNotesState } from '@/shared/model/globalNotes'

type Point = {
  x: number
  y: number
}

type Rect = {
  left: number
  top: number
  width: number
  height: number
}

type StoredNote = {
  id: string
  content: string
  savedAt: string
}

type StoredState = {
  position?: Point
  draft?: string
  savedNotes?: StoredNote[]
}

type PanelPlacement = {
  left: number
  top: number
  origin: string
  maxHeight: number
}

const FAB_SIZE = 56
const EDGE_MARGIN = 16
const PANEL_GAP = 14
const PANEL_WIDTH = 360
const PANEL_FALLBACK_HEIGHT = 368
const PANEL_MIN_HEIGHT = 280
const TUTOR_AVOID_INTERVAL_MS = 240

const { currentUser } = useCurrentUser()
const route = useRoute()

const layerRef = ref<HTMLElement | null>(null)
const fabRef = ref<HTMLElement | null>(null)
const panelRef = ref<HTMLElement | null>(null)

const visible = computed(() => Boolean(currentUser.value))
const storageKey = computed(() => currentUser.value ? `global-note-fab:${currentUser.value.id}` : '')

const fabPos = ref<Point>({ x: 0, y: 0 })
const isDragging = ref(false)
const isOpen = ref(false)
const editorText = ref('')
const savedNotes = ref<StoredNote[]>([])
const panelStyle = ref<Record<string, string>>({})

const isStickRight = computed(() => fabPos.value.x + FAB_SIZE / 2 >= window.innerWidth / 2)
const panelSubtitle = computed(() => editorText.value.trim() ? '当前是未保存草稿，收起后会自动保留' : '保存后会清空草稿，下次打开是新的空白页')
const draftStatusLabel = computed(() => editorText.value.trim() ? '草稿已恢复' : '空白新页')
const lastSavedLabel = computed(() => {
  const latest = savedNotes.value[0]
  if (!latest) return ''
  return `最近保存 ${formatSavedAt(latest.savedAt)}`
})

let dragStartX = 0
let dragStartY = 0
let dragInitialX = 0
let dragInitialY = 0
let dragDistance = 0
let startedWhileOpen = false
let isHydrating = false
let tutorAvoidTimer: number | null = null

function formatSavedAt(savedAt: string) {
  const date = new Date(savedAt)
  if (Number.isNaN(date.getTime())) return '刚刚'
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function clamp(value: number, min: number, max: number) {
  if (max < min) return min
  return Math.min(Math.max(value, min), max)
}

function toRect(rect: DOMRect): Rect {
  return {
    left: rect.left,
    top: rect.top,
    width: rect.width,
    height: rect.height
  }
}

function rectRight(rect: Rect) {
  return rect.left + rect.width
}

function rectBottom(rect: Rect) {
  return rect.top + rect.height
}

function createRect(left: number, top: number, width: number, height: number): Rect {
  return { left, top, width, height }
}

function getOverlapArea(a: Rect, b: Rect | null) {
  if (!b) return 0
  const overlapWidth = Math.max(0, Math.min(rectRight(a), rectRight(b)) - Math.max(a.left, b.left))
  const overlapHeight = Math.max(0, Math.min(rectBottom(a), rectBottom(b)) - Math.max(a.top, b.top))
  return overlapWidth * overlapHeight
}

function getTopSafeInset() {
  const navbar = document.querySelector('.top-navbar') as HTMLElement | null
  if (!navbar) return EDGE_MARGIN
  return Math.max(EDGE_MARGIN, Math.round(navbar.getBoundingClientRect().bottom + 12))
}

function getViewportBounds() {
  const top = getTopSafeInset()
  return {
    left: EDGE_MARGIN,
    top,
    right: window.innerWidth - EDGE_MARGIN,
    bottom: window.innerHeight - EDGE_MARGIN
  }
}

function getTutorFabRect(): Rect | null {
  if (!route.path.startsWith('/tutor')) return null
  const tutorFab = document.querySelector('.fab-container') as HTMLElement | null
  if (!tutorFab) return null
  const rect = tutorFab.getBoundingClientRect()
  if (rect.width <= 0 || rect.height <= 0) return null
  return toRect(rect)
}

function getPointerPosition(event: MouseEvent | TouchEvent) {
  if (event instanceof MouseEvent) {
    return { x: event.clientX, y: event.clientY }
  }
  const touch = event.touches[0]
  return touch ? { x: touch.clientX, y: touch.clientY } : null
}

function persistState() {
  if (isHydrating || !storageKey.value) return
  const state: StoredState = {
    position: fabPos.value,
    draft: editorText.value,
    savedNotes: savedNotes.value.slice(0, GLOBAL_NOTE_STORAGE_LIMIT)
  }
  localStorage.setItem(storageKey.value, JSON.stringify(state))
}

function loadState() {
  if (!storageKey.value) return

  isHydrating = true

  const defaultPosition = resolveFabPosition(getDefaultFabPosition(), false)
  fabPos.value = defaultPosition
  editorText.value = ''
  savedNotes.value = []

  if (currentUser.value?.id) {
    const state = readGlobalNotesState(currentUser.value.id) as StoredState
    if (state.position) {
      fabPos.value = resolveFabPosition(state.position, false)
    }
    editorText.value = typeof state.draft === 'string' ? state.draft : ''
    savedNotes.value = Array.isArray(state.savedNotes) ? state.savedNotes.slice(0, GLOBAL_NOTE_STORAGE_LIMIT) : []
  }

  isHydrating = false
  persistState()
}

function getDefaultFabPosition(): Point {
  const bounds = getViewportBounds()
  return {
    x: bounds.right - FAB_SIZE,
    y: bounds.bottom - FAB_SIZE
  }
}

function clampFabPosition(point: Point) {
  const bounds = getViewportBounds()
  return {
    x: clamp(point.x, bounds.left, bounds.right - FAB_SIZE),
    y: clamp(point.y, bounds.top, bounds.bottom - FAB_SIZE)
  }
}

function buildFabCandidates(point: Point, snapToEdge: boolean) {
  const bounds = getViewportBounds()
  const clamped = clampFabPosition(point)
  const candidates: Point[] = []
  const leftEdge = bounds.left
  const rightEdge = bounds.right - FAB_SIZE
  const centerX = (bounds.left + bounds.right) / 2
  const snapX = clamped.x + FAB_SIZE / 2 >= centerX ? rightEdge : leftEdge

  if (snapToEdge) {
    candidates.push({ x: snapX, y: clamped.y })
    candidates.push({ x: snapX === rightEdge ? leftEdge : rightEdge, y: clamped.y })
  } else {
    candidates.push(clamped)
    candidates.push({ x: clamped.x + FAB_SIZE / 2 >= centerX ? leftEdge : rightEdge, y: clamped.y })
  }

  const tutorRect = getTutorFabRect()
  if (tutorRect) {
    const aboveY = tutorRect.top - FAB_SIZE - PANEL_GAP
    const belowY = rectBottom(tutorRect) + PANEL_GAP
    const leftX = tutorRect.left - FAB_SIZE - PANEL_GAP
    const rightX = rectRight(tutorRect) + PANEL_GAP
    const yAnchor = clamp(clamped.y, bounds.top, bounds.bottom - FAB_SIZE)

    candidates.push({ x: leftEdge, y: aboveY })
    candidates.push({ x: leftEdge, y: belowY })
    candidates.push({ x: rightEdge, y: aboveY })
    candidates.push({ x: rightEdge, y: belowY })
    candidates.push({ x: leftX, y: yAnchor })
    candidates.push({ x: rightX, y: yAnchor })
  }

  return candidates.map(clampFabPosition)
}

function resolveFabPosition(point: Point, snapToEdge: boolean) {
  const obstacle = getTutorFabRect()
  const candidates = buildFabCandidates(point, snapToEdge)
  const unique = new Map<string, Point>()
  const bounds = getViewportBounds()

  candidates.forEach((candidate) => {
    unique.set(`${Math.round(candidate.x)}:${Math.round(candidate.y)}`, candidate)
  })

  let best = clampFabPosition(point)
  let bestScore = Number.POSITIVE_INFINITY

  unique.forEach((candidate) => {
    const rect = createRect(candidate.x, candidate.y, FAB_SIZE, FAB_SIZE)
    const overlapPenalty = getOverlapArea(rect, obstacle) * 1000
    const distancePenalty = Math.abs(candidate.x - point.x) + Math.abs(candidate.y - point.y)
    const edgePenalty = snapToEdge && candidate.x !== bounds.left && candidate.x !== bounds.right - FAB_SIZE ? 120 : 0
    const score = overlapPenalty + distancePenalty + edgePenalty

    if (score < bestScore) {
      best = candidate
      bestScore = score
    }
  })

  return best
}

function updateFabPosition(point: Point, snapToEdge: boolean) {
  fabPos.value = resolveFabPosition(point, snapToEdge)
}

function buildPanelPlacements(buttonRect: Rect, width: number, height: number, maxHeight: number) {
  const bounds = getViewportBounds()
  const verticalCenter = buttonRect.top + buttonRect.height / 2 - height / 2
  const alignTop = buttonRect.top
  const alignBottom = rectBottom(buttonRect) - height
  const alignAbove = buttonRect.top - PANEL_GAP - height
  const alignBelow = rectBottom(buttonRect) + PANEL_GAP
  const rightSide = rectRight(buttonRect) + PANEL_GAP
  const leftSide = buttonRect.left - PANEL_GAP - width
  const centered = buttonRect.left + buttonRect.width / 2 - width / 2

  const placements: PanelPlacement[] = [
    { left: rightSide, top: alignBottom, origin: 'bottom left', maxHeight },
    { left: leftSide, top: alignBottom, origin: 'bottom right', maxHeight },
    { left: rightSide, top: alignTop, origin: 'top left', maxHeight },
    { left: leftSide, top: alignTop, origin: 'top right', maxHeight },
    { left: rightSide, top: verticalCenter, origin: 'center left', maxHeight },
    { left: leftSide, top: verticalCenter, origin: 'center right', maxHeight },
    { left: centered, top: alignAbove, origin: 'bottom center', maxHeight },
    { left: centered, top: alignBelow, origin: 'top center', maxHeight }
  ]

  return placements.map((placement) => ({
    left: clamp(placement.left, bounds.left, bounds.right - width),
    top: clamp(placement.top, bounds.top, bounds.bottom - height),
    origin: placement.origin,
    maxHeight: Math.max(PANEL_MIN_HEIGHT, maxHeight)
  }))
}

function updatePanelPosition() {
  if (!isOpen.value || !fabRef.value) return

  const bounds = getViewportBounds()
  const buttonRect = toRect(fabRef.value.getBoundingClientRect())
  const panelWidth = panelRef.value?.offsetWidth ?? Math.min(PANEL_WIDTH, window.innerWidth - EDGE_MARGIN * 2)
  const availableHeight = Math.max(PANEL_MIN_HEIGHT, bounds.bottom - bounds.top)
  const measuredHeight = panelRef.value?.offsetHeight ?? PANEL_FALLBACK_HEIGHT
  const panelHeight = Math.min(Math.max(PANEL_MIN_HEIGHT, measuredHeight), availableHeight)
  const tutorRect = getTutorFabRect()
  const placements = buildPanelPlacements(buttonRect, panelWidth, panelHeight, availableHeight)

  const firstPlacement = placements[0]
  if (!firstPlacement) return

  let best = firstPlacement
  let bestScore = Number.POSITIVE_INFINITY

  placements.forEach((placement) => {
    const rect = createRect(placement.left, placement.top, panelWidth, panelHeight)
    const overlapPenalty = getOverlapArea(rect, tutorRect) * 1000
    const anchorPenalty = Math.abs(placement.left - buttonRect.left) + Math.abs(placement.top - buttonRect.top)
    const score = overlapPenalty + anchorPenalty

    if (score < bestScore) {
      best = placement
      bestScore = score
    }
  })

  panelStyle.value = {
    left: `${best.left}px`,
    top: `${best.top}px`,
    width: `min(${PANEL_WIDTH}px, calc(100vw - ${EDGE_MARGIN * 2}px))`,
    maxHeight: `${best.maxHeight}px`,
    transformOrigin: best.origin
  }
}

function schedulePanelPosition() {
  if (!isOpen.value) return
  nextTick(() => {
    window.requestAnimationFrame(() => {
      updatePanelPosition()
    })
  })
}

function collapsePanel() {
  isOpen.value = false
}

function togglePanel() {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    schedulePanelPosition()
  }
}

function startDrag(event: MouseEvent | TouchEvent) {
  const pointer = getPointerPosition(event)
  if (!pointer) return

  startedWhileOpen = isOpen.value
  if (startedWhileOpen) {
    isOpen.value = false
  }

  isDragging.value = true
  dragDistance = 0
  dragStartX = pointer.x
  dragStartY = pointer.y
  dragInitialX = fabPos.value.x
  dragInitialY = fabPos.value.y

  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', endDrag)
  document.addEventListener('touchmove', onDrag, { passive: false })
  document.addEventListener('touchend', endDrag)
}

function onDrag(event: MouseEvent | TouchEvent) {
  if (!isDragging.value) return
  event.preventDefault()

  const pointer = getPointerPosition(event)
  if (!pointer) return

  const dx = pointer.x - dragStartX
  const dy = pointer.y - dragStartY
  dragDistance = Math.abs(dx) + Math.abs(dy)

  fabPos.value = clampFabPosition({
    x: dragInitialX + dx,
    y: dragInitialY + dy
  })
}

function endDrag() {
  if (!isDragging.value) return

  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', endDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', endDrag)

  if (dragDistance < 5) {
    if (startedWhileOpen) {
      collapsePanel()
    } else {
      togglePanel()
    }
  } else {
    updateFabPosition(fabPos.value, true)
  }

  persistState()
}

function saveNote() {
  const content = editorText.value.trim()
  if (!content) {
    ElMessage.warning({ message: '请先输入笔记内容', plain: true })
    return
  }

  savedNotes.value = [
    {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      content,
      savedAt: new Date().toISOString()
    },
    ...savedNotes.value
  ].slice(0, GLOBAL_NOTE_STORAGE_LIMIT)

  editorText.value = ''
  if (currentUser.value?.id) {
    writeGlobalNotesState(currentUser.value.id, (prev) => ({
      ...prev,
      draft: '',
      savedNotes: savedNotes.value.slice(0, GLOBAL_NOTE_STORAGE_LIMIT)
    }))
  }
  persistState()
  ElMessage.success({ message: '笔记已保存，下次打开将展示新的空白页', plain: true })
  schedulePanelPosition()
}

function handleWindowResize() {
  updateFabPosition(fabPos.value, false)
  schedulePanelPosition()
}

function handleGlobalPointerDown(event: MouseEvent | TouchEvent) {
  if (!isOpen.value) return
  const target = event.target as Node | null
  if (target && layerRef.value?.contains(target)) return
  collapsePanel()
}

function handleGlobalKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    collapsePanel()
  }
}

function startTutorAvoidLoop() {
  stopTutorAvoidLoop()
  tutorAvoidTimer = window.setInterval(() => {
    const nextPosition = resolveFabPosition(fabPos.value, false)
    if (nextPosition.x !== fabPos.value.x || nextPosition.y !== fabPos.value.y) {
      fabPos.value = nextPosition
      persistState()
    }
    if (isOpen.value) {
      updatePanelPosition()
    }
  }, TUTOR_AVOID_INTERVAL_MS)
}

function stopTutorAvoidLoop() {
  if (tutorAvoidTimer) {
    clearInterval(tutorAvoidTimer)
    tutorAvoidTimer = null
  }
}

watch(storageKey, (key) => {
  isOpen.value = false
  if (!key) return
  loadState()
  schedulePanelPosition()
}, { immediate: true })

watch(editorText, () => {
  if (currentUser.value?.id) {
    writeGlobalNotesState(currentUser.value.id, (prev) => ({
      ...prev,
      draft: editorText.value,
      savedNotes: savedNotes.value.slice(0, GLOBAL_NOTE_STORAGE_LIMIT)
    }))
  }
  persistState()
})

watch(savedNotes, () => {
  persistState()
}, { deep: true })

watch(fabPos, () => {
  persistState()
})

watch(isOpen, (open) => {
  if (open) {
    schedulePanelPosition()
  }
})

watch(() => route.path, (path) => {
  updateFabPosition(fabPos.value.x || fabPos.value.y ? fabPos.value : getDefaultFabPosition(), false)
  if (path.startsWith('/tutor')) {
    startTutorAvoidLoop()
  } else {
    stopTutorAvoidLoop()
  }
  schedulePanelPosition()
}, { immediate: true })

onMounted(() => {
  window.addEventListener('resize', handleWindowResize)
  document.addEventListener('mousedown', handleGlobalPointerDown)
  document.addEventListener('touchstart', handleGlobalPointerDown, { passive: true })
  document.addEventListener('keydown', handleGlobalKeydown)
})

onBeforeUnmount(() => {
  stopTutorAvoidLoop()
  window.removeEventListener('resize', handleWindowResize)
  document.removeEventListener('mousedown', handleGlobalPointerDown)
  document.removeEventListener('touchstart', handleGlobalPointerDown)
  document.removeEventListener('keydown', handleGlobalKeydown)
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', endDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', endDrag)
})
</script>

<style scoped>
.global-note-layer {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 1200;
}

.global-note-fab,
.note-panel {
  pointer-events: auto;
}

.global-note-fab {
  position: fixed;
  touch-action: none;
  transition: left 0.22s ease, top 0.22s ease, transform 0.22s ease;
}

.global-note-fab.is-dragging {
  transition: none;
}

.note-fab-button {
  width: 56px;
  height: 56px;
  border: none;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1d4ed8, #2563eb 55%, #0f766e);
  color: #fff;
  font-size: 1.35rem;
  box-shadow: 0 18px 40px rgba(29, 78, 216, 0.22), 0 8px 18px rgba(15, 118, 110, 0.16);
  cursor: pointer;
}

.note-fab-button:hover {
  transform: translateY(-1px) scale(1.03);
}

.note-panel {
  position: fixed;
  display: flex;
  flex-direction: column;
  max-width: calc(100vw - 32px);
  max-height: calc(100vh - 32px);
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(191, 219, 254, 0.92);
  border-radius: 24px;
  box-shadow: 0 22px 60px rgba(15, 23, 42, 0.16), 0 8px 18px rgba(37, 99, 235, 0.08);
  overflow: hidden;
  backdrop-filter: blur(18px);
}

.note-panel-header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 18px 56px 14px;
  background:
    radial-gradient(circle at top right, rgba(191, 219, 254, 0.95), transparent 40%),
    linear-gradient(180deg, rgba(239, 246, 255, 0.96), rgba(255, 255, 255, 0.92));
  border-bottom: 1px solid rgba(191, 219, 254, 0.78);
  cursor: pointer;
}

.note-panel-title-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-width: 0;
  flex: 1;
  text-align: center;
}

.note-panel-icon {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(37, 99, 235, 0.12);
  color: #1d4ed8;
  flex-shrink: 0;
}

.note-panel-title-wrap h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
}

.note-panel-title-wrap p {
  margin: 4px 0 0;
  font-size: 0.78rem;
  line-height: 1.5;
  color: #475569;
}

.collapse-btn {
  position: absolute;
  top: 18px;
  right: 18px;
  width: 34px;
  height: 34px;
  min-height: 34px;
  padding: 0;
  border: none;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(255, 255, 255, 0.96);
  color: #1e293b;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  box-shadow: 0 6px 16px rgba(148, 163, 184, 0.16);
  z-index: 1;
}

.collapse-btn .el-icon {
  font-size: 1rem;
  font-weight: 700;
}

.collapse-btn:hover {
  background: #eff6ff;
  color: #1d4ed8;
  border-color: rgba(96, 165, 250, 0.42);
}

.collapse-btn:active {
  transform: scale(0.96);
}

.note-panel-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px 18px 18px;
  min-height: 0;
  flex: 1;
}

.note-meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
  font-size: 0.78rem;
  font-weight: 600;
}

.meta-chip.subtle {
  background: rgba(226, 232, 240, 0.7);
  color: #475569;
}

.note-textarea {
  width: 100%;
  min-height: 220px;
  flex: 1;
  resize: none;
  border: 1px solid rgba(203, 213, 225, 0.95);
  border-radius: 18px;
  padding: 16px;
  font: inherit;
  line-height: 1.7;
  color: #0f172a;
  background: rgba(248, 250, 252, 0.9);
  box-sizing: border-box;
  outline: none;
}

.note-textarea:focus {
  border-color: rgba(59, 130, 246, 0.75);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.12);
}

.note-panel-footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.footer-hint {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.saved-count {
  font-size: 0.78rem;
  color: #64748b;
}

.save-btn {
  height: 42px;
  padding: 0 16px;
  border: none;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #2563eb, #0f766e);
  color: #fff;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  flex-shrink: 0;
  justify-content: center;
  min-width: 132px;
}

.save-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 22px rgba(37, 99, 235, 0.24);
}

.note-panel-fade-enter-active,
.note-panel-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.note-panel-fade-enter-from,
.note-panel-fade-leave-to {
  opacity: 0;
  transform: scale(0.96);
}

@media (max-width: 768px) {
  .note-panel-header {
    padding: 16px 16px 12px;
  }

  .note-panel-body {
    padding: 14px 16px 16px;
  }

  .note-textarea {
    min-height: 180px;
  }
}
</style>
