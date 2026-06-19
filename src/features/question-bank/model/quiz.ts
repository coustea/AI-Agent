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
