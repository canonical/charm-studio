import type { HistoryEntry } from '../../types'
import { HistoryList } from './HistoryList'

interface Props {
  history: HistoryEntry[]
  activePipelineId: string | null
  collapsed: boolean
  onNewImport: () => void
  onSelect: (entry: HistoryEntry) => void
}

export function Sidebar({ history, activePipelineId, collapsed, onNewImport, onSelect }: Props) {
  if (collapsed) return null

  return (
    <aside className="app-sidebar">
      <div className="sidebar__new-import">
        <button className="p-button u-no-margin--bottom" onClick={onNewImport}>
          New import
        </button>
      </div>
      <HistoryList history={history} activePipelineId={activePipelineId} onSelect={onSelect} />
    </aside>
  )
}
