import type {
  ApiEnvelope,
  Attachment,
  Conversation,
  LoginResp,
  Message,
  User,
  WorkspaceFile,
} from "@/types/api";

const TOKEN_STORAGE_KEY = "mentorly_auth_token";

export class ApiError extends Error {
  status: number;
  code: number;

  constructor(status: number, code: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

let onUnauthorizedCallback: (() => void) | null = null;

export function setUnauthorizedHandler(fn: (() => void) | null): void {
  onUnauthorizedCallback = fn;
}

export function getAuthToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch {
    // 浏览器禁用本地存储时仅维持内存会话
  }
}

export function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...extra };
  const token = getAuthToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

export async function parseErrorResponse(res: Response): Promise<ApiError> {
  let code = res.status * 100;
  let message = res.statusText || "请求失败";
  try {
    const body = (await res.json()) as Partial<ApiEnvelope<unknown>>;
    if (typeof body.code === "number") code = body.code;
    if (typeof body.message === "string" && body.message.trim()) {
      message = body.message;
    }
  } catch {
    // 非 JSON 错误体保留 HTTP 状态文本
  }
  return new ApiError(res.status, code, message);
}

async function requestJson<T>(
  url: string,
  init: RequestInit = {},
  options: { auth?: boolean; notifyUnauthorized?: boolean } = {},
): Promise<T> {
  const { auth = true, notifyUnauthorized = true } = options;
  const headers = new Headers(init.headers);
  if (auth) {
    const token = getAuthToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(url, { ...init, headers });
  if (res.status === 401 && notifyUnauthorized) {
    onUnauthorizedCallback?.();
  }
  if (!res.ok) {
    throw await parseErrorResponse(res);
  }

  const env = (await res.json()) as ApiEnvelope<T>;
  if (env.code !== 0) {
    throw new ApiError(res.status, env.code, env.message || "业务处理失败");
  }
  return env.data as T;
}

export const api = {
  register(payload: { username: string; email: string; password: string }) {
    return requestJson<LoginResp>(
      "/api/v1/auth/register",
      { method: "POST", body: JSON.stringify(payload) },
      { auth: false, notifyUnauthorized: false },
    );
  },

  login(payload: { email: string; password: string }) {
    return requestJson<LoginResp>(
      "/api/v1/auth/login",
      { method: "POST", body: JSON.stringify(payload) },
      { auth: false, notifyUnauthorized: false },
    );
  },

  profile(signal?: AbortSignal) {
    return requestJson<User>("/api/v1/profile", { signal });
  },

  listConversations(limit = 50) {
    return requestJson<Conversation[]>(`/api/v1/conversations?limit=${limit}`);
  },

  createConversation(title = "") {
    return requestJson<Conversation>("/api/v1/conversations", {
      method: "POST",
      body: title ? JSON.stringify({ title }) : undefined,
    });
  },

  renameConversation(id: string, title: string) {
    return requestJson<{ ok: boolean }>(`/api/v1/conversations/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    });
  },

  deleteConversation(id: string) {
    return requestJson<{ ok: boolean }>(`/api/v1/conversations/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
  },

  listMessages(conversationId: string, signal?: AbortSignal) {
    return requestJson<Message[]>(
      `/api/v1/conversations/${encodeURIComponent(conversationId)}/messages`,
      { signal },
    );
  },

  uploadAttachment(conversationId: string, file: File) {
    const form = new FormData();
    form.append("conversation_id", conversationId);
    form.append("file", file);
    return requestJson<Attachment>("/api/v1/attachments", {
      method: "POST",
      body: form,
    });
  },

  listWorkspaceFiles(conversationId: string, signal?: AbortSignal) {
    return requestJson<WorkspaceFile[]>(
      `/api/v1/workspaces/${encodeURIComponent(conversationId)}/files`,
      { signal },
    );
  },
};
