import http from '@/shared/api/http'
import type { ApiResponse } from '@/shared/api/http'
import type {
  LoginParams,
  RegisterParams,
  LoginData,
  UserData,
  UserUpdateParams,
  AvatarUploadData,
} from '@/features/auth/model/auth'

export type {
  LoginParams,
  RegisterParams,
  LoginData,
  UserData,
  UserUpdateParams,
  AvatarUploadData,
}

export function login(params: LoginParams) {
  return http.post<ApiResponse<LoginData>>('/users/auth', params)
}

export function register(params: RegisterParams) {
  return http.post<ApiResponse<UserData>>('/users', params)
}

export function logout() {
  return http.post<ApiResponse>('/users/auth/logout')
}

export function getAuthStatus() {
  return http.get<ApiResponse>('/users/auth/status')
}

export function getMe() {
  return http.get<ApiResponse<LoginData['user']>>('/users/me')
}

export function updateMe(params: UserUpdateParams) {
  return http.patch<ApiResponse<LoginData['user']>>('/users/me', params)
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
