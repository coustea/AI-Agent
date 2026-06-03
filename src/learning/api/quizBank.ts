import http from '@/shared/utils/http'
import type {
  QuizBankQuestion,
  QuizBankQuestionListResponse,
} from '@/learning/types/evaluation'

export type { QuizBankQuestion, QuizBankQuestionListResponse }

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
