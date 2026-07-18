export type TutorChatMode = 'standard' | 'digital_human'

export interface TutorModeSessionIds {
  standard?: string
  digitalHuman?: string
}

export function selectSessionForMode(
  mode: TutorChatMode,
  sessionId: string,
  current: TutorModeSessionIds,
): TutorModeSessionIds {
  if (mode === 'digital_human') {
    return { ...current, digitalHuman: sessionId }
  }
  return { ...current, standard: sessionId }
}
