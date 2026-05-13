import type { HistoryEntry } from '../../types'

interface Props {
  entry: HistoryEntry
  isActive: boolean
  onSelect: (entry: HistoryEntry) => void
}

const STATUS_CLASS: Record<string, string> = {
  pending: 'status-chip--pending',
  running: 'status-chip--running',
  done: 'status-chip--done',
  failed: 'status-chip--failed',
  cancelled: 'status-chip--cancelled',
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

export function HistoryItem({ entry, isActive, onSelect }: Props) {
  return (
    <div
      className={`history-item${isActive ? ' is-active' : ''}`}
      onClick={() => onSelect(entry)}
    >
      <div className="history-item__top">
        <span className="history-item__label">{entry.label}</span>
        <span className={`status-chip ${STATUS_CLASS[entry.status] ?? ''}`}>
          {entry.status}
        </span>
      </div>
      <span className="history-item__time">{relativeTime(entry.timestamp)}</span>
    </div>
  )
}
