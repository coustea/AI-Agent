import { describe, expect, it } from 'vitest'

import {
  MAX_HIGHLIGHT_CHARS,
  MAX_HIGHLIGHT_LINES,
  languageLoaders,
  normalizeLanguage,
  shouldHighlight,
} from './languages'

describe('normalizeLanguage', () => {
  it.each([
    ['py', 'python'],
    ['js', 'javascript'],
    ['ts', 'typescript'],
    ['sh', 'bash'],
    ['yml', 'yaml'],
    ['cpp', 'cpp'],
    ['c++', 'cpp'],
    ['h', 'c'],
    ['vue', 'vue'],
  ])('normalizes %s to %s', (input, expected) => {
    expect(normalizeLanguage(input)).toBe(expected)
  })

  it.each(['brainfuck', ''])('falls back to text for %j', (input) => {
    expect(normalizeLanguage(input)).toBe('text')
  })
})

describe('languageLoaders', () => {
  it('loads the default language input', async () => {
    const language = await languageLoaders.python()

    expect(Array.isArray(language)).toBe(true)
    if (!Array.isArray(language)) {
      throw new Error('Expected the loader to return a language array')
    }
    expect(language[0]?.name).toBe('python')
  })
})

describe('shouldHighlight', () => {
  it('highlights small code in a registered language', () => {
    expect(shouldHighlight('print("hello")', 'python')).toBe(true)
  })

  it('does not highlight text', () => {
    expect(shouldHighlight('plain text', 'text')).toBe(false)
  })

  it('does not highlight code over the character limit', () => {
    expect(shouldHighlight('x'.repeat(MAX_HIGHLIGHT_CHARS + 1), 'python')).toBe(false)
  })

  it('does not highlight code over the line limit', () => {
    const code = Array.from({ length: MAX_HIGHLIGHT_LINES + 1 }, () => 'x').join('\n')

    expect(shouldHighlight(code, 'python')).toBe(false)
  })
})
