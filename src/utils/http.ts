import axios from 'axios'

export function getErrorMessage(error: any, fallback = '请求失败，请稍后重试') {
  const data = error?.response?.data
  if (!data) return error?.message || fallback

  if (typeof data.message === 'string' && data.message) {
    return data.message
  }

  if (typeof data.detail === 'string' && data.detail) {
    return data.detail
  }

  if (Array.isArray(data.detail) && data.detail.length > 0) {
    return data.detail
      .map((item: any) => {
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
  (response) => response,
  (error) => {
    const status = error.response?.status
    const url = error.config?.url || ''
    // 登录/注册接口的 401/400 不跳转，只由页面 catch 处理
    const isAuthRequest = url.includes('/users/auth') || url === '/users'
    if (status === 401 && !isAuthRequest) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export default http
