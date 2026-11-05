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
    onboarding_completed?: boolean
    school?: string | null
    school_level?: string | null
    major?: string | null
    grade?: string | null
    daily_study_time?: string | null
    global_learning_goal?: string | null
    programming_languages?: string[] | null
    courses?: string[] | null
    foundational_level?: string | null
    learning_style?: string | null
    content_depth?: string | null
    weak_points?: string[] | null
  }
}

export interface UserData {
  user: {
    id: number
    username: string
    email: string | null
    avatar: string | null
    created_at: string
    onboarding_completed?: boolean
    school?: string | null
    school_level?: string | null
    major?: string | null
    grade?: string | null
    daily_study_time?: string | null
    global_learning_goal?: string | null
    programming_languages?: string[] | null
    courses?: string[] | null
    foundational_level?: string | null
    learning_style?: string | null
    content_depth?: string | null
    weak_points?: string[] | null
  }
}

export interface AvatarUploadData {
  avatar: string
}
