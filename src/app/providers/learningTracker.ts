import type { App } from 'vue'
import type { Router } from 'vue-router'
import { startTracking, stopTracking } from '@/features/learning/model/useLearningTracker'
import type { TrackingContext } from '@/features/learning/model/useLearningTracker'

const LEARNING_ROUTE_NAMES = new Set([
  'ResourceDetail',
  'PathResourceDetail',
  'Tutor',
  'LearningPathNode',
  'QuestionBank',
])

function getContextFromRoute(route: Router['currentRoute']['value']): TrackingContext | null {
  const name = route.name as string

  if (name === 'ResourceDetail') {
    return {
      sourcePage: 'resource',
      resourceId: route.params.id ? Number(route.params.id) : undefined,
    }
  }

  if (name === 'PathResourceDetail') {
    return {
      sourcePage: 'path_resource',
      resourceId: route.params.id ? Number(route.params.id) : undefined,
      pathId: route.query.pathId ? Number(route.query.pathId) : undefined,
      pathNodeId: route.query.pathNodeId ? Number(route.query.pathNodeId) : undefined,
      nodeId: route.query.nodeId ? String(route.query.nodeId) : undefined,
    }
  }

  if (name === 'Tutor') {
    return { sourcePage: 'tutor' }
  }

  if (name === 'LearningPathNode') {
    return {
      sourcePage: 'path_node',
      pathNodeId: route.params.nodeId ? Number(route.params.nodeId) : undefined,
    }
  }

  if (name === 'QuestionBank') {
    return { sourcePage: 'question-bank' }
  }

  return null
}

export const learningTrackerPlugin = {
  install(_app: App, options: { router: Router }) {
    const router = options.router

    router.afterEach((to) => {
      stopTracking()

      const name = to.name as string
      if (!LEARNING_ROUTE_NAMES.has(name)) return

      const context = getContextFromRoute(to)
      if (context) {
        startTracking(context)
      }
    })
  },
}
