import type { ProfileData } from '@/profile/api/profile'

interface DisplayItem {
  label: string
  value: string
}

interface CourseProfileCard {
  name: string
  level: string
  goal: string
  weakPoints: string[]
}

type KnowledgeMasteryItem = Record<string, any>

function getLearningProfile(profile: ProfileData | null) {
  return (profile?.learning_profile as any) || {}
}

export function getGlobalProfileCards(profile: ProfileData | null): DisplayItem[] {
  const globalProfile = getLearningProfile(profile).global_profile || {}

  return [
    { label: '专业背景', value: globalProfile.major_background?.value || '暂无' },
    { label: '学习阶段', value: globalProfile.student_stage?.value || '暂无' },
    { label: '学习节奏', value: globalProfile.learning_pace?.value || '暂无' },
    { label: '认知风格', value: globalProfile.cognitive_style?.value || '暂无' },
  ]
}

export function getCourseProfileCards(profile: ProfileData | null): CourseProfileCard[] {
  const courses = (getLearningProfile(profile).course_profiles || []) as any[]

  return courses.map((course) => ({
    name: course.course_context?.value?.course || '未命名课程',
    level: course.knowledge_level?.value || '暂无',
    goal: ((course.learning_goal_type?.value || []) as string[]).join(' / ') || '暂无目标',
    weakPoints: (course.weak_knowledge_points?.value || []).map((item: any) => item.name || item),
  }))
}

export function getStrategyList(profile: ProfileData | null): string[] {
  const strategy = profile?.initial_strategy || {}

  return [
    strategy.strategy_summary,
    strategy.path_planning_strategy,
    strategy.tutor_strategy,
  ].filter(Boolean) as string[]
}

function getMasteryItems(profile: ProfileData | null): KnowledgeMasteryItem[] {
  return (profile?.knowledge_mastery || []) as KnowledgeMasteryItem[]
}

export function getMasteryTop(profile: ProfileData | null, limit = 4): KnowledgeMasteryItem[] {
  return [...getMasteryItems(profile)]
    .sort((a, b) => (a.mastery_score || 0) - (b.mastery_score || 0))
    .slice(0, limit)
}
