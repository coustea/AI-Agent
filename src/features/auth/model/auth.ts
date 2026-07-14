// 登录请求参数
export interface LoginParams { // 登录请求参数
  username: string // 用户名
  password: string // 密码
}

// 注册请求参数（邮箱选填）
export interface RegisterParams { // 注册请求参数
  username: string // 用户名
  password: string // 密码
  email?: string // 邮箱（可选）
}

// 登录成功返回的数据：token + 用户基础信息
export interface LoginData { // 登录响应数据
  token: string // JWT Token
  user: { // 用户信息
    id: number // 用户 ID
    username: string // 用户名
    email: string | null // 邮箱
    avatar: string | null // 头像 URL
    created_at: string // 创建时间
    onboarding_completed?: boolean // onboarding 是否已完成（false=未完成需弹窗，true=已完成）
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
export interface UserData { // 注册响应数据
  user: { // 用户信息
    id: number // 用户 ID
    username: string // 用户名
    email: string | null // 邮箱
    avatar: string | null // 头像 URL
    created_at: string // 创建时间
    onboarding_completed?: boolean // onboarding 是否已完成（false=未完成需弹窗，true=已完成）
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
export interface UserUpdateParams { // 用户信息更新参数
  username?: string // 用户名
  email?: string // 邮箱
  avatar?: string // 头像 URL
  onboarding_completed?: boolean // onboarding 是否已完成（false=未完成需弹窗，true=已完成）
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
export interface AvatarUploadData { // 头像上传响应数据
  avatar: string // 新头像 URL
}
