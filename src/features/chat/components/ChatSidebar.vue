<script setup lang="ts">
import { computed, ref } from 'vue'
import { PopoverRoot, PopoverTrigger, PopoverPortal, PopoverContent } from 'reka-ui'
import { PhChatCenteredText as ChatLineRound, PhChat as ChatLineSquare,
  PhTrash as Delete, PhPencilSimple as EditPen, PhMagnifyingGlass as Search,
  PhClock as Timer } from '@phosphor-icons/vue'
import type { ChatSession } from '../types/chat'
import { formatRelativeTime } from '../views/tutorUtils'

const props = defineProps<{ sessions: ChatSession[]; activeId?: string }>()
const emit = defineEmits<{ create: []; select: [id: string]; archive: [id: string] }>()

const sessionSidebarCollapsed = ref(false)
const searchPopoverVisible = ref(false)
const historyPopoverVisible = ref(false)
const searchKeyword = ref('')

const groupedSessions = computed(() => {
  if (!props.sessions.length) return []

  const nowDate = new Date()
  const todayStart = new Date(nowDate.getFullYear(), nowDate.getMonth(), nowDate.getDate()).getTime()
  const yesterdayStart = todayStart - 24 * 60 * 60 * 1000
  const weekStart = todayStart - 7 * 24 * 60 * 60 * 1000

  const buckets: Record<'today' | 'yesterday' | 'week' | 'older', ChatSession[]> = {
    today: [],
    yesterday: [],
    week: [],
    older: [],
  }

  for (const s of props.sessions) {
    const ts = s.updated_at ? new Date(s.updated_at).getTime() : 0
    if (ts >= todayStart) {
      buckets.today.push(s)
    } else if (ts >= yesterdayStart) {
      buckets.yesterday.push(s)
    } else if (ts >= weekStart) {
      buckets.week.push(s)
    } else {
      buckets.older.push(s)
    }
  }

  const groups: Array<{ label: string; items: ChatSession[] }> = []
  if (buckets.today.length) groups.push({ label: '今天', items: buckets.today })
  if (buckets.yesterday.length) groups.push({ label: '昨天', items: buckets.yesterday })
  if (buckets.week.length) groups.push({ label: '最近 7 天', items: buckets.week })
  if (buckets.older.length) groups.push({ label: '更早', items: buckets.older })
  return groups
})

const filteredSessions = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return []
  return props.sessions.filter(s => {
    const title = s.title || '新对话'
    return title.toLowerCase().includes(keyword)
  })
})

</script>

