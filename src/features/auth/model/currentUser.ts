import { computed, ref } from 'vue'
import { getMe } from '@/features/auth/api/auth'
import type { LoginData } from '@/features/auth/model/auth'

type CurrentUser = LoginData['user']

const currentUser = ref<CurrentUser | null>(null)
const currentUserLoaded = ref(false)
let currentUserRequest: Promise<CurrentUser | null> | null = null

export function useCurrentUser() {
  const userName = computed(() => currentUser.value?.username || '用户')

  return {
    currentUser,
    currentUserLoaded,
    userName,
  }
}

export function setCurrentUser(user: CurrentUser | null) {
  currentUser.value = user
  currentUserLoaded.value = true
}

export function clearCurrentUser() {
  currentUser.value = null
  currentUserLoaded.value = false
  currentUserRequest = null
}

export async function ensureCurrentUser(force = false): Promise<CurrentUser | null> {
  if (!force && currentUserLoaded.value) {
    return currentUser.value
  }

  if (!force && currentUserRequest) {
    return currentUserRequest
  }

  currentUserRequest = getMe()
    .then((res) => {
      const user = res.data.data || null
      setCurrentUser(user)
      return user
    })
    .catch(() => {
      clearCurrentUser()
      return null
    })
    .finally(() => {
      currentUserRequest = null
    })

  return currentUserRequest
}
