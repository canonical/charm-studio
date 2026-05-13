import { useState } from 'react'
import type { HistoryEntry } from '../../types'
import { HistoryList } from './HistoryList'

interface Props {
  history: HistoryEntry[]
  activePipelineId: string | null
  onNewImport: () => void
  onSelect: (entry: HistoryEntry) => void
}

export function Sidebar({ history, activePipelineId, onNewImport, onSelect }: Props) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside className={`l-aside${collapsed ? ' is-collapsed' : ''}`}>
      <div className="sidebar__toggle">
        <button
          className="p-button--base sidebar__toggle-btn"
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? '›' : '‹'}
        </button>
      </div>
      {!collapsed && (
        <>
          <div className="sidebar__new-import">
            <button className="p-button u-no-margin--bottom" onClick={onNewImport}>
              New import
            </button>
          </div>
          <HistoryList history={history} activePipelineId={activePipelineId} onSelect={onSelect} />
        </>
      )}
    </aside>
  )
}
