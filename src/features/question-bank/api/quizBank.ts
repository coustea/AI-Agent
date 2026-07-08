import http from '@/shared/api/http'

export interface QuizBankQuestion {
  id: string
  subject: string
  subject_en?: string | null
  type: string
  difficulty?: string | null
  content: string
  options?: Record<string, string> | null
  answer: string
  analysis: string
  knowledge_points: string[]
  tags: string[]
  language?: string | null
  split?: string | null
}

export interface QuizBankQuestionListResponse {
  items: QuizBankQuestion[]
  total: number
  page: number
  page_size: number
  subjects: string[]
  difficulties: string[]
  types: string[]
}

const QUESTION_TYPE_LABELS: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  judge: '判断题',
  fill_blank: '填空题',
  short_answer: '简答题',
  analysis: '分析题',
  comprehensive: '综合题',
}

export interface QuizReviewRequest {
  question_id: string
  question_type: string
  question_content: string
  standard_answer: string
  user_answer: string
  knowledge_points?: string[]
}

export interface QuizReviewResult {
  score: number
  is_correct: boolean
  feedback: string
  improvement_hints: string[]
}

export async function fetchQuizBankQuestions(params?: {
  query?: string
  subject?: string
  subjects?: string[]
  difficulty?: string
  type?: string
  page?: number
  page_size?: number
}): Promise<QuizBankQuestionListResponse> {
  const requestParams = {
    subject: params?.subject,
    subjects: params?.subjects?.length ? params.subjects : undefined,
    difficulty: params?.difficulty,
    type: params?.type,
    query: params?.query || undefined,
    page: params?.page,
    page_size: params?.page_size,
  }
  const response = await http.get('/ai/quiz', { params: requestParams })
  const payload = response.data.data as Partial<QuizBankQuestionListResponse> & { items?: any[] }
  const items = (payload.items || []).map((item) => normalizeQuizQuestion(item))
  const subjects = payload.subjects?.length ? payload.subjects : unique(items.map((item) => item.subject))
  const difficulties = payload.difficulties?.length ? payload.difficulties : unique(items.map((item) => item.difficulty || '').filter(Boolean))
  const types = payload.types?.length ? payload.types.map(toQuestionTypeLabel) : unique(items.map((item) => item.type))

  return {
    items,
    total: payload.total || 0,
    page: payload.page || requestParams.page || 1,
    page_size: payload.page_size || requestParams.page_size || 20,
    subjects,
    difficulties,
    types,
  }
}

export async function fetchQuizReview(request: QuizReviewRequest): Promise<QuizReviewResult> {
  const response = await http.post('/ai/quiz/review', request, { timeout: 60000 })
  return response.data as QuizReviewResult
}

export interface ObjectiveQuestionResult {
  question_id: string
  user_answer: string
  is_correct: boolean
  subject?: string
  question_type?: string
  content?: string
  options?: Record<string, string> | null
  answer?: string
  analysis?: string
}

export interface ObjectiveSubmitRequest {
  results: ObjectiveQuestionResult[]
}

export interface ObjectiveSubmitResponse {
  processed_count: number
  wrong_saved_count: number
}

export async function submitObjectiveResults(request: ObjectiveSubmitRequest): Promise<ObjectiveSubmitResponse> {
  const response = await http.post('/ai/quiz/submit', request)
  return response.data.data as ObjectiveSubmitResponse
}

function normalizeQuizQuestion(item: Record<string, any>) {
  return {
    id: String(item.id || ''),
    subject: String(item.subject || ''),
    subject_en: item.subject_en ?? null,
    type: toQuestionTypeLabel(item.type),
    difficulty: item.difficulty ?? null,
    content: String(item.content || ''),
    options: normalizeOptions(item.options),
    answer: String(item.answer || ''),
    analysis: String(item.analysis || ''),
    knowledge_points: Array.isArray(item.knowledge_points) ? item.knowledge_points.map(String) : [],
    tags: Array.isArray(item.tags) ? item.tags.map(String) : [],
    language: item.language ?? null,
    split: item.split ?? null,
  }
}

function normalizeOptions(options: unknown): Record<string, string> | null {
  if (!options || typeof options !== 'object' || Array.isArray(options)) return null
  return Object.fromEntries(
    Object.entries(options as Record<string, unknown>).map(([key, value]) => [key, String(value ?? '')]),
  )
}

export function toQuestionTypeLabel(value: unknown): string {
  const key = String(value || '').trim()
  return QUESTION_TYPE_LABELS[key] || key
}

function unique(items: string[]) {
  return Array.from(new Set(items.filter(Boolean)))
}
