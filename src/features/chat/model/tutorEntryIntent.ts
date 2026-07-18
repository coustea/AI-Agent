let pendingBlankSession = false

export interface TutorEntryTransition {
  fromPath: string
  toPath: string
  hasResolvedFromRoute: boolean
}

export function recordTutorEntryIntent({
  fromPath,
  toPath,
  hasResolvedFromRoute,
}: TutorEntryTransition): void {
  pendingBlankSession = (
    hasResolvedFromRoute
    && toPath === '/tutor'
    && !fromPath.startsWith('/tutor')
  )
}

export function consumeTutorEntryIntent(): boolean {
  const shouldStartBlank = pendingBlankSession
  pendingBlankSession = false
  return shouldStartBlank
}
