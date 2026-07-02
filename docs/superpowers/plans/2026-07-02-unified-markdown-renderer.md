# Unified Markdown Renderer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace every frontend Markdown path with one Worker-isolated renderer that prioritizes Shiki code highlighting, supports KaTeX math, blocks unsafe HTML, and cannot freeze route navigation.

**Architecture:** A single `MarkdownRenderer.vue` delegates parsing, sanitizing, KaTeX, and Shiki work to one shared Web Worker through a request-ID client. Unified/Remark/Rehype owns syntax, a small language registry owns the supported teaching languages and size limits, and every business module passes raw Markdown without preprocessing. Backend agents that directly emit Markdown append one shared output contract while `resource` and `path` retain separate records and persistence.

**Tech Stack:** Vue 3, TypeScript, Vite Web Workers, Vitest, Vue Test Utils, Unified, Remark, Rehype, KaTeX, Shiki, FastAPI prompt infrastructure, pytest.

---

## File map

### New frontend files

- `vitest.config.ts` — frontend unit-test configuration and `@` alias.
- `src/test/setup.ts` — DOM cleanup and browser API test defaults.
- `src/shared/markdown/types.ts` — renderer, Worker, and theme contracts.
- `src/shared/markdown/languages.ts` — language aliases, supported loaders, and size limits.
- `src/shared/markdown/schema.ts` — Rehype sanitize schema.
- `src/shared/markdown/codeBlocks.ts` — code-node normalization and trusted code-block chrome.
- `src/shared/markdown/pipeline.ts` — the only Markdown-to-HTML pipeline.
- `src/shared/markdown/markdown.worker.ts` — Worker message handler.
- `src/shared/markdown/workerClient.ts` — shared Worker lifecycle, timeout, restart, and fallback.
- `src/shared/markdown/escapeHtml.ts` — safe degraded plain-text output.
- `src/shared/ui/MarkdownRenderer.vue` — the only Vue Markdown renderer.
- `src/shared/styles/markdown.css` — system-wide Markdown, KaTeX, and code styles.
- `src/shared/markdown/*.test.ts` — pipeline, Worker client, and architecture tests.
- `src/shared/ui/MarkdownRenderer.test.ts` — component behavior tests.

### Modified frontend files

- `package.json`, `package-lock.json` — replace legacy parser/highlighter dependencies and add tests.
- `vite.config.ts` — remove legacy renderer chunk checks and include Shiki/Unified.
- `src/features/chat/components/TutorMessageContent.vue` — become a thin `MarkdownRenderer` adapter.
- `src/features/resource/components/CodeView.vue` — remove direct Highlight.js and render code as Markdown.
- `src/features/resource/components/MarkdownView.vue` — use the shared renderer and remove duplicate prose styles.
- `src/features/resource/components/QuizView.vue` — replace synchronous helper calls with components.
- `src/features/question-bank/views/QuestionBank.vue` — replace local inline parser.
- `src/features/question-bank/components/ExamTab.vue` — replace local inline parser.
- `src/features/question-bank/components/WrongBookTab.vue` — replace local inline parser.
- `src/features/question-bank/components/SearchTab.vue` — replace local inline parser.
- `src/features/question-bank/components/DailyPracticeTab.vue` — replace local inline parser.

### Deleted frontend files

- `src/shared/utils/markdown.ts`
- `src/shared/ui/MarkdownPreview.vue`
- `src/shims-markdown-it-katex.d.ts`

### New backend files

- `server/app/infra/prompt_contracts/markdown_output.md` — single AI Markdown output contract.
- `server/app/infra/markdown_output.py` — appends the shared contract to direct Markdown prompts.
- `server/tests/infra/test_markdown_output_contract.py` — contract registration and producer coverage.

### Modified backend files

- `server/app/infra/prompts.py` — register the shared contract directory.
- `server/app/chat/agent/nodes.py` — append the contract to tutor answers.
- `server/app/chat/memory/compression.py` — append the contract to direct Markdown summaries.
- `server/app/resource/agents/content.py` — append contract and remove fence cleanup.
- `server/app/resource/agents/code.py` — append contract.
- `server/app/resource/agents/mindmap.py` — append contract and remove output cleanup.
- `server/app/path/workflows.py` — append contract to tutorial generation only.

## Task 1: Install the new stack and establish frontend tests

**Files:**
- Modify: `package.json`
- Modify: `package-lock.json`
- Create: `vitest.config.ts`
- Create: `src/test/setup.ts`
- Test: `src/test/smoke.test.ts`

- [ ] **Step 1: Add a failing smoke test**

```ts
// src/test/smoke.test.ts
import { describe, expect, it } from 'vitest'

describe('frontend test runtime', () => {
  it('provides a DOM', () => {
    expect(document.createElement('div')).toBeInstanceOf(HTMLElement)
  })
})
```

- [ ] **Step 2: Run the test before adding Vitest**

Run: `npm test -- --run src/test/smoke.test.ts`

Expected: FAIL because the `test` script and Vitest are not installed.

- [ ] **Step 3: Replace dependencies and add the test configuration**

Run:

```bash
npm uninstall highlight.js markdown-it markdown-it-katex @types/markdown-it
npm install unified remark-parse remark-gfm remark-math remark-rehype rehype-katex rehype-sanitize rehype-stringify unist-util-visit shiki @shikijs/rehype @shikijs/langs @shikijs/themes
npm install -D vitest @vue/test-utils jsdom
```

Add scripts to `package.json`:

```json
{
  "scripts": {
    "test": "vitest",
    "test:run": "vitest run"
  }
}
```

Create:

```ts
// vitest.config.ts
import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    clearMocks: true,
  },
})
```

```ts
// src/test/setup.ts
import { afterEach } from 'vitest'

afterEach(() => {
  document.body.innerHTML = ''
  document.documentElement.classList.remove('dark')
})
```

- [ ] **Step 4: Run the smoke test**

Run: `npm run test:run -- src/test/smoke.test.ts`

Expected: PASS, 1 test.

- [ ] **Step 5: Commit**

