import { computed, ref } from 'vue'
import { getMe } from '@/features/auth/api/auth'
import type { LoginData } from '@/features/auth/model/auth'

type CurrentUser = LoginData['user']

// 全局共享的当前用户状态（跨越组件保持单例）
const currentUser = ref<CurrentUser | null>(null)
const currentUserLoaded = ref(false)
let currentUserRequest: Promise<CurrentUser | null> | null = null

// 提供当前用户相关响应式引用
export function useCurrentUser() {
  const userName = computed(() => currentUser.value?.username || '用户')

  return {
    currentUser,
    currentUserLoaded,
    userName,
  }
}

// 写入用户信息并标记已加载
export function setCurrentUser(user: CurrentUser | null) {
  currentUser.value = user
  currentUserLoaded.value = true
}

// 清空用户状态（登出或鉴权失败时调用）
export function clearCurrentUser() {
  currentUser.value = null
  currentUserLoaded.value = false
  currentUserRequest = null
}

// 确保当前用户已加载：命中缓存或复用进行中的请求，避免重复拉取
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
