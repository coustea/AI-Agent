/** 需要主观评阅的题型（填空优先规则短路，分析题走 AI）。 */
const AI_REVIEWED_QUESTION_TYPES = new Set(['填空题', '分析题'])

const FILL_BLANK_TYPES = new Set(['填空题', 'fill_blank', 'fill'])

/** 交卷等多题场景的默认前端并发上限（后端另有信号量保护）。 */
export const QUIZ_REVIEW_CLIENT_CONCURRENCY = 3

export interface RuleGradeResult {
  score: number
  is_correct: boolean
  feedback: string
  improvement_hints: string[]
}

export function requiresAiReview(questionType: string): boolean {
  return AI_REVIEWED_QUESTION_TYPES.has(questionType)
}

export function isFillBlankType(questionType: string): boolean {
  const key = String(questionType || '').trim()
  return FILL_BLANK_TYPES.has(key) || FILL_BLANK_TYPES.has(key.toLowerCase())
}

export function pendingAnswerLabel(questionType: string): string {
  if (isFillBlankType(questionType)) return '评阅中'
  return requiresAiReview(questionType) ? 'AI 评阅中' : '提交中'
}

export function pendingAnswerMessage(questionType: string): string {
  if (isFillBlankType(questionType)) return '正在评阅你的答案，请稍候...'
  return requiresAiReview(questionType)
    ? 'AI 正在评阅你的答案，请稍候...'
    : '正在提交答题结果，请稍候...'
}

/** 规范化答案：去首尾空白、折叠空白、小写。 */
export function normalizeAnswerText(text: string): string {
  return String(text || '')
    .replace(/[\u3000]/g, ' ')
    .replace(/[\uFF01-\uFF5E]/g, (ch) => String.fromCharCode(ch.charCodeAt(0) - 0xfee0))
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ')
}

function splitFillParts(text: string): string[] {
  // 多空分隔不含 /|，二者保留给同一空的多写法
  const parts = String(text || '')
    .split(/[,，、;；\n]+/)
    .map((part) => part.trim())
    .filter(Boolean)
  const trimmed = String(text || '').trim()
  return parts.length ? parts : trimmed ? [trimmed] : []
}

function splitAnswerAlternatives(text: string): string[] {
  const raw = String(text || '').trim()
  if (!raw) return []
  const alts = raw
    .split(/[/|]/)
    .map((part) => part.trim())
    .filter(Boolean)
  return alts.length ? alts : [raw]
}

/** 填空题精确匹配（多空、多写法、大小写/空白/全半角）。 */
export function fillBlankMatches(standardAnswer: string, userAnswer: string): boolean {
  const userNorm = normalizeAnswerText(userAnswer)
  if (!userNorm) return false

  if (normalizeAnswerText(standardAnswer) === userNorm) return true
  for (const alt of splitAnswerAlternatives(standardAnswer)) {
    if (normalizeAnswerText(alt) === userNorm) return true
  }

  const userParts = splitFillParts(userAnswer)
  const stdParts = splitFillParts(standardAnswer)
  if (userParts.length !== stdParts.length || stdParts.length <= 1) return false

  return stdParts.every((stdPart, index) => {
    const userPartNorm = normalizeAnswerText(userParts[index] || '')
    return splitAnswerAlternatives(stdPart).some((alt) => normalizeAnswerText(alt) === userPartNorm)
  })
}

/**
 * 规则短路评阅：空答 / 填空精确匹配可直接出分。
 * 返回 null 表示需要走 AI（目前仅分析题非空答）。
 */
export function tryRuleGrade(
  questionType: string,
  standardAnswer: string,
  userAnswer: string,
): RuleGradeResult | null {
  const userText = String(userAnswer || '').trim()
  if (!userText) {
    return {
      score: 0,
      is_correct: false,
      feedback: '本题未作答',
      improvement_hints: ['请完成作答后再提交'],
    }
  }

  if (!isFillBlankType(questionType)) return null

  if (fillBlankMatches(standardAnswer, userAnswer)) {
    return {
      score: 100,
      is_correct: true,
      feedback: '答案正确',
      improvement_hints: [],
    }
  }

  return {
    score: 0,
    is_correct: false,
    feedback: '答案与标准答案不一致',
    improvement_hints: ['请对照参考答案检查拼写、大小写与空格', '确认多空是否按顺序填写完整'],
  }
}

/** 有限并发执行异步任务，结果顺序与输入一致。 */
export async function mapWithConcurrency<T, R>(
  items: readonly T[],
  concurrency: number,
  worker: (item: T, index: number) => Promise<R>,
): Promise<R[]> {
  if (!items.length) return []

  const limit = Math.max(1, Math.min(concurrency, items.length))
  const results = new Array<R>(items.length)
  let nextIndex = 0

  async function runWorker() {
    while (nextIndex < items.length) {
      const current = nextIndex
      nextIndex += 1
      results[current] = await worker(items[current] as T, current)
    }
  }

  await Promise.all(Array.from({ length: limit }, () => runWorker()))
  return results
}
