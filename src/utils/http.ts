import axios from 'axios'

/** 后端统一响应信封 */
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

/** 从错误中提取可读消息，统一处理 HttpResponse.error 和 HTTPException 两种格式 */
export function getErrorMessage(error: unknown, fallback = '请求失败，请稍后重试'): string {
  const err = error as { response?: { data?: { message?: string; detail?: string | unknown[] } }; message?: string }
  const data = err?.response?.data
  if (!data) return err?.message || fallback

  // HttpResponse.error 格式: { code, message, data }
  if (typeof data.message === 'string' && data.message) {
    return data.message
  }

  // HTTPException 格式: { detail: string | array }
  if (typeof data.detail === 'string' && data.detail) {
    return data.detail
  }

  if (Array.isArray(data.detail) && data.detail.length > 0) {
    return (data.detail as any[])
      .map((item) => {
        const field = Array.isArray(item?.loc) ? item.loc.slice(1).join('.') : ''
        const message = item?.msg || String(item)
        return field ? `${field}: ${message}` : message
      })
      .join('；')
  }

  return fallback
}

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
})

// 请求拦截器：自动附加 token
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
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
          data: { message: body.message, code: body.code },
          status: body.code,
        },
      })
    }
    return response
  },
  (error) => {
    const status = error.response?.status
    const url = error.config?.url || ''
    // 登录/注册接口的 401/400 不跳转，只由页面 catch 处理
    const isAuthRequest = url.includes('/users/auth') || url === '/users'
    if (status === 401 && !isAuthRequest) {
      localStorage.removeItem('token')
      // 不再硬跳转，由 useAuthPolling 轮询或 router.beforeEach 统一处理
      // 派发自定义事件通知 token 失效
      window.dispatchEvent(new CustomEvent('auth:expired'))
    }
    return Promise.reject(error)
  },
)

export default http
