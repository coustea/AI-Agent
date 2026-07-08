import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { getAuthStatus } from '@/features/auth/api/auth'
import { clearCurrentUser } from '@/features/auth/model/currentUser'
import { AUTH_EXPIRED_EVENT, clearAuthToken } from '@/shared/auth/token'

// 定时轮询鉴权状态，登录失效时自动跳转到登录页
export function useAuthPolling(intervalMs: number = 60000) {
  const router = useRouter()
  let timer: number | undefined
  let isChecking = false
  let redirected = false

  // 清除用户态与令牌并跳转登录页（只跳转一次）
  const redirectToLogin = () => {
    if (redirected) return
    redirected = true
    clearCurrentUser()
    clearAuthToken()
    router.push('/login')
  }

  // 单次校验：请求失败即视为已失效，触发跳转
  const checkAuth = async () => {
    if (isChecking || redirected) return
    isChecking = true
    try {
      await getAuthStatus()
    } catch {
      redirectToLogin()
    } finally {
      isChecking = false
    }
  }

  // 监听全局“令牌过期”事件后跳转
  const onAuthExpired = () => {
    redirectToLogin()
  }

  // 立即校验一次并启动定时轮询
  const startPolling = () => {
    if (timer) return
    checkAuth()
    timer = window.setInterval(checkAuth, intervalMs)
  }

  // 停止轮询并清理定时器
  const stopPolling = () => {
    if (timer) {
      clearInterval(timer)
      timer = undefined
    }
  }

  onMounted(() => {
    startPolling()
    window.addEventListener(AUTH_EXPIRED_EVENT, onAuthExpired)
  })

  onUnmounted(() => {
    stopPolling()
    window.removeEventListener(AUTH_EXPIRED_EVENT, onAuthExpired)
  })

  return { startPolling, stopPolling, checkAuth }
}
