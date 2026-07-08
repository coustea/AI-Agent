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

// 登录：向后端换取 JWT 令牌与用户信息
export function login(params: LoginParams) {
  return http.post<ApiResponse<LoginData>>('/users/auth', params)
}

// 注册：创建新用户账户
export function register(params: RegisterParams) {
  return http.post<ApiResponse<UserData>>('/users', params)
}

// 登出：使后端会话失效
export function logout() {
  return http.post<ApiResponse>('/users/auth/logout')
}

// 查询当前登录态（用于轮询鉴权）
export function getAuthStatus() {
  return http.get<ApiResponse>('/users/auth/status')
}

// 获取当前登录用户的基础信息
export function getMe() {
  return http.get<ApiResponse<LoginData['user']>>('/users/me')
}

// 更新当前用户资料（如用户名、邮箱、是否首次登录等）
export function updateMe(params: UserUpdateParams) {
  return http.patch<ApiResponse<LoginData['user']>>('/users/me', params)
}

// 上传头像：multipart/form-data 包装文件后提交
export function uploadAvatar(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return http.post<ApiResponse<AvatarUploadData>>('/users/me/avatar', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}
