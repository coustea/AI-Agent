export interface ApiEnvelope<T> {
  code: number;
  message: string;
  data?: T;
}

export interface User {
  id: string;
  username: string;
  email: string;
}

export interface LoginResp {
  token: string;
  user: User;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface AttachmentBrief {
  id: string;
  filename: string;
  kind: string;
  mime: string;
  size: number;
  download_url: string;
}

export interface Attachment extends AttachmentBrief {
  text_length?: number;
  extract_error?: string;
}

export interface Message {
  id: number;
  role: "user" | "assistant" | string;
  content: string;
  status: "completed" | "failed" | "cancelled" | "streaming" | string;
  tokens?: number;
  attachment_ids?: string[];
  attachments?: AttachmentBrief[];
  created_at: string;
}

export interface WorkspaceFile {
  name: string;
  path: string;
  size: number;
  modified_at: string;
  download_url: string;
}

export interface PreviewableFile {
  name: string;
  path?: string;
  size: number;
  download_url: string;
}

export interface MessageEventData {
  text: string;
  reset?: boolean;
}

export interface ToolEventData {
  name: string;
  call_id?: string;
  args?: string;
  result?: string;
  elapsed_ms?: number;
}

export interface ErrorEventData {
  message: string;
  retryable?: boolean;
}

export interface DoneEventData {
  message_id: number;
  status: string;
  elapsed_ms: number;
  tool_calls?: string[];
}

export interface ToolStep {
  callId: string;
  name: string;
  args?: string;
  result?: string;
  elapsedMs?: number;
  status: "running" | "done";
}

export interface ChatMessageItem extends Message {
  clientId: string;
  toolSteps?: ToolStep[];
  errorMessage?: string;
  retryable?: boolean;
  elapsedMs?: number;
}
