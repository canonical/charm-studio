import { useCallback, useEffect, useRef, useState } from 'react'
import { getPipelineStatus } from '../api/client'
import type { PipelineStatus } from '../types'

export function usePipelineStatus(pipelineId: string | null) {
  const [status, setStatus] = useState<PipelineStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!pipelineId) {
      setStatus(null)
      setError(null)
      stopPolling()
      return
    }

    const poll = async () => {
      try {
        const s = await getPipelineStatus(pipelineId)
        setStatus(s)
        if (s.done) stopPolling()
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err))
      }
    }

    void poll()
    intervalRef.current = setInterval(poll, 2000)

    return stopPolling
  }, [pipelineId, stopPolling])

  return { status, error, stopPolling }
}
