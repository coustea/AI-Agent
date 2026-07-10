import { onMounted, onUnmounted } from 'vue' // 导入 Vue 生命周期钩子
import { useRouter } from 'vue-router' // 导入路由实例
import { getAuthStatus } from '@/features/auth/api/auth' // 导入认证状态检查 API
import { clearCurrentUser } from '@/features/auth/model/currentUser' // 导入清除用户缓存函数
import { AUTH_EXPIRED_EVENT, clearAuthToken } from '@/shared/auth/token' // 导入 Token 管理函数

// 定时轮询鉴权状态，登录失效时自动跳转到登录页
export function useAuthPolling(intervalMs: number = 60000) { // 认证状态轮询钩子（默认 60 秒检查一次）
  const router = useRouter()
  let timer: number | undefined // 定时器 ID
  let isChecking = false // 是否正在检查中（防止并发）
  let redirected = false // 是否已重定向到登录页（防止重复跳转）

  // 清除用户态与令牌并跳转登录页（只跳转一次）
  const redirectToLogin = () => { // 重定向到登录页并清理认证状态
    if (redirected) return // 已重定向则跳过
    redirected = true
    clearCurrentUser() // 清除用户缓存
    clearAuthToken() // 清除本地 Token
    router.push('/login') // 跳转登录页
  }

  // 单次校验：请求失败即视为已失效，触发跳转
  const checkAuth = async () => { // 检查认证状态
    if (isChecking || redirected) return // 正在检查或已重定向则跳过
    isChecking = true
    try {
      await getAuthStatus() // 调用后端认证状态接口
    } catch {
      redirectToLogin() // 请求失败 → Token 失效，重定向登录
    } finally {
      isChecking = false
    }
  }

  // 监听全局“令牌过期”事件后跳转
  const onAuthExpired = () => { // Token 过期事件回调
    redirectToLogin()
  }

  // 立即校验一次并启动定时轮询
  const startPolling = () => { // 启动轮询
    if (timer) return // 已启动则跳过
    checkAuth() // 首次立即检查
    timer = window.setInterval(checkAuth, intervalMs) // 定时轮询
  }

  // 停止轮询并清理定时器
  const stopPolling = () => { // 停止轮询
    if (timer) {
      clearInterval(timer)
      timer = undefined
    }
  }

  onMounted(() => { // 挂载时启动轮询和事件监听
    startPolling()
    window.addEventListener(AUTH_EXPIRED_EVENT, onAuthExpired) // 监听 Token 过期事件
  })

  onUnmounted(() => { // 卸载时清理轮询和事件监听
    stopPolling()
    window.removeEventListener(AUTH_EXPIRED_EVENT, onAuthExpired)
  })

  return { startPolling, stopPolling, checkAuth } // 暴露控制函数
}
