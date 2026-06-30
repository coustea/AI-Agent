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
  const requestParams = {
    subject: params?.subject,
    type: params?.question_type,
    archived: params?.is_archived,
    page: params?.page,
    page_size: params?.page_size,
  }
  const response = await http.get('/ai/wrong', { params: requestParams })
  return response.data as WrongQuestionListResponse
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
  return response.data.data as WrongQuestion | null
}
