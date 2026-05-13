import { useState } from 'react'
import NavigationBar from './components/NavigationBar'
import { Sidebar } from './components/Sidebar/Sidebar'
import { ImportView } from './components/ImportView/ImportView'
import { PipelineView } from './components/PipelineView/PipelineView'
import { useHistory } from './hooks/useHistory'
import type { HistoryEntry } from './types'

export default function App() {
  const [activePipelineId, setActivePipelineId] = useState<string | null>(null)
  const { history, addEntry, updateStatus } = useHistory()

  function handlePipelineStarted(pipelineId: string, label: string) {
    const entry: HistoryEntry = {
      pipeline_id: pipelineId,
      label,
      timestamp: new Date().toISOString(),
      status: 'pending',
    }
    addEntry(entry)
    setActivePipelineId(pipelineId)
  }

  function handleNewImport() {
    setActivePipelineId(null)
  }

  function handleHistorySelect(entry: HistoryEntry) {
    setActivePipelineId(entry.pipeline_id)
  }

  return (
    <>
      <NavigationBar />
      <div className="l-application">
        <Sidebar
          history={history}
          onNewImport={handleNewImport}
          onSelect={handleHistorySelect}
          activePipelineId={activePipelineId}
        />
        <main className="l-main">
          {activePipelineId === null ? (
            <ImportView onPipelineStarted={handlePipelineStarted} />
          ) : (
            <PipelineView
              pipelineId={activePipelineId}
              onStatusChange={(pid, status) => updateStatus(pid, status)}
            />
          )}
        </main>
      </div>
    </>
  )
}