```bash
git add package.json package-lock.json vitest.config.ts src/test/setup.ts src/test/smoke.test.ts
git commit -m "test: add frontend markdown test runtime"
```

## Task 2: Define language support and hard rendering limits

**Files:**
- Create: `src/shared/markdown/types.ts`
- Create: `src/shared/markdown/languages.ts`
- Test: `src/shared/markdown/languages.test.ts`

- [ ] **Step 1: Write failing language-registry tests**

```ts
// src/shared/markdown/languages.test.ts
import { describe, expect, it } from 'vitest'
import {
  MAX_HIGHLIGHT_CHARS,
  MAX_HIGHLIGHT_LINES,
  normalizeLanguage,
  shouldHighlight,
} from './languages'

describe('Markdown language registry', () => {
  it.each([
    ['py', 'python'],
    ['js', 'javascript'],
    ['ts', 'typescript'],
    ['sh', 'bash'],
    ['yml', 'yaml'],
    ['cpp', 'cpp'],
    ['c++', 'cpp'],
    ['vue', 'vue'],
  ])('normalizes %s to %s', (input, expected) => {
    expect(normalizeLanguage(input)).toBe(expected)
  })

  it('uses text for unknown or missing languages', () => {
    expect(normalizeLanguage('brainfuck')).toBe('text')
    expect(normalizeLanguage('')).toBe('text')
  })

  it('skips highlighter work without dropping large code', () => {
    expect(shouldHighlight('x'.repeat(MAX_HIGHLIGHT_CHARS + 1), 'python')).toBe(false)
    expect(shouldHighlight('x\n'.repeat(MAX_HIGHLIGHT_LINES + 1), 'python')).toBe(false)
    expect(shouldHighlight('print(1)', 'python')).toBe(true)
    expect(shouldHighlight('print(1)', 'text')).toBe(false)
  })
})
```

- [ ] **Step 2: Verify the tests fail**

Run: `npm run test:run -- src/shared/markdown/languages.test.ts`

Expected: FAIL because `languages.ts` does not exist.

- [ ] **Step 3: Add stable types and the fine-grained registry**

```ts
// src/shared/markdown/types.ts
export type MarkdownTheme = 'light' | 'dark'

export interface MarkdownRenderRequest {
  type: 'render'
  requestId: number
  markdown: string
  theme: MarkdownTheme
}

export interface MarkdownRenderSuccess {
  type: 'success'
  requestId: number
  html: string
}

export interface MarkdownRenderFailure {
  type: 'error'
  requestId: number
  message: string
}

export type MarkdownRenderResponse = MarkdownRenderSuccess | MarkdownRenderFailure

export interface MarkdownRenderResult {
  html: string
  degraded: boolean
  error?: string
}
```

```ts
// src/shared/markdown/languages.ts
import type { LanguageInput } from 'shiki/core'

export const MAX_HIGHLIGHT_CHARS = 50_000
export const MAX_HIGHLIGHT_LINES = 2_000

const aliases: Record<string, string> = {
  py: 'python',
  js: 'javascript',
  jsx: 'javascript',
  ts: 'typescript',
  tsx: 'typescript',
  sh: 'bash',
  shell: 'bash',
  yml: 'yaml',
  'c++': 'cpp',
  cplusplus: 'cpp',
  h: 'c',
  hpp: 'cpp',
}

export const languageLoaders: Record<string, () => Promise<LanguageInput>> = {
  python: () => import('@shikijs/langs/python').then((module) => module.default),
  c: () => import('@shikijs/langs/c').then((module) => module.default),
  cpp: () => import('@shikijs/langs/cpp').then((module) => module.default),
  java: () => import('@shikijs/langs/java').then((module) => module.default),
  javascript: () => import('@shikijs/langs/javascript').then((module) => module.default),
  typescript: () => import('@shikijs/langs/typescript').then((module) => module.default),
  vue: () => import('@shikijs/langs/vue').then((module) => module.default),
  html: () => import('@shikijs/langs/html').then((module) => module.default),
  css: () => import('@shikijs/langs/css').then((module) => module.default),
  sql: () => import('@shikijs/langs/sql').then((module) => module.default),
  bash: () => import('@shikijs/langs/bash').then((module) => module.default),
  go: () => import('@shikijs/langs/go').then((module) => module.default),
  rust: () => import('@shikijs/langs/rust').then((module) => module.default),
  json: () => import('@shikijs/langs/json').then((module) => module.default),
  yaml: () => import('@shikijs/langs/yaml').then((module) => module.default),
}

export function normalizeLanguage(value: string): string {
  const normalized = value.trim().toLowerCase()
  const canonical = aliases[normalized] ?? normalized
  return canonical in languageLoaders ? canonical : 'text'
}

export function shouldHighlight(code: string, language: string): boolean {
  if (language === 'text') return false
  if (code.length > MAX_HIGHLIGHT_CHARS) return false
  return code.split('\n').length <= MAX_HIGHLIGHT_LINES
}
```

- [ ] **Step 4: Run the registry tests**

Run: `npm run test:run -- src/shared/markdown/languages.test.ts`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/shared/markdown/types.ts src/shared/markdown/languages.ts src/shared/markdown/languages.test.ts
git commit -m "feat: define markdown language registry"
```

## Task 3: Build the safe Unified pipeline

**Files:**
- Create: `src/shared/markdown/schema.ts`
- Create: `src/shared/markdown/codeBlocks.ts`
- Create: `src/shared/markdown/pipeline.ts`
- Test: `src/shared/markdown/pipeline.test.ts`
- Fixture: `src/shared/markdown/fixtures/tutor-freeze-regression.md`

- [ ] **Step 1: Add the historical freeze fixture**

Create the fixture with the same delimiter pattern that triggered the old catastrophic regex:

````markdown
# 动态规划复杂度分析

设状态数量为 $n$，每个状态需要枚举 $m$ 个决策，因此基础时间复杂度是
$T(n, m)=O(nm)$。当转移还需要扫描此前的所有状态时，复杂度会变为
$O(n^2m)$，而空间复杂度通常是 $S(n)=O(n)$。

状态转移可以写成：

$$
dp[i] = \min_{0 \le j < i}\left(dp[j] + cost(j, i)\right)
$$

若使用滚动数组，原来的 $O(n)$ 额外空间可以在只依赖前一层时降到 $O(1)$。
注意这里的价格字符串 `$5` 不是公式；生成代码时必须保持原样。

```python
def solve(cost: list[int]) -> int:
    price_label = "$5"
    dp = [0] * len(cost)
    for i in range(1, len(cost)):
        dp[i] = min(dp[j] + cost[i] for j in range(i))
    return dp[-1]
