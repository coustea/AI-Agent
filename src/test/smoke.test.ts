import { describe, expect, it } from 'vitest'

describe('frontend test runtime', () => {
  it('provides a DOM', () => {
    expect(document.createElement('div')).toBeInstanceOf(HTMLElement)
  })
})