<template>
  <aside class="session-sidebar" :class="{ collapsed: sessionSidebarCollapsed }">
    <div class="sidebar-top-header">
      <div class="sidebar-brand" v-if="!sessionSidebarCollapsed">
        <span class="brand-seal">
          <ChatLineRound class="brand-icon" />
        </span>
        <span class="brand-text">Mentorly</span>
      </div>
      <button
        class="collapse-toggle-btn"
        @click="sessionSidebarCollapsed = !sessionSidebarCollapsed"
        :title="sessionSidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
        :aria-label="sessionSidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <rect x="3.5" y="4" width="17" height="16" rx="3.5"></rect>
          <line x1="9" y1="4" x2="9" y2="20"></line>
        </svg>
      </button>
    </div>

    <div class="standard-sidebar-nav">
      <button
        type="button"
        :class="['nav-item', 'new-chat-btn', { active: !activeId }]"
        @click="emit('create')"
        title="新建对话"
      >
        <EditPen class="nav-icon" />
        <span class="nav-text">新建对话</span>
      </button>

      <PopoverRoot v-model:open="searchPopoverVisible">
        <PopoverTrigger as="button" type="button" class="nav-item search-item" title="搜索历史对话">
          <Search class="nav-icon" />
          <span class="nav-text">搜索对话</span>
        </PopoverTrigger>

        <PopoverPortal>
          <PopoverContent
            class="popover-content-container search-popover-content"
            side="right"
            align="start"
            :side-offset="10"
          >
            <div class="popover-search-container">
              <div class="search-input-wrapper">
                <Search class="search-input-icon" />
                <input
                  v-model="searchKeyword"
                  type="text"
                  placeholder="输入关键词搜索对话..."
                  class="input-control search-input"
                />
                <button v-if="searchKeyword" type="button" class="search-clear-btn" @click="searchKeyword = ''">×</button>
              </div>

              <div class="popover-session-scroll search-results-scroll" v-show="searchKeyword.trim() !== ''">
                <div
                  v-for="s in filteredSessions"
                  :key="s.id"
                  :class="['nav-item', 'session-item', { active: s.id === activeId }]"
                  @click="emit('select', s.id); searchPopoverVisible = false"
                >
                  <ChatLineSquare class="session-icon" />
                  <div class="session-info nav-text">
                    <span class="session-title">{{ s.title || '新对话' }}</span>
                    <span class="session-time">{{ formatRelativeTime(s.updated_at) }}</span>
                  </div>
                </div>

                <div v-if="filteredSessions.length === 0" class="session-empty nav-text">
                  未找到匹配的对话记录
                </div>
              </div>
            </div>
          </PopoverContent>
        </PopoverPortal>
      </PopoverRoot>

      <!-- 折叠态下的历史记录弹窗入口 -->
      <PopoverRoot v-model:open="historyPopoverVisible">
        <PopoverTrigger
          v-if="sessionSidebarCollapsed"
          as="button"
          type="button"
          class="nav-item history-collapsed-btn"
          title="历史记录"
          aria-label="历史记录"
        >
          <Timer class="nav-icon" />
        </PopoverTrigger>

        <PopoverPortal>
          <PopoverContent
            class="popover-content-container history-popover-content"
            side="right"
            align="start"
            :side-offset="10"
          >
            <div class="history-popover-header">
              <div class="history-popover-heading">
                <Timer class="history-popover-icon" aria-hidden="true" />
                <div>
                  <div class="popover-title">历史记录</div>
                  <div class="history-popover-count">{{ sessions.length }} 个对话</div>
                </div>
              </div>
            </div>
            <div class="popover-session-scroll">
              <div
                v-for="s in sessions"
                :key="s.id"
                :class="['nav-item', 'session-item', { active: s.id === activeId }]"
                :title="s.title || '新对话'"
                :aria-current="s.id === activeId ? 'true' : undefined"
                @click="emit('select', s.id); historyPopoverVisible = false"
              >
                <ChatLineSquare class="session-icon" />
                <div class="session-info nav-text">
                  <span class="session-title-line">
                    <span class="session-title">{{ s.title || '新对话' }}</span>
                    <span v-if="s.id === activeId" class="current-session-indicator">当前</span>
                  </span>
                  <span class="session-time">{{ formatRelativeTime(s.updated_at) }}</span>
                </div>
                <button
                  type="button"
                  class="btn-link del-btn nav-text"
                  aria-label="删除对话"
                  title="删除对话"
                  @click.stop="historyPopoverVisible = false; emit('archive', s.id)"
                >
                  <Delete class="del-icon" />
                </button>
              </div>
              <div v-if="sessions.length === 0" class="session-empty nav-text">暂无对话记录</div>
            </div>
          </PopoverContent>
        </PopoverPortal>
      </PopoverRoot>
    </div>

    <!-- 展开态：按时间分组的历史会话列表 -->
    <div class="session-list" v-show="!sessionSidebarCollapsed">
      <template v-if="groupedSessions.length > 0">
        <div
          v-for="group in groupedSessions"
          :key="group.label"
          class="session-group"
        >
          <div class="session-group-label">{{ group.label }}</div>
          <div
            v-for="s in group.items"
            :key="s.id"
            :class="['nav-item', 'session-item', { active: s.id === activeId }]"
            :title="s.title || '新对话'"
            @click="emit('select', s.id)"
          >
            <ChatLineSquare class="session-icon" />
            <div class="session-info nav-text">
              <span class="session-title">{{ s.title || '新对话' }}</span>
              <span class="session-time">{{ formatRelativeTime(s.updated_at) }}</span>
            </div>
            <button
              type="button"
              class="btn-link del-btn nav-text"
              title="删除对话"
              aria-label="删除对话"
              @click.stop="emit('archive', s.id)"
            >
              <Delete class="del-icon" />
            </button>
          </div>
        </div>
      </template>
      <div v-else class="session-empty nav-text">
        暂无历史对话，开始你的第一次提问吧
      </div>
    </div>
  </aside>
</template>

<style scoped>
.session-sidebar {
  position: relative;
  width: 256px;
  background: var(--color-bg);
  border-right: 1px solid var(--color-border-light);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-top-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 12px 10px 16px;
  height: 58px;
  box-sizing: border-box;
  flex-shrink: 0;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--color-text-strong);
  font-weight: 700;
  font-size: 0.98rem;
  letter-spacing: -0.01em;
}

.brand-seal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--color-primary-soft);
  border: 1px solid var(--color-primary-border);
  color: var(--color-primary-text);
}

.brand-icon {
  width: 17px;
  height: 17px;
}

.collapse-toggle-btn {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: background-color 150ms ease, color 150ms ease;
  width: 34px;
  height: 34px;
  padding: 0;
}

.collapse-toggle-btn:hover {
  background: var(--color-surface-hover);
  color: var(--color-text-strong);
}

.collapse-toggle-btn svg {
  width: 18px;
  height: 18px;
}

.standard-sidebar-nav {
  padding: 4px 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
}

.nav-item {
  width: 100%;
  height: auto;
  min-height: 38px;
  background: transparent;
  border: 1px solid transparent;
  box-shadow: none;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 9px;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 150ms ease;
  color: var(--color-text-secondary);
  text-align: left;
}

