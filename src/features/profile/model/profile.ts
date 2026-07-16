export interface BaseInfoData {
  school: string | null
  school_level: string | null
  major: string | null
  grade: string | null
  daily_study_time: string | null
  global_learning_goal: string | null
  programming_languages: string[]
  courses: string[]
  foundational_level: string | null
  learning_style: string | null
  content_depth: string | null
  weak_points: string[]
}

export interface DimensionValue {
  value: string
  evidence: string[]
}

/**
 * 7 维度画像键
 * - 赛题要求: knowledge_level, cognitive_style, weak_knowledge_points
 * - 新增维度: knowledge_gap_pattern, learning_goal_type, difficulty_tolerance, self_correction_ability
 */
export type ProfileDimensionKey =
  | 'knowledge_level'
  | 'cognitive_style'
  | 'weak_knowledge_points'
  | 'knowledge_gap_pattern'
  | 'learning_goal_type'
  | 'difficulty_tolerance'
  | 'self_correction_ability'

export interface ProfileData {
  user_id: number | null
  module: string | null
  base_info: BaseInfoData
  dimensions: Record<ProfileDimensionKey, DimensionValue>
  profile_score_json: {
    overall_score: number
    dimension_scores: Record<ProfileDimensionKey, number>
    scored_at: string | null
  } | null
  updated_at: string | null
}

export type GlobalDimensionValue = DimensionValue

export interface ProfileOnboardingData {
  base_info: BaseInfoData
  student_profile: StudentProfileData
  profile_initialized: boolean
}

export interface StudentProfileData {
  school: string | null
  school_level: string | null
  major: string | null
  grade: string | null
  courses: string[]
  learning_goal: string | null
  preferred_language: string | null
}

export interface ProfileOnboardingUpdate {
  school: string
  major: string
  grade: string
  daily_study_time: string
  global_learning_goal: string
  programming_languages: string[]
  courses: string[]
  foundational_level: 'beginner' | 'entry' | 'proficient' | 'master' | ''
  learning_style: 'theory_first' | 'practice_first' | 'case_driven' | ''
  content_depth: 'quick_overview' | 'systematic_deep' | ''
  weak_points: string[]
}

export interface ProfileOnboardingUpdateResult {
  inference_ok: boolean
}

export function isProfileOnboardingComplete(baseInfo: BaseInfoData | null | undefined): boolean {
  if (!baseInfo) return false

  return Boolean(
    baseInfo.school &&
    baseInfo.major &&
    baseInfo.grade &&
    baseInfo.daily_study_time &&
    baseInfo.global_learning_goal &&
    Array.isArray(baseInfo.courses) &&
    baseInfo.courses.length > 0 &&
    baseInfo.foundational_level &&
    baseInfo.learning_style &&
    baseInfo.content_depth,
  )
}