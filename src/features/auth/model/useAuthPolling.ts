import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { getAuthStatus } from '@/features/auth/api/auth'
import { clearCurrentUser } from '@/features/auth/model/currentUser'
import { AUTH_EXPIRED_EVENT, clearAuthToken } from '@/shared/auth/token'

export function useAuthPolling(intervalMs: number = 60000) {
  const router = useRouter()
  let timer: number | undefined
  let isChecking = false
  let redirected = false

  const redirectToLogin = () => {
    if (redirected) return
    redirected = true
    clearCurrentUser()
    clearAuthToken()
    router.push('/login')
  }

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

  const onAuthExpired = () => {
    redirectToLogin()
  }

  const startPolling = () => {
    if (timer) return
    checkAuth()
    timer = window.setInterval(checkAuth, intervalMs)
  }

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
