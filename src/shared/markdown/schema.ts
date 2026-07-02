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
  },
}
