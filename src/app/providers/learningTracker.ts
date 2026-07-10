import type { App } from 'vue'
import type { Router } from 'vue-router'
import { hasAuthToken } from '@/shared/auth/token'
import { startTracking, stopTracking } from '@/features/evaluation/model/useLearningTracker'
import type { TrackingContext } from '@/features/evaluation/model/useLearningTracker'

// 工具函数：安全地将未知值转为数字，无效值返回 undefined
function toNumber(value: unknown): number | undefined {
  if (value === null || value === undefined || value === '') return undefined
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : undefined
}

// 根据当前路由解析学习追踪上下文（来源页面、资源/路径节点 ID 等）
function getContextFromRoute(route: Router['currentRoute']['value']): TrackingContext {
  const name = String(route.name || '')

  // 资源详情页：记录 resourceId
  if (name === 'ResourceResult') {
    return {
      sourcePage: 'resource-detail',
      resourceId: toNumber(route.params.id),
    }
  }

  // 学习路径节点页：记录 pathNodeId
  if (name === 'PathNodeStudy') {
    return {
      sourcePage: 'learning-path-node',
      pathNodeId: toNumber(route.params.nodeId),
    }
  }

  return {
    sourcePage: route.path.replace(/^\/+/, '').replace(/\//g, '-') || 'dashboard',
  }
}

// 同步学习追踪状态：有 Token 时启动追踪，否则停止
function syncTracking(route: Router['currentRoute']['value']) {
  if (!hasAuthToken()) {
    stopTracking()
    return
  }

  const context = getContextFromRoute(route)
  startTracking(context)
}

// 学习追踪 Vue 插件：初始化时和路由切换后自动同步追踪上下文
export const learningTrackerPlugin = {
  install(_app: App, options: { router: Router }) {
    const router = options.router

    // 初始化时同步追踪
    syncTracking(router.currentRoute.value)

    // 每次路由切换后重新同步
    router.afterEach((to) => {
      syncTracking(to)
    })
  },
}
