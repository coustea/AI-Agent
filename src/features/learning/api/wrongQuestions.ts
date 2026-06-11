import http from '@/shared/api/http'

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
  const response = await http.get('/ai/wrong-questions', { params })
  return response.data as WrongQuestionListResponse
}

export async function addWrongQuestion(data: {
  question_id: string
  user_answer?: string
}): Promise<{ id: number; action: string }> {
  const response = await http.post('/ai/wrong-questions', data)
  return response.data.data
}

export async function removeWrongQuestion(wrongId: number): Promise<void> {
  await http.delete(`/ai/wrong-questions/${wrongId}`)
}

export async function archiveWrongQuestion(wrongId: number): Promise<void> {
  await http.post(`/ai/wrong-questions/${wrongId}/archive`)
}

export async function unarchiveWrongQuestion(wrongId: number): Promise<void> {
  await http.post(`/ai/wrong-questions/${wrongId}/unarchive`)
}

export async function fetchRandomWrongQuestion(subject?: string): Promise<WrongQuestion | null> {
  const response = await http.get('/ai/wrong-questions/random', {
    params: subject ? { subject } : undefined,
  })
  return response.data.data as WrongQuestion | null
}
