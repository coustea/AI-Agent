import http from '@/utils/http'

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

export async function fetchQuizBankQuestions(params?: {
  query?: string
  subject?: string
  subjects?: string[]
  difficulty?: string
  type?: string
  page?: number
  page_size?: number
}): Promise<QuizBankQuestionListResponse> {
  const response = await http.get('/ai/quiz-bank/questions', { params })
  return response.data.data as QuizBankQuestionListResponse
}
