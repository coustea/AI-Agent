export function normalizePageNumber(value: string | number, totalPages: number): number | null {
  const parsed = typeof value === 'number' ? value : Number(value.trim())
  if (!Number.isFinite(parsed) || String(value).trim() === '') return null

  const lastPage = Math.max(1, Math.trunc(totalPages))
  return Math.min(lastPage, Math.max(1, Math.trunc(parsed)))
}
