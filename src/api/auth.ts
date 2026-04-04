import http from '@/utils/http'

export interface LoginParams {
  username: string
  password: string
}

export interface RegisterParams {
  username: string
  password: string
  email?: string
}

export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

export interface LoginData {
  token: string
  user: {
    id: string
    username: string
    email: string | null
    avatar: string | null
    major: string | null
    grade: string | null
    school: string | null
    created_at: string
  }
}

export interface UserData {
  user: {
    id: string
    username: string
    email: string | null
    avatar: string | null
    major: string | null
    grade: string | null
    school: string | null
    created_at: string
  }
}

export function login(params: LoginParams) {
  return http.post<ApiResponse<LoginData>>('/users/auth', params)
}

export function register(params: RegisterParams) {
  return http.post<ApiResponse<UserData>>('/users', params)
}

export function logout() {
  return http.delete<ApiResponse>('/users/auth')
}

export function getMe() {
  return http.get<ApiResponse<LoginData['user']>>('/users/me')
}
