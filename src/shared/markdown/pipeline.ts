import githubDark from '@shikijs/themes/github-dark'
import githubLight from '@shikijs/themes/github-light'
import rehypeShikiFromHighlighter from '@shikijs/rehype/core'
import type { Element, Root } from 'hast'
import rehypeKatex from 'rehype-katex'
import rehypeSanitize from 'rehype-sanitize'
import rehypeStringify from 'rehype-stringify'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import remarkParse from 'remark-parse'
import remarkRehype from 'remark-rehype'
import { createHighlighterCore, type HighlighterCore } from 'shiki/core'
import { createJavaScriptRegexEngine } from 'shiki/engine/javascript'
import { unified, type Plugin } from 'unified'
import { visit } from 'unist-util-visit'

import {
  configureCodeBlockHighlighter,
  rehypeDecorateCodeBlocks,
  rehypePrepareCodeBlocks,
} from './codeBlocks'
import { markdownSanitizeSchema } from './schema'
import type { MarkdownTheme } from './types'

// Markdown 渲染管道：统一 remark → rehype → Shiki 高亮 → 净化 → HTML

let highlighterPromise: Promise<HighlighterCore> | undefined

function getHighlighter(): Promise<HighlighterCore> {
  highlighterPromise ??= createHighlighterCore({
    themes: [githubLight, githubDark],
    langs: [],
    engine: createJavaScriptRegexEngine(),
  })

  return highlighterPromise
}

function rehypeExternalLinkPolicy(): (tree: Root) => void {
  return tree => {
    visit(tree, 'element', node => {
      if (node.tagName !== 'a' || typeof node.properties.href !== 'string') {
        return
      }

      if (!/^https?:\/\//i.test(node.properties.href)) {
        return
      }

      let url: URL
      try {
        url = new URL(node.properties.href)
      } catch {
        return
      }

      if (url.protocol !== 'http:' && url.protocol !== 'https:') {
        return
      }

      node.properties.target = '_blank'
      node.properties.rel = ['noopener', 'noreferrer']
    })
  }
}

const rehypeSafeMarkdown: Plugin<[], Root> = () => (
  rehypeSanitize(markdownSanitizeSchema)
)

const rehypeRenderMath: Plugin<[], Root> = () => (
  rehypeKatex({ strict: 'ignore' })
)

export async function renderMarkdownToHtml(
  markdown: string,
  theme: MarkdownTheme,
): Promise<string> {
  const highlighter = await getHighlighter()
  configureCodeBlockHighlighter(highlighter)

  const processor = unified()
    .use(remarkParse)
    .use(remarkGfm)
    .use(remarkMath)
    .use(remarkRehype)
    .use(rehypeSafeMarkdown)
    .use(rehypeRenderMath)
    .use(rehypePrepareCodeBlocks)
    .use(() => rehypeShikiFromHighlighter(
      highlighter as unknown as Parameters<typeof rehypeShikiFromHighlighter>[0],
      {
        themes: { light: 'github-light', dark: 'github-dark' },
        defaultColor: theme,
        fallbackLanguage: 'text',
        transformers: [{
          name: 'markdown-code-metadata',
          pre(node: Element) {
            node.properties.dataLanguage = this.options.lang
            node.properties.dataTheme = theme
          },
        }],
      },
    ))
    .use(rehypeDecorateCodeBlocks)
    .use(rehypeExternalLinkPolicy)
    .use(rehypeStringify)

  return String(await processor.process(markdown))
}
