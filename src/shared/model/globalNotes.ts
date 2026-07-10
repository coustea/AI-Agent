import { ref, watch, type Ref } from 'vue' // 导入 Vue 响应式 API

// 全局笔记模型：管理跨组件的笔记持久化、草稿同步与存储操作

export interface GlobalStoredNote { // 全局笔记存储结构
  id: string // 笔记唯一标识
  content: string // 笔记内容
  savedAt: string // 保存时间戳
}

interface GlobalNotesState { // 全局笔记状态（包含位置、草稿和已保存列表）
  position?: {
    x: number // X 坐标位置
    y: number // Y 坐标位置
  }
  draft?: string // 当前草稿内容
  savedNotes?: GlobalStoredNote[] // 已保存的笔记列表
}

export const GLOBAL_NOTE_STORAGE_LIMIT = 20 // 全局笔记最大存储条数
export const GLOBAL_NOTE_STORAGE_EVENT = 'global-note-storage-updated' // 笔记存储更新自定义事件名

export function getGlobalNoteStorageKey(userId: number | string) { // 根据用户 ID 生成 localStorage 存储键
  return `global-note-fab:${userId}`
}

export function readGlobalNotesState(userId: number | string): GlobalNotesState { // 从 localStorage 读取笔记状态
  const storageKey = getGlobalNoteStorageKey(userId)
  const raw = localStorage.getItem(storageKey)

  if (!raw) return {} // 无数据时返回空状态

  try {
    return JSON.parse(raw) as GlobalNotesState // 解析 JSON
  } catch {
    localStorage.removeItem(storageKey) // 解析失败时清除损坏数据
    return {}
  }
}

export function writeGlobalNotesState(userId: number | string, updater: (prev: GlobalNotesState) => GlobalNotesState) { // 写入笔记状态（支持增量更新）
  const storageKey = getGlobalNoteStorageKey(userId)
  const previous = readGlobalNotesState(userId) // 读取当前状态
  const next = updater(previous) // 应用更新函数
  localStorage.setItem(storageKey, JSON.stringify(next)) // 写入 localStorage
  window.dispatchEvent(new CustomEvent(GLOBAL_NOTE_STORAGE_EVENT, { // 派发更新事件通知其他组件
    detail: { storageKey }
  }))
}

export function useGlobalNotesSnapshot(userId: Ref<number | null | undefined>) { // 响应式笔记快照钩子（跨组件同步笔记状态）
  const draft = ref('') // 当前草稿内容
  const savedNotes = ref<GlobalStoredNote[]>([]) // 已保存笔记列表

  const sync = () => { // 从 localStorage 同步笔记状态到响应式变量
    if (!userId.value) { // 无用户时清空
      draft.value = ''
      savedNotes.value = []
      return
    }

    const state = readGlobalNotesState(userId.value)
    draft.value = typeof state.draft === 'string' ? state.draft : ''
    savedNotes.value = Array.isArray(state.savedNotes) ? state.savedNotes.slice(0, GLOBAL_NOTE_STORAGE_LIMIT) : [] // 限制最大条数
  }

  sync() // 初始同步

  const handleUpdate = (event: Event) => { // 监听其他组件的笔记更新事件
    if (!userId.value) return
    const customEvent = event as CustomEvent<{ storageKey?: string }>
    if (customEvent.detail?.storageKey !== getGlobalNoteStorageKey(userId.value)) return // 仅处理当前用户的更新
    sync()
  }

  window.addEventListener(GLOBAL_NOTE_STORAGE_EVENT, handleUpdate) // 注册跨组件更新监听
  watch(userId, () => { // 用户切换时重新同步
    sync()
  })

  return {
    draft, // 草稿内容
    savedNotes, // 已保存笔记
    sync, // 手动同步函数
    dispose() { // 清理事件监听
      window.removeEventListener(GLOBAL_NOTE_STORAGE_EVENT, handleUpdate)
    }
  }
}
