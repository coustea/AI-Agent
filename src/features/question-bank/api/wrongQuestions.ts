import http from '@/shared/api/http'

const QUESTION_TYPE_LABELS: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  judge: '判断题',
  fill_blank: '填空题',
  short_answer: '简答题',
  analysis: '分析题',
  comprehensive: '综合题',
  programming: '编程题',
}

export interface WrongQuestion {
  id: number
  question_id: string
  subject: string
  question_type: string
  content: string
  options: Record<string, string> | null
  standard_answer: string | null
  analysis: string | null
  user_answer: string | null
  wrong_count: number
  note: string | null
  is_archived: boolean
  created_at: string
  updated_at: string
}

export interface WrongQuestionListResponse {
  items: WrongQuestion[]
  total: number
  page: number
  page_size: number
  subjects: string[]
  types: string[]
}

export async function fetchWrongQuestions(params?: {
  subject?: string
  question_type?: string
  is_archived?: boolean
  page?: number
  page_size?: number
}): Promise<WrongQuestionListResponse> {
  const requestParams = {
    subject: params?.subject,
    type: params?.question_type,
    archived: params?.is_archived,
    page: params?.page,
    page_size: params?.page_size,
  }
  const response = await http.get('/ai/wrong', { params: requestParams })
  const payload = response.data as Partial<WrongQuestionListResponse> & { items?: any[] }
  return {
    items: (payload.items || []).map(normalizeWrongQuestion),
    total: payload.total || 0,
    page: payload.page || requestParams.page || 1,
    page_size: payload.page_size || requestParams.page_size || 20,
    subjects: payload.subjects || [],
    types: (payload.types || []).map(toQuestionTypeLabel),
  }
}


export async function removeWrongQuestion(wrongId: number): Promise<void> {
  await http.delete(`/ai/wrong/${wrongId}`)
}

export async function archiveWrongQuestion(wrongId: number): Promise<void> {
  await http.post(`/ai/wrong/${wrongId}/archive`)
}


export async function fetchRandomWrongQuestion(subject?: string): Promise<WrongQuestion | null> {
  const response = await http.get('/ai/wrong/random', {
    params: subject ? { subject } : undefined,
  })
  return response.data.data ? normalizeWrongQuestion(response.data.data) : null
}

function normalizeWrongQuestion(item: Record<string, any>): WrongQuestion {
  return {
    id: Number(item.id || 0),
    question_id: String(item.question_id || ''),
    subject: String(item.subject || ''),
    question_type: toQuestionTypeLabel(item.question_type),
    content: String(item.content || ''),
    options: normalizeOptions(item.options),
    standard_answer: item.standard_answer != null ? String(item.standard_answer) : null,
    analysis: item.analysis != null ? String(item.analysis) : null,
    user_answer: item.user_answer != null ? String(item.user_answer) : null,
    wrong_count: Number(item.wrong_count || 0),
    note: item.note != null ? String(item.note) : null,
    is_archived: Boolean(item.is_archived),
    created_at: String(item.created_at || ''),
    updated_at: String(item.updated_at || ''),
  }
}

function normalizeOptions(options: unknown): Record<string, string> | null {
  if (!options || typeof options !== 'object' || Array.isArray(options)) return null
  return Object.fromEntries(
    Object.entries(options as Record<string, unknown>).map(([key, value]) => [key, String(value ?? '')]),
  )
}

function toQuestionTypeLabel(value: unknown): string {
  const key = String(value || '').trim()
  return QUESTION_TYPE_LABELS[key] || key
}
