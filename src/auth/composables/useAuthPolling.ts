import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { getAuthStatus } from '@/auth/api/auth'

export function useAuthPolling(intervalMs: number = 60000) {
  const router = useRouter()
  let timer: number | undefined
  let isChecking = false
  let redirected = false

  const redirectToLogin = () => {
    if (redirected) return
    redirected = true
    localStorage.removeItem('token')
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
    window.addEventListener('auth:expired', onAuthExpired)
  })

  onUnmounted(() => {
    stopPolling()
    window.removeEventListener('auth:expired', onAuthExpired)
  })

  return { startPolling, stopPolling, checkAuth }
}
