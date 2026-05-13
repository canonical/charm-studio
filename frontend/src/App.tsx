import { useState } from 'react'
import { Routes, Route, useNavigate, useParams } from 'react-router-dom'
import NavigationBar from './components/NavigationBar'
import { Sidebar } from './components/Sidebar/Sidebar'
import { ImportView } from './components/ImportView/ImportView'
import { PipelineView } from './components/PipelineView/PipelineView'
import { useHistory } from './hooks/useHistory'
import type { HistoryEntry } from './types'

function PipelineRoute({ history, updateStatus, sidebarOpen, setSidebarOpen }: {
  history: ReturnType<typeof useHistory>['history']
  updateStatus: ReturnType<typeof useHistory>['updateStatus']
  sidebarOpen: boolean
  setSidebarOpen: (v: boolean) => void
}) {
  const { pipelineId } = useParams<{ pipelineId: string }>()
  const navigate = useNavigate()

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
          />
        </main>
      </div>
    </>
  )
}

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { history, addEntry, updateStatus } = useHistory()
  const navigate = useNavigate()

  function handlePipelineStarted(pipelineId: string, label: string) {
    const entry: HistoryEntry = {
      pipeline_id: pipelineId,
      label,
      timestamp: new Date().toISOString(),
      status: 'pending',
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
            updateStatus={updateStatus}
            sidebarOpen={sidebarOpen}
            setSidebarOpen={setSidebarOpen}
          />
        }
      />
    </Routes>
  )
}
