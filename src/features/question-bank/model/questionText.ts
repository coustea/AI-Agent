export function summarizeQuestionText(text: string, maxLength?: number): string {
  const summary = String(text || '').replace(/\s+/g, ' ').trim()
  if (!maxLength || summary.length <= maxLength) return summary
  return `${summary.slice(0, maxLength)}...`
}