.nav-item:hover {
  background: var(--color-surface-hover);
  color: var(--color-text-strong);
}

.nav-item.new-chat-btn {
  background: var(--color-surface);
  border-color: var(--color-border);
  color: var(--color-text-strong);
  font-weight: 600;
  box-shadow: var(--shadow-xs);
}

.nav-item.new-chat-btn:hover {
  border-color: var(--color-primary);
  background: var(--color-surface-hover);
}

.nav-icon {
  width: 17px;
  height: 17px;
  flex-shrink: 0;
  color: var(--color-primary-text);
}

/* 会话分组列表 */
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.session-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.session-group-label {
  padding: 4px 10px 4px;
  font-size: 11px;
  font-weight: 650;
  color: var(--color-text-faint);
  letter-spacing: 0.02em;
  user-select: none;
}

.session-item {
  min-height: 44px;
  padding: 7px 10px;
  border-radius: 9px;
  color: var(--color-text-secondary);
}

.session-item:hover {
  background: var(--color-surface);
  border-color: var(--color-border-light);
  color: var(--color-text-strong);
}

.session-item.active {
  background: var(--color-primary-soft);
  border-color: var(--color-primary-border);
  color: var(--color-primary-text);
  font-weight: 600;
}

.session-icon {
  width: 16px;
  height: 16px;
  color: var(--color-text-faint);
  flex-shrink: 0;
  transition: color 150ms ease;
}

.session-item.active .session-icon {
  color: var(--color-primary-text);
}

.session-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1px;
  overflow: hidden;
  min-width: 0;
}

.session-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.84rem;
  line-height: 1.35;
}

.session-time {
  font-size: 0.68rem;
  color: var(--color-text-faint);
  white-space: nowrap;
}

.session-item.active .session-time {
  color: var(--color-text-secondary);
}

.del-btn {
  opacity: 0;
  width: 26px;
  height: 26px;
  min-height: 26px;
  padding: 0;
  border-radius: 6px;
  color: var(--color-text-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: opacity 140ms ease, background-color 140ms ease, color 140ms ease;
}

.session-item:hover .del-btn,
.del-btn:focus-visible {
  opacity: 1;
}

.del-btn:hover {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

.del-icon {
  width: 14px;
  height: 14px;
}

.session-empty {
  font-size: 0.8rem;
  color: var(--color-text-faint);
  text-align: center;
  padding: 28px 12px;
  line-height: 1.5;
}

/* 侧边栏折叠态 */
.session-sidebar.collapsed {
  width: 64px;
}

.session-sidebar.collapsed .nav-text,
.session-sidebar.collapsed .session-info {
  display: none;
}

.session-sidebar.collapsed .sidebar-top-header,
.session-sidebar.collapsed .standard-sidebar-nav {
  padding-left: 0;
  padding-right: 0;
  align-items: center;
}

.session-sidebar.collapsed .collapse-toggle-btn,
.session-sidebar.collapsed .nav-item {
  width: 40px !important;
  height: 40px !important;
  min-width: 40px !important;
  min-height: 40px !important;
  padding: 0;
  justify-content: center;
  border-radius: 10px;
}

/* 侧边栏弹出层 (Search & History Popover) */
:global(.search-popover-content),
:global(.history-popover-content) {
  width: min(320px, calc(100vw - 88px));
  max-height: min(500px, calc(100vh - 32px));
  padding: 12px;
  overflow: hidden;
  box-sizing: border-box;
  background-color: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  box-shadow: var(--shadow-md);
  outline: none;
  z-index: 1200;
}

.popover-search-container {
  display: flex;
  flex-direction: column;
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  height: 36px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 8px;
}

.search-input-icon {
  width: 15px;
  height: 15px;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font-size: 0.84rem;
  color: var(--color-text);
}

.search-clear-btn {
  width: 20px;
  height: 20px;
  min-height: 20px;
  padding: 0;
  background: transparent;
  color: var(--color-text-muted);
}

.popover-session-scroll {
  max-height: 360px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 8px;
}

.history-popover-header {
  display: flex;
  align-items: center;
  padding: 2px 4px 10px;
  border-bottom: 1px solid var(--color-border-light);
}

.history-popover-heading {
  display: flex;
  align-items: center;
  gap: 10px;
}

.history-popover-icon {
  width: 30px;
  height: 30px;
  padding: 6px;
  color: var(--color-primary-text);
  background: var(--color-primary-soft);
  border-radius: 8px;
}

.popover-title {
  color: var(--color-text-strong);
  font-size: 0.9rem;
  font-weight: 700;
}

.history-popover-count {
  color: var(--color-text-faint);
  font-size: 0.72rem;
}

.session-title-line {
  display: flex;
  align-items: center;
  gap: 6px;
}

.current-session-indicator {
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  font-size: 0.65rem;
  font-weight: 650;
}

</style>
