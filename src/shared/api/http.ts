import axios from 'axios' // 导入 axios HTTP 客户端
import { clearCurrentUser } from '@/features/auth/model/currentUser' // 导入清除用户缓存函数
import { clearAuthToken, emitAuthExpired, getAuthToken } from '@/shared/auth/token' // 导入 Token 管理函数

// HTTP 客户端模块：封装 axios 实例，处理请求认证与响应错误

/** 后端统一响应信封 */
export interface ApiResponse<T = unknown> {
  code: number // 业务状态码（200 表示成功）
  message: string // 响应消息
  data: T // 响应数据
}

/** 从错误中提取可读消息，统一处理 HttpResponse.error 和 HTTPException 两种格式 */
export function getErrorMessage(error: unknown, fallback = '请求失败，请稍后重试'): string {
  const err = error as { response?: { data?: { message?: string; detail?: string | unknown[] } }; message?: string }
  const data = err?.response?.data
  if (!data) return err?.message || fallback // 无响应体时取 axios 错误消息

  // HttpResponse.error 格式: { code, message, data }
  if (typeof data.message === 'string' && data.message) {
    return data.message
  }

  // HTTPException 格式: { detail: string | array }
  if (typeof data.detail === 'string' && data.detail) {
    return data.detail
  }

  if (Array.isArray(data.detail) && data.detail.length > 0) { // Pydantic 校验错误数组格式
    return (data.detail as any[])
      .map((item) => {
        const field = Array.isArray(item?.loc) ? item.loc.slice(1).join('.') : '' // 提取字段路径（去掉 body 前缀）
        const message = item?.msg || String(item)
        return field ? `${field}: ${message}` : message
      })
      .join('；')
  }

  return fallback
}

const http = axios.create({ // 创建 axios 实例
  baseURL: '/api/v1', // API 基础路径（由 Vite 代理到后端）
  timeout: 10000, // 请求超时 10 秒
})

// 请求拦截器：自动附加 token
http.interceptors.request.use((config) => {
  const token = getAuthToken() // 获取当前 Token
  if (token) {
    config.headers.Authorization = `Bearer ${token}` // 附加 Bearer 认证头
  }
  return config
})

// 响应拦截器：统一处理错误
http.interceptors.response.use(
  (response) => {
    const body = response.data as ApiResponse
    // 业务错误码非 200 时，统一 reject，调用方只需 catch 即可
    if (body && typeof body.code === 'number' && body.code !== 200) {
      return Promise.reject({
        response: {
          data: { message: body.message, code: body.code, data: body.data },
          status: body.code,
        },
      })
    }
    return response
  },
  (error) => {
    const status = error.response?.status // HTTP 状态码
    const url = error.config?.url || '' // 请求 URL
    // 登录/注册接口的 401/400 不跳转，只由页面 catch 处理
    const isAuthRequest = url.includes('/users/auth') || url === '/users'
    if (status === 401 && !isAuthRequest) { // 非认证接口收到 401 → Token 失效
      clearCurrentUser() // 清除用户缓存
      clearAuthToken() // 清除本地 Token
      // 不再硬跳转，由 useAuthPolling 轮询或 router.beforeEach 统一处理
      // 派发自定义事件通知 token 失效
      emitAuthExpired()
    }
    return Promise.reject(error)
  },
)

export default http // 导出配置好的 axios 实例
