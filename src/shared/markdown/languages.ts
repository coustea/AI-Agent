import type { LanguageInput } from 'shiki/core'

export const MAX_HIGHLIGHT_CHARS = 50_000
export const MAX_HIGHLIGHT_LINES = 2_000

export const languageLoaders = {
  python: () => import('@shikijs/langs/python').then(module => module.default),
  c: () => import('@shikijs/langs/c').then(module => module.default),
  cpp: () => import('@shikijs/langs/cpp').then(module => module.default),
  java: () => import('@shikijs/langs/java').then(module => module.default),
  javascript: () => import('@shikijs/langs/javascript').then(module => module.default),
  typescript: () => import('@shikijs/langs/typescript').then(module => module.default),
  vue: () => import('@shikijs/langs/vue').then(module => module.default),
  html: () => import('@shikijs/langs/html').then(module => module.default),
  css: () => import('@shikijs/langs/css').then(module => module.default),
  sql: () => import('@shikijs/langs/sql').then(module => module.default),
  bash: () => import('@shikijs/langs/bash').then(module => module.default),
  go: () => import('@shikijs/langs/go').then(module => module.default),
  rust: () => import('@shikijs/langs/rust').then(module => module.default),
  json: () => import('@shikijs/langs/json').then(module => module.default),
  yaml: () => import('@shikijs/langs/yaml').then(module => module.default),
} satisfies Record<string, LanguageInput>

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

export function normalizeLanguage(value: string): string {
  const normalized = value.trim().toLowerCase()
  const canonical = aliases[normalized] ?? normalized

  return Object.prototype.hasOwnProperty.call(languageLoaders, canonical) ? canonical : 'text'
}

export function shouldHighlight(code: string, language: string): boolean {
  if (normalizeLanguage(language) === 'text' || code.length > MAX_HIGHLIGHT_CHARS) {
    return false
  }

  return code.split('\n').length <= MAX_HIGHLIGHT_LINES
}
