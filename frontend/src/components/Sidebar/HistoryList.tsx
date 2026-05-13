import type { HistoryEntry } from '../../types'
import { HistoryItem } from './HistoryItem'

interface Props {
  history: HistoryEntry[]
  activePipelineId: string | null
  onSelect: (entry: HistoryEntry) => void
}

export function HistoryList({ history, activePipelineId, onSelect }: Props) {
  if (history.length === 0) {
    return <p style={{ padding: '1rem', color: '#666', fontSize: '14px' }}>No history yet.</p>
  }
  return (
    <div>
      {history.map(entry => (
        <HistoryItem
          key={entry.pipeline_id}
          entry={entry}
          isActive={entry.pipeline_id === activePipelineId}
          onSelect={onSelect}
        />
      ))}
    </div>
  )
}