```

对比 $f(i)$、$g(j)$ 与块公式：

$$
\sum_{i=1}^{n}\sum_{j=1}^{m} a_{ij}
$$

最终结论为 $O(n^2 + nm)$，并且代码中的 `"$5"` 不参与数学解析。
````

- [ ] **Step 2: Write failing syntax, code, math, and security tests**

```ts
// src/shared/markdown/pipeline.test.ts
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { renderMarkdownToHtml } from './pipeline'

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
      'price = \"$5\"',
      'print(price)',
      '```',
    ].join('\n'), 'light')

    expect(html).toContain('<table>')
    expect(html).toContain('class="katex"')
    expect(html).toContain('data-language="python"')
    expect(html).toContain('code-block-copy')
    expect(html).toContain('$5')
  })

  it('never parses code contents as math or raw HTML', async () => {
    const html = await renderMarkdownToHtml(
      '```html\n<script>alert(\"$x$\")</script>\n```',
      'light',
    )

    expect(html).not.toContain('<script>')
    expect(html).not.toContain('class="katex"')
    expect(html).toContain('&lt;script&gt;')
  })

  it('blocks executable HTML and dangerous links', async () => {
    const html = await renderMarkdownToHtml([
      '<img src=x onerror=alert(1)>',
      '[bad](javascript:alert(1))',
      '[good](https://example.com)',
    ].join('\n'), 'light')

    expect(html).not.toContain('onerror')
    expect(html).not.toContain('javascript:')
    expect(html).toContain('rel="noopener noreferrer"')
  })

  it('falls back to plain code for unknown and huge blocks without truncation', async () => {
    const code = 'x'.repeat(50_001)
    const html = await renderMarkdownToHtml(`\`\`\`unknown\n${code}\n\`\`\``, 'light')

    expect(html).toContain('data-language="text"')
    expect(html).toContain(code)
    expect(html).not.toContain('class="shiki')
  })

  it('completes the route-freeze regression fixture within one second', async () => {
    const fixtureUrl = new URL('./fixtures/tutor-freeze-regression.md', import.meta.url)
    const markdown = await readFile(fileURLToPath(fixtureUrl), 'utf8')
    const startedAt = performance.now()

    const html = await renderMarkdownToHtml(markdown, 'light')

    expect(html.length).toBeGreaterThan(0)
    expect(performance.now() - startedAt).toBeLessThan(1_000)
  })
})
```

- [ ] **Step 3: Verify the pipeline tests fail**

Run: `npm run test:run -- src/shared/markdown/pipeline.test.ts`

Expected: FAIL because the pipeline files do not exist.

- [ ] **Step 4: Implement schema, code-node plugins, and pipeline**

`schema.ts` must derive from `defaultSchema`, allow only `language-*`, `math-inline`, and
`math-display` classes before trusted plugins run, and allow `data-language` on `pre`:

```ts
import { defaultSchema } from 'rehype-sanitize'

export const markdownSanitizeSchema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    code: [
      ...(defaultSchema.attributes?.code ?? []),
      ['className', /^language-./, 'math-inline', 'math-display'],
    ],
    pre: [
      ...(defaultSchema.attributes?.pre ?? []),
      ['dataLanguage'],
    ],
  },
}
```

`codeBlocks.ts` must export two plugins:

```ts
export function rehypePrepareCodeBlocks(): (tree: Root) => Promise<void>
export function rehypeDecorateCodeBlocks(): (tree: Root) => void
```

`rehypePrepareCodeBlocks` must:

- visit every `pre > code`;
- read the `language-*` class;
- normalize it through `normalizeLanguage`;
- change oversized or unknown blocks to `language-text`;
- dynamically load a supported Shiki grammar once;
- preserve the normalized language on `pre.properties.dataLanguage`.

`rehypeDecorateCodeBlocks` must replace each `pre` with this trusted HAST structure:

```html
<div class="code-block-wrapper" data-language="python">
  <div class="code-block-header">
    <span class="code-block-language">python</span>
    <button type="button" class="code-block-copy" aria-label="复制 python 代码">复制</button>
  </div>
  <div class="code-block-scroll">
    <!-- original Shiki <pre> -->
  </div>
</div>
```

It must add class `code-line` to each Shiki line span. CSS counters provide visible line numbers;
line-number text must not enter `code.textContent`.

`pipeline.ts` must lazily create one fine-grained Shiki highlighter per Worker:

```ts
import { createJavaScriptRegexEngine } from 'shiki/engine/javascript'
import { createHighlighterCore } from 'shiki/core'
import githubDark from '@shikijs/themes/github-dark'
import githubLight from '@shikijs/themes/github-light'
import { rehypeShikiFromHighlighter } from '@shikijs/rehype/core'

const highlighterPromise = createHighlighterCore({
  themes: [githubLight, githubDark],
  langs: [],
  engine: createJavaScriptRegexEngine(),
})
```

Then create exactly this processing order:

```ts
unified()
  .use(remarkParse)
  .use(remarkGfm)
  .use(remarkMath)
  .use(remarkRehype)
  .use(rehypeSanitize, markdownSanitizeSchema)
  .use(rehypeKatex, { throwOnError: false, strict: 'ignore' })
  .use(rehypePrepareCodeBlocks)
  .use(rehypeShikiFromHighlighter, highlighter, {
    themes: { light: 'github-light', dark: 'github-dark' },
    defaultColor: false,
    fallbackLanguage: 'text',
  })
  .use(rehypeDecorateCodeBlocks)
  .use(rehypeExternalLinkPolicy)
  .use(rehypeStringify)
