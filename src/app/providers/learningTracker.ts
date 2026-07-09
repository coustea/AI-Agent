import type { App } from 'vue'
import type { Router } from 'vue-router'
import { hasAuthToken } from '@/shared/auth/token'
import { startTracking, stopTracking } from '@/features/evaluation/model/useLearningTracker'
import type { TrackingContext } from '@/features/evaluation/model/useLearningTracker'

function toNumber(value: unknown): number | undefined {
  if (value === null || value === undefined || value === '') return undefined
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : undefined
}

function getContextFromRoute(route: Router['currentRoute']['value']): TrackingContext {
  const name = String(route.name || '')

  if (name === 'ResourceResult') {
    return {
      sourcePage: 'resource-detail',
      resourceId: toNumber(route.params.id),
    }
  }

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

function syncTracking(route: Router['currentRoute']['value']) {
  if (!hasAuthToken()) {
    stopTracking()
    return
  }

  const context = getContextFromRoute(route)
  startTracking(context)
}

export const learningTrackerPlugin = {
  install(_app: App, options: { router: Router }) {
    const router = options.router

    syncTracking(router.currentRoute.value)

    router.afterEach((to) => {
      syncTracking(to)
    })
  },
}
