import http from '@/utils/http'
import type { ApiResponse } from '@/utils/http'

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

export interface AvatarUploadData {
  avatar: string
}

export function uploadAvatar(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return http.post<ApiResponse<AvatarUploadData>>('/users/me/avatar', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}
