import { beforeEach, describe, expect, it, vi } from 'vitest'

const { getMock, postMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
  postMock: vi.fn(),
}))

vi.mock('@/shared/api/http', () => ({
  default: {
    get: getMock,
    post: postMock,
  },
}))

import { fetchQuizAnswerHistory, fetchQuizReviewBatch, submitObjectiveResults } from './quizBank'
import {
  fillBlankMatches,
  mapWithConcurrency,
  pendingAnswerLabel,
  pendingAnswerMessage,
  requiresAiReview,
  tryRuleGrade,
} from '../model/grading'
import { normalizePageNumber } from '../model/pagination'
import { summarizeQuestionText } from '../model/questionText'

function historyItem(index: number) {
  return {
    question_id: `q-${index}`,
    subject: '操作系统',
    question_type: 'single_choice',
    score: index % 2 === 0 ? 100 : 0,
    is_correct: index % 2 === 0,
    attempts: 1,
    last_answer: 'A',
    created_at: '2026-07-12T00:00:00Z',
  }
}

describe('quiz bank API', () => {
  beforeEach(() => {
    getMock.mockReset()
    postMock.mockReset()
  })

  it('loads all answer history within the backend page-size limit', async () => {
    getMock
      .mockResolvedValueOnce({
        data: {
          data: {
            items: Array.from({ length: 100 }, (_, index) => historyItem(index)),
            total: 101,
            page: 1,
            page_size: 100,
          },
        },
      })
      .mockResolvedValueOnce({
        data: {
          data: {
            items: [historyItem(100)],
            total: 101,
            page: 2,
            page_size: 100,
          },
        },
      })

    const result = await fetchQuizAnswerHistory()

    expect(result.size).toBe(101)
    expect(getMock).toHaveBeenNthCalledWith(1, '/ai/quiz/history', {
      params: { page: 1, page_size: 100 },
    })
    expect(getMock).toHaveBeenNthCalledWith(2, '/ai/quiz/history', {
      params: { page: 2, page_size: 100 },
    })
  })

  it('unwraps the objective submit response', async () => {
    postMock.mockResolvedValueOnce({
      data: {
        data: {
          processed_count: 1,
          wrong_saved_count: 0,
        },
      },
    })

    const result = await submitObjectiveResults({
      results: [{ question_id: 'q-1', user_answer: '分析过程', is_correct: true, score: 85 }],
    })

    expect(result).toEqual({ processed_count: 1, wrong_saved_count: 0 })
    expect(postMock).toHaveBeenCalledWith(
      '/ai/quiz/submit',
      {
        results: [{ question_id: 'q-1', user_answer: '分析过程', is_correct: true, score: 85 }],
      },
      expect.objectContaining({ timeout: expect.any(Number) }),
    )
  })

  it('unwraps the batch review response envelope', async () => {
    postMock.mockResolvedValueOnce({
      data: {
        code: 200,
        data: {
          results: [
            {
              question_id: 'a-1',
              score: 80,
              is_correct: true,
              feedback: '过程正确',
              improvement_hints: ['补充细节'],
            },
          ],
        },
      },
    })

    const result = await fetchQuizReviewBatch({
      items: [
        {
          question_id: 'a-1',
          question_type: '分析题',
          question_content: '分析调度',
          standard_answer: '标准',
          user_answer: '用户答案',
        },
      ],
    })

    expect(result).toEqual([
      {
        question_id: 'a-1',
        score: 80,
        is_correct: true,
        feedback: '过程正确',
        improvement_hints: ['补充细节'],
      },
    ])
    expect(postMock).toHaveBeenCalledWith(
      '/ai/quiz/review/batch',
      {
        items: [
          {
            question_id: 'a-1',
            question_type: '分析题',
            question_content: '分析调度',
            standard_answer: '标准',
            user_answer: '用户答案',
          },
        ],
      },
      expect.objectContaining({ timeout: expect.any(Number) }),
    )
  })
})

describe('quiz grading strategy', () => {
  it.each([
    ['填空题', true],
    ['分析题', true],
    ['单选题', false],
    ['选择题', false],
    ['判断题', false],
    ['未知题型', false],
  ])('uses AI review for %s: %s', (questionType, expected) => {
    expect(requiresAiReview(questionType)).toBe(expected)
  })

  it('does not describe objective submission as AI review', () => {
    expect(pendingAnswerLabel('单选题')).toBe('提交中')
    expect(pendingAnswerMessage('判断题')).toBe('正在提交答题结果，请稍候...')
    expect(pendingAnswerLabel('填空题')).toBe('评阅中')
    expect(pendingAnswerLabel('分析题')).toBe('AI 评阅中')
  })

  it('short-circuits fill-blank grading without AI', () => {
    expect(tryRuleGrade('填空题', 'OS', ' os ')).toEqual({
      score: 100,
      is_correct: true,
      feedback: '答案正确',
      improvement_hints: [],
    })
    expect(tryRuleGrade('填空题', 'OS', 'Windows')?.score).toBe(0)
    expect(tryRuleGrade('分析题', '标准', '用户长答案')).toBeNull()
    expect(tryRuleGrade('分析题', '标准', '')?.feedback).toBe('本题未作答')
  })

  it('matches multi-blank and alternative answers', () => {
    expect(fillBlankMatches('进程/process，线程', 'process, 线程')).toBe(true)
    expect(fillBlankMatches('A|B', 'b')).toBe(true)
    expect(fillBlankMatches('A，B', 'A')).toBe(false)
  })

  it('runs async work with a concurrency pool and preserves order', async () => {
    let active = 0
    let maxActive = 0
    const items = [1, 2, 3, 4, 5]

    const results = await mapWithConcurrency(items, 2, async (item) => {
      active += 1
      maxActive = Math.max(maxActive, active)
      await new Promise((resolve) => setTimeout(resolve, 20))
      active -= 1
      return item * 10
    })

    expect(results).toEqual([10, 20, 30, 40, 50])
    expect(maxActive).toBeLessThanOrEqual(2)
  })
})

describe('question text summary', () => {
  it('preserves blank markers and meaningful punctuation', () => {
    expect(summarizeQuestionText('操作系统是对____进行管理的软件。')).toBe('操作系统是对____进行管理的软件。')
    expect(summarizeQuestionText('进程 P0-P4\n 共享资源')).toBe('进程 P0-P4 共享资源')
  })
})

describe('question pagination', () => {
  it('normalizes direct page input to the available range', () => {
    expect(normalizePageNumber('5', 20)).toBe(5)
    expect(normalizePageNumber('0', 20)).toBe(1)
    expect(normalizePageNumber('99', 20)).toBe(20)
    expect(normalizePageNumber('2.9', 20)).toBe(2)
    expect(normalizePageNumber('', 20)).toBeNull()
    expect(normalizePageNumber('abc', 20)).toBeNull()
  })
})
