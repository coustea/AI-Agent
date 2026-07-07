export interface LoginParams {
  username: string
  password: string
}

export interface RegisterParams {
  username: string
  password: string
  email?: string
}

export interface LoginData {
  token: string
  user: {
    id: number
    username: string
    email: string | null
    avatar: string | null
    created_at: string
    is_first_login?: boolean
    // 基础信息（原 profile base_info，onboarding 填写）
    school?: string | null
    school_level?: string | null
    major?: string | null
    grade?: string | null
    daily_study_time?: string | null
    global_learning_goal?: string | null
    programming_languages?: string[] | null
    courses?: string[] | null
  }
}

export interface UserData {
  user: {
    id: number
    username: string
    email: string | null
    avatar: string | null
    created_at: string
    is_first_login?: boolean
    school?: string | null
    school_level?: string | null
    major?: string | null
    grade?: string | null
    daily_study_time?: string | null
    global_learning_goal?: string | null
    programming_languages?: string[] | null
    courses?: string[] | null
  }
}

export interface UserUpdateParams {
  username?: string
  email?: string
  avatar?: string
  is_first_login?: boolean
  school?: string | null
  school_level?: string | null
  major?: string | null
  grade?: string | null
  daily_study_time?: string | null
  global_learning_goal?: string | null
  programming_languages?: string[] | null
  courses?: string[] | null
}

export interface AvatarUploadData {
  avatar: string
}
