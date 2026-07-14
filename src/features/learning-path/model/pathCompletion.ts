export const PATH_COMPLETION_HOLD_MS = 300

interface PathCompletionTransition {
  markComplete: () => void
  waitForRender: () => Promise<unknown>
  wait: (ms: number) => Promise<unknown>
  navigate: () => Promise<unknown>
}

interface PathTerminalEventHandlers {
  onCompleted: () => void
  onFailed: (error: Error) => void
}

interface PathTerminalEventWaitOptions {
  timeoutMs: number
  start: (handlers: PathTerminalEventHandlers) => void
  onCompleted: () => Promise<void>
  onFailed: (error: Error) => void
  onTimeout: () => void
  signal?: AbortSignal
}

export async function runPathCompletionTransition(
  options: PathCompletionTransition,
): Promise<void> {
  options.markComplete()
  await options.waitForRender()
  await options.wait(PATH_COMPLETION_HOLD_MS)
  await options.navigate()
}

export function waitForPathTerminalEvent(
  options: PathTerminalEventWaitOptions,
): Promise<void> {
  return new Promise((resolve, reject) => {
    let settled = false
    let timeoutId: ReturnType<typeof setTimeout> | undefined

    const cleanup = () => {
      if (timeoutId !== undefined) {
        clearTimeout(timeoutId)
      }
      options.signal?.removeEventListener('abort', handleAbort)
    }

    const handleAbort = () => {
      if (settled) return
      settled = true
      cleanup()
      resolve()
    }

    const handleCompleted = () => {
      if (settled) return
      settled = true
      cleanup()
      void options.onCompleted().then(resolve, reject)
    }

    const handleFailed = (error: Error) => {
      if (settled) return
      settled = true
      cleanup()

      try {
        options.onFailed(error)
        resolve()
      } catch (failureHandlerError) {
        reject(failureHandlerError)
      }
    }

    if (options.signal?.aborted) {
      resolve()
      return
    }

    options.signal?.addEventListener('abort', handleAbort, {
      once: true,
    })

    timeoutId = setTimeout(() => {
      if (settled) return
      settled = true
      cleanup()
      options.onTimeout()
      reject(
        new Error(
          '路径规划等待超时，请稍后前往历史路径查看生成结果。',
        ),
      )
    }, options.timeoutMs)

    try {
      options.start({
        onCompleted: handleCompleted,
        onFailed: handleFailed,
      })
    } catch (error) {
      settled = true
      cleanup()
      reject(error)
    }
  })
}
