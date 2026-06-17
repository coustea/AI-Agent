import { ref, watch, type Ref } from 'vue'

export interface GlobalStoredNote {
  id: string
  content: string
  savedAt: string
}

interface GlobalNotesState {
  position?: {
    x: number
    y: number
  }
  draft?: string
  savedNotes?: GlobalStoredNote[]
}

export const GLOBAL_NOTE_STORAGE_LIMIT = 20
export const GLOBAL_NOTE_STORAGE_EVENT = 'global-note-storage-updated'

export function getGlobalNoteStorageKey(userId: number | string) {
  return `global-note-fab:${userId}`
}

export function readGlobalNotesState(userId: number | string): GlobalNotesState {
  const storageKey = getGlobalNoteStorageKey(userId)
  const raw = localStorage.getItem(storageKey)

  if (!raw) return {}

  try {
    return JSON.parse(raw) as GlobalNotesState
  } catch {
    localStorage.removeItem(storageKey)
    return {}
  }
}

export function writeGlobalNotesState(userId: number | string, updater: (prev: GlobalNotesState) => GlobalNotesState) {
  const storageKey = getGlobalNoteStorageKey(userId)
  const previous = readGlobalNotesState(userId)
  const next = updater(previous)
  localStorage.setItem(storageKey, JSON.stringify(next))
  window.dispatchEvent(new CustomEvent(GLOBAL_NOTE_STORAGE_EVENT, {
    detail: { storageKey }
  }))
}

export function useGlobalNotesSnapshot(userId: Ref<number | null | undefined>) {
  const draft = ref('')
  const savedNotes = ref<GlobalStoredNote[]>([])

  const sync = () => {
    if (!userId.value) {
      draft.value = ''
      savedNotes.value = []
      return
    }

    const state = readGlobalNotesState(userId.value)
    draft.value = typeof state.draft === 'string' ? state.draft : ''
    savedNotes.value = Array.isArray(state.savedNotes) ? state.savedNotes.slice(0, GLOBAL_NOTE_STORAGE_LIMIT) : []
  }

  sync()

  const handleUpdate = (event: Event) => {
    if (!userId.value) return
    const customEvent = event as CustomEvent<{ storageKey?: string }>
    if (customEvent.detail?.storageKey !== getGlobalNoteStorageKey(userId.value)) return
    sync()
  }

  window.addEventListener(GLOBAL_NOTE_STORAGE_EVENT, handleUpdate)
  watch(userId, () => {
    sync()
  })

  return {
    draft,
    savedNotes,
    sync,
    dispose() {
      window.removeEventListener(GLOBAL_NOTE_STORAGE_EVENT, handleUpdate)
    }
  }
}
