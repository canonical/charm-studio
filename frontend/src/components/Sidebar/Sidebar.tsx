import type { HistoryEntry } from '../../types'
import { HistoryList } from './HistoryList'

interface Props {
  history: HistoryEntry[]
  activePipelineId: string | null
  collapsed: boolean
  onSelect: (entry: HistoryEntry) => void
}

export function Sidebar({ history, activePipelineId, collapsed, onSelect }: Props) {
  if (collapsed) return null

  return (
    <aside className="app-sidebar">
      <HistoryList history={history} activePipelineId={activePipelineId} onSelect={onSelect} />
    </aside>
  )
}
