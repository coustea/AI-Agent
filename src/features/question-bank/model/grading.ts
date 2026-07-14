const AI_REVIEWED_QUESTION_TYPES = new Set(['填空题', '分析题'])

export function requiresAiReview(questionType: string): boolean {
  return AI_REVIEWED_QUESTION_TYPES.has(questionType)
}

export function pendingAnswerLabel(questionType: string): string {
  return requiresAiReview(questionType) ? 'AI 评阅中' : '提交中'
}

export function pendingAnswerMessage(questionType: string): string {
  return requiresAiReview(questionType)
    ? 'AI 正在评阅你的答案，请稍候...'
    : '正在提交答题结果，请稍候...'
}
