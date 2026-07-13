const AI_REVIEW_QUESTION_TYPES = new Set(['填空题', '分析题'])

export function requiresAiReview(questionType: string | null | undefined) {
  return AI_REVIEW_QUESTION_TYPES.has(String(questionType || '').trim())
}

export function pendingAnswerLabel(questionType: string | null | undefined) {
  return requiresAiReview(questionType) ? 'AI 评阅中' : '提交中'
}

export function pendingAnswerMessage(questionType: string | null | undefined) {
  return requiresAiReview(questionType)
    ? 'AI 正在评阅你的答案，请稍候...'
    : '答案正在提交，请稍候...'
}
