const AUTH_TOKEN_KEY = 'token' // localStorage 中 Token 的存储键名

export const AUTH_EXPIRED_EVENT = 'auth:expired' // Token 过期自定义事件名

// Token 管理模块：localStorage 的认证令牌读写与过期事件通知

export function getAuthToken(): string | null { // 从 localStorage 读取认证 Token
  return localStorage.getItem(AUTH_TOKEN_KEY)
}

export function setAuthToken(token: string): void { // 将认证 Token 写入 localStorage
  localStorage.setItem(AUTH_TOKEN_KEY, token)
}

export function clearAuthToken(): void { // 从 localStorage 移除认证 Token
  localStorage.removeItem(AUTH_TOKEN_KEY)
}

export function hasAuthToken(): boolean { // 检查是否存在有效的认证 Token
  return Boolean(getAuthToken())
}

export function emitAuthExpired(): void { // 派发 Token 过期事件，通知全局监听器
  window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT))
}