```

`rehypeExternalLinkPolicy` must add `target="_blank"` and `rel="noopener noreferrer"` only to
absolute `http`/`https` links. Export:

```ts
export async function renderMarkdownToHtml(
  markdown: string,
  theme: MarkdownTheme,
): Promise<string>
```

The `theme` argument selects the Shiki default theme but does not create another highlighter.

- [ ] **Step 5: Run focused tests and type checking**

Run: `npm run test:run -- src/shared/markdown/languages.test.ts src/shared/markdown/pipeline.test.ts`

Expected: PASS.

Run: `npx vue-tsc -b`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/shared/markdown/schema.ts src/shared/markdown/codeBlocks.ts src/shared/markdown/pipeline.ts src/shared/markdown/pipeline.test.ts src/shared/markdown/fixtures/tutor-freeze-regression.md
git commit -m "feat: add safe markdown rendering pipeline"
```

## Task 4: Isolate rendering behind one recoverable Worker

**Files:**
- Create: `src/shared/markdown/escapeHtml.ts`
- Create: `src/shared/markdown/markdown.worker.ts`
- Create: `src/shared/markdown/workerClient.ts`
- Test: `src/shared/markdown/workerClient.test.ts`

- [ ] **Step 1: Write failing Worker lifecycle tests**

```ts
// src/shared/markdown/workerClient.test.ts
import { describe, expect, it, vi } from 'vitest'
import { createMarkdownWorkerClient, type WorkerLike } from './workerClient'

class FakeWorker implements WorkerLike {
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: ErrorEvent) => void) | null = null
  posted: unknown[] = []
  terminated = false

  postMessage(message: unknown) {
    this.posted.push(message)
  }

  terminate() {
    this.terminated = true
  }
}

describe('MarkdownWorkerClient', () => {
  it('matches responses by request id', async () => {
    const worker = new FakeWorker()
    const client = createMarkdownWorkerClient({ createWorker: () => worker, timeoutMs: 2_000 })
    const pending = client.render('**hello**', 'light')
    const request = worker.posted[0] as { requestId: number }

    worker.onmessage?.(new MessageEvent('message', {
      data: { type: 'success', requestId: request.requestId, html: '<p>hello</p>' },
    }))

    await expect(pending).resolves.toEqual({ html: '<p>hello</p>', degraded: false })
  })

  it('terminates, recreates, and safely degrades every pending render on timeout', async () => {
    vi.useFakeTimers()
    const workers = [new FakeWorker(), new FakeWorker()]
    const client = createMarkdownWorkerClient({
      createWorker: () => workers.shift()!,
      timeoutMs: 2_000,
    })
    const pending = client.render('<script>alert(1)</script>', 'light')

    await vi.advanceTimersByTimeAsync(2_001)

    await expect(pending).resolves.toMatchObject({
      html: '&lt;script&gt;alert(1)&lt;/script&gt;',
      degraded: true,
    })
    expect(workers.length).toBe(0)
    vi.useRealTimers()
  })

  it('ignores a response for an unknown request id', () => {
    const worker = new FakeWorker()
    const client = createMarkdownWorkerClient({ createWorker: () => worker, timeoutMs: 2_000 })

    expect(() => worker.onmessage?.(new MessageEvent('message', {
      data: { type: 'success', requestId: 999, html: '<p>stale</p>' },
    }))).not.toThrow()
    client.dispose()
  })
})
```

- [ ] **Step 2: Verify Worker tests fail**

Run: `npm run test:run -- src/shared/markdown/workerClient.test.ts`

Expected: FAIL because the Worker client does not exist.

- [ ] **Step 3: Implement escaped fallback, Worker handler, and shared client**

```ts
// src/shared/markdown/escapeHtml.ts
export function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}
```

`markdown.worker.ts` must contain no Vue or DOM imports:

```ts
import { renderMarkdownToHtml } from './pipeline'
import type { MarkdownRenderRequest, MarkdownRenderResponse } from './types'

self.onmessage = async (event: MessageEvent<MarkdownRenderRequest>) => {
  const request = event.data
  if (request.type !== 'render') return

  let response: MarkdownRenderResponse
  try {
    response = {
      type: 'success',
      requestId: request.requestId,
      html: await renderMarkdownToHtml(request.markdown, request.theme),
    }
  } catch (error) {
    response = {
      type: 'error',
      requestId: request.requestId,
      message: error instanceof Error ? error.message : 'Markdown rendering failed',
    }
  }
  self.postMessage(response)
}
```

`workerClient.ts` must export:

```ts
export interface WorkerLike {
  onmessage: ((event: MessageEvent<MarkdownRenderResponse>) => void) | null
  onerror: ((event: ErrorEvent) => void) | null
  postMessage(message: MarkdownRenderRequest): void
  terminate(): void
}

export interface MarkdownWorkerClient {
  render(markdown: string, theme: MarkdownTheme): Promise<MarkdownRenderResult>
  dispose(): void
}

export function createMarkdownWorkerClient(options: {
  createWorker: () => WorkerLike
  timeoutMs: number
}): MarkdownWorkerClient
```

On timeout or `onerror`, it must resolve every pending item with `escapeHtml(originalMarkdown)`,
clear every timer, terminate the failed Worker, and eagerly create a replacement. Production code
must create one module-level client with:

```ts
new Worker('./markdown.worker.ts', { type: 'module' })
```

and export:

```ts
export function renderMarkdown(
  markdown: string,
  theme: MarkdownTheme,
): Promise<MarkdownRenderResult>
```

- [ ] **Step 4: Run Worker and pipeline tests**

