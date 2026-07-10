import { computed, ref } from 'vue' // 导入 Vue 响应式 API
import { getMe } from '@/features/auth/api/auth' // 导入获取当前用户信息 API
import type { LoginData } from '@/features/auth/model/auth' // 导入登录数据类型

type CurrentUser = LoginData['user'] // 当前用户类型（复用登录响应中的 user 结构）

// 全局共享的当前用户状态（跨越组件保持单例）
const currentUser = ref<CurrentUser | null>(null) // 全局当前用户响应式状态
const currentUserLoaded = ref(false) // 用户信息是否已加载标记
let currentUserRequest: Promise<CurrentUser | null> | null = null // 正在进行的请求（防止重复调用）

// 暴露当前用户相关响应式引用供组件使用
export function useCurrentUser() { // 获取当前用户信息的组合式函数
  const userName = computed(() => currentUser.value?.username || '用户') // 计算用户名，未加载时显示默认值

  return {
    currentUser, // 当前用户对象
    currentUserLoaded, // 是否已加载
    userName, // 用户名（计算属性）
  }
}

// 写入用户信息并标记已加载
export function setCurrentUser(user: CurrentUser | null) { // 设置当前用户信息
  currentUser.value = user
  currentUserLoaded.value = true
}

// 清空用户状态（登出或鉴权失败时调用）
export function clearCurrentUser() { // 清除当前用户缓存（登出或 Token 失效时调用）
  currentUser.value = null
  currentUserLoaded.value = false
  currentUserRequest = null
}

// 确保当前用户已加载：命中缓存或复用进行中的请求，避免重复拉取
export async function ensureCurrentUser(force = false): Promise<CurrentUser | null> { // 确保用户信息已加载（支持强制刷新）
  if (!force && currentUserLoaded.value) { // 已加载且非强制刷新 → 直接返回缓存
    return currentUser.value
  }

  if (!force && currentUserRequest) { // 请求进行中 → 复用同一个 Promise
    return currentUserRequest
  }

  currentUserRequest = getMe() // 发起获取用户信息请求
    .then((res) => {
      const user = res.data.data || null
      setCurrentUser(user) // 设置用户信息
      return user
    })
    .catch(() => {
      clearCurrentUser() // 请求失败 → 清除缓存
      return null
    })
    .finally(() => {
      currentUserRequest = null // 请求结束后清除引用
    })

  return currentUserRequest
}
