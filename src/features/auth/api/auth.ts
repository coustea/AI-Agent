import http from '@/shared/api/http' // 导入配置好的 axios 实例
import type { ApiResponse } from '@/shared/api/http' // 导入响应信封类型
import type {
  LoginParams,
  RegisterParams,
  LoginData,
  UserData,
  UserUpdateParams,
  AvatarUploadData,
} from '@/features/auth/model/auth' // 导入认证相关 DTO 类型

export type { // 重导出 DTO 类型供外部使用
  LoginParams,
  RegisterParams,
  LoginData,
  UserData,
  UserUpdateParams,
  AvatarUploadData,
}

// 登录：向后端换取 JWT 令牌与用户信息
export function login(params: LoginParams) { // 用户登录
  return http.post<ApiResponse<LoginData>>('/users/auth', params)
}

// 注册：创建新用户账户
export function register(params: RegisterParams) { // 用户注册
  return http.post<ApiResponse<UserData>>('/users', params)
}

// 登出：使后端会话失效
export function logout() { // 退出登录
  return http.post<ApiResponse>('/users/auth/logout')
}

// 查询当前登录态（用于轮询鉴权）
export function getAuthStatus() { // 检查认证状态（轮询用）
  return http.get<ApiResponse>('/users/auth/status')
}

// 获取当前登录用户的基础信息
export function getMe() { // 获取当前登录用户信息
  return http.get<ApiResponse<LoginData['user']>>('/users/me')
}

// 更新当前用户资料（如用户名、邮箱、是否首次登录等）
export function updateMe(params: UserUpdateParams) { // 更新当前用户信息
  return http.patch<ApiResponse<LoginData['user']>>('/users/me', params)
}

// 上传头像：multipart/form-data 包装文件后提交
export function uploadAvatar(file: File) { // 上传用户头像
  const formData = new FormData()
  formData.append('file', file) // 将文件添加到 FormData
  return http.post<ApiResponse<AvatarUploadData>>('/users/me/avatar', formData, {
    headers: {
      'Content-Type': 'multipart/form-data' // 文件上传使用 multipart 编码
    }
  })
}
