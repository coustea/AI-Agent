import type { Schema } from 'hast-util-sanitize'
import { defaultSchema } from 'rehype-sanitize'

// Markdown 净化白名单：扩展默认 schema 以允许代码块、数学公式和自定义类名

export const markdownSanitizeSchema: Schema = {
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
    // 允许教程元数据横幅等自定义 HTML 块携带 className
    div: [
      ...(defaultSchema.attributes?.div ?? []),
      'className',
    ],
    span: [
      ...(defaultSchema.attributes?.span ?? []),
      'className',
    ],
    strong: [
      ...(defaultSchema.attributes?.strong ?? []),
      'className',
    ],
  },
}
