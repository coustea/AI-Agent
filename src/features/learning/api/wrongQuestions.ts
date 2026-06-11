import http from '@/shared/api/http'

export interface AddWrongQuestionRequest {
  question_id: string
  user_answer?: string
}

export interface WrongQuestionItem {
  id: number
  question_id: string
  subject: string
  question_type: string
  content: string
  options_json: Record<string, unknown> | null
  standard_answer: string | null
  analysis: string | null
  user_answer: string | null
  wrong_count: number
  note: string | null
  created_at: string | null
  updated_at: string | null
}

export async function addWrongQuestion(request: AddWrongQuestionRequest): Promise<void> {
  await http.post('/ai/wrong-questions', request)
}

export async function fetchWrongQuestions(params?: {
  page?: number
  page_size?: number
}): Promise<{ items: WrongQuestionItem[]; total: number; page: number; page_size: number }> {
  const response = await http.get('/ai/wrong-questions', { params })
  return response.data.data
}

export async function archiveWrongQuestion(wrongId: number): Promise<void> {
  await http.put(`/ai/wrong-questions/${wrongId}/archive`)
}
