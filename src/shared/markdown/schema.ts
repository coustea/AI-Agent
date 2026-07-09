import type { Schema } from 'hast-util-sanitize'
import { defaultSchema } from 'rehype-sanitize'

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
