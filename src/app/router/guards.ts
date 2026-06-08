import type { Router } from 'vue-router'
import { hasAuthToken } from '@/shared/auth/token'

const AUTH_PATHS = new Set(['/login', '/register'])
const PUBLIC_PATHS = new Set(['/login', '/register', '/onboarding'])

export function installRouterGuards(router: Router): void {
  router.beforeEach((to, _from, next) => {
    const hasToken = hasAuthToken()

    if (!PUBLIC_PATHS.has(to.path) && !hasToken) {
      next('/login')
      return
    }

    if (AUTH_PATHS.has(to.path) && hasToken) {
      next('/dashboard')
      return
    }

    next()
  })
}