Run: `npm run test:run -- src/shared/markdown`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/shared/markdown/escapeHtml.ts src/shared/markdown/markdown.worker.ts src/shared/markdown/workerClient.ts src/shared/markdown/workerClient.test.ts
git commit -m "feat: isolate markdown rendering in worker"
```

## Task 5: Build the only public Markdown component

**Files:**
- Create: `src/shared/ui/MarkdownRenderer.vue`
- Create: `src/shared/ui/MarkdownRenderer.test.ts`
- Create: `src/shared/styles/markdown.css`
- Modify: `src/main.ts`

- [ ] **Step 1: Write failing component tests**

```ts
// src/shared/ui/MarkdownRenderer.test.ts
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MarkdownRenderer from './MarkdownRenderer.vue'
import { renderMarkdown } from '@/shared/markdown/workerClient'

vi.mock('@/shared/markdown/workerClient', () => ({
  renderMarkdown: vi.fn(),
}))

const mockedRender = vi.mocked(renderMarkdown)

describe('MarkdownRenderer', () => {
  beforeEach(() => {
    mockedRender.mockResolvedValue({ html: '<p>rendered</p>', degraded: false })
  })

  it('applies only the newest async result', async () => {
    let resolveOld!: (value: { html: string; degraded: boolean }) => void
    mockedRender
      .mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve }))
      .mockResolvedValueOnce({ html: '<p>new</p>', degraded: false })
    const wrapper = mount(MarkdownRenderer, { props: { content: 'old' } })

    await wrapper.setProps({ content: 'new' })
    await vi.waitFor(() => expect(wrapper.html()).toContain('new'))
    resolveOld({ html: '<p>old</p>', degraded: false })
    await Promise.resolve()

    expect(wrapper.html()).not.toContain('<p>old</p>')
  })

  it('copies code text without line-number decorations', async () => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    })
    mockedRender.mockResolvedValue({
      html: '<div class="code-block-wrapper"><button class="code-block-copy">复制</button><pre><code>print(1)</code></pre></div>',
      degraded: false,
    })
    const wrapper = mount(MarkdownRenderer, { props: { content: 'code' } })
    await vi.waitFor(() => expect(wrapper.find('.code-block-copy').exists()).toBe(true))

    await wrapper.get('.code-block-copy').trigger('click')

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('print(1)')
  })

  it('marks degraded output without throwing', async () => {
    mockedRender.mockResolvedValue({
      html: '&lt;unsafe&gt;',
      degraded: true,
      error: 'timeout',
    })
    const wrapper = mount(MarkdownRenderer, { props: { content: '<unsafe>' } })

    await vi.waitFor(() => expect(wrapper.attributes('data-degraded')).toBe('true'))
    expect(wrapper.text()).toContain('<unsafe>')
  })
})
```

- [ ] **Step 2: Verify component tests fail**

Run: `npm run test:run -- src/shared/ui/MarkdownRenderer.test.ts`

Expected: FAIL because the component does not exist.

- [ ] **Step 3: Implement the component**

The public API is final:

```ts
const props = withDefaults(defineProps<{
  content: string
  streaming?: boolean
}>(), {
  content: '',
  streaming: false,
})
```

The template must contain the repository's only model-content `v-html`:

```vue
<div
  class="markdown-renderer markdown-body"
  :class="{ 'is-streaming': streaming }"
  :data-degraded="degraded || undefined"
  @click="handleClick"
>
  <div class="markdown-renderer__content" v-html="html"></div>
  <span v-if="streaming" class="markdown-stream-caret" aria-hidden="true"></span>
</div>
```

Implementation requirements:

- finished content renders immediately;
- streaming changes use one 80 ms trailing timer;
- a monotonically increasing local version ignores stale Promise results;
- `onBeforeUnmount` clears the timer and invalidates pending results;
- theme is `dark` when `document.documentElement.classList` contains `dark`;
- a `MutationObserver` rerenders only when that class changes;
- delegated copy finds `.code-block-copy`, then its sibling wrapper's `pre code`;
- copy success changes button text to `已复制` for 1.6 seconds;
- copy failure changes button text to `复制失败`; it must not throw;
- degraded output sets `data-degraded="true"`.

- [ ] **Step 4: Add the single shared stylesheet**

`markdown.css` must define:

- headings, paragraphs, lists, blockquotes, tables, links, images, and horizontal rules;
- inline code separately from fenced code;
- `.code-block-wrapper`, header, language label, copy button, and scrolling;
- `.code-line` with CSS counters and `::before` line numbers;
- Shiki dual-theme variables for normal and `.dark` roots;
- KaTeX display overflow on narrow screens;
- `.markdown-stream-caret`;
- degraded plain-text `white-space: pre-wrap`;
- `prefers-reduced-motion` behavior.

Import exactly once from `src/main.ts`:

```ts
import 'katex/dist/katex.min.css'
import '@/shared/styles/markdown.css'
```

- [ ] **Step 5: Run component and Markdown tests**

Run: `npm run test:run -- src/shared/ui/MarkdownRenderer.test.ts src/shared/markdown`

Expected: PASS.

Run: `npx vue-tsc -b`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/shared/ui/MarkdownRenderer.vue src/shared/ui/MarkdownRenderer.test.ts src/shared/styles/markdown.css src/main.ts
git commit -m "feat: add shared Markdown renderer component"
```

## Task 6: Replace the tutor route rendering path

**Files:**
- Modify: `src/features/chat/components/TutorMessageContent.vue`
- Test: `src/features/chat/components/TutorMessageContent.test.ts`

- [ ] **Step 1: Write a failing thin-adapter test**

```ts
// src/features/chat/components/TutorMessageContent.test.ts
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import TutorMessageContent from './TutorMessageContent.vue'

describe('TutorMessageContent', () => {
  it('passes raw content and streaming state to the shared renderer', () => {
    const wrapper = mount(TutorMessageContent, {
      props: { content: 'A  B\n\n$x$', isStreaming: true },
      global: {
        stubs: {
          MarkdownRenderer: {
            props: ['content', 'streaming'],
            template: '<output :data-content="content" :data-streaming="streaming" />',
          },
        },
      },
    })

    expect(wrapper.get('output').attributes('data-content')).toBe('A  B\n\n$x$')
    expect(wrapper.get('output').attributes('data-streaming')).toBe('true')
  })
})
```

