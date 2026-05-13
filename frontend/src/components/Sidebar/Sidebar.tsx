import type { HistoryEntry } from '../../types'
import { HistoryList } from './HistoryList'

interface Props {
  history: HistoryEntry[]
  activePipelineId: string | null
  onNewImport: () => void
  onSelect: (entry: HistoryEntry) => void
}

export function Sidebar({ history, activePipelineId, onNewImport, onSelect }: Props) {
  return (
    <aside className="l-aside">
      <div style={{ padding: '1rem' }}>
        <button className="p-button--positive u-no-margin--bottom" onClick={onNewImport}>
          New import
        </button>
      </div>
      <HistoryList history={history} activePipelineId={activePipelineId} onSelect={onSelect} />
    </aside>
  )
}
