// 登录请求参数
export interface LoginParams {
  username: string
  password: string
}

// 注册请求参数（邮箱选填）
export interface RegisterParams {
  username: string
  password: string
  email?: string
}

// 登录成功返回的数据：token + 用户基础信息
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

// 注册成功返回的数据：仅包含用户基础信息
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

// 更新用户资料的请求参数（全部字段均可选）
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

// 头像上传成功后返回的头像地址
export interface AvatarUploadData {
  avatar: string
}
