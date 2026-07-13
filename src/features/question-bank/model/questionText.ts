export function summarizeQuestionText(text: string | null | undefined, maxLength?: number) {
  const summary = String(text || '')
    .replace(/\s+/g, ' ')
    .replace(/[#*_`>-]/g, '')
    .trim()

  if (maxLength === undefined || summary.length <= maxLength) return summary
  return `${summary.slice(0, maxLength)}...`
}
