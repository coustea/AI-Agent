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
function getContextFromRoute(route: Router['currentRoute']['value']): TrackingContext | null {
  const name = String(route.name || '')

  if (name === 'ResourceResult' || name === 'ResourceItemDetail') {
    return {
      sourcePage: 'resource',
      resourceId: toNumber(route.params.id),
    }
  }

  // 资源生成页面也属于学习行为
  if (name === 'ResourceGenerator') {
    return { sourcePage: 'resource' }
  }

  if (name === 'LearningPathNode') {
    return {
      sourcePage: 'path',
      pathNodeId: toNumber(route.params.nodeId),
    }
  }

  // 路径规划相关页面
  if (name === 'LearningPathEntry' || name === 'LearningPathOverview' || name === 'LearningPathHistory') {
    return { sourcePage: 'path' }
  }

  if (name === 'Tutor') {
    return { sourcePage: 'chat' }
  }

  if (name === 'QuestionBank') {
    return { sourcePage: 'quiz' }
  }

  if (name === 'AlgorithmVisualizer') {
    return { sourcePage: 'visualizer' }
  }

  // 学习评估页面
  if (name === 'LearningAssessment') {
    return { sourcePage: 'assessment' }
  }

  return null
}

// 同步学习追踪状态：有 Token 时启动追踪，否则停止
function syncTracking(route: Router['currentRoute']['value']) {
  if (!hasAuthToken()) {
    stopTracking()
    return
  }

  const context = getContextFromRoute(route)
  if (!context) {
    stopTracking()
    return
  }
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
