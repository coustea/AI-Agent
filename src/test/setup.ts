import { afterEach } from 'vitest'

const storage = new Map<string, string>()
const mockLocalStorage = {
  getItem: (key: string) => storage.get(key) ?? null,
  setItem: (key: string, value: string) => storage.set(key, String(value)),
  removeItem: (key: string) => storage.delete(key),
  clear: () => storage.clear(),
  get length() { return storage.size },
  key: (i: number) => Array.from(storage.keys())[i] ?? null,
}
Object.defineProperty(window, 'localStorage', { value: mockLocalStorage, writable: true })
if (typeof globalThis.localStorage !== 'undefined') {
  Object.defineProperty(globalThis, 'localStorage', { value: mockLocalStorage, writable: true })
}

afterEach(() => {
  document.body.innerHTML = ''
  document.documentElement.classList.remove('dark')
})

