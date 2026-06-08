import { createRouter, createWebHistory } from 'vue-router'
import { installRouterGuards } from '@/app/router/guards'
import { routes } from '@/app/router/routes'

const router = createRouter({
  history: createWebHistory(),
  routes
})

installRouterGuards(router)

export default router
