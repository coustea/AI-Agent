export interface BaseInfoData {
  school: string | null
  school_level: string | null
  major: string | null
  grade: string | null
  daily_study_time: string | null
  global_learning_goal: string | null
  programming_languages: string[]
  courses: string[]
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
  updated_reason: string | null
  updated_at: string | null
}

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
}

export interface ProfileOnboardingUpdateResult {
  profile: ProfileData
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

export interface ProfileScoreDimension {
  key: string
  label: string
  score: number
}

export interface ProfileScoreData {
  user_id: number | null
  module: string | null
  score: number | null
  metrics: {
    dimension_scores?: Record<string, number>
  }
  dimensions?: ProfileScoreDimension[]
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
