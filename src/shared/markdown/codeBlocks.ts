import type { Element, ElementContent, Root } from 'hast'
import type { HighlighterCore } from 'shiki/core'
import { toString } from 'hast-util-to-string'
import { visit } from 'unist-util-visit'

import { languageLoaders, normalizeLanguage, shouldHighlight } from './languages'

// 代码块高亮模块：解析代码语言、加载语法高亮、为代码块添加头部和行标签

let highlighter: HighlighterCore | undefined
const languagePromises = new Map<string, Promise<void>>()

export function configureCodeBlockHighlighter(value: HighlighterCore): void {
  if (highlighter !== value) {
    highlighter = value
    languagePromises.clear()
  }
}

function loadLanguage(language: string): Promise<void> {
  const existing = languagePromises.get(language)
  if (existing) {
    return existing
  }

  const loader = languageLoaders[language as keyof typeof languageLoaders]
  const promise = loader()
    .then(grammar => highlighter?.loadLanguage(grammar))
    .then(() => undefined)

  languagePromises.set(language, promise)
  return promise
}

function readLanguage(code: Element): string {
  const classes = code.properties.className
  if (!Array.isArray(classes)) {
    return 'text'
  }

  const languageClass = classes.find(
    value => typeof value === 'string' && value.startsWith('language-'),
  )

  return typeof languageClass === 'string'
    ? normalizeLanguage(languageClass.slice('language-'.length))
    : 'text'
}

export function rehypePrepareCodeBlocks(): (tree: Root) => Promise<void> {
  return async tree => {
    const pending: Promise<void>[] = []

    visit(tree, 'element', node => {
      if (node.tagName !== 'pre') {
        return
      }

      const code = node.children[0]
      if (code?.type !== 'element' || code.tagName !== 'code') {
        return
      }

      const requestedLanguage = readLanguage(code)
      const codeText = toString(code)
      const language = shouldHighlight(codeText, requestedLanguage)
        ? requestedLanguage
        : 'text'

      node.properties.dataLanguage = language

      if (language === 'text') {
        code.properties.className = []
        return
      }

      code.properties.className = [`language-${language}`]
      pending.push(loadLanguage(language))
    })

    await Promise.all(pending)
  }
}

function addCodeLineClass(node: Element): void {
  for (const child of node.children) {
    if (child.type !== 'element') {
      continue
    }

    if (child.tagName === 'span') {
      const classValue = child.properties.className ?? child.properties.class
      const classes = Array.isArray(classValue)
        ? classValue
        : typeof classValue === 'string'
          ? classValue.split(/\s+/)
          : []

      if (classes.includes('line') && !classes.includes('code-line')) {
        delete child.properties.class
        child.properties.className = [...classes, 'code-line']
      }
    }

    addCodeLineClass(child)
  }
}

function addPlainCodeLines(code: Element): void {
  const value = toString(code)
  const normalized = value.endsWith('\n') ? value.slice(0, -1) : value
  const lines = normalized.split('\n')

  code.children = lines.flatMap((line, index) => {
    const lineElement = element('span', {
      className: ['line', 'code-line'],
    }, [
      { type: 'text', value: line },
    ])

    return index < lines.length - 1
      ? [lineElement, { type: 'text' as const, value: '\n' }]
      : [lineElement]
  })
}

function element(
  tagName: string,
  properties: Element['properties'],
  children: ElementContent[],
): Element {
  return { type: 'element', tagName, properties, children }
}

export function rehypeDecorateCodeBlocks(): (tree: Root) => void {
  return tree => {
    visit(tree, 'element', (node, index, parent) => {
      if (node.tagName !== 'pre' || index === undefined || !parent) {
        return
      }

      const language = typeof node.properties.dataLanguage === 'string'
        ? node.properties.dataLanguage
        : 'text'

      const code = node.children[0]
      if (
        language === 'text'
        && code?.type === 'element'
        && code.tagName === 'code'
      ) {
        code.properties.className = ['language-text']
        addPlainCodeLines(code)
      }

      addCodeLineClass(node)

      const header = element('div', { className: ['code-block-header'] }, [
        element('span', { className: ['code-block-language'] }, [
          { type: 'text', value: language },
        ]),
        element('button', {
          type: 'button',
          className: ['code-block-copy'],
          ariaLabel: `复制 ${language} 代码`,
        }, [
          { type: 'text', value: '复制' },
        ]),
      ])
      const scroll = element('div', { className: ['code-block-scroll'] }, [node])

      parent.children[index] = element('div', {
        className: ['code-block-wrapper'],
        dataLanguage: language,
      }, [header, scroll])

      return 'skip'
    })
  }
}
