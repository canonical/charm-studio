import { useCallback, useState } from 'react'
import type { HistoryEntry, HistoryStatus } from '../types'

const STORAGE_KEY = 'cs_history'
const MAX_ENTRIES = 20

function readHistory(): HistoryEntry[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]') as HistoryEntry[]
  } catch {
    return []
  }
}

function writeHistory(entries: HistoryEntry[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries))
}

export function useHistory() {
  const [history, setHistory] = useState<HistoryEntry[]>(readHistory)

  const addEntry = useCallback((entry: HistoryEntry) => {
    setHistory(prev => {
      const updated = [entry, ...prev.filter(e => e.pipeline_id !== entry.pipeline_id)]
        .slice(0, MAX_ENTRIES)
      writeHistory(updated)
      return updated
    })
  }, [])

  const updateStatus = useCallback((pipelineId: string, status: HistoryStatus) => {
    setHistory(prev => {
      const updated = prev.map(e =>
        e.pipeline_id === pipelineId ? { ...e, status } : e
      )
      writeHistory(updated)
      return updated
    })
  }, [])

  return { history, addEntry, updateStatus }
}
