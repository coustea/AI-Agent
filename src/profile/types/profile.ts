export interface CourseBaseInfo {
  course: string
  foundation_level: string
  current_topic?: string | null
  course_learning_goal?: string | null
  weak_points?: string[]
}

export interface BaseInfoData {
  school: string | null
  school_level: string | null
  major: string | null
  grade: string | null
  daily_study_time: string | null
  global_learning_goal: string | null
  resource_preference: string[]
  programming_languages: string[]
  learning_style_tags: string[]
  self_description?: string | null
  courses: CourseBaseInfo[]
}

export interface ProfileData {
  user_id: number | null
  module: string | null
  base_info: BaseInfoData
  learning_profile: Record<string, unknown>
  knowledge_mastery: Array<Record<string, unknown>>
  initial_strategy: Record<string, unknown>
  profile_meta: Record<string, unknown>
  profile_markdown: string | null
  profile_json: Record<string, unknown> | null
  profile_score_json: Record<string, unknown> | null
  version: number | null
  confidence: number | null
  updated_reason: string | null
  updated_at: string | null
}

export interface ProfileOnboardingData {
  base_info: BaseInfoData
  student_profile: StudentProfileData
  profile_initialized: boolean
}

export interface StudentProfileData {
  education_level: string | null
  grade: string | null
  major: string | null
  courses: string[]
  learning_goal: string | null
  school: string | null
  school_level: string | null
  preferred_language: string | null
  weakness_points?: string[]
}

export interface ProfileOnboardingUpdate {
  school: string | null
  school_level?: string | null
  major: string
  grade: string
  daily_study_time: string | null
  global_learning_goal: string | null
  courses: CourseBaseInfo[]
  resource_preference: string[]
  programming_languages: string[]
  learning_style_tags: string[]
  self_description: string | null
}

export interface ProfileOnboardingUpdateResult {
  profile: ProfileData
  onboarding: ProfileOnboardingData
}

export interface TutoringEvidence {
  source?: string
  signal_type: string
  summary: string
  course?: string | null
  knowledge_point?: string | null
  confidence?: number
}

export interface TutoringProfileUpdatePayload {
  session_id?: string | null
  active_course?: string | null
  active_topic?: string | null
  dialogue_excerpt?: string | null
  evidence?: TutoringEvidence[]
  behavior_signals?: Record<string, unknown>
  update_reason?: string
}

export interface TutoringProfileUpdateResult {
  profile_updated: boolean
  learning_profile: Record<string, unknown>
  knowledge_mastery: Array<Record<string, unknown>>
  profile_meta: Record<string, unknown>
  version?: number
  updated_at?: string | null
}

export interface ProfileScoreData {
  user_id: number | null
  module: string | null
  version: number | null
  score: number | null
  confidence: number | null
  metrics: {
    dimension_scores?: Record<string, number | null>
    section_coverage?: number | null
    evidence_quality?: number | null
    uncertainty_handling?: number | null
    content_richness?: number | null
  }
  missing_sections: string[]
  scored_at: string | null
  updated_at: string | null
}

export interface ProfileHistoryItem {
  id: number
  user_id: number
  module: string
  version: number
  profile_json: Record<string, unknown> | null
  profile_score_json: Record<string, unknown> | null
  change_reason: string | null
  source_session_ids: string[] | null
  created_at: string | null
}
