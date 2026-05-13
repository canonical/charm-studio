import { useState } from 'react'
import { Routes, Route, useNavigate, useParams } from 'react-router-dom'
import NavigationBar from './components/NavigationBar'
import { Sidebar } from './components/Sidebar/Sidebar'
import { ImportView } from './components/ImportView/ImportView'
import { PipelineView } from './components/PipelineView/PipelineView'
import { useHistory } from './hooks/useHistory'
import { startPipeline } from './api/client'
import type { HistoryEntry, ImportSource } from './types'

function PipelineRoute({ history, replaceEntry, updateStatus, sidebarOpen, setSidebarOpen }: {
  history: ReturnType<typeof useHistory>['history']
  replaceEntry: ReturnType<typeof useHistory>['replaceEntry']
  updateStatus: ReturnType<typeof useHistory>['updateStatus']
  sidebarOpen: boolean
  setSidebarOpen: (v: boolean) => void
}) {
  const { pipelineId } = useParams<{ pipelineId: string }>()
  const navigate = useNavigate()

  const currentEntry = history.find(e => e.pipeline_id === pipelineId)

  async function handleRetry() {
    if (!currentEntry?.source) {
      navigate('/')
      return
    }
    const { pipeline_id } = await startPipeline(currentEntry.source)
    replaceEntry(pipelineId!, {
      ...currentEntry,
      pipeline_id: pipeline_id,
      status: 'pending',
      timestamp: new Date().toISOString(),
    })
    navigate(`/pipelines/${pipeline_id}`)
  }

  return (
    <>
      <NavigationBar sidebarOpen={sidebarOpen} onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} onNewImport={() => navigate('/')} />
      <div className={`l-application${!sidebarOpen ? ' sidebar-collapsed' : ''}`}>
        <Sidebar
          history={history}
          onNewImport={() => navigate('/')}
          onSelect={(entry) => navigate(`/pipelines/${entry.pipeline_id}`)}
          activePipelineId={pipelineId ?? null}
          collapsed={!sidebarOpen}
        />
        <main className="l-main" style={{ padding: '2rem 3rem' }}>
          <PipelineView
            pipelineId={pipelineId!}
            onStatusChange={(pid, status) => updateStatus(pid, status)}
            onRetry={handleRetry}
          />
        </main>
      </div>
    </>
  )
}

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { history, addEntry, updateStatus, replaceEntry } = useHistory()
  const navigate = useNavigate()

  function handlePipelineStarted(pipelineId: string, label: string, source: ImportSource) {
    const entry: HistoryEntry = {
      pipeline_id: pipelineId,
      label,
      timestamp: new Date().toISOString(),
      status: 'pending',
      source,
    }
    addEntry(entry)
    navigate(`/pipelines/${pipelineId}`)
  }

  function handleNewImport() {
    navigate('/')
  }

  function handleHistorySelect(entry: HistoryEntry) {
    navigate(`/pipelines/${entry.pipeline_id}`)
  }

  return (
    <Routes>
      <Route
        path="/"
        element={
          <>
            <NavigationBar sidebarOpen={sidebarOpen} onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} onNewImport={handleNewImport} />
            <div className={`l-application${!sidebarOpen ? ' sidebar-collapsed' : ''}`}>
              <Sidebar
                history={history}
                onNewImport={handleNewImport}
                onSelect={handleHistorySelect}
                activePipelineId={null}
                collapsed={!sidebarOpen}
              />
              <main className="l-main" style={{ padding: '2rem 3rem' }}>
                <ImportView onPipelineStarted={handlePipelineStarted} />
              </main>
            </div>
          </>
        }
      />
      <Route
        path="/pipelines/:pipelineId"
        element={
          <PipelineRoute
            history={history}
            replaceEntry={replaceEntry}
            updateStatus={updateStatus}
            sidebarOpen={sidebarOpen}
            setSidebarOpen={setSidebarOpen}
          />
        }
      />
    </Routes>
  )
}