- [ ] **Step 2: Verify the test fails**

Run: `npm run test:run -- src/features/chat/components/TutorMessageContent.test.ts`

Expected: FAIL because the component still preprocesses and synchronously renders content.

- [ ] **Step 3: Replace the component with a thin adapter**

```vue
<template>
  <div class="tutor-message-content">
    <MarkdownRenderer :content="content" :streaming="isStreaming" />
  </div>
</template>

<script setup lang="ts">
import MarkdownRenderer from '@/shared/ui/MarkdownRenderer.vue'

withDefaults(defineProps<{
  content: string
  isStreaming?: boolean
}>(), {
  content: '',
  isStreaming: false,
})
</script>
```

Keep only tutor-layout styles. Delete table repair, synchronous rendering, caret DOM mutation, timers,
copy handling, and old Markdown utility imports.

- [ ] **Step 4: Run tutor and freeze regression tests**

Run: `npm run test:run -- src/features/chat/components/TutorMessageContent.test.ts src/shared/markdown/pipeline.test.ts`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/features/chat/components/TutorMessageContent.vue src/features/chat/components/TutorMessageContent.test.ts
git commit -m "fix: move tutor Markdown off the main thread"
```

## Task 7: Replace resource Markdown and code rendering

**Files:**
- Modify: `src/features/resource/components/CodeView.vue`
- Modify: `src/features/resource/components/MarkdownView.vue`
- Modify: `src/features/resource/components/QuizView.vue`
- Test: `src/features/resource/components/MarkdownConsumers.test.ts`

- [ ] **Step 1: Write failing resource-consumer tests**

Mount each component with `MarkdownRenderer` stubbed and assert:

```ts
expect(markdownRenderer.attributes('data-content')).toBe(originalMarkdown)
expect(wrapper.find('.hljs').exists()).toBe(false)
```

For pure code input, assert the exact Markdown passed to the renderer:

```ts
expect(markdownRenderer.attributes('data-content')).toBe(
  '```python\nprint("$5")\n```',
)
```

For a quiz, assert each stem, option, answer, and explanation creates a `MarkdownRenderer` instance,
and no rendered child receives transformed HTML.

- [ ] **Step 2: Verify tests fail**

Run: `npm run test:run -- src/features/resource/components/MarkdownConsumers.test.ts`

Expected: FAIL because the components still use `MarkdownPreview`, Highlight.js, and `v-html`.

- [ ] **Step 3: Migrate all three components**

- Replace every `MarkdownPreview` with `MarkdownRenderer`.
- Replace Quiz `v-html` nodes with `<MarkdownRenderer :content="String(value || '')" />`.
- In `CodeView.vue`, retain data-shape extraction only.
- Convert pure code to a Markdown fence with:

```ts
const pureCodeMarkdown = computed(() => {
  if (!pureCode.value) return ''
  return `\`\`\`${pureLanguage.value}\n${pureCode.value}\n\`\`\``
})
```

- Delete Highlight.js imports, `nextTick` highlighting, code click handling, duplicate language aliases,
  and duplicate copy behavior.
- Delete Markdown/code prose styles now owned by `markdown.css`; keep resource-card layout styles.

- [ ] **Step 4: Run resource tests and type checking**

Run: `npm run test:run -- src/features/resource/components/MarkdownConsumers.test.ts`

Expected: PASS.

Run: `npx vue-tsc -b`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/features/resource/components/CodeView.vue src/features/resource/components/MarkdownView.vue src/features/resource/components/QuizView.vue src/features/resource/components/MarkdownConsumers.test.ts
git commit -m "refactor: unify resource Markdown rendering"
```

## Task 8: Remove question-bank inline parsers

**Files:**
- Modify: `src/features/question-bank/views/QuestionBank.vue`
- Modify: `src/features/question-bank/components/ExamTab.vue`
- Modify: `src/features/question-bank/components/WrongBookTab.vue`
- Modify: `src/features/question-bank/components/SearchTab.vue`
- Modify: `src/features/question-bank/components/DailyPracticeTab.vue`
- Test: `src/features/question-bank/components/MarkdownUsage.test.ts`

- [ ] **Step 1: Write a failing source-boundary test**

```ts
// src/features/question-bank/components/MarkdownUsage.test.ts
import { readFile } from 'node:fs/promises'
import { describe, expect, it } from 'vitest'

const files = [
  '../views/QuestionBank.vue',
  './ExamTab.vue',
  './WrongBookTab.vue',
  './SearchTab.vue',
  './DailyPracticeTab.vue',
]

describe('question bank Markdown usage', () => {
  it.each(files)('%s uses only MarkdownRenderer', async (relativePath) => {
    const source = await readFile(new URL(relativePath, import.meta.url), 'utf8')
    expect(source).toContain('MarkdownRenderer')
    expect(source).not.toContain('v-html')
    expect(source).not.toContain('renderInline')
  })
})
```

- [ ] **Step 2: Verify the boundary test fails**

Run: `npm run test:run -- src/features/question-bank/components/MarkdownUsage.test.ts`

Expected: FAIL for all five files.

- [ ] **Step 3: Replace every inline parser use**

For block content:

```vue
<MarkdownRenderer :content="question.content || ''" />
```

For option text, replace the inline `span` with:

```vue
<div class="option-text">
  <MarkdownRenderer :content="String(text || '')" />
</div>
```

Import `MarkdownRenderer` in all five files. Delete each `renderInline` function and every model-content
`v-html`. Preserve selection, answer, timer, and navigation behavior.

- [ ] **Step 4: Run question-bank tests and type checking**

Run: `npm run test:run -- src/features/question-bank/components/MarkdownUsage.test.ts`

Expected: PASS.

