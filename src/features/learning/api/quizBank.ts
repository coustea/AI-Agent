import http from '@/shared/api/http'
import type {
  QuizBankQuestionListResponse,
} from '@/features/learning/model/evaluation'

export type { QuizBankQuestionListResponse }

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
  const response = await http.get('/ai/quiz-bank/questions', { params })
  return response.data.data as QuizBankQuestionListResponse
}

export async function fetchQuizReview(request: QuizReviewRequest): Promise<QuizReviewResult> {
  const response = await http.post('/ai/quiz-review', request)
  return response.data as QuizReviewResult
}
