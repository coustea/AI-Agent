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
  }
}

export interface UserUpdateParams {
  username?: string
  email?: string
  avatar?: string
  is_first_login?: boolean
}

export interface AvatarUploadData {
  avatar: string
}