Run: `npx vue-tsc -b`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/features/question-bank/views/QuestionBank.vue src/features/question-bank/components/ExamTab.vue src/features/question-bank/components/WrongBookTab.vue src/features/question-bank/components/SearchTab.vue src/features/question-bank/components/DailyPracticeTab.vue src/features/question-bank/components/MarkdownUsage.test.ts
git commit -m "refactor: unify question bank Markdown rendering"
```

## Task 9: Enforce one backend AI output contract

**Files:**
- Create: `server/app/infra/prompt_contracts/markdown_output.md`
- Create: `server/app/infra/markdown_output.py`
- Modify: `server/app/infra/prompts.py`
- Modify: `server/app/chat/agent/nodes.py`
- Modify: `server/app/chat/memory/compression.py`
- Modify: `server/app/resource/agents/content.py`
- Modify: `server/app/resource/agents/code.py`
- Modify: `server/app/resource/agents/mindmap.py`
- Modify: `server/app/path/workflows.py`
- Test: `server/tests/infra/test_markdown_output_contract.py`

- [ ] **Step 1: Write failing contract tests**

```py
# server/tests/infra/test_markdown_output_contract.py
from pathlib import Path

from app.infra.markdown_output import with_markdown_output_contract
from app.infra.prompts import prompts


def test_shared_markdown_contract_is_registered() -> None:
    contract = prompts.get("shared").get("markdown_output")
    assert "```language" in contract
    assert "$$" in contract
    assert "原始 HTML" in contract


def test_contract_is_appended_once() -> None:
    rendered = with_markdown_output_contract("业务规则")
    assert rendered.startswith("业务规则")
    assert rendered.count("# 统一 Markdown 输出规范") == 1
    assert with_markdown_output_contract(rendered) == rendered


def test_direct_markdown_producers_use_shared_helper() -> None:
    app_dir = Path(__file__).resolve().parents[2] / "app"
    files = [
        app_dir / "chat" / "agent" / "nodes.py",
        app_dir / "chat" / "memory" / "compression.py",
        app_dir / "resource" / "agents" / "content.py",
        app_dir / "resource" / "agents" / "code.py",
        app_dir / "resource" / "agents" / "mindmap.py",
        app_dir / "path" / "workflows.py",
    ]
    for path in files:
        source = path.read_text(encoding="utf-8")
        assert "with_markdown_output_contract" in source, path


def test_legacy_markdown_cleanup_is_removed() -> None:
    resource_agents = Path(__file__).resolve().parents[2] / "app" / "resource" / "agents"
    assert "_clean_markdown_fences" not in (resource_agents / "content.py").read_text()
    assert "_clean_markdown" not in (resource_agents / "mindmap.py").read_text()
```

- [ ] **Step 2: Verify tests fail**

Run: `cd server && uv run pytest tests/infra/test_markdown_output_contract.py -q`

Expected: FAIL because the shared module and registration do not exist.

- [ ] **Step 3: Add the contract and helper**

```markdown
<!-- server/app/infra/prompt_contracts/markdown_output.md -->
# 统一 Markdown 输出规范

- 仅输出 CommonMark + GFM，不使用原始 HTML。
- 行内代码使用单反引号。
- 多行代码必须使用围栏代码块，并把真实语言写在开头，例如 ` ```language `；
  不确定语言时使用 `text`，不得省略语言。
- 行内公式只使用 `$...$`，块公式的开始和结束 `$$` 必须分别独占一行。
- 普通美元符号写作 `\$`。
- 不要用一个额外的 Markdown 围栏包住整篇回答。
- 最终输出必须闭合所有代码围栏和块公式分隔符。
```

Register:

```py
prompts.register("shared", _APP_DIR / "infra" / "prompt_contracts")
```

Create:

```py
# server/app/infra/markdown_output.py
from app.infra.prompts import prompts

_MARKER = "# 统一 Markdown 输出规范"


def with_markdown_output_contract(prompt: str) -> str:
    if _MARKER in prompt:
        return prompt
    contract = prompts.get("shared").get("markdown_output").strip()
    return f"{prompt.rstrip()}\n\n{contract}"
```

- [ ] **Step 4: Apply it only to direct Markdown responses**

Import `with_markdown_output_contract` in the six producer files.

- Tutor: wrap the completed `tutor_system` prompt before date/evidence additions.
- Compression: wrap the compression system prompt before invoking the LLM.
- Content and code agents: wrap their resource system prompt before concatenating input.
- Mindmap: wrap its prompt; keep stricter Markmap structure rules after the shared contract.
- Path: wrap only `NodeLearningAgent.generate_tutorial`; do not change JSON planner or question prompts.

Remove `_clean_markdown_fences` and `_clean_markdown` plus their call sites. Do not change any database
model, API response schema, resource record, path record, or persistence service.

- [ ] **Step 5: Run focused backend tests**

Run: `cd server && uv run pytest tests/infra/test_markdown_output_contract.py -q`

Expected: PASS.

Run: `cd server && uv run pytest tests/chat/ tests/path/ tests/resource/ -q --ignore=tests/chat/test_agent_single_module_refactor.py --ignore=tests/chat/test_onboarding_api.py --ignore=tests/chat/test_reasoning_agent.py`

Expected: PASS, excluding the three documented pre-existing failures.

- [ ] **Step 6: Commit**

```bash
git add server/app/infra/prompt_contracts/markdown_output.md server/app/infra/markdown_output.py server/app/infra/prompts.py server/app/chat/agent/nodes.py server/app/chat/memory/compression.py server/app/resource/agents/content.py server/app/resource/agents/code.py server/app/resource/agents/mindmap.py server/app/path/workflows.py server/tests/infra/test_markdown_output_contract.py
git commit -m "feat: standardize AI Markdown output"
```

## Task 10: Delete the legacy renderer and close every bypass

**Files:**
- Delete: `src/shared/utils/markdown.ts`
- Delete: `src/shared/ui/MarkdownPreview.vue`
- Delete: `src/shims-markdown-it-katex.d.ts`
- Modify: `vite.config.ts`
- Modify: `package.json`
- Modify: `package-lock.json`
- Create: `src/shared/markdown/architecture.test.ts`

- [ ] **Step 1: Write a failing repository-boundary test**

