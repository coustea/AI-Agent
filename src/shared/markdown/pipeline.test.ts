import { describe, expect, it } from 'vitest'

import tutorFreezeRegression from './fixtures/tutor-freeze-regression.md?raw'
import { renderMarkdownToHtml } from './markdown'

describe('renderMarkdownToHtml', () => {
  it('renders GFM, math, and highlighted teaching code', async () => {
    const html = await renderMarkdownToHtml([
      '| A | B |',
      '| - | - |',
      '| 1 | 2 |',
      '',
      '行内公式 $x^2$。',
      '',
      '$$',
      'E = mc^2',
      '$$',
      '',
      '```python',
      'price = "$5"',
      'print(price)',
      '```',
    ].join('\n'), 'light')

    expect(html).toContain('<table>')
    expect(html).toContain('class="katex"')
    expect(html).toContain('data-language="python"')
    expect(html).toContain('code-block-copy')
    expect(html).toContain('data-code-action="copy"')
    expect(html).toContain('data-code-action="wrap"')
    expect(html).toContain('2 行')
    expect(html).toContain('class="line code-line"')
    expect(html).toContain('$5')
  })

  it.each(['mermaid', 'svg'])('preserves %s blocks for diagram rendering', async language => {
    const source = language === 'mermaid' ? 'flowchart LR\n A --> B' : '<svg><text>diagram</text></svg>'
    const html = await renderMarkdownToHtml(`\`\`\`${language}\n${source}\n\`\`\``, 'light')
    const container = document.createElement('div')
    container.innerHTML = html
    expect(container.querySelector(`pre > code.language-${language}`)?.textContent?.trim()).toBe(source)
    expect(container.querySelector('.code-block-wrapper')).toBeNull()
  })

  it('never parses code contents as math or raw HTML', async () => {
    const html = await renderMarkdownToHtml(
      '```html\n<script>alert("$x$")</script>\n```',
      'light',
    )

    expect(html).not.toContain('<script>')
    expect(html).not.toContain('class="katex"')
    expect(html).toContain('&#x3C;')
  })

  it('blocks executable HTML and dangerous links', async () => {
    const html = await renderMarkdownToHtml([
      '<img src=x onerror=alert(1)>',
      '',
      '[bad](javascript:alert(1))',
      '',
      '[good](https://example.com)',
    ].join('\n'), 'light')

    expect(html).not.toContain('onerror')
    expect(html).not.toContain('javascript:')
    expect(html).toContain('target="_blank"')
    expect(html).toContain('rel="noopener noreferrer"')
  })

  it('falls back to plain code for unknown and huge blocks without truncation', async () => {
    const code = 'x'.repeat(50_001)
    const html = await renderMarkdownToHtml(`\`\`\`unknown\n${code}\n\`\`\``, 'light')

    expect(html).toContain('data-language="text"')
    expect(html).toContain('class="language-text"')
    expect(html).toContain(code)
    expect(html).not.toContain('class="shiki')
  })

  it.each([
    ['unknown', 'unknown', 'first\nsecond'],
    ['oversized', 'python', `${'x'.repeat(50_001)}\nsecond`],
    ['plain text', 'text', 'first\nsecond'],
  ])('adds CSS-only line wrappers to %s fallback code', async (_, language, code) => {
    const html = await renderMarkdownToHtml(
      `\`\`\`${language}\n${code}\n\`\`\``,
      'light',
    )
    const container = document.createElement('div')
    container.innerHTML = html
    const codeElement = container.querySelector('code')

    expect(codeElement?.querySelectorAll('.line.code-line')).toHaveLength(2)
    expect(codeElement?.textContent).toBe(code)
    expect(codeElement?.textContent).not.toMatch(/^\s*\d+/)
    expect(html).not.toContain('class="shiki')
  })

  it('selects the requested Shiki theme as the default color', async () => {
    const markdown = '```python\nprint("theme")\n```'

    const lightHtml = await renderMarkdownToHtml(markdown, 'light')
    const darkHtml = await renderMarkdownToHtml(markdown, 'dark')
    const container = document.createElement('div')

    container.innerHTML = lightHtml
    expect(container.querySelector('pre')?.style.color).toBe('rgb(36, 41, 46)')
    expect(container.querySelector('pre')?.style.backgroundColor).toBe('rgb(255, 255, 255)')

    container.innerHTML = darkHtml
    expect(container.querySelector('pre')?.style.color).toBe('rgb(225, 228, 232)')
    expect(container.querySelector('pre')?.style.backgroundColor).toBe('rgb(36, 41, 46)')
  })

  it('does not throw for malformed HTTP-like links', async () => {
    await expect(
      renderMarkdownToHtml('[x](http://[)', 'light'),
    ).resolves.toContain('x')
  })

  it('completes the route-freeze regression fixture within one second', async () => {
    const startedAt = performance.now()

    const html = await renderMarkdownToHtml(tutorFreezeRegression, 'light')

    expect(html.length).toBeGreaterThan(0)
    expect(performance.now() - startedAt).toBeLessThan(1_000)
  })
})
