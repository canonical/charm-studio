import type { HistoryEntry } from '../../types'

interface Props {
  entry: HistoryEntry
  isActive: boolean
  onSelect: (entry: HistoryEntry) => void
}

const STATUS_CLASSES: Record<string, string> = {
  pending: 'p-chip--caution',
  running: 'p-chip--information',
  done: 'p-chip--positive',
  failed: 'p-chip--negative',
  cancelled: '',
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
    <li
      className="p-list__item"
      style={{ cursor: 'pointer', fontWeight: isActive ? 'bold' : 'normal' }}
      onClick={() => onSelect(entry)}
    >
      <span>{entry.label}</span>{' '}
      <span className={`p-chip ${STATUS_CLASSES[entry.status] ?? ''}`} style={{ fontSize: '0.75rem' }}>
        {entry.status}
      </span>
      <br />
      <small style={{ color: '#666' }}>{relativeTime(entry.timestamp)}</small>
    </li>
  )
}
