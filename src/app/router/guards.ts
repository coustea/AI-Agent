import type { Router } from 'vue-router' // 导入路由类型
import { hasAuthToken } from '@/shared/auth/token' // 导入 Token 检测函数
import { recordTutorEntryIntent } from '@/features/chat/model/tutorEntryIntent'

const AUTH_PATHS = new Set(['/login', '/register']) // 认证页面路径集合（已登录时需跳转走）
const PUBLIC_PATHS = new Set(['/login', '/register', '/onboarding']) // 公开页面路径集合（无需登录即可访问）

// 安装全局前置路由守卫（登录状态校验与重定向）
export function installRouterGuards(router: Router): void { // 安装路由守卫函数
  // 全局前置守卫：校验登录状态并执行路由拦截/放行
  router.beforeEach((to, from, next) => { // 全局前置守卫
    const hasToken = hasAuthToken() // 检查是否持有有效 Token
    const isPublicPath = PUBLIC_PATHS.has(to.path) // 检查目标路径是否为公开页面

    // 未登录访问受保护页面 → 重定向到登录页
    if (!isPublicPath && !hasToken) { // 未登录访问受保护页面 → 重定向到登录
      next('/login')
      return
    }

    // 已登录访问登录/注册页 → 重定向到仪表盘
    if (AUTH_PATHS.has(to.path) && hasToken) { // 已登录访问认证页面 → 重定向到首页
      next('/dashboard')
      return
    }

    recordTutorEntryIntent({
      fromPath: from.path,
      toPath: to.path,
      hasResolvedFromRoute: from.matched.length > 0,
    })

    next() // 放行
  })
}
