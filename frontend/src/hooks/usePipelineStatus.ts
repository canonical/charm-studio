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

    // Reset state when switching pipelines
    setStatus(null)
    setError(null)

    let cancelled = false

    const poll = async () => {
      try {
        const s = await getPipelineStatus(pipelineId)
        if (cancelled) return
        setStatus(s)
        setError(null)
        if (s.done) stopPolling()
      } catch (err) {
        if (cancelled) return
        const msg = err instanceof Error ? err.message : String(err)
        // 404 means the worker hasn't written status yet — keep loading
        if (msg.includes('404')) return
        setError(msg)
      }
    }

    void poll()
    intervalRef.current = setInterval(poll, 2000)

    return () => {
      cancelled = true
      stopPolling()
    }
  }, [pipelineId, stopPolling])

  return { status, error, stopPolling }
}
