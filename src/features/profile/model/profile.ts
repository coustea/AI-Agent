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

export interface GlobalDimensionValue {
  value: string
  evidence: string[]
}

export interface ProfileJsonData {
  base_info: BaseInfoData
  dimensions: Record<string, GlobalDimensionValue>
}

export interface ProfileData {
  user_id: number | null
  module: string | null
  base_info: BaseInfoData
  dimensions: Record<string, GlobalDimensionValue>
  profile_json: ProfileJsonData | null
  profile_score_json: Record<string, unknown> | null
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



export interface ProfileScoreDimension {
  key: string
  label: string
  score: number | null
  evidence: string[]
}

export interface ProfileScoreData {
  user_id: number | null
  module: string | null
  score: number | null
  metrics: {
    dimension_scores?: Record<string, number>
    dimension_evidence?: Record<string, string[]>
  }
  dimensions?: ProfileScoreDimension[]
  scored_at: string | null
  updated_at: string | null
}