```ts
// src/shared/markdown/architecture.test.ts
import { readdir, readFile } from 'node:fs/promises'
import { extname, join, relative } from 'node:path'
import { describe, expect, it } from 'vitest'

async function sourceFiles(root: string): Promise<string[]> {
  const entries = await readdir(root, { withFileTypes: true })
  const nested = await Promise.all(entries.map(async (entry) => {
    const path = join(root, entry.name)
    if (entry.isDirectory()) return sourceFiles(path)
    return ['.ts', '.vue'].includes(extname(path)) ? [path] : []
  }))
  return nested.flat()
}

describe('Markdown architecture boundary', () => {
  it('has one renderer and no legacy parser or business v-html bypass', async () => {
    const root = new URL('../../..', import.meta.url).pathname
    const files = await sourceFiles(root)
    const violations: string[] = []

    for (const path of files) {
      if (path.endsWith('.test.ts')) continue
      const source = await readFile(path, 'utf8')
      const isRenderer = path.endsWith('/shared/ui/MarkdownRenderer.vue')
      if (/markdown-it|highlight\.js|shared\/utils\/markdown|MarkdownPreview/.test(source)) {
        violations.push(`${relative(root, path)} imports a legacy renderer`)
      }
      if (!isRenderer && source.includes('v-html')) {
        violations.push(`${relative(root, path)} uses v-html outside MarkdownRenderer`)
      }
      if (!path.includes('/shared/markdown/') && /remark-|rehype-|shiki/.test(source)) {
        violations.push(`${relative(root, path)} bypasses the shared Markdown boundary`)
      }
    }

    expect(violations).toEqual([])
  })
})
```

- [ ] **Step 2: Verify the architecture test fails**

Run: `npm run test:run -- src/shared/markdown/architecture.test.ts`

Expected: FAIL listing the old renderer, old preview, or remaining bypasses.

- [ ] **Step 3: Delete old code and clean build configuration**

Delete the three legacy files. Confirm `package.json` contains none of:

```text
highlight.js
markdown-it
markdown-it-katex
@types/markdown-it
```

In `vite.config.ts`, replace the old renderer chunk condition with:

```ts
if (
  id.includes('shiki') ||
  id.includes('@shikijs') ||
  id.includes('katex') ||
  id.includes('remark-') ||
  id.includes('rehype-') ||
  id.includes('unified')
) {
  return 'vendor-renderers'
}
```

Search and remove orphaned `.hljs`, duplicate `.shiki`, duplicate KaTeX, copy-button, and
`.markdown-body` definitions outside `src/shared/styles/markdown.css`.

- [ ] **Step 4: Run the complete frontend suite**

Run: `npm run test:run`

Expected: PASS.

Run: `npm run build`

Expected: PASS.

Run:

```bash
rg -n "markdown-it|highlight\\.js|shared/utils/markdown|MarkdownPreview|renderInline|renderQuizHtml" src package.json vite.config.ts
```

Expected: no matches.

- [ ] **Step 5: Commit**

```bash
git add -A src package.json package-lock.json vite.config.ts
git commit -m "refactor: remove legacy Markdown renderer"
```

## Task 11: Verify the route-freeze fix in a real browser

**Files:**
- No file changes expected.

- [ ] **Step 1: Start backend and frontend**

Run in terminal 1:

```bash
cd server
uv run fastapi dev app/main.py --port 9999
```

Run in terminal 2:

```bash
npm run dev
```

Expected: backend on `127.0.0.1:9999`, frontend on `127.0.0.1:5173`.

- [ ] **Step 2: Exercise the original route transition**

Using the in-app browser:

1. Open the application and authenticate with the available local test account.
2. Open any non-tutor route.
3. Click the navigation item “智能辅导”.
4. Let the current historical session load.
5. Repeat the route transition five times.

Expected:

- navigation responds immediately every time;
- session list remains clickable;
- a historical message containing mixed `$...$`, `$$...$$`, and code renders;
- main-thread long tasks do not show a sustained 100% CPU loop.

- [ ] **Step 3: Exercise teaching-code behavior**

Submit a tutor prompt requesting Python, C++, Java, JavaScript, TypeScript, Vue, HTML, CSS, SQL,
Bash, Go, Rust, JSON, and YAML snippets plus one formula.

Expected:

- each supported language is highlighted;
- language label, line numbers, horizontal scroll, and copy work;
- copied text contains source code but not line numbers;
- `$` inside code stays code;
- light/dark theme remains readable.

- [ ] **Step 4: Exercise failure boundaries**

In browser devtools, pause or terminate the Markdown Worker during a render.

Expected:

- after 2 seconds the message becomes escaped plain text;
- navigation and other controls remain responsive;
- the next message uses a recreated Worker and renders normally.

- [ ] **Step 5: Run final automated verification**

Run:

```bash
npm run test:run
npm run build
cd server
uv run pytest tests/infra/test_markdown_output_contract.py -q
```

Expected: all commands PASS.

- [ ] **Step 6: Record the verification result**

Do not create an empty commit. If any check fails, return to the task that owns the failing behavior,
add a focused failing regression test there, implement the minimal fix, rerun Task 11 from Step 2,
and use that owning task's explicit commit file list and message.

## Final acceptance checklist

- [ ] The historical tutor fixture completes without main-thread parsing.
- [ ] `MarkdownRenderer.vue` is the only model-content `v-html` owner.
- [ ] No business component imports Unified, Rehype, KaTeX, or Shiki.
- [ ] No legacy Markdown-It, Highlight.js, repair regex, or preview component remains.
- [ ] All 15 approved teaching languages highlight; unknown and huge blocks remain complete plain text.
- [ ] Math renders outside code and never inside code.
- [ ] Raw HTML and dangerous URL protocols cannot become executable DOM.
- [ ] Timeout, Worker crash, stale result, streaming, unmount, and theme change tests pass.
- [ ] Chat, resource, path, and question-bank UI all use the same component.
- [ ] Direct AI Markdown producers use one contract.
- [ ] `resource` and `path` records, schemas, detail pages, and persistence remain separate.
- [ ] Frontend tests, frontend build, focused backend tests, and browser route regression pass.
